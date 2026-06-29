"""
Build Quanta Aptus Publish Package v2.

Reads publish_candidate_resource_bank_v2.json and packages all eligible
resources (publish_ready + approved_by_teacher) into student/teacher payloads
with HTML previews.

Usage:
    python tools/ingest/build_publish_package_v2.py \\
        data\\bank\\cambridge_igcse\\physics_0625\\teacher_review\\publish_candidate_resource_bank_v2.json

Output (data/publish/cambridge_igcse/physics_0625/resource_package_v2/):
    publish_package_v2.json
    student_resource_payload_v2.json
    teacher_resource_payload_v2.json
    resource_package_v2_report.json
    resource_package_v2_manifest.md
    static_preview/student_resource_preview_v2.html
    static_preview/teacher_resource_preview_v2.html
"""

import sys
import json
import html
import argparse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PACKAGE_ID      = "cambridge_igcse_physics_0625_resource_package_v2"
PACKAGE_VERSION = "0.2.0"
PACKAGE_STATUS  = "internal_demo"

# Both statuses are eligible for packaging
PUBLISH_STATUSES = {"publish_ready", "approved_by_teacher"}

# Teacher-only resource types — no student payload entry
TEACHER_ONLY_TYPES = {
    "marking_checklist",
    "graph_marking_checklist",
    "planning_marking_checklist",
}

# Types where worked_solution is instructional content for students
STUDENT_WORKED_SOLUTION_TYPES = {
    "worked_example",
    "worked_explanation",
}

STUDENT_BASE_FIELDS = [
    "resource_id",
    "resource_type",
    "topic",
    "skill_name",
    "skill_type",
    "difficulty",
    "student_prompt",
    "options",
    "estimated_time_minutes",
]

TEACHER_BASE_FIELDS = STUDENT_BASE_FIELDS + [
    "correct_answer",
    "worked_solution",
    "marking_guidance",
    "common_misconception",
    "teacher_note",
    "validation_status",
    "bank_status",
]

# Review metadata — only present on approved_by_teacher items
REVIEW_FIELDS = [
    "review_id",
    "teacher_decision",
    "teacher_notes",
    "decided_at",
    "decided_by",
]


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def build_student_item(item: dict) -> dict | None:
    """Return trimmed student item, or None for teacher-only resource types."""
    if item.get("resource_type") in TEACHER_ONLY_TYPES:
        return None
    out: dict = {f: item.get(f) for f in STUDENT_BASE_FIELDS}
    if item.get("resource_type") in STUDENT_WORKED_SOLUTION_TYPES:
        out["worked_solution"] = item.get("worked_solution")
    return out


def build_teacher_item(item: dict) -> dict:
    """Return full teacher item including review metadata when present."""
    out: dict = {f: item.get(f) for f in TEACHER_BASE_FIELDS}
    for f in REVIEW_FIELDS:
        val = item.get(f)
        if val is not None:
            out[f] = val
    return out


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def build_summary(items: list[dict]) -> dict:
    resource_types:  dict[str, int] = {}
    component_types: dict[str, int] = {}
    topics:          dict[str, int] = {}
    skill_types:     dict[str, int] = {}
    difficulties:    dict[str, int] = {}
    total_time = 0

    def inc(d: dict, k: str | None) -> None:
        if k:
            d[k] = d.get(k, 0) + 1

    for item in items:
        inc(resource_types,  item.get("resource_type"))
        inc(component_types, item.get("component_type"))
        inc(topics,          item.get("topic"))
        inc(skill_types,     item.get("skill_type"))
        inc(difficulties,    item.get("difficulty"))
        total_time += item.get("estimated_time_minutes") or 0

    return {
        "resource_count":               len(items),
        "estimated_total_time_minutes": total_time,
        "resource_types":               resource_types,
        "component_types":              component_types,
        "topics":                       topics,
        "skill_types":                  skill_types,
        "difficulties":                 difficulties,
    }


# ---------------------------------------------------------------------------
# Package document
# ---------------------------------------------------------------------------

def build_package_doc(
    items: list[dict],
    summary: dict,
    source_path: str,
    now_iso: str,
    teacher_approved_count: int,
    decision_file_rel: str,
) -> dict:
    return {
        "package_id":       PACKAGE_ID,
        "version":          PACKAGE_VERSION,
        "status":           PACKAGE_STATUS,
        "created_at":       now_iso,
        "board":            "cambridge",
        "level":            "igcse",
        "subject":          "physics",
        "syllabus_code":    "0625",
        "content_origin":   "quanta_aptus_original_generated",
        "copyright_status": "original_quanta_aptus_content",
        "source_candidate_bank": source_path,
        "copyright_note": (
            "All resources are original Quanta Aptus content generated from "
            "derived skill metadata only. No Cambridge source paper text, "
            "numbers, diagrams, or mark scheme wording is included."
        ),
        "resource_count": len(items),
        "resources": items,
        "summary": summary,
        "teacher_review_metadata": {
            "includes_teacher_approved_items": teacher_approved_count > 0,
            "source_decision_file": decision_file_rel,
            "teacher_approved_added_count": teacher_approved_count,
        },
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(
    resource_count: int,
    source_path: str,
    student_count: int,
    teacher_count: int,
    teacher_only_count: int,
    teacher_approved_count: int,
    summary: dict,
    out_files: dict,
) -> dict:
    status = "passed" if resource_count > 0 else "failed"
    return {
        "status":                       status,
        "package_id":                   PACKAGE_ID,
        "source_candidate_bank":        source_path,
        "resource_count":               resource_count,
        "student_payload_count":        student_count,
        "teacher_payload_count":        teacher_count,
        "teacher_only_resource_count":  teacher_only_count,
        "estimated_total_time_minutes": summary["estimated_total_time_minutes"],
        "resource_types":               summary["resource_types"],
        "topics":                       summary["topics"],
        "skill_types":                  summary["skill_types"],
        "difficulties":                 summary["difficulties"],
        "teacher_approved_added_count": teacher_approved_count,
        "output_files":                 out_files,
    }


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def build_manifest_md(report: dict, source_path: str, now_iso: str) -> str:
    lines = [
        "# Quanta Aptus Publish Package v2",
        "",
        f"- **Package ID:** `{PACKAGE_ID}`",
        f"- **Version:** {PACKAGE_VERSION}",
        f"- **Status:** {PACKAGE_STATUS}",
        f"- **Created:** {now_iso}",
        f"- **Source candidate bank:** `{source_path}`",
        "",
        "## Resource Counts",
        "",
        f"- **Total resources:** {report['resource_count']}",
        f"- **Student payload items:** {report['student_payload_count']}",
        f"- **Teacher payload items:** {report['teacher_payload_count']}",
        f"- **Teacher-only resources:** {report['teacher_only_resource_count']}",
        f"- **Teacher-approved added (v2):** {report['teacher_approved_added_count']}",
        f"- **Estimated total time:** {report['estimated_total_time_minutes']} min",
        "",
        "## Resource Types",
        "",
    ]
    for rt, n in sorted(report["resource_types"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{rt}:** {n}")

    lines += ["", "## Topics", ""]
    for topic, n in sorted(report["topics"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{topic}:** {n}")

    lines += ["", "## Difficulty Distribution", ""]
    for diff, n in sorted(report["difficulties"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{diff}:** {n}")

    lines += ["", "## Output Files", ""]
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")

    lines += [
        "",
        "---",
        "",
        "> **Copyright:** This package contains original Quanta Aptus generated "
        "and teacher-approved resources only. Cambridge source papers are internal "
        "reference only.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML — shared CSS (same style as v1, with additions for approved badge)
# ---------------------------------------------------------------------------

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: Georgia, 'Times New Roman', serif;
    background: #f4f4f2;
    color: #222;
    padding: 24px 16px;
    max-width: 960px;
    margin: 0 auto;
}
h1 { font-size: 1.6rem; margin-bottom: 4px; color: #1a1a2e; }
.subtitle { font-size: 0.9rem; color: #555; margin-bottom: 28px; }
h2.topic-heading {
    font-size: 1.2rem;
    color: #fff;
    background: #1a1a2e;
    padding: 8px 14px;
    border-radius: 4px;
    margin: 32px 0 12px;
}
.card {
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;
}
.resource-type {
    font-size: 0.75rem;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: .06em;
    background: #e8f0fe;
    color: #1a56db;
    padding: 2px 8px;
    border-radius: 3px;
}
.resource-type.teacher-only { background: #fde8e8; color: #b91c1c; }
.approved-badge {
    font-size: 0.72rem;
    font-weight: bold;
    background: #d1fae5;
    color: #065f46;
    padding: 2px 8px;
    border-radius: 3px;
    border: 1px solid #6ee7b7;
}
.difficulty {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 3px;
    font-weight: bold;
}
.difficulty.easy   { background: #d1fae5; color: #065f46; }
.difficulty.medium { background: #fef3c7; color: #92400e; }
.difficulty.hard   { background: #fee2e2; color: #991b1b; }
.skill-name { font-size: 0.8rem; color: #555; margin-bottom: 8px; }
.field-label {
    font-size: 0.72rem;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: #888;
    margin: 10px 0 3px;
}
.field-value {
    font-size: 0.92rem;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
}
.options-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 10px;
    margin: 4px 0;
}
.opt-key { font-weight: bold; color: #444; font-size: 0.92rem; }
.opt-val { font-size: 0.92rem; }
.time-badge { font-size: 0.75rem; color: #666; margin-top: 10px; }
.correct-answer {
    display: inline-block;
    font-size: 0.8rem;
    font-weight: bold;
    background: #d1fae5;
    color: #065f46;
    padding: 2px 8px;
    border-radius: 3px;
    margin: 4px 0;
}
.teacher-section {
    background: #fffbeb;
    border-left: 3px solid #f59e0b;
    padding: 10px 12px;
    margin-top: 10px;
    border-radius: 0 4px 4px 0;
}
.review-section {
    background: #f0fdf4;
    border-left: 3px solid #34d399;
    padding: 7px 12px;
    margin-top: 8px;
    border-radius: 0 4px 4px 0;
    font-size: 0.82rem;
    color: #065f46;
}
.resource-id {
    font-size: 0.68rem;
    color: #aaa;
    margin-top: 10px;
    word-break: break-all;
}
.copyright-footer {
    margin-top: 40px;
    font-size: 0.78rem;
    color: #888;
    border-top: 1px solid #ddd;
    padding-top: 12px;
}
"""


def _e(text: object) -> str:
    if text is None:
        return ""
    return html.escape(str(text))


def _field_block(label: str, value: object) -> str:
    if not value and value != 0:
        return ""
    return (
        f'<div class="field-label">{_e(label)}</div>'
        f'<div class="field-value">{_e(value)}</div>'
    )


def _options_block(options: dict | None) -> str:
    if not options:
        return ""
    pairs = [(k, v) for k, v in options.items() if v is not None]
    if not pairs:
        return ""
    rows = "".join(
        f'<div class="opt-key">{_e(k)}</div><div class="opt-val">{_e(v)}</div>'
        for k, v in pairs
    )
    return (
        '<div class="field-label">Options</div>'
        f'<div class="options-grid">{rows}</div>'
    )


def _difficulty_badge(diff: str | None) -> str:
    d = (diff or "").lower()
    cls = d if d in ("easy", "medium", "hard") else ""
    return f'<span class="difficulty {cls}">{_e(diff or "")}</span>' if diff else ""


def _resource_type_badge(rt: str, teacher_only: bool = False) -> str:
    extra = " teacher-only" if teacher_only else ""
    return f'<span class="resource-type{extra}">{_e(rt)}</span>'


# ---------------------------------------------------------------------------
# Student HTML
# ---------------------------------------------------------------------------

def _student_card(item: dict) -> str:
    rt       = item.get("resource_type", "")
    skill    = item.get("skill_name", "")
    diff     = item.get("difficulty")
    prompt   = item.get("student_prompt")
    options  = item.get("options")
    worked   = item.get("worked_solution")
    time_min = item.get("estimated_time_minutes")
    rid      = item.get("resource_id", "")

    parts = [
        '<div class="card">',
        '<div class="card-header">',
        _resource_type_badge(rt),
        _difficulty_badge(diff),
        '</div>',
        f'<div class="skill-name">{_e(skill)}</div>',
    ]
    if prompt:
        parts.append(_field_block("Question / Task", prompt))
    if options:
        parts.append(_options_block(options))
    if worked:
        parts.append(_field_block("Worked Solution", worked))
    if time_min:
        parts.append(f'<div class="time-badge">Estimated time: {_e(time_min)} min</div>')
    parts.append(f'<div class="resource-id">ID: {_e(rid)}</div>')
    parts.append('</div>')
    return "\n".join(parts)


def build_student_html(items: list[dict], package_id: str, created_at: str) -> str:
    by_topic: dict[str, list[dict]] = {}
    for item in items:
        by_topic.setdefault(item.get("topic") or "Unknown", []).append(item)

    cards_html = ""
    for topic in sorted(by_topic.keys()):
        cards_html += f'\n<h2 class="topic-heading">{_e(topic)}</h2>\n'
        for item in by_topic[topic]:
            cards_html += _student_card(item) + "\n"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quanta Aptus - Student Resources v2</title>
<style>
{_CSS}
</style>
</head>
<body>
<h1>Quanta Aptus Student Resources v2</h1>
<div class="subtitle">
Cambridge IGCSE Physics 0625 &bull;
{_e(len(items))} resources &bull;
Package: {_e(package_id)} &bull;
{_e(created_at[:10])}
</div>
{cards_html}
<div class="copyright-footer">
All resources are original Quanta Aptus content generated from derived skill
metadata only. No Cambridge source paper text, numbers, or diagrams are
included. &copy; Quanta Aptus.
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Teacher HTML
# ---------------------------------------------------------------------------

def _teacher_card(item: dict) -> str:
    rt              = item.get("resource_type", "")
    is_teacher_only = rt in TEACHER_ONLY_TYPES
    is_approved     = item.get("bank_status") == "approved_by_teacher"
    skill           = item.get("skill_name", "")
    diff            = item.get("difficulty")
    prompt          = item.get("student_prompt")
    options         = item.get("options")
    correct         = item.get("correct_answer")
    worked          = item.get("worked_solution")
    marking         = item.get("marking_guidance")
    misconception   = item.get("common_misconception")
    teacher_note    = item.get("teacher_note")
    time_min        = item.get("estimated_time_minutes")
    validation_status = item.get("validation_status", "")
    bank_status     = item.get("bank_status", "")
    rid             = item.get("resource_id", "")
    teacher_decision = item.get("teacher_decision")
    teacher_notes   = item.get("teacher_notes", "") or ""

    parts = [
        '<div class="card">',
        '<div class="card-header">',
        _resource_type_badge(rt, teacher_only=is_teacher_only),
        _difficulty_badge(diff),
    ]
    if is_approved:
        parts.append('<span class="approved-badge">Teacher Approved</span>')
    parts += ['</div>', f'<div class="skill-name">{_e(skill)}</div>']

    if prompt:
        parts.append(_field_block("Student Prompt", prompt))
    elif is_teacher_only:
        parts.append(
            '<div class="field-label">Student Prompt</div>'
            '<div class="field-value" style="color:#aaa;">'
            '[Teacher-only resource — no student prompt]</div>'
        )

    if options:
        parts.append(_options_block(options))

    if correct:
        parts.append(
            f'<div class="field-label">Correct Answer</div>'
            f'<span class="correct-answer">{_e(correct)}</span>'
        )

    parts.append('<div class="teacher-section">')
    if worked:
        parts.append(_field_block("Worked Solution", worked))
    if marking:
        parts.append(_field_block("Marking Guidance", marking))
    if misconception:
        parts.append(_field_block("Common Misconception", misconception))
    if teacher_note:
        parts.append(_field_block("Teacher Note", teacher_note))
    parts.append('</div>')

    if is_approved and teacher_decision:
        notes_text = f" &bull; Notes: {_e(teacher_notes)}" if teacher_notes else ""
        parts.append(
            f'<div class="review-section">'
            f'Teacher decision: <strong>{_e(teacher_decision)}</strong>{notes_text}'
            f'</div>'
        )

    if time_min:
        parts.append(f'<div class="time-badge">Estimated time: {_e(time_min)} min</div>')

    meta = f"validation: {_e(validation_status)} | bank: {_e(bank_status)}"
    parts.append(f'<div class="resource-id">ID: {_e(rid)} &bull; {meta}</div>')
    parts.append('</div>')
    return "\n".join(parts)


def build_teacher_html(items: list[dict], package_id: str, created_at: str) -> str:
    by_topic: dict[str, list[dict]] = {}
    for item in items:
        by_topic.setdefault(item.get("topic") or "Unknown", []).append(item)

    cards_html = ""
    for topic in sorted(by_topic.keys()):
        cards_html += f'\n<h2 class="topic-heading">{_e(topic)}</h2>\n'
        for item in by_topic[topic]:
            cards_html += _teacher_card(item) + "\n"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quanta Aptus - Teacher Resources v2</title>
<style>
{_CSS}
</style>
</head>
<body>
<h1>Quanta Aptus Teacher Resources v2</h1>
<div class="subtitle">
Cambridge IGCSE Physics 0625 &bull;
{_e(len(items))} resources (including teacher-only) &bull;
Package: {_e(package_id)} &bull;
{_e(created_at[:10])}
</div>
{cards_html}
<div class="copyright-footer">
All resources are original Quanta Aptus content generated from derived skill
metadata only. No Cambridge source paper text, numbers, or diagrams are
included. &copy; Quanta Aptus &bull; Teacher use only.
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build Quanta Aptus Publish Package v2."
    )
    ap.add_argument(
        "candidate_bank",
        help="Path to publish_candidate_resource_bank_v2.json",
    )
    args = ap.parse_args()

    candidate_path = Path(args.candidate_bank)
    if not candidate_path.exists():
        sys.exit(f"Error: file not found: {candidate_path}")

    try:
        doc = json.loads(candidate_path.read_text(encoding="utf-8"))
    except Exception as exc:
        sys.exit(f"Error reading candidate bank: {exc}")

    if not isinstance(doc, dict):
        sys.exit("Error: candidate bank must be a JSON object.")

    raw_items: list[dict] = doc.get("items", [])
    if not isinstance(raw_items, list):
        sys.exit("Error: 'items' must be a list in the candidate bank.")

    # Filter to publishable statuses only
    items = [i for i in raw_items if i.get("bank_status") in PUBLISH_STATUSES]
    skipped = len(raw_items) - len(items)
    if skipped:
        print(f"Warning: skipped {skipped} item(s) with non-publishable bank_status.")

    teacher_approved_count = sum(
        1 for i in items if i.get("bank_status") == "approved_by_teacher"
    )

    # Relative path to decision file for metadata field
    decision_file_rel = str(
        Path("data") / "bank" / "cambridge_igcse" / "physics_0625"
        / "teacher_review" / "teacher_review_decisions_v1.json"
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    # ── Build payloads ─────────────────────────────────────────────────────────
    student_items: list[dict] = []
    teacher_items: list[dict] = []
    teacher_only_count = 0

    for item in items:
        teacher_items.append(build_teacher_item(item))
        s = build_student_item(item)
        if s is not None:
            student_items.append(s)
        else:
            teacher_only_count += 1

    # ── Output paths ───────────────────────────────────────────────────────────
    out_dir = (
        PROJECT_ROOT / "data" / "publish"
        / "cambridge_igcse" / "physics_0625" / "resource_package_v2"
    )
    static_dir = out_dir / "static_preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)

    pkg_path          = out_dir / "publish_package_v2.json"
    student_path      = out_dir / "student_resource_payload_v2.json"
    teacher_path      = out_dir / "teacher_resource_payload_v2.json"
    report_path       = out_dir / "resource_package_v2_report.json"
    manifest_path     = out_dir / "resource_package_v2_manifest.md"
    student_html_path = static_dir / "student_resource_preview_v2.html"
    teacher_html_path = static_dir / "teacher_resource_preview_v2.html"

    out_files = {
        "publish_package":      str(pkg_path),
        "student_payload":      str(student_path),
        "teacher_payload":      str(teacher_path),
        "report":               str(report_path),
        "manifest":             str(manifest_path),
        "student_html_preview": str(student_html_path),
        "teacher_html_preview": str(teacher_html_path),
    }

    # ── Build all documents ────────────────────────────────────────────────────
    summary = build_summary(items)

    pkg_doc = build_package_doc(
        items=items,
        summary=summary,
        source_path=str(candidate_path),
        now_iso=now_iso,
        teacher_approved_count=teacher_approved_count,
        decision_file_rel=decision_file_rel,
    )

    report = build_report(
        resource_count=len(items),
        source_path=str(candidate_path),
        student_count=len(student_items),
        teacher_count=len(teacher_items),
        teacher_only_count=teacher_only_count,
        teacher_approved_count=teacher_approved_count,
        summary=summary,
        out_files=out_files,
    )

    manifest = build_manifest_md(report, str(candidate_path), now_iso)

    student_payload = {
        "package_id":     PACKAGE_ID,
        "payload_type":   "student",
        "created_at":     now_iso,
        "resource_count": len(student_items),
        "copyright_note": (
            "All resources are original Quanta Aptus content. "
            "No Cambridge source text is included."
        ),
        "resources": student_items,
    }

    teacher_payload = {
        "package_id":                  PACKAGE_ID,
        "payload_type":                "teacher",
        "created_at":                  now_iso,
        "resource_count":              len(teacher_items),
        "teacher_only_resource_count": teacher_only_count,
        "teacher_approved_count":      teacher_approved_count,
        "copyright_note": (
            "All resources are original Quanta Aptus content. "
            "No Cambridge source text is included. Teacher use only."
        ),
        "resources": teacher_items,
    }

    student_html = build_student_html(student_items, PACKAGE_ID, now_iso)
    teacher_html = build_teacher_html(teacher_items, PACKAGE_ID, now_iso)

    def write_json(path: Path, obj: dict) -> None:
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    write_json(pkg_path,     pkg_doc)
    write_json(student_path, student_payload)
    write_json(teacher_path, teacher_payload)
    write_json(report_path,  report)
    manifest_path.write_text(manifest, encoding="utf-8")
    student_html_path.write_text(student_html, encoding="utf-8")
    teacher_html_path.write_text(teacher_html, encoding="utf-8")

    # ── Terminal summary ───────────────────────────────────────────────────────
    print(f"status                       : {report['status']}")
    print(f"package_id                   : {PACKAGE_ID}")
    print(f"resource_count               : {report['resource_count']}")
    print(f"student_payload_count        : {report['student_payload_count']}")
    print(f"teacher_payload_count        : {report['teacher_payload_count']}")
    print(f"teacher_only_resource_count  : {report['teacher_only_resource_count']}")
    print(f"teacher_approved_added_count : {report['teacher_approved_added_count']}")
    print(f"estimated_total_time_minutes : {summary['estimated_total_time_minutes']}")
    print(f"publish_package              : {pkg_path}")
    print(f"student_payload              : {student_path}")
    print(f"teacher_payload              : {teacher_path}")
    print(f"student_html_preview         : {student_html_path}")
    print(f"teacher_html_preview         : {teacher_html_path}")
    print(f"report                       : {report_path}")
    print(f"manifest                     : {manifest_path}")


if __name__ == "__main__":
    main()
