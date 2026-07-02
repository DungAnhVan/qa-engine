"""
Gate 70C -- Build AI Bank Package Candidate v1

Reads Gate 70B approved AI bank items and builds a package candidate.
Only approved items enter the package. Pending/revision/rejected items
are excluded.

Safety policy:
  - No AI API calls.
  - No Supabase writes.
  - No publish.
  - No active switch.
  - teacher_final_publish_required=True.
  - auto_publish_enabled=False.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate70c_ai_bank_package_candidate_v1.py

Input:
  data/ai/approved/gate70b_approved_ai_bank_items_v1.json

Output:
  data/ai/package_candidates/gate70c_ai_bank_package_candidate_v1.json
  data/diagnostics/gate70c_ai_bank_package_candidate_build_report_v1.json
"""

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

APPROVED_FILE = ROOT / "data" / "ai" / "approved" / "gate70b_approved_ai_bank_items_v1.json"
OUT_DIR       = ROOT / "data" / "ai" / "package_candidates"
OUT_FILE      = OUT_DIR / "gate70c_ai_bank_package_candidate_v1.json"
OUT_REPORT    = ROOT / "data" / "diagnostics" / "gate70c_ai_bank_package_candidate_build_report_v1.json"

ESTIMATED_TIME = {"question": 10, "worked_example": 8, "explanation": 6, "practice_set": 15}
STUDENT_INSTRUCTIONS = {
    "worked_example": "Study the following worked example carefully. Make sure you understand each step before moving on.",
    "question":       "Answer the following question in full. Show all working where required.",
    "explanation":    "Read the following explanation. Note the key concepts and definitions.",
    "practice_set":   "Complete the following practice problems. Show your working for each.",
}

print("Gate 70C -- Build AI Bank Package Candidate v1")
print("=" * 60)

issues: list[str] = []

if not APPROVED_FILE.exists():
    print(f"ERROR: Approved items file not found: {APPROVED_FILE.relative_to(ROOT)}")
    print("Run test_gate70b_ai_bank_review_v1.py first.")
    sys.exit(1)

approved_doc  = json.loads(APPROVED_FILE.read_text(encoding="utf-8"))
approved_items: list[dict] = approved_doc.get("items", [])

print(f"Approved items loaded: {len(approved_items)}")

# Filter: only items with approved status and approve decision
resources: list[dict] = []
skipped = 0
now = datetime.datetime.now(datetime.timezone.utc).isoformat()

for item in approved_items:
    status   = item.get("status", "")
    decision = item.get("decision", "")
    bank_id  = item.get("bank_id", "")

    if status != "approved_pending_package" or decision != "approve":
        skipped += 1
        issues.append(f"Skipped {bank_id}: status={status} decision={decision}")
        continue

    # Derive resource fields
    resource_type = item.get("resource_type", "question")
    topic         = item.get("topic", "")
    skill_name    = item.get("skill_name", "")

    title = f"{topic}: {skill_name[:60]}" if skill_name else topic

    teacher_notes = (
        f"AI-generated content. Approved by {item.get('reviewer_id', 'teacher')} "
        f"on {item.get('decided_at', now)[:10]}. "
        f"Review notes: {item.get('review_notes', '')}. "
        "Teacher must verify content accuracy before use with students."
    )

    resource = {
        "resource_id":    item["resource_id"],
        "bank_item_id":   item["bank_id"],
        "origin_batch_id": item.get("origin_batch_id", item.get("batch_id", "")),
        "provider":       item.get("provider", "mock"),
        "model":          item.get("model", "mock"),
        "resource_type":  resource_type,
        "title":          title,
        "topic":          topic,
        "subtopic":       item.get("subtopic", ""),
        "skill_name":     skill_name,
        "skill_type":     item.get("skill_type", ""),
        "difficulty":     item.get("difficulty", "medium"),
        "estimated_time_minutes": ESTIMATED_TIME.get(resource_type, 10),
        "student_prompt": item.get("student_prompt", ""),
        "student_instructions": STUDENT_INSTRUCTIONS.get(
            resource_type,
            "Answer the following question. Show your working.",
        ),
        "answer_key":      item.get("answer_key", ""),
        "marking_rubric":  item.get("marking_rubric", []),
        "teacher_notes":   teacher_notes,
        "safety_declaration": item.get("safety_declaration", {}),
        "provenance": {
            "origin":                   "ai_generated_question_bank",
            "gate":                     "70C",
            "gate70b_approved":         True,
            "teacher_review_required":  True,
            "no_raw_source_text_used":  True,
            "reviewer_id":              item.get("reviewer_id", "local_demo_teacher"),
            "approved_at":              item.get("decided_at", now),
        },
    }
    resources.append(resource)
    print(f"  + {resource['resource_id']}: {title[:70]}")

if skipped:
    for iss in issues:
        print(f"  ! {iss}")

print(f"\nResources in package: {len(resources)}  Skipped: {skipped}")

if len(resources) == 0:
    issues.append("No approved resources — apply at least one approve decision first (Gate 70B)")

package = {
    "package_candidate_id":  "quanta_aptus_gate70c_ai_bank_package_candidate_v1",
    "version":               "0.1.0",
    "status":                "draft_package_candidate",
    "source":                "gate70b_approved_ai_bank_items",
    "created_at":            now,
    "teacher_final_publish_required": True,
    "auto_publish_enabled":          False,
    "supabase_write_performed":       False,
    "ai_api_called":                  False,
    "resource_count":       len(resources),
    "student_payload_count": len(resources),
    "teacher_payload_count": len(resources),
    "issues":               issues,
    "resources":            resources,
}

OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE.write_text(json.dumps(package, indent=2), encoding="utf-8")
print(f"Package: {OUT_FILE.relative_to(ROOT)}")

status = "passed" if len(issues) == 0 and len(resources) > 0 else "needs_review"
report = {
    "gate":               "70C",
    "status":             status,
    "generated_at":       now,
    "approved_items_loaded": len(approved_items),
    "resources_included":    len(resources),
    "resources_skipped":     skipped,
    "teacher_final_publish_required": True,
    "auto_publish_enabled":          False,
    "supabase_write_performed":       False,
    "ai_api_called":                  False,
    "issues":             issues,
}
OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report: {OUT_REPORT.relative_to(ROOT)}")
print(f"Status: {status.upper()}")
sys.exit(0 if status == "passed" else 1)
