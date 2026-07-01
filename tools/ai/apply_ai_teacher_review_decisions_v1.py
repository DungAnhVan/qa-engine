"""
Gate 69D -- Apply AI Teacher Review Decisions v1

Reads the teacher review queue and decisions file, applies each decision,
and routes resources to:
  - data/ai/approved/ai_approved_resource_candidates_v1.json
  - data/ai/revision/ai_revision_queue_v1.json
  - data/ai/rejected/ai_rejected_resources_v1.json

No Supabase writes. No AI API calls. Safety declarations are preserved.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\apply_ai_teacher_review_decisions_v1.py

Output:
  data/ai/approved/ai_approved_resource_candidates_v1.json
  data/ai/revision/ai_revision_queue_v1.json
  data/ai/rejected/ai_rejected_resources_v1.json
  data/diagnostics/ai_teacher_review_decisions_apply_report_v1.json
"""

import json
import sys
import datetime
from pathlib import Path

ROOT         = Path(__file__).resolve().parents[2]
REVIEW_DIR   = ROOT / "data" / "ai" / "review"
QUEUE_FILE   = REVIEW_DIR / "ai_teacher_review_queue_v1.json"
DECISION_FILE = REVIEW_DIR / "ai_teacher_review_decisions_v1.json"

APPROVED_DIR  = ROOT / "data" / "ai" / "approved"
REVISION_DIR  = ROOT / "data" / "ai" / "revision"
REJECTED_DIR  = ROOT / "data" / "ai" / "rejected"

APPROVED_FILE = APPROVED_DIR / "ai_approved_resource_candidates_v1.json"
REVISION_FILE = REVISION_DIR / "ai_revision_queue_v1.json"
REJECTED_FILE = REJECTED_DIR / "ai_rejected_resources_v1.json"

REPORT_FILE   = ROOT / "data" / "diagnostics" / "ai_teacher_review_decisions_apply_report_v1.json"

VALID_DECISIONS = {"approve", "needs_revision", "reject"}


def load_json(path: Path, label: str) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, f"{label} not found: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, f"{label} parse error: {exc}"


def apply_decisions() -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    issues: list[str] = []

    # ── Load queue ─────────────────────────────────────────────────────────────
    queue, err = load_json(QUEUE_FILE, "Review queue")
    if err:
        return {"status": "failed", "error": err, "generated_at": now}

    # ── Load decisions ─────────────────────────────────────────────────────────
    decisions_data, err = load_json(DECISION_FILE, "Decisions file")
    if err:
        return {"status": "failed", "error": err, "generated_at": now}

    queue_items: list[dict] = queue.get("items", [])
    raw_decisions: list[dict] = decisions_data.get("decisions", [])

    # Index decisions by review_item_id (last decision wins for duplicates)
    decision_map: dict[str, dict] = {}
    for d in raw_decisions:
        rid = d.get("review_item_id")
        dec = d.get("decision", "")
        if not rid:
            issues.append(f"Decision missing review_item_id: {d}")
            continue
        if dec not in VALID_DECISIONS:
            issues.append(f"Invalid decision value {dec!r} for {rid}")
            continue
        decision_map[rid] = d

    # ── Apply decisions ────────────────────────────────────────────────────────
    approved:       list[dict] = []
    needs_revision: list[dict] = []
    rejected:       list[dict] = []
    pending:        list[dict] = []

    for item in queue_items:
        item_id = item.get("review_item_id")
        if item_id in decision_map:
            d = decision_map[item_id]
            decision = d["decision"]
            applied_item = {
                **item,
                "review_status":   decision,
                "review_decision": decision,
                "review_notes":    d.get("review_notes"),
                "reviewer_id":     d.get("reviewer_id", "local_demo_teacher"),
                "decision_at":     d.get("created_at", now),
            }
            if decision == "approve":
                approved.append(applied_item)
            elif decision == "needs_revision":
                needs_revision.append(applied_item)
            elif decision == "reject":
                rejected.append(applied_item)
        else:
            pending.append({**item, "review_status": "pending"})

    # ── Write outputs ──────────────────────────────────────────────────────────
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    REVISION_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    approved_bank = {
        "bank_id":                  "quanta_aptus_ai_approved_resource_candidates_v1",
        "version":                  "0.1.0",
        "generated_at":             now,
        "source_queue":             str(QUEUE_FILE.relative_to(ROOT)),
        "approved_count":           len(approved),
        "auto_publish_enabled":     False,
        "supabase_write_performed": False,
        "teacher_approval_required": True,
        "resources":                approved,
    }
    APPROVED_FILE.write_text(json.dumps(approved_bank, indent=2), encoding="utf-8")

    revision_queue = {
        "queue_id":                 "quanta_aptus_ai_revision_queue_v1",
        "version":                  "0.1.0",
        "generated_at":             now,
        "source_queue":             str(QUEUE_FILE.relative_to(ROOT)),
        "needs_revision_count":     len(needs_revision),
        "auto_publish_enabled":     False,
        "supabase_write_performed": False,
        "items":                    needs_revision,
    }
    REVISION_FILE.write_text(json.dumps(revision_queue, indent=2), encoding="utf-8")

    rejected_store = {
        "store_id":                 "quanta_aptus_ai_rejected_resources_v1",
        "version":                  "0.1.0",
        "generated_at":             now,
        "source_queue":             str(QUEUE_FILE.relative_to(ROOT)),
        "rejected_count":           len(rejected),
        "auto_publish_enabled":     False,
        "supabase_write_performed": False,
        "resources":                rejected,
    }
    REJECTED_FILE.write_text(json.dumps(rejected_store, indent=2), encoding="utf-8")

    status = "failed" if issues else "passed"

    return {
        "status":                   status,
        "queue_item_count":         len(queue_items),
        "decision_count":           len(decision_map),
        "approved_count":           len(approved),
        "needs_revision_count":     len(needs_revision),
        "rejected_count":           len(rejected),
        "pending_count":            len(pending),
        "auto_publish_enabled":     False,
        "supabase_write_performed": False,
        "teacher_approval_required": True,
        "issues":                   issues,
        "generated_at":             now,
    }


def main():
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    print("Gate 69D -- Apply AI Teacher Review Decisions v1")
    print("-" * 55)

    result = apply_decisions()

    sym = lambda ok: "+" if ok else "!"
    print(f"  [{sym(result['status'] == 'passed')}] status:                {result.get('status')}")
    print(f"  [{sym(True)}] queue_item_count:      {result.get('queue_item_count', 0)}")
    print(f"  [{sym(True)}] decision_count:        {result.get('decision_count', 0)}")
    print(f"  [{sym(result.get('approved_count', 0) >= 0)}] approved_count:        {result.get('approved_count', 0)}")
    print(f"  [{sym(result.get('needs_revision_count', 0) >= 0)}] needs_revision_count:  {result.get('needs_revision_count', 0)}")
    print(f"  [{sym(result.get('rejected_count', 0) >= 0)}] rejected_count:        {result.get('rejected_count', 0)}")
    print(f"  [{sym(result.get('pending_count', 0) == 0)}] pending_count:         {result.get('pending_count', 0)}")
    print(f"  [+] auto_publish_enabled:     {result.get('auto_publish_enabled')}")
    print(f"  [+] supabase_write_performed: {result.get('supabase_write_performed')}")

    if result.get("issues"):
        print("\n  Issues:")
        for iss in result["issues"]:
            print(f"    ! {iss}")

    print(f"\n  Approved bank:  {APPROVED_FILE}")
    print(f"  Revision queue: {REVISION_FILE}")
    print(f"  Rejected store: {REJECTED_FILE}")

    REPORT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nStatus: {result['status']}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
