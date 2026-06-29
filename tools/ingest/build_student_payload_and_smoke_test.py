"""
Build student/teacher app payloads from a publish package and run smoke tests.

Usage:
    python tools/ingest/build_student_payload_and_smoke_test.py <publish_package_v0.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_student_payload_and_smoke_test.py \
        data/publish/cambridge_igcse/physics_0625/package_v0/publish_package_v0.json
"""

import sys
import json
from collections import defaultdict
from pathlib import Path

ANSWER_LEAK_FIELDS = {"correct_answer", "explanation", "common_misconception", "answer_key"}

PLACEHOLDER_STRINGS = [
    "Original question",
    "option alpha",
    "option beta",
    "option gamma",
    "option delta",
    "core principle",
    "Students often confuse the key terms",
]

SAMPLE_ANSWERS = {1: "B", 2: "D", 3: "A", 4: "B", 5: "C"}

REQUIRED_ITEM_FIELDS = [
    "quiz_question_number", "item_id", "topic", "subtopic", "skill",
    "difficulty", "question_type", "stem", "options",
]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_package(pkg):
    errors = []
    for field in ("package_id", "quiz", "answer_key"):
        if not pkg.get(field):
            errors.append(f"Missing or empty field: '{field}'")

    quiz = pkg.get("quiz", {})
    if not quiz.get("items"):
        errors.append("Missing or empty: quiz.items")

    items = quiz.get("items", [])
    ak = pkg.get("answer_key", [])

    if items and ak and len(items) != len(ak):
        errors.append(f"quiz.items count ({len(items)}) != answer_key count ({len(ak)})")

    for i, item in enumerate(items, 1):
        for field in REQUIRED_ITEM_FIELDS:
            if field not in item or item[field] == "" or item[field] is None:
                errors.append(f"quiz.items[{i}]: missing or empty '{field}'")
        for opt in ("A", "B", "C", "D"):
            if opt not in item.get("options", {}):
                errors.append(f"quiz.items[{i}]: missing option '{opt}'")

    return errors


def check_placeholders(items):
    hits = []
    for item in items:
        texts = [item.get("stem", "")]
        texts += list(item.get("options", {}).values())
        combined = " ".join(texts)
        for ph in PLACEHOLDER_STRINGS:
            if ph.lower() in combined.lower():
                hits.append(
                    f"Item {item.get('quiz_question_number', '?')}: found placeholder '{ph}'"
                )
                break
    return hits


def check_answer_leakage(student_payload):
    serialized = json.dumps(student_payload)
    leaks = []
    for field in ANSWER_LEAK_FIELDS:
        # Match as a JSON key: "field":
        if f'"{field}":' in serialized:
            leaks.append(field)
    return leaks


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def build_student_payload(pkg):
    quiz = pkg["quiz"]
    return {
        "package_id": pkg["package_id"],
        "quiz_id": quiz["quiz_id"],
        "title": quiz["title"],
        "description": quiz.get("description", ""),
        "board": pkg["board"],
        "level": pkg["level"],
        "subject": pkg["subject"],
        "syllabus_code": pkg["syllabus_code"],
        "question_count": quiz["question_count"],
        "estimated_time_minutes": quiz.get("estimated_time_minutes", 0),
        "items": [
            {
                "quiz_question_number": item["quiz_question_number"],
                "item_id": item["item_id"],
                "topic": item["topic"],
                "subtopic": item["subtopic"],
                "skill": item["skill"],
                "difficulty": item["difficulty"],
                "question_type": item["question_type"],
                "stem": item["stem"],
                "options": item["options"],
            }
            for item in quiz["items"]
        ],
    }


def build_teacher_payload(pkg):
    quiz = pkg["quiz"]
    return {
        "package_id": pkg["package_id"],
        "quiz_id": quiz["quiz_id"],
        "answer_key": [
            {
                "quiz_question_number": ak["quiz_question_number"],
                "item_id": ak["item_id"],
                "correct_answer": ak["correct_answer"],
                "explanation": ak["explanation"],
                "common_misconception": ak["common_misconception"],
            }
            for ak in pkg["answer_key"]
        ],
    }


# ---------------------------------------------------------------------------
# Sample grading
# ---------------------------------------------------------------------------

def grade_attempt(pkg, student_answers):
    quiz = pkg["quiz"]
    answer_key = {ak["quiz_question_number"]: ak for ak in pkg["answer_key"]}
    quiz_items  = {item["quiz_question_number"]: item for item in quiz["items"]}

    results = []
    skill_scores  = defaultdict(lambda: {"correct": 0, "total": 0})
    topic_scores  = defaultdict(lambda: {"correct": 0, "total": 0})
    total_correct = 0

    for qn in sorted(student_answers.keys()):
        student_ans = student_answers[qn]
        ak   = answer_key[qn]
        item = quiz_items[qn]
        is_correct = student_ans == ak["correct_answer"]
        if is_correct:
            total_correct += 1

        skill = item["skill"]
        topic = item["topic"]
        skill_scores[skill]["total"] += 1
        topic_scores[topic]["total"] += 1
        if is_correct:
            skill_scores[skill]["correct"] += 1
            topic_scores[topic]["correct"] += 1

        results.append({
            "quiz_question_number": qn,
            "item_id": item["item_id"],
            "student_answer": student_ans,
            "correct_answer": ak["correct_answer"],
            "is_correct": is_correct,
            "skill": skill,
            "topic": topic,
            "explanation": ak["explanation"],
        })

    total = len(student_answers)
    pct   = round(total_correct / total * 100, 1) if total else 0.0

    skill_breakdown = {
        sk: {
            "correct": v["correct"],
            "total": v["total"],
            "percentage": round(v["correct"] / v["total"] * 100, 1) if v["total"] else 0.0,
        }
        for sk, v in skill_scores.items()
    }
    topic_breakdown = {
        tp: {
            "correct": v["correct"],
            "total": v["total"],
            "percentage": round(v["correct"] / v["total"] * 100, 1) if v["total"] else 0.0,
        }
        for tp, v in topic_scores.items()
    }

    return {
        "package_id": pkg["package_id"],
        "quiz_id": quiz["quiz_id"],
        "attempt_id": "sample_attempt_001",
        "score": total_correct,
        "total": total,
        "percentage": pct,
        "results": results,
        "skill_breakdown": skill_breakdown,
        "topic_breakdown": topic_breakdown,
    }


# ---------------------------------------------------------------------------
# Report and manifest
# ---------------------------------------------------------------------------

def build_report(pkg, student_payload, attempt, out_files):
    quiz_id = pkg["quiz"]["quiz_id"]
    return {
        "status": "passed",
        "package_id": pkg["package_id"],
        "quiz_id": quiz_id,
        "student_payload_question_count": len(student_payload["items"]),
        "teacher_answer_count": len(pkg["answer_key"]),
        "answer_leakage_check": "passed",
        "placeholder_check": "passed",
        "sample_score": attempt["score"],
        "sample_total": attempt["total"],
        "sample_percentage": attempt["percentage"],
        "output_files": out_files,
    }


def build_manifest_md(report, pkg):
    quiz = pkg["quiz"]
    lines = []
    lines.append("# Quanta Aptus App Payload Smoke Test")
    lines.append("")
    lines.append(f"**Package ID:** `{report['package_id']}`")
    lines.append(f"**Quiz ID:** `{report['quiz_id']}`")
    lines.append("")
    lines.append("## Payload Files")
    lines.append("")
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")
    lines.append("")
    lines.append("## Sample Attempt")
    lines.append("")
    lines.append(f"**Score:** {report['sample_score']} / {report['sample_total']}  "
                 f"({report['sample_percentage']}%)")
    lines.append("")
    lines.append("## Safety Checks")
    lines.append("")
    lines.append(f"| Check | Status |")
    lines.append(f"| ----- | ------ |")
    lines.append(f"| Answer leakage check | {report['answer_leakage_check']} |")
    lines.append(f"| Placeholder check | {report['placeholder_check']} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> Student payload contains no answers or explanations.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(package_path):
    pkg = json.loads(package_path.read_text(encoding="utf-8"))

    # Structural validation
    errors = validate_package(pkg)
    if errors:
        for e in errors:
            print(f"VALIDATION ERROR: {e}")
        sys.exit("Payload blocked: package failed structural validation.")

    # Placeholder check (runs on quiz items inside the package)
    hits = check_placeholders(pkg["quiz"]["items"])
    if hits:
        for h in hits:
            print(f"PLACEHOLDER DETECTED: {h}")
        sys.exit("Payload blocked: placeholder/dummy content detected.")

    # Build payloads
    student_payload = build_student_payload(pkg)
    teacher_payload = build_teacher_payload(pkg)

    # Answer leakage check — must run AFTER building student_payload
    leaks = check_answer_leakage(student_payload)
    if leaks:
        for field in leaks:
            print(f"ANSWER LEAKAGE: field '{field}' found in student payload")
        sys.exit("Student payload blocked: answer leakage detected.")

    # Grade sample attempt
    attempt = grade_attempt(pkg, SAMPLE_ANSWERS)

    # Write outputs
    out_dir = package_path.parent / "app_payloads"
    out_dir.mkdir(parents=True, exist_ok=True)

    student_path  = out_dir / "student_quiz_payload.json"
    teacher_path  = out_dir / "teacher_answer_payload.json"
    attempt_path  = out_dir / "sample_attempt_result.json"
    report_path   = out_dir / "payload_smoke_test_report.json"
    manifest_path = out_dir / "payload_smoke_test_manifest.md"

    out_files = {
        "student_quiz_payload":  str(student_path),
        "teacher_answer_payload": str(teacher_path),
        "sample_attempt_result": str(attempt_path),
        "smoke_test_report":     str(report_path),
        "smoke_test_manifest":   str(manifest_path),
    }

    report   = build_report(pkg, student_payload, attempt, out_files)
    manifest = build_manifest_md(report, pkg)

    student_path.write_text(json.dumps(student_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    teacher_path.write_text(json.dumps(teacher_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    attempt_path.write_text(json.dumps(attempt, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(manifest, encoding="utf-8")

    print(f"status                        : {report['status']}")
    print(f"package_id                    : {report['package_id']}")
    print(f"quiz_id                       : {report['quiz_id']}")
    print(f"student_payload_question_count: {report['student_payload_question_count']}")
    print(f"teacher_answer_count          : {report['teacher_answer_count']}")
    print(f"answer_leakage_check          : {report['answer_leakage_check']}")
    print(f"placeholder_check             : {report['placeholder_check']}")
    print(f"sample_score                  : {report['sample_score']} / {report['sample_total']} ({report['sample_percentage']}%)")
    print(f"output_folder                 : {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <publish_package_v0.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    run(p)
