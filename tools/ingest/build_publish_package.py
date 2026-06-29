"""
Build a publish package from a demo quiz JSON.

Usage:
    python tools/ingest/build_publish_package.py <quiz_demo_NNN.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_publish_package.py \
        data/publish/cambridge_igcse/physics_0625/demo_quiz_001/quiz_demo_001.json
"""

import sys
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_ID = "cambridge_igcse_physics_0625_publish_package_v0"
PACKAGE_VERSION = "0.1.0"

REQUIRED_QUIZ_FIELDS = ["quiz_id", "title", "board", "level", "subject", "syllabus_code", "items", "question_count"]
REQUIRED_ITEM_FIELDS = [
    "quiz_question_number", "item_id", "topic", "subtopic", "skill",
    "difficulty", "stem", "options", "correct_answer", "explanation", "common_misconception",
]

PLACEHOLDER_STRINGS = [
    "Original question",
    "option alpha",
    "option beta",
    "option gamma",
    "option delta",
    "core principle",
    "Students often confuse the key terms",
]

SOURCE_PIPELINE = [
    "markitdown_ingest",
    "segment_mcq",
    "normalize_questions",
    "classify_topics",
    "parse_mcq_mark_scheme",
    "enrich_questions",
    "reconcile_options",
    "build_internal_bank",
    "build_skill_index",
    "build_generation_targets",
    "build_authoring_batch",
    "repair_generated_target_ids",
    "validate_authoring_batch",
    "build_original_draft_bank",
    "build_teacher_review_queue",
    "build_demo_quiz",
    "build_publish_package",
]


def validate_quiz(quiz):
    errors = []

    for field in REQUIRED_QUIZ_FIELDS:
        if not quiz.get(field):
            errors.append(f"Missing or empty field: {field}")

    items = quiz.get("items", [])
    if len(items) != quiz.get("question_count", -1):
        errors.append(
            f"item count ({len(items)}) does not match question_count ({quiz.get('question_count')})"
        )

    for i, item in enumerate(items, 1):
        for field in REQUIRED_ITEM_FIELDS:
            if field not in item or item[field] == "" or item[field] is None:
                errors.append(f"Item {i}: missing or empty field '{field}'")
        options = item.get("options", {})
        for opt in ("A", "B", "C", "D"):
            if opt not in options or not options[opt]:
                errors.append(f"Item {i}: missing or empty option '{opt}'")

    return errors


def check_placeholders(items):
    hits = []
    for item in items:
        texts = [item.get("stem", "")]
        texts += list(item.get("options", {}).values())
        texts.append(item.get("explanation", ""))
        texts.append(item.get("common_misconception", ""))

        for text in texts:
            for ph in PLACEHOLDER_STRINGS:
                if ph.lower() in text.lower():
                    hits.append(
                        f"Item {item.get('quiz_question_number', '?')} "
                        f"(id={item.get('item_id', '?')}): found placeholder '{ph}'"
                    )
                    break

    return hits


def aggregate(items):
    topics = defaultdict(int)
    skills = defaultdict(int)
    difficulties = defaultdict(int)
    for item in items:
        topics[item["topic"]] += 1
        skills[item["skill"]] += 1
        difficulties[item["difficulty"]] += 1
    return dict(topics), dict(skills), dict(difficulties)


def build_package(quiz, quiz_path):
    items = quiz["items"]
    topics, skills, difficulties = aggregate(items)

    quiz_items_public = []
    for item in items:
        quiz_items_public.append({
            "quiz_question_number": item["quiz_question_number"],
            "item_id": item["item_id"],
            "topic": item["topic"],
            "subtopic": item["subtopic"],
            "skill": item["skill"],
            "difficulty": item["difficulty"],
            "question_type": "mcq",
            "stem": item["stem"],
            "options": item["options"],
        })

    answer_key = []
    for item in items:
        answer_key.append({
            "quiz_question_number": item["quiz_question_number"],
            "item_id": item["item_id"],
            "correct_answer": item["correct_answer"],
            "explanation": item["explanation"],
            "common_misconception": item["common_misconception"],
        })

    return {
        "package_id": PACKAGE_ID,
        "version": PACKAGE_VERSION,
        "status": "internal_demo",
        "content_origin": "quanta_aptus_original_generated",
        "copyright_status": "original_quanta_aptus_content",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "board": quiz["board"],
        "level": quiz["level"],
        "subject": quiz["subject"],
        "syllabus_code": quiz["syllabus_code"],
        "source": {
            "quiz_id": quiz["quiz_id"],
            "source_quiz_file": str(quiz_path),
            "source_pipeline": SOURCE_PIPELINE,
        },
        "quiz": {
            "quiz_id": quiz["quiz_id"],
            "title": quiz["title"],
            "description": quiz.get("description", ""),
            "question_count": quiz["question_count"],
            "estimated_time_minutes": quiz.get("estimated_time_minutes", 0),
            "items": quiz_items_public,
        },
        "answer_key": answer_key,
        "learning_metadata": {
            "topics": topics,
            "skills": skills,
            "difficulties": difficulties,
        },
    }


def build_report(package, out_pkg_path, out_report_path, out_manifest_path):
    meta = package["learning_metadata"]
    return {
        "package_id": package["package_id"],
        "source_quiz_id": package["source"]["quiz_id"],
        "status": "passed",
        "question_count": package["quiz"]["question_count"],
        "answer_key_count": len(package["answer_key"]),
        "topics": meta["topics"],
        "skills": meta["skills"],
        "difficulties": meta["difficulties"],
        "placeholder_check": "passed",
        "output_files": {
            "publish_package": str(out_pkg_path),
            "report": str(out_report_path),
            "manifest": str(out_manifest_path),
        },
    }


def build_manifest_md(package, report):
    meta = package["learning_metadata"]
    lines = []
    lines.append("# Quanta Aptus Publish Package v0")
    lines.append("")
    lines.append(f"**Package ID:** `{package['package_id']}`")
    lines.append(f"**Version:** {package['version']}")
    lines.append(f"**Status:** {package['status']}")
    lines.append(f"**Created:** {package['created_at']}")
    lines.append("")
    lines.append(f"**Source quiz:** `{package['source']['quiz_id']}`")
    lines.append(f"**Question count:** {package['quiz']['question_count']}")
    lines.append("")
    lines.append("## Topics")
    lines.append("")
    for topic, count in sorted(meta["topics"].items()):
        lines.append(f"- {topic}: {count}")
    lines.append("")
    lines.append("## Skills")
    lines.append("")
    for skill, count in sorted(meta["skills"].items()):
        lines.append(f"- {skill}: {count}")
    lines.append("")
    lines.append("## Difficulties")
    lines.append("")
    for diff in ("easy", "medium", "hard"):
        count = meta["difficulties"].get(diff, 0)
        lines.append(f"- {diff}: {count}")
    lines.append("")
    lines.append("## Output")
    lines.append("")
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "> This package contains original Quanta Aptus generated questions "
        "for internal demo use."
    )
    lines.append("")
    return "\n".join(lines)


def run(quiz_path):
    quiz = json.loads(quiz_path.read_text(encoding="utf-8"))

    # Structural validation
    errors = validate_quiz(quiz)
    if errors:
        for e in errors:
            print(f"VALIDATION ERROR: {e}")
        sys.exit("Publish package blocked: quiz failed structural validation.")

    # Placeholder safety check
    hits = check_placeholders(quiz["items"])
    if hits:
        for h in hits:
            print(f"PLACEHOLDER DETECTED: {h}")
        sys.exit("Publish package blocked: demo quiz contains placeholder/dummy content.")

    package = build_package(quiz, quiz_path)

    out_dir = quiz_path.parents[1] / "package_v0"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_pkg_path      = out_dir / "publish_package_v0.json"
    out_report_path   = out_dir / "publish_package_report.json"
    out_manifest_path = out_dir / "publish_package_manifest.md"

    report = build_report(package, out_pkg_path, out_report_path, out_manifest_path)
    manifest = build_manifest_md(package, report)

    out_pkg_path.write_text(json.dumps(package, indent=2, ensure_ascii=False), encoding="utf-8")
    out_report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    out_manifest_path.write_text(manifest, encoding="utf-8")

    print(f"package_id       : {package['package_id']}")
    print(f"status           : {package['status']}")
    print(f"question_count   : {package['quiz']['question_count']}")
    print(f"answer_key_count : {len(package['answer_key'])}")
    print(f"publish_package  : {out_pkg_path}")
    print(f"report           : {out_report_path}")
    print(f"manifest         : {out_manifest_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <quiz_demo_NNN.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    run(p)
