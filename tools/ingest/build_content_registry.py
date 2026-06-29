"""
Build content registry from publish package.

Usage:
    python tools/ingest/build_content_registry.py <publish_package_v0.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_content_registry.py \
        data/publish/cambridge_igcse/physics_0625/package_v0/publish_package_v0.json
"""

import sys
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_ID = "quanta_aptus_content_registry_v0"
REGISTRY_VERSION = "0.1.0"

PLACEHOLDER_STRINGS = [
    "Original question",
    "option alpha",
    "option beta",
    "option gamma",
    "option delta",
    "core principle",
    "Students often confuse the key terms",
]

REQUIRED_PACKAGE_FIELDS = [
    "package_id", "version", "status", "board", "level",
    "subject", "syllabus_code", "answer_key", "learning_metadata",
]
REQUIRED_QUIZ_FIELDS = ["quiz_id", "title", "question_count", "items"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_package(pkg):
    errors = []
    for field in REQUIRED_PACKAGE_FIELDS:
        if not pkg.get(field):
            errors.append(f"Missing or empty field: '{field}'")
    quiz = pkg.get("quiz", {})
    if not quiz:
        errors.append("Missing or empty field: 'quiz'")
    else:
        for field in REQUIRED_QUIZ_FIELDS:
            if not quiz.get(field):
                errors.append(f"Missing or empty field: quiz.{field}")
    return errors


def check_placeholders(raw_text):
    return [
        f"Found placeholder: '{ph}'"
        for ph in PLACEHOLDER_STRINGS
        if ph.lower() in raw_text.lower()
    ]


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def sibling_paths(package_path):
    pkg_dir = package_path.parent
    return {
        "student_payload":        pkg_dir / "app_payloads" / "student_quiz_payload.json",
        "teacher_answer_payload": pkg_dir / "app_payloads" / "teacher_answer_payload.json",
        "sample_attempt_result":  pkg_dir / "app_payloads" / "sample_attempt_result.json",
        "student_preview":        pkg_dir / "static_preview" / "student_quiz_preview.html",
        "teacher_preview":        pkg_dir / "static_preview" / "teacher_answer_preview.html",
        "sample_result_preview":  pkg_dir / "static_preview" / "sample_result_preview.html",
    }


# ---------------------------------------------------------------------------
# Registry builder
# ---------------------------------------------------------------------------

def build_content_entry(pkg, package_path, siblings):
    quiz = pkg["quiz"]
    meta = pkg.get("learning_metadata", {})

    paths = {"publish_package": str(package_path)}
    availability = {"publish_package": True}
    for key, path in siblings.items():
        paths[key] = str(path)
        availability[key] = path.exists()

    return {
        "package_id":       pkg["package_id"],
        "package_version":  pkg["version"],
        "package_status":   pkg["status"],
        "content_origin":   pkg.get("content_origin", ""),
        "copyright_status": pkg.get("copyright_status", ""),
        "board":            pkg["board"],
        "level":            pkg["level"],
        "subject":          pkg["subject"],
        "syllabus_code":    pkg["syllabus_code"],
        "quiz_id":          quiz["quiz_id"],
        "title":            quiz["title"],
        "description":      quiz.get("description", ""),
        "question_count":   quiz["question_count"],
        "estimated_time_minutes": quiz.get("estimated_time_minutes", 0),
        "topics":      meta.get("topics", {}),
        "skills":      meta.get("skills", {}),
        "difficulties": meta.get("difficulties", {}),
        "paths":        paths,
        "availability": availability,
    }


def build_summary(contents):
    boards    = defaultdict(int)
    levels    = defaultdict(int)
    subjects  = defaultdict(int)
    syllabuses = defaultdict(int)
    topics    = defaultdict(int)
    skills    = defaultdict(int)
    total_q   = 0

    for c in contents:
        boards[c["board"]] += 1
        levels[c["level"]] += 1
        subjects[c["subject"]] += 1
        syllabuses[c["syllabus_code"]] += 1
        total_q += c["question_count"]
        for topic, cnt in c.get("topics", {}).items():
            topics[topic] += cnt
        for skill, cnt in c.get("skills", {}).items():
            skills[skill] += cnt

    return {
        "boards":          dict(boards),
        "levels":          dict(levels),
        "subjects":        dict(subjects),
        "syllabus_codes":  dict(syllabuses),
        "total_questions": total_q,
        "topics":          dict(topics),
        "skills":          dict(skills),
    }


def build_registry(contents, summary):
    return {
        "registry_id":   REGISTRY_ID,
        "version":       REGISTRY_VERSION,
        "status":        "internal_demo",
        "created_at":    datetime.now(timezone.utc).isoformat(),
        "content_count": len(contents),
        "contents":      contents,
        "summary":       summary,
    }


def build_report(registry, summary, out_files):
    return {
        "status":           "passed",
        "registry_id":      registry["registry_id"],
        "content_count":    registry["content_count"],
        "total_questions":  summary["total_questions"],
        "boards":           summary["boards"],
        "levels":           summary["levels"],
        "subjects":         summary["subjects"],
        "syllabus_codes":   summary["syllabus_codes"],
        "placeholder_check": "passed",
        "output_files":     out_files,
    }


def build_manifest_md(registry, contents, report):
    c = contents[0]
    avail = c["availability"]
    lines = []
    lines.append("# Quanta Aptus Content Registry v0")
    lines.append("")
    lines.append(f"**Registry ID:** `{registry['registry_id']}`")
    lines.append(f"**Version:** {registry['version']}")
    lines.append(f"**Status:** {registry['status']}")
    lines.append(f"**Created:** {registry['created_at']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| ------ | ----: |")
    lines.append(f"| Content count | {registry['content_count']} |")
    lines.append(f"| Total questions | {report['total_questions']} |")
    lines.append("")
    lines.append("## Content Entry")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"| ----- | ----- |")
    lines.append(f"| Board | {c['board']} |")
    lines.append(f"| Level | {c['level']} |")
    lines.append(f"| Subject | {c['subject']} |")
    lines.append(f"| Syllabus | {c['syllabus_code']} |")
    lines.append(f"| Package ID | `{c['package_id']}` |")
    lines.append(f"| Quiz ID | `{c['quiz_id']}` |")
    lines.append(f"| Questions | {c['question_count']} |")
    lines.append("")
    lines.append("## Available Payloads / Previews")
    lines.append("")
    lines.append("| Asset | Available | Path |")
    lines.append("| ----- | :-------: | ---- |")
    for key, path in c["paths"].items():
        status = "✓" if avail.get(key) else "✗"
        lines.append(f"| {key} | {status} | `{path}` |")
    lines.append("")
    lines.append("## Output Paths")
    lines.append("")
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "> This registry is the internal index for Quanta Aptus published learning resources."
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(package_path):
    raw = package_path.read_text(encoding="utf-8")
    pkg = json.loads(raw)

    # Structural validation
    errors = validate_package(pkg)
    if errors:
        for e in errors:
            print(f"VALIDATION ERROR: {e}")
        sys.exit("Content registry blocked: package failed structural validation.")

    # Placeholder safety check
    hits = check_placeholders(raw)
    if hits:
        for h in hits:
            print(f"PLACEHOLDER: {h}")
        sys.exit("Content registry blocked: placeholder/dummy content detected.")

    siblings = sibling_paths(package_path)
    entry    = build_content_entry(pkg, package_path, siblings)
    contents = [entry]
    summary  = build_summary(contents)
    registry = build_registry(contents, summary)

    out_dir = Path("data") / "registry"
    out_dir.mkdir(parents=True, exist_ok=True)

    reg_path      = out_dir / "content_registry_v0.json"
    report_path   = out_dir / "content_registry_report.json"
    manifest_path = out_dir / "content_registry_manifest.md"

    out_files = {
        "registry": str(reg_path),
        "report":   str(report_path),
        "manifest": str(manifest_path),
    }

    report   = build_report(registry, summary, out_files)
    manifest = build_manifest_md(registry, contents, report)

    reg_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(manifest, encoding="utf-8")

    quiz = pkg["quiz"]
    print(f"status         : {report['status']}")
    print(f"registry_id    : {registry['registry_id']}")
    print(f"content_count  : {registry['content_count']}")
    print(f"total_questions: {summary['total_questions']}")
    print(f"board          : {pkg['board']}")
    print(f"level          : {pkg['level']}")
    print(f"subject        : {pkg['subject']}")
    print(f"syllabus_code  : {pkg['syllabus_code']}")
    print(f"package_id     : {pkg['package_id']}")
    print(f"quiz_id        : {quiz['quiz_id']}")
    print(f"registry       : {reg_path}")
    print(f"report         : {report_path}")
    print(f"manifest       : {manifest_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <publish_package_v0.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    run(p)
