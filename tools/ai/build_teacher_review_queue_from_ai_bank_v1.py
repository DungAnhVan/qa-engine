"""
Gate 70A -- Build Teacher Review Queue from AI Bank v1

Reads the AI question bank and produces a teacher review queue JSON —
sorted by topic and difficulty, with only fields needed for review
(no internal metadata, no secrets).

The queue shows: bank_id, topic, subtopic, skill_name, difficulty,
resource_type, generated_text, provider, dry_run flag.

Teachers must approve each item before it can be published.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_teacher_review_queue_from_ai_bank_v1.py

Output:
  data/ai/teacher_review/ai_teacher_review_queue_v1.json
"""

import json
import sys
from pathlib import Path
import datetime

ROOT      = Path(__file__).resolve().parents[2]
BANK_FILE = ROOT / "data" / "ai" / "question_bank" / "ai_generated_question_bank_v1.json"
OUT_DIR   = ROOT / "data" / "ai" / "teacher_review"
OUT_FILE  = OUT_DIR / "ai_teacher_review_queue_v1.json"

DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2, "very_hard": 3}

print("Gate 70A -- Build Teacher Review Queue v1")
print("=" * 60)

if not BANK_FILE.exists():
    print(f"Bank file not found: {BANK_FILE.relative_to(ROOT)}")
    print("Run run_live_ai_generation_to_bank_v1.py first.")
    out = {
        "schema_version": "gate70a_v1",
        "generated_at":   datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "queue_count":    0,
        "status":         "empty",
        "message":        "No bank items — run generation first",
        "queue":          [],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, indent=2), encoding="utf-8")
    sys.exit(0)

bank  = json.loads(BANK_FILE.read_text(encoding="utf-8"))
items = bank.get("items", [])

# Filter to pending review
pending = [e for e in items if e.get("status") == "generated_needs_teacher_review"]

# Sort by topic then difficulty then bank_id
pending.sort(key=lambda e: (
    e.get("topic", ""),
    DIFFICULTY_ORDER.get(e.get("difficulty", "medium"), 1),
    e.get("bank_id", ""),
))

# Build queue entries (safe fields only, no secrets)
queue: list[dict] = []
for item in pending:
    queue.append({
        "bank_id":          item["bank_id"],
        "batch_id":         item.get("batch_id"),
        "topic":            item.get("topic"),
        "subtopic":         item.get("subtopic"),
        "skill_name":       item.get("skill_name"),
        "skill_type":       item.get("skill_type"),
        "difficulty":       item.get("difficulty"),
        "resource_type":    item.get("resource_type"),
        "learning_objective": item.get("learning_objective"),
        "generated_text":   item.get("generated_text"),
        "provider":         item.get("provider"),
        "model":            item.get("model"),
        "dry_run":          item.get("dry_run"),
        "generated_at":     item.get("generated_at"),
        "review_status":    "pending",
        "teacher_decision": None,
        "teacher_notes":    None,
        "approval_required": True,
        "auto_publish_enabled": False,
    })

print(f"Bank items:    {len(items)}")
print(f"Pending review: {len(pending)}")
print(f"Queue entries:  {len(queue)}")

out = {
    "schema_version":    "gate70a_v1",
    "generated_at":      datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "bank_total":        len(items),
    "queue_count":       len(queue),
    "status":            "ready_for_review" if queue else "empty",
    "teacher_review_required":  True,
    "auto_publish_enabled":     False,
    "approval_required_before_publish": True,
    "queue":             queue,
}

OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE.write_text(json.dumps(out, indent=2), encoding="utf-8")

print(f"Output: {OUT_FILE.relative_to(ROOT)}")
print("Done. Teachers must review and approve each item before publication.")
