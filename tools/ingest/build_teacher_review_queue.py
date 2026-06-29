"""
Split original question bank into teacher review queue and publish candidates.

Usage:
    python tools/ingest/build_teacher_review_queue.py <original_question_bank_v0.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_teacher_review_queue.py \
        data/bank/cambridge_igcse/physics_0625/original_question_bank_v0.json
"""

import sys
import json
from collections import defaultdict
from pathlib import Path

QUEUE_ID = "cambridge_igcse_physics_0625_teacher_review_queue_v0"
CANDIDATE_BANK_ID = "cambridge_igcse_physics_0625_publish_candidate_bank_v0"

REVIEW_CHECKLIST = [
    "[ ] Scientifically correct",
    "[ ] One clear correct answer",
    "[ ] Distractors plausible",
    "[ ] Language appropriate for IGCSE",
    "[ ] No copyright/source issue",
    "[ ] Approve / Edit / Reject",
]


def build_queue_item(item):
    return {
        "item_id": item["item_id"],
        "topic": item["topic"],
        "subtopic": item["subtopic"],
        "skill": item["skill"],
        "difficulty": item["difficulty"],
        "stem": item["stem"],
        "options": item["options"],
        "correct_answer": item["correct_answer"],
        "explanation": item["explanation"],
        "common_misconception": item["common_misconception"],
        "validation_issues": item["quality"].get("validation_issues", []),
        "review_fields": {
            "teacher_decision": "pending",
            "teacher_notes": "",
            "suggested_action": "approve|edit|reject",
        },
    }


def build_markdown(review_items, total_original, candidate_count, review_count):
    lines = []
    lines.append("# Quanta Aptus Teacher Review Queue v0")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| ------ | ----: |")
    lines.append(f"| Total original items | {total_original} |")
    lines.append(f"| Publish candidates (draft_ready) | {candidate_count} |")
    lines.append(f"| Needs teacher review (draft_needs_review) | {review_count} |")
    lines.append("")

    # Group by topic
    by_topic = defaultdict(list)
    for item in review_items:
        by_topic[item["topic"]].append(item)

    for topic in sorted(by_topic.keys()):
        lines.append(f"## Topic: {topic}")
        lines.append("")

        for item in by_topic[topic]:
            lines.append(f"### {item['item_id']}")
            lines.append("")
            lines.append(f"**Skill:** {item['skill']}")
            lines.append(f"**Difficulty:** {item['difficulty']}")
            lines.append("")
            lines.append(f"**Stem:** {item['stem']}")
            lines.append("")
            lines.append("**Options:**")
            for key, text in item["options"].items():
                lines.append(f"- **{key}.** {text}")
            lines.append("")
            lines.append(f"**Correct answer:** {item['correct_answer']}")
            lines.append("")
            lines.append(f"**Explanation:** {item['explanation']}")
            lines.append("")
            lines.append(f"**Common misconception:** {item['common_misconception']}")
            lines.append("")

            issues = item["validation_issues"]
            if issues:
                lines.append("**Validation issues:**")
                for issue in issues:
                    lines.append(f"- {issue}")
                lines.append("")

            lines.append("**Review checklist:**")
            for check in REVIEW_CHECKLIST:
                lines.append(check)
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def run(bank_path):
    data = json.loads(bank_path.read_text(encoding="utf-8"))
    all_items = data.get("items", [])
    total_original = len(all_items)

    review_items_raw = [i for i in all_items if i["quality"]["bank_status"] == "draft_needs_review"]
    candidate_items  = [i for i in all_items if i["quality"]["bank_status"] == "draft_ready"]

    # Sanity check
    accounted = len(review_items_raw) + len(candidate_items)
    if accounted != total_original:
        print(
            f"WARNING: {total_original - accounted} items not accounted for "
            f"(unknown bank_status). Check input."
        )

    queue_items = [build_queue_item(i) for i in review_items_raw]

    queue_json = {
        "queue_id": QUEUE_ID,
        "total_items": len(queue_items),
        "items": queue_items,
    }

    candidate_json = {
        "bank_id": CANDIDATE_BANK_ID,
        "total_items": len(candidate_items),
        "items": candidate_items,
    }

    md = build_markdown(
        queue_items,
        total_original,
        len(candidate_items),
        len(queue_items),
    )

    out_dir = bank_path.parent
    queue_path     = out_dir / "teacher_review_queue_v0.json"
    queue_md_path  = out_dir / "teacher_review_queue_v0.md"
    candidate_path = out_dir / "publish_candidate_bank_v0.json"

    queue_path.write_text(json.dumps(queue_json, indent=2, ensure_ascii=False), encoding="utf-8")
    queue_md_path.write_text(md, encoding="utf-8")
    candidate_path.write_text(json.dumps(candidate_json, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"total_original_items   : {total_original}")
    print(f"publish_candidate_count: {len(candidate_items)}")
    print(f"review_queue_count     : {len(queue_items)}")
    print(f"review_queue_json      : {queue_path}")
    print(f"review_queue_md        : {queue_md_path}")
    print(f"publish_candidate_json : {candidate_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <original_question_bank_v0.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    run(p)
