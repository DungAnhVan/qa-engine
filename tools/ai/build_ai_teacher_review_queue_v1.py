"""
Gate 69D -- Build AI Teacher Review Queue v1

Reads a generated AI batch, validates it, and creates a review queue file
for teacher decision-making (approve / needs_revision / reject).

No Supabase writes. No AI API calls. No raw Cambridge text.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_teacher_review_queue_v1.py \\
      data\\ai\\generated_batches\\gate69c_sample_generated_batch_v1.json

Output:
  data/ai/review/ai_teacher_review_queue_v1.json
  data/diagnostics/ai_teacher_review_queue_build_report_v1.json
"""

import json
import sys
import uuid
import datetime
import argparse
from pathlib import Path

ROOT       = Path(__file__).resolve().parents[2]
REVIEW_DIR = ROOT / "data" / "ai" / "review"
OUTPUT_FILE = REVIEW_DIR / "ai_teacher_review_queue_v1.json"
REPORT_FILE = ROOT / "data" / "diagnostics" / "ai_teacher_review_queue_build_report_v1.json"

sys.path.insert(0, str(ROOT))
from tools.ai.validate_ai_generated_batch_v1 import validate_batch


def build_review_queue(batch_path: Path) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Validate batch
    validation = validate_batch(batch_path)
    if not validation["valid"]:
        return {
            "ok": False,
            "error": "Batch validation failed",
            "issues": validation.get("issues", []),
            "generated_at": now,
        }

    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    resources = batch.get("resources", [])

    items = []
    for resource in resources:
        item = {
            "review_item_id":    f"review_{resource['resource_id']}",
            "resource_id":       resource["resource_id"],
            "resource_type":     resource.get("resource_type", "question"),
            "title":             resource.get("title", ""),
            "topic":             resource.get("topic", ""),
            "skill_name":        resource.get("skill_name", ""),
            "skill_type":        resource.get("skill_type", ""),
            "difficulty":        resource.get("difficulty", ""),
            "student_prompt":    resource.get("student_prompt", ""),
            "answer_key":        resource.get("answer_key", ""),
            "marking_rubric":    resource.get("marking_rubric", []),
            "teacher_notes":     resource.get("teacher_notes", ""),
            "safety_declaration": resource.get("safety_declaration", {}),
            "review_status":     "pending",
            "review_decision":   None,
            "review_notes":      None,
        }
        items.append(item)

    queue = {
        "queue_id":     "quanta_aptus_ai_teacher_review_queue_v1",
        "version":      "0.1.0",
        "source_batch": str(batch_path.relative_to(ROOT) if batch_path.is_absolute() else batch_path),
        "batch_id":     batch.get("batch_id", "unknown"),
        "created_at":   now,
        "status":       "pending_review",
        "item_count":   len(items),
        "items":        items,
    }
    return {"ok": True, "queue": queue, "validation": validation, "generated_at": now}


def main():
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description="Gate 69D -- Build AI Teacher Review Queue")
    parser.add_argument("batch_file", help="Path to generated AI batch JSON")
    args = parser.parse_args()

    batch_path = Path(args.batch_file)
    if not batch_path.is_absolute():
        batch_path = ROOT / batch_path

    print("Gate 69D -- Build AI Teacher Review Queue v1")
    print(f"Batch: {batch_path}")
    print("-" * 55)

    result = build_review_queue(batch_path)
    now = result["generated_at"]

    if not result["ok"]:
        print(f"  ! FAILED: {result['error']}")
        for iss in result.get("issues", []):
            print(f"    ! {iss}")
        report = {
            "status": "failed",
            "error": result["error"],
            "issues": result.get("issues", []),
            "generated_at": now,
        }
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport: {REPORT_FILE}")
        sys.exit(1)

    queue     = result["queue"]
    val       = result["validation"]

    print(f"  + batch_id:      {queue['batch_id']}")
    print(f"  + item_count:    {queue['item_count']}")
    print(f"  + validated:     {val['valid']} ({val['resources_valid']}/{val['resource_count']} resources)")
    print(f"  + status:        {queue['status']}")

    OUTPUT_FILE.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    print(f"\nReview queue: {OUTPUT_FILE}")

    report = {
        "status":              "passed",
        "queue_id":            queue["queue_id"],
        "source_batch":        queue["source_batch"],
        "item_count":          queue["item_count"],
        "batch_valid":         val["valid"],
        "resources_valid":     val["resources_valid"],
        "auto_publish_enabled":   False,
        "supabase_write_performed": False,
        "teacher_approval_required": True,
        "generated_at":        now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report:       {REPORT_FILE}")


if __name__ == "__main__":
    main()
