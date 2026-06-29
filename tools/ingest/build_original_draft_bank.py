"""
Build original question bank from validated generated batch.

Usage:
    python tools/ingest/build_original_draft_bank.py <validated_batch.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_original_draft_bank.py \
        data/bank/cambridge_igcse/physics_0625/generated_batch_001.repaired.validated.json
"""

import sys
import json
from collections import defaultdict
from pathlib import Path

BANK_ID = "cambridge_igcse_physics_0625_original_question_bank_v0"
BOARD = "cambridge"
LEVEL = "igcse"
SUBJECT = "physics"
SYLLABUS_CODE = "0625"
ORIGIN = "quanta_aptus_generated"
COPYRIGHT_STATUS = "original_quanta_aptus_content"

STATUS_MAP = {
    "pass": "draft_ready",
    "needs_review": "draft_needs_review",
    # "fail" → skip
}


def build_item(raw, source_batch_id):
    validation = raw.get("validation", {})
    val_status = validation.get("status", "fail")
    bank_status = STATUS_MAP.get(val_status)  # None for "fail"

    if bank_status is None:
        return None

    return {
        "item_id": raw["generated_item_id"],
        "origin": ORIGIN,
        "source_batch_id": source_batch_id,
        "board": BOARD,
        "level": LEVEL,
        "subject": SUBJECT,
        "syllabus_code": SYLLABUS_CODE,
        "topic": raw.get("topic", ""),
        "subtopic": raw.get("subtopic", ""),
        "skill": raw.get("skill", ""),
        "question_type": raw.get("question_type", "mcq"),
        "stem": raw.get("stem", ""),
        "options": raw.get("options", {}),
        "correct_answer": raw.get("correct_answer", ""),
        "explanation": raw.get("explanation", ""),
        "common_misconception": raw.get("common_misconception", ""),
        "difficulty": raw.get("difficulty", ""),
        "quality": {
            "bank_status": bank_status,
            "validation_status": val_status,
            "validation_issues": validation.get("issues", []),
        },
        "copyright_status": COPYRIGHT_STATUS,
    }


def aggregate(items):
    by_topic = defaultdict(lambda: {"total": 0, "draft_ready": 0, "draft_needs_review": 0})
    by_skill = defaultdict(lambda: {"total": 0, "draft_ready": 0, "draft_needs_review": 0})
    by_difficulty = defaultdict(lambda: {"total": 0, "draft_ready": 0, "draft_needs_review": 0})

    for item in items:
        bank_status = item["quality"]["bank_status"]
        topic = item["topic"]
        skill = item["skill"]
        diff = item["difficulty"]

        for agg in (by_topic[topic], by_skill[skill], by_difficulty[diff]):
            agg["total"] += 1
            agg[bank_status] += 1

    return (
        {k: dict(v) for k, v in by_topic.items()},
        {k: dict(v) for k, v in by_skill.items()},
        {k: dict(v) for k, v in by_difficulty.items()},
    )


def build_markdown(bank_id, items, by_topic, by_skill, by_difficulty):
    draft_ready = sum(1 for i in items if i["quality"]["bank_status"] == "draft_ready")
    draft_needs_review = sum(1 for i in items if i["quality"]["bank_status"] == "draft_needs_review")
    total = len(items)

    lines = []
    lines.append("# Quanta Aptus Original Question Bank v0")
    lines.append("")
    lines.append(f"**Bank ID:** `{bank_id}`")
    lines.append("")
    lines.append("> **Note:** Not publish-ready until teacher review.")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| ------ | ----: |")
    lines.append(f"| Total items | {total} |")
    lines.append(f"| draft_ready | {draft_ready} |")
    lines.append(f"| draft_needs_review | {draft_needs_review} |")
    lines.append(f"| Origin | {ORIGIN} |")
    lines.append(f"| Copyright status | {COPYRIGHT_STATUS} |")
    lines.append("")

    lines.append("## Items by Topic")
    lines.append("")
    lines.append("| Topic | Total | draft_ready | draft_needs_review |")
    lines.append("| ----- | ----: | ----------: | -----------------: |")
    for topic, counts in sorted(by_topic.items()):
        lines.append(
            f"| {topic} | {counts['total']} | {counts['draft_ready']} | {counts['draft_needs_review']} |"
        )
    lines.append("")

    lines.append("## Items by Difficulty")
    lines.append("")
    lines.append("| Difficulty | Total | draft_ready | draft_needs_review |")
    lines.append("| ---------- | ----: | ----------: | -----------------: |")
    for diff in ("easy", "medium", "hard"):
        counts = by_difficulty.get(diff, {"total": 0, "draft_ready": 0, "draft_needs_review": 0})
        lines.append(
            f"| {diff} | {counts['total']} | {counts['draft_ready']} | {counts['draft_needs_review']} |"
        )
    lines.append("")

    lines.append("## Skills Covered")
    lines.append("")
    lines.append("| Skill | Total | draft_ready | draft_needs_review |")
    lines.append("| ----- | ----: | ----------: | -----------------: |")
    for skill, counts in sorted(by_skill.items()):
        lines.append(
            f"| {skill} | {counts['total']} | {counts['draft_ready']} | {counts['draft_needs_review']} |"
        )
    lines.append("")

    return "\n".join(lines)


def run(validated_path):
    data = json.loads(validated_path.read_text(encoding="utf-8"))

    source_batch_id = data.get("batch_id", "")
    raw_items = data.get("items", data.get("generated_items", []))

    items = []
    skipped = 0
    for raw in raw_items:
        item = build_item(raw, source_batch_id)
        if item is None:
            skipped += 1
        else:
            items.append(item)

    draft_ready_count = sum(1 for i in items if i["quality"]["bank_status"] == "draft_ready")
    draft_needs_review_count = sum(1 for i in items if i["quality"]["bank_status"] == "draft_needs_review")

    by_topic, by_skill, by_difficulty = aggregate(items)

    bank = {
        "bank_id": BANK_ID,
        "total_items": len(items),
        "items": items,
    }

    report = {
        "bank_id": BANK_ID,
        "total_items": len(items),
        "draft_ready_count": draft_ready_count,
        "draft_needs_review_count": draft_needs_review_count,
        "skipped_fail_count": skipped,
        "by_topic": by_topic,
        "by_skill": by_skill,
        "by_difficulty": by_difficulty,
    }

    md = build_markdown(BANK_ID, items, by_topic, by_skill, by_difficulty)

    out_dir = validated_path.parent
    bank_path   = out_dir / "original_question_bank_v0.json"
    report_path = out_dir / "original_question_bank_report.json"
    md_path     = out_dir / "original_question_bank_report.md"

    bank_path.write_text(json.dumps(bank, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(md, encoding="utf-8")

    print(f"bank_id                  : {BANK_ID}")
    print(f"total_items              : {len(items)}")
    print(f"draft_ready_count        : {draft_ready_count}")
    print(f"draft_needs_review_count : {draft_needs_review_count}")
    print(f"skipped_fail_count       : {skipped}")
    print(f"bank_json                : {bank_path}")
    print(f"report_json              : {report_path}")
    print(f"report_md                : {md_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <validated_batch.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    run(p)
