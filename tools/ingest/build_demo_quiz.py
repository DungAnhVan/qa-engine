"""
Build a demo quiz from publish candidates.

Usage:
    python tools/ingest/build_demo_quiz.py <publish_candidate_bank_v0.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_demo_quiz.py \
        data/bank/cambridge_igcse/physics_0625/publish_candidate_bank_v0.json
"""

import sys
import json
from collections import defaultdict
from pathlib import Path

QUIZ_NUMBER = "001"
QUIZ_ID = f"cambridge_igcse_physics_0625_demo_quiz_{QUIZ_NUMBER}"
QUIZ_TITLE = "Cambridge IGCSE Physics 0625 — Demo Quiz 001"
MAX_QUESTIONS = 5
ESTIMATED_TIME_MINUTES = 8


def build_quiz_json(items):
    quiz_items = []
    for n, item in enumerate(items, 1):
        quiz_items.append({
            "quiz_question_number": n,
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
        })

    return {
        "quiz_id": QUIZ_ID,
        "title": QUIZ_TITLE,
        "description": "A short Quanta Aptus demo quiz using original generated MCQs.",
        "board": "cambridge",
        "level": "igcse",
        "subject": "physics",
        "syllabus_code": "0625",
        "question_count": len(quiz_items),
        "estimated_time_minutes": ESTIMATED_TIME_MINUTES,
        "status": "demo_internal",
        "items": quiz_items,
    }


def build_quiz_md(items):
    lines = []
    lines.append(f"# {QUIZ_TITLE}")
    lines.append("")
    lines.append(f"**Questions:** {len(items)}  |  **Estimated time:** {ESTIMATED_TIME_MINUTES} minutes")
    lines.append("")
    lines.append("---")
    lines.append("")

    for n, item in enumerate(items, 1):
        lines.append(f"## Question {n}")
        lines.append("")
        lines.append(f"**Topic:** {item['topic']}  |  **Skill:** {item['skill']}")
        lines.append("")
        lines.append(item["stem"])
        lines.append("")
        for key, text in item["options"].items():
            lines.append(f"**{key}.** {text}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("*Answer key is in answer_key_demo_001.md*")
    lines.append("")

    return "\n".join(lines)


def build_answer_key_md(items):
    lines = []
    lines.append(f"# Answer Key — Demo Quiz {QUIZ_NUMBER}")
    lines.append("")
    lines.append(f"Quiz: {QUIZ_TITLE}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for n, item in enumerate(items, 1):
        lines.append(f"## Question {n}")
        lines.append("")
        lines.append(f"**Correct answer:** {item['correct_answer']}")
        lines.append("")
        lines.append(f"**Explanation:** {item['explanation']}")
        lines.append("")
        lines.append(f"**Common misconception:** {item['common_misconception']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def build_report(items, source_bank_path):
    topics = defaultdict(int)
    difficulties = defaultdict(int)
    for item in items:
        topics[item["topic"]] += 1
        difficulties[item["difficulty"]] += 1

    return {
        "quiz_id": QUIZ_ID,
        "source_bank": str(source_bank_path),
        "question_count": len(items),
        "topics": dict(topics),
        "difficulties": dict(difficulties),
        "item_ids": [item["item_id"] for item in items],
    }


def run(bank_path):
    data = json.loads(bank_path.read_text(encoding="utf-8"))
    all_items = data.get("items", [])

    candidates = [
        i for i in all_items
        if i.get("quality", {}).get("bank_status") == "draft_ready"
    ]

    selected = candidates[:MAX_QUESTIONS]

    if not selected:
        sys.exit("Error: no draft_ready items found in input bank.")

    quiz = build_quiz_json(selected)
    quiz_md = build_quiz_md(selected)
    answer_key_md = build_answer_key_md(selected)
    report = build_report(selected, bank_path)

    out_dir = bank_path.parents[3] / "publish" / "cambridge_igcse" / "physics_0625" / f"demo_quiz_{QUIZ_NUMBER}"
    out_dir.mkdir(parents=True, exist_ok=True)

    quiz_path       = out_dir / f"quiz_demo_{QUIZ_NUMBER}.json"
    quiz_md_path    = out_dir / f"quiz_demo_{QUIZ_NUMBER}.md"
    answer_key_path = out_dir / f"answer_key_demo_{QUIZ_NUMBER}.md"
    report_path     = out_dir / "demo_quiz_report.json"

    quiz_path.write_text(json.dumps(quiz, indent=2, ensure_ascii=False), encoding="utf-8")
    quiz_md_path.write_text(quiz_md, encoding="utf-8")
    answer_key_path.write_text(answer_key_md, encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"quiz_id        : {QUIZ_ID}")
    print(f"question_count : {len(selected)}")
    print(f"output_folder  : {out_dir}")
    print(f"quiz_json      : {quiz_path}")
    print(f"quiz_md        : {quiz_md_path}")
    print(f"answer_key_md  : {answer_key_path}")
    print(f"report_json    : {report_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <publish_candidate_bank_v0.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    run(p)
