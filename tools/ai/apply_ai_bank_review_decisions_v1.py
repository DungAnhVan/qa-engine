"""
Gate 70B -- Apply AI Bank Review Decisions v1

Reads the AI question bank, review queue, and teacher decisions.
Applies decisions to produce approved, revision, rejected, and pending outputs.

Safety policy:
  - No AI API calls.
  - No Supabase writes.
  - No publish.
  - Approved items retain teacher_review_required=True.
  - auto_publish_enabled=False on all outputs.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\apply_ai_bank_review_decisions_v1.py

Output:
  data/ai/approved/gate70b_approved_ai_bank_items_v1.json
  data/ai/revision/gate70b_ai_bank_revision_items_v1.json
  data/ai/rejected/gate70b_rejected_ai_bank_items_v1.json
  data/ai/review/gate70b_pending_ai_bank_review_items_v1.json
  data/diagnostics/gate70b_ai_bank_review_apply_report_v1.json
"""

import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BANK_FILE      = ROOT / "data" / "ai" / "question_bank" / "ai_generated_question_bank_v1.json"
# Gate 70A queue — try both paths
QUEUE_FILE     = ROOT / "data" / "ai" / "teacher_review" / "ai_teacher_review_queue_v1.json"
QUEUE_ALT      = ROOT / "data" / "ai" / "review" / "gate70a_ai_bank_teacher_review_queue_v1.json"
DECISIONS_FILE = ROOT / "data" / "ai" / "review" / "gate70b_ai_bank_review_decisions_v1.json"

OUT_APPROVED  = ROOT / "data" / "ai" / "approved" / "gate70b_approved_ai_bank_items_v1.json"
OUT_REVISION  = ROOT / "data" / "ai" / "revision" / "gate70b_ai_bank_revision_items_v1.json"
OUT_REJECTED  = ROOT / "data" / "ai" / "rejected" / "gate70b_rejected_ai_bank_items_v1.json"
OUT_PENDING   = ROOT / "data" / "ai" / "review"   / "gate70b_pending_ai_bank_review_items_v1.json"
OUT_REPORT    = ROOT / "data" / "diagnostics" / "gate70b_ai_bank_review_apply_report_v1.json"

VALID_DECISIONS = {"approve", "needs_revision", "reject"}

print("Gate 70B -- Apply AI Bank Review Decisions v1")
print("=" * 60)

# ---------------------------------------------------------------------------
# Load inputs
# ---------------------------------------------------------------------------

def load_json(path: Path, alt: Path | None = None) -> dict | list | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if alt and alt.exists():
        return json.loads(alt.read_text(encoding="utf-8"))
    return None


bank_doc      = load_json(BANK_FILE)
queue_doc     = load_json(QUEUE_FILE, QUEUE_ALT)
decisions_doc = load_json(DECISIONS_FILE)

issues: list[str] = []

if bank_doc is None:
    issues.append("Bank file not found — run run_live_ai_generation_to_bank_v1.py first")
if queue_doc is None:
    issues.append("Review queue not found — run build_teacher_review_queue_from_ai_bank_v1.py first")
if decisions_doc is None:
    issues.append("Decisions file not found — expected gate70b_ai_bank_review_decisions_v1.json")

if issues:
    for iss in issues:
        print(f"  ! {iss}")
    report = {
        "gate": "70B", "status": "failed",
        "bank_item_count": 0, "decision_count": 0,
        "approved_count": 0, "needs_revision_count": 0,
        "rejected_count": 0, "pending_count": 0,
        "auto_publish_enabled": False, "supabase_write_performed": False, "ai_api_called": False,
        "issues": issues,
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    sys.exit(1)

bank_items: list[dict] = (bank_doc or {}).get("items", [])  # type: ignore[union-attr]
queue_items: list[dict] = (queue_doc or {}).get("queue", [])  # type: ignore[union-attr]
decisions: list[dict]  = (decisions_doc or {}).get("decisions", [])  # type: ignore[union-attr]

print(f"Bank items:  {len(bank_items)}")
print(f"Queue items: {len(queue_items)}")
print(f"Decisions:   {len(decisions)}")

# Index decisions by bank_item_id (last decision wins if duplicates)
decision_map: dict[str, dict] = {}
for d in decisions:
    bid = d.get("bank_item_id") or d.get("bank_id")
    if bid:
        decision_map[bid] = d

print(f"Unique decision targets: {len(decision_map)}")

# ---------------------------------------------------------------------------
# Derive structured fields from bank item
# ---------------------------------------------------------------------------

DRY_RUN_RE = re.compile(r'\s*\[DRY-RUN:.*?\]\s*$', re.DOTALL)


def _resource_id(bank_id: str) -> str:
    h = hashlib.md5(bank_id.encode()).hexdigest()[:8]
    return f"ai_res_70b_{h}"


def _review_item_id(bank_id: str) -> str:
    return f"review_{bank_id}"


def _student_prompt(generated_text: str) -> str:
    return DRY_RUN_RE.sub("", generated_text).strip()


def _answer_key(skill_name: str, topic: str) -> str:
    return (
        f"[Teacher review required] "
        f"Worked answer for topic: {topic}. "
        f"Skill: {skill_name}. "
        "AI-generated content — teacher must verify correctness and originality before use."
    )


def _marking_rubric(difficulty: str) -> list[dict]:
    marks = {"easy": 2, "medium": 3, "hard": 4, "very_hard": 5}.get(difficulty, 3)
    rubric = [
        {"criterion": "Correct method demonstrated", "marks": 1,
         "guidance": "Award for correct approach. Teacher to verify."},
    ]
    if marks >= 2:
        rubric.append({"criterion": "Clear working shown", "marks": 1,
                       "guidance": "Award for clear working. Teacher to verify."})
    if marks >= 3:
        rubric.append({"criterion": "Correct answer with appropriate units/form", "marks": 1,
                       "guidance": "Award for correct final answer. Teacher to verify."})
    return rubric


def _safety_declaration(safety: dict) -> dict:
    return {
        "no_raw_source_text":    safety.get("no_raw_source_text", True),
        "no_cambridge_pdf_text": safety.get("no_cambridge_pdf_text", True),
        "no_mark_scheme_text":   safety.get("no_mark_scheme_text", True),
        "metadata_only_prompt":  safety.get("metadata_only_prompt", True),
        "original_content":      True,
        "teacher_review_required": True,
    }


# ---------------------------------------------------------------------------
# Apply decisions
# ---------------------------------------------------------------------------

now = datetime.datetime.now(datetime.timezone.utc).isoformat()

approved:  list[dict] = []
revision:  list[dict] = []
rejected:  list[dict] = []
pending:   list[dict] = []

for item in bank_items:
    bank_id = item["bank_id"]
    dec     = decision_map.get(bank_id)

    resource_id    = _resource_id(bank_id)
    review_item_id = _review_item_id(bank_id)
    student_prompt = _student_prompt(item.get("generated_text", ""))
    answer_key     = _answer_key(item.get("skill_name", ""), item.get("topic", ""))
    marking_rubric = _marking_rubric(item.get("difficulty", "medium"))
    safety_decl    = _safety_declaration(item.get("safety", {}))

    base = {
        "bank_id":               bank_id,
        "resource_id":           resource_id,
        "review_item_id":        review_item_id,
        "request_id":            item.get("request_id", ""),
        "batch_id":              item.get("batch_id", ""),
        "origin_batch_id":       item.get("batch_id", ""),
        "subject_slug":          item.get("subject_slug", ""),
        "syllabus_code":         item.get("syllabus_code", ""),
        "topic":                 item.get("topic", ""),
        "subtopic":              item.get("subtopic", ""),
        "skill_name":            item.get("skill_name", ""),
        "skill_type":            item.get("skill_type", ""),
        "difficulty":            item.get("difficulty", "medium"),
        "resource_type":         item.get("resource_type", "worked_example"),
        "learning_objective":    item.get("learning_objective", ""),
        "student_prompt":        student_prompt,
        "answer_key":            answer_key,
        "marking_rubric":        marking_rubric,
        "safety_declaration":    safety_decl,
        "provider":              item.get("provider", "mock"),
        "model":                 item.get("model", "mock"),
        "dry_run":               item.get("dry_run", True),
        "generated_at":          item.get("generated_at"),
        "teacher_review_required":  True,
        "auto_publish_enabled":     False,
        "supabase_write_performed": False,
    }

    if dec is None:
        pending.append({**base, "status": "pending_review", "decision": None})
        continue

    decision_val = dec.get("decision", "")
    if decision_val not in VALID_DECISIONS:
        issues.append(f"Unknown decision {decision_val!r} for {bank_id}")
        pending.append({**base, "status": "pending_review", "decision": None})
        continue

    enriched = {
        **base,
        "decision":    decision_val,
        "reviewer_id": dec.get("reviewer_id", "local_demo_teacher"),
        "review_notes": dec.get("review_notes", ""),
        "decided_at":  dec.get("created_at", now),
    }

    if decision_val == "approve":
        approved.append({**enriched, "status": "approved_pending_package"})
    elif decision_val == "needs_revision":
        revision.append({**enriched, "status": "needs_revision"})
    elif decision_val == "reject":
        rejected.append({**enriched, "status": "rejected"})

print(f"\nApplied decisions:")
print(f"  Approved:      {len(approved)}")
print(f"  Needs revision: {len(revision)}")
print(f"  Rejected:       {len(rejected)}")
print(f"  Pending:        {len(pending)}")

# ---------------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------------

OUT_APPROVED.parent.mkdir(parents=True, exist_ok=True)
OUT_REVISION.parent.mkdir(parents=True, exist_ok=True)
OUT_REJECTED.parent.mkdir(parents=True, exist_ok=True)
OUT_PENDING.parent.mkdir(parents=True, exist_ok=True)

OUT_APPROVED.write_text(json.dumps({
    "approved_file_id": "quanta_aptus_gate70b_approved_ai_bank_items_v1",
    "version":          "0.1.0",
    "created_at":       now,
    "status":           "approved_for_package_candidate",
    "item_count":       len(approved),
    "teacher_review_required":  True,
    "auto_publish_enabled":     False,
    "supabase_write_performed": False,
    "ai_api_called":            False,
    "items":            approved,
}, indent=2), encoding="utf-8")

OUT_REVISION.write_text(json.dumps({
    "revision_file_id": "quanta_aptus_gate70b_ai_bank_revision_items_v1",
    "version":    "0.1.0",
    "created_at": now,
    "item_count": len(revision),
    "items":      revision,
}, indent=2), encoding="utf-8")

OUT_REJECTED.write_text(json.dumps({
    "rejected_file_id": "quanta_aptus_gate70b_rejected_ai_bank_items_v1",
    "version":    "0.1.0",
    "created_at": now,
    "item_count": len(rejected),
    "items":      rejected,
}, indent=2), encoding="utf-8")

OUT_PENDING.write_text(json.dumps({
    "pending_file_id": "quanta_aptus_gate70b_pending_ai_bank_review_items_v1",
    "version":    "0.1.0",
    "created_at": now,
    "item_count": len(pending),
    "items":      pending,
}, indent=2), encoding="utf-8")

print(f"\nApproved:  {OUT_APPROVED.relative_to(ROOT)}")
print(f"Revision:  {OUT_REVISION.relative_to(ROOT)}")
print(f"Rejected:  {OUT_REJECTED.relative_to(ROOT)}")
print(f"Pending:   {OUT_PENDING.relative_to(ROOT)}")

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

status = "passed" if len(issues) == 0 else "needs_review"
report = {
    "gate":                "70B",
    "status":              status,
    "generated_at":        now,
    "bank_item_count":     len(bank_items),
    "decision_count":      len(decisions),
    "approved_count":      len(approved),
    "needs_revision_count": len(revision),
    "rejected_count":      len(rejected),
    "pending_count":       len(pending),
    "auto_publish_enabled":     False,
    "supabase_write_performed": False,
    "ai_api_called":            False,
    "issues":              issues,
}
OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report:    {OUT_REPORT.relative_to(ROOT)}")
print(f"\nStatus: {status.upper()}")
sys.exit(0 if status == "passed" else 1)
