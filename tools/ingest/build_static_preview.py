"""
Build static HTML preview files from app payloads.

Usage:
    python tools/ingest/build_static_preview.py <app_payloads_folder>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_static_preview.py \
        data/publish/cambridge_igcse/physics_0625/package_v0/app_payloads
"""

import sys
import json
import html as html_lib
from pathlib import Path

PLACEHOLDER_STRINGS = [
    "Original question",
    "option alpha",
    "option beta",
    "option gamma",
    "option delta",
    "core principle",
    "Students often confuse the key terms",
]

ANSWER_LEAK_STRINGS = ["correct_answer", "explanation", "common_misconception", "answer_key"]

REQUIRED_ITEM_FIELDS = [
    "quiz_question_number", "item_id", "topic", "subtopic", "skill",
    "difficulty", "question_type", "stem", "options",
]

CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Georgia, serif; background: #f8f8f6; color: #222; padding: 2rem; }
    h1 { font-size: 1.6rem; color: #1a1a2e; border-bottom: 2px solid #c8a96e; padding-bottom: .5rem; margin-bottom: 1.5rem; }
    h2 { font-size: 1.1rem; color: #1a1a2e; margin-bottom: .4rem; }
    .meta { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 1rem 1.2rem; margin-bottom: 1.5rem; font-size: .9rem; line-height: 1.8; }
    .meta span { font-weight: bold; color: #444; }
    .question { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 1.2rem 1.4rem; margin-bottom: 1.2rem; }
    .q-header { display: flex; gap: 1rem; font-size: .8rem; color: #666; margin-bottom: .6rem; }
    .badge { background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 4px; padding: 2px 7px; }
    .badge.hard { background: #fef2f2; border-color: #fecaca; }
    .badge.medium { background: #fffbeb; border-color: #fde68a; }
    .badge.easy { background: #f0fdf4; border-color: #bbf7d0; }
    .stem { font-size: 1rem; margin-bottom: .8rem; line-height: 1.5; }
    .options { list-style: none; }
    .options li { padding: .35rem .6rem; border-radius: 4px; margin-bottom: .25rem; font-size: .95rem; }
    .options li:hover { background: #f0f4ff; }
    .options .label { font-weight: bold; display: inline-block; width: 1.4rem; color: #555; }
    .correct { background: #dcfce7 !important; border-left: 4px solid #22c55e; font-weight: bold; }
    .wrong   { background: #fee2e2 !important; border-left: 4px solid #ef4444; }
    .expln-box { margin-top: .7rem; padding: .6rem .8rem; background: #f0fdf4; border-left: 3px solid #22c55e; font-size: .9rem; border-radius: 0 4px 4px 0; }
    .miscn-box { margin-top: .4rem; padding: .6rem .8rem; background: #fffbeb; border-left: 3px solid #f59e0b; font-size: .9rem; border-radius: 0 4px 4px 0; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; font-size: .9rem; }
    th { background: #1a1a2e; color: #fff; padding: .5rem .8rem; text-align: left; }
    td { padding: .45rem .8rem; border-bottom: 1px solid #eee; }
    tr:nth-child(even) td { background: #fafafa; }
    .pass { color: #16a34a; font-weight: bold; }
    .fail { color: #dc2626; font-weight: bold; }
    .score-banner { background: #1a1a2e; color: #fff; border-radius: 8px; padding: 1.2rem 1.6rem; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 2rem; }
    .score-number { font-size: 2.5rem; font-weight: bold; color: #c8a96e; }
    .score-label { font-size: .9rem; line-height: 1.6; opacity: .85; }
    .section-title { font-size: 1rem; font-weight: bold; color: #1a1a2e; margin: 1.2rem 0 .5rem; border-left: 4px solid #c8a96e; padding-left: .5rem; }
    footer { margin-top: 2rem; font-size: .75rem; color: #aaa; text-align: center; }
"""


def esc(s):
    return html_lib.escape(str(s))


def html_shell(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <style>{CSS}</style>
</head>
<body>
{body}
  <footer>Quanta Aptus &mdash; Internal Preview &mdash; Not for distribution</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_student_payload(sp):
    errors = []
    for field in ("package_id", "quiz_id", "title", "items"):
        if not sp.get(field):
            errors.append(f"Missing or empty field: '{field}'")
    for i, item in enumerate(sp.get("items", []), 1):
        for field in REQUIRED_ITEM_FIELDS:
            if field not in item or item[field] == "" or item[field] is None:
                errors.append(f"items[{i}]: missing or empty '{field}'")
        for opt in ("A", "B", "C", "D"):
            if opt not in item.get("options", {}):
                errors.append(f"items[{i}]: missing option '{opt}'")
    return errors


def check_placeholders(*raw_texts):
    hits = []
    for text in raw_texts:
        for ph in PLACEHOLDER_STRINGS:
            if ph.lower() in text.lower():
                hits.append(f"Found placeholder: '{ph}'")
    return hits


def check_answer_leakage_html(html_text):
    return [s for s in ANSWER_LEAK_STRINGS if s in html_text]


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

def build_student_html(sp):
    lines = []
    lines.append(f'  <h1>🎓 {esc(sp["title"])}</h1>')

    lines.append('  <div class="meta">')
    lines.append(f'    <span>Board:</span> {esc(sp.get("board",""))} &nbsp;|&nbsp; ')
    lines.append(f'    <span>Level:</span> {esc(sp.get("level",""))} &nbsp;|&nbsp; ')
    lines.append(f'    <span>Subject:</span> {esc(sp.get("subject",""))} &nbsp;|&nbsp; ')
    lines.append(f'    <span>Syllabus:</span> {esc(sp.get("syllabus_code",""))}<br>')
    lines.append(f'    <span>Questions:</span> {esc(sp.get("question_count",""))} &nbsp;|&nbsp; ')
    lines.append(f'    <span>Estimated time:</span> {esc(sp.get("estimated_time_minutes",""))} minutes')
    lines.append('  </div>')

    for item in sp["items"]:
        diff = esc(item["difficulty"])
        lines.append('  <div class="question">')
        lines.append(f'    <h2>Question {esc(item["quiz_question_number"])}</h2>')
        lines.append('    <div class="q-header">')
        lines.append(f'      <span class="badge">{esc(item["topic"])}</span>')
        lines.append(f'      <span class="badge">{esc(item["skill"])}</span>')
        lines.append(f'      <span class="badge {diff}">{diff}</span>')
        lines.append('    </div>')
        lines.append(f'    <p class="stem">{esc(item["stem"])}</p>')
        lines.append('    <ul class="options">')
        for key in ("A", "B", "C", "D"):
            opt_text = item["options"].get(key, "")
            lines.append(
                f'      <li><span class="label">{esc(key)}.</span> {esc(opt_text)}</li>'
            )
        lines.append('    </ul>')
        lines.append('  </div>')

    return html_shell("Quanta Aptus — Student Quiz Preview", "\n".join(lines))


def build_teacher_html(sp, tp):
    ak_map = {e["quiz_question_number"]: e for e in tp["answer_key"]}
    item_map = {item["quiz_question_number"]: item for item in sp["items"]}

    lines = []
    lines.append('  <h1>📋 Teacher Answer Preview</h1>')
    lines.append(f'  <p class="meta"><span>Quiz ID:</span> {esc(tp["quiz_id"])}</p>')

    for qn in sorted(ak_map.keys()):
        ak = ak_map[qn]
        item = item_map.get(qn, {})
        diff = esc(item.get("difficulty", ""))
        lines.append('  <div class="question">')
        lines.append(f'    <h2>Question {esc(qn)}</h2>')
        lines.append('    <div class="q-header">')
        lines.append(f'      <span class="badge">{esc(item.get("topic",""))}</span>')
        lines.append(f'      <span class="badge">{esc(item.get("skill",""))}</span>')
        lines.append(f'      <span class="badge {diff}">{diff}</span>')
        lines.append('    </div>')
        lines.append(f'    <p class="stem">{esc(item.get("stem",""))}</p>')
        lines.append('    <ul class="options">')
        for key in ("A", "B", "C", "D"):
            opt_text = item.get("options", {}).get(key, "")
            css_cls = ' class="correct"' if key == ak["correct_answer"] else ""
            lines.append(
                f'      <li{css_cls}><span class="label">{esc(key)}.</span> {esc(opt_text)}</li>'
            )
        lines.append('    </ul>')
        lines.append(
            f'    <div class="expln-box"><strong>Explanation:</strong> {esc(ak["explanation"])}</div>'
        )
        lines.append(
            f'    <div class="miscn-box"><strong>Common misconception:</strong> {esc(ak["common_misconception"])}</div>'
        )
        lines.append('  </div>')

    return html_shell("Quanta Aptus — Teacher Answer Preview", "\n".join(lines))


def build_result_html(ar):
    lines = []
    pct = ar["percentage"]
    lines.append('  <h1>📊 Sample Attempt Result</h1>')
    lines.append('  <div class="score-banner">')
    lines.append(f'    <div class="score-number">{esc(ar["score"])}/{esc(ar["total"])}</div>')
    lines.append(
        f'    <div class="score-label">Score: <strong>{esc(pct)}%</strong><br>'
        f'Quiz: {esc(ar["quiz_id"])}<br>Attempt: {esc(ar["attempt_id"])}</div>'
    )
    lines.append('  </div>')

    lines.append('  <p class="section-title">Question-by-question breakdown</p>')
    lines.append('  <table>')
    lines.append(
        '    <tr><th>#</th><th>Student</th><th>Correct</th><th>Result</th>'
        '<th>Skill</th><th>Topic</th></tr>'
    )
    for r in ar["results"]:
        result_cls = "pass" if r["is_correct"] else "fail"
        result_txt = "✓ Correct" if r["is_correct"] else "✗ Wrong"
        lines.append(
            f'    <tr>'
            f'<td>{esc(r["quiz_question_number"])}</td>'
            f'<td>{esc(r["student_answer"])}</td>'
            f'<td>{esc(r["correct_answer"])}</td>'
            f'<td class="{result_cls}">{result_txt}</td>'
            f'<td>{esc(r["skill"])}</td>'
            f'<td>{esc(r["topic"])}</td>'
            f'</tr>'
        )
    lines.append('  </table>')

    lines.append('  <p class="section-title">Skill breakdown</p>')
    lines.append('  <table>')
    lines.append('    <tr><th>Skill</th><th>Correct</th><th>Total</th><th>Score</th></tr>')
    for skill, v in ar["skill_breakdown"].items():
        lines.append(
            f'    <tr><td>{esc(skill)}</td><td>{esc(v["correct"])}</td>'
            f'<td>{esc(v["total"])}</td><td>{esc(v["percentage"])}%</td></tr>'
        )
    lines.append('  </table>')

    lines.append('  <p class="section-title">Topic breakdown</p>')
    lines.append('  <table>')
    lines.append('    <tr><th>Topic</th><th>Correct</th><th>Total</th><th>Score</th></tr>')
    for topic, v in ar["topic_breakdown"].items():
        lines.append(
            f'    <tr><td>{esc(topic)}</td><td>{esc(v["correct"])}</td>'
            f'<td>{esc(v["total"])}</td><td>{esc(v["percentage"])}%</td></tr>'
        )
    lines.append('  </table>')

    return html_shell("Quanta Aptus — Sample Result Preview", "\n".join(lines))


# ---------------------------------------------------------------------------
# Report and manifest
# ---------------------------------------------------------------------------

def build_report(sp, tp, ar, out_files):
    return {
        "status": "passed",
        "package_id": sp["package_id"],
        "quiz_id": sp["quiz_id"],
        "student_question_count": len(sp["items"]),
        "teacher_answer_count": len(tp["answer_key"]),
        "sample_score": ar["score"],
        "sample_total": ar["total"],
        "sample_percentage": ar["percentage"],
        "answer_leakage_check": "passed",
        "placeholder_check": "passed",
        "output_files": out_files,
    }


def build_manifest_md(report):
    of = report["output_files"]
    lines = []
    lines.append("# Quanta Aptus Static Preview")
    lines.append("")
    lines.append(f"**Package ID:** `{report['package_id']}`")
    lines.append(f"**Quiz ID:** `{report['quiz_id']}`")
    lines.append("")
    lines.append("## Preview Files")
    lines.append("")
    lines.append(f"- **Student preview:** `{of['student_preview']}`")
    lines.append(f"- **Teacher answer preview:** `{of['teacher_preview']}`")
    lines.append(f"- **Sample result preview:** `{of['sample_result_preview']}`")
    lines.append("")
    lines.append("## Safety Checks")
    lines.append("")
    lines.append("| Check | Status |")
    lines.append("| ----- | ------ |")
    lines.append(f"| Answer leakage check | {report['answer_leakage_check']} |")
    lines.append(f"| Placeholder check | {report['placeholder_check']} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "> Student preview contains no answers, explanations, or teacher-only fields."
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(payloads_dir):
    sp_path = payloads_dir / "student_quiz_payload.json"
    tp_path = payloads_dir / "teacher_answer_payload.json"
    ar_path = payloads_dir / "sample_attempt_result.json"

    for p in (sp_path, tp_path, ar_path):
        if not p.exists():
            sys.exit(f"Error: file not found: {p}")

    sp_raw = sp_path.read_text(encoding="utf-8")
    tp_raw = tp_path.read_text(encoding="utf-8")
    ar_raw = ar_path.read_text(encoding="utf-8")

    sp = json.loads(sp_raw)
    tp = json.loads(tp_raw)
    ar = json.loads(ar_raw)

    # Structural validation
    errors = validate_student_payload(sp)
    if errors:
        for e in errors:
            print(f"VALIDATION ERROR: {e}")
        sys.exit("Static preview blocked: student payload failed validation.")

    # Placeholder check on all inputs
    hits = check_placeholders(sp_raw, tp_raw, ar_raw)
    if hits:
        for h in hits:
            print(f"PLACEHOLDER: {h}")
        sys.exit("Static preview blocked: placeholder/dummy content detected.")

    # Build HTML files
    student_html = build_student_html(sp)
    teacher_html = build_teacher_html(sp, tp)
    result_html  = build_result_html(ar)

    # Answer leakage check on student HTML
    leaks = check_answer_leakage_html(student_html)
    if leaks:
        for field in leaks:
            print(f"ANSWER LEAKAGE: '{field}' found in student preview HTML")
        sys.exit("Static preview blocked: answer leakage detected in student preview.")

    # Write outputs
    out_dir = payloads_dir.parent / "static_preview"
    out_dir.mkdir(parents=True, exist_ok=True)

    student_path  = out_dir / "student_quiz_preview.html"
    teacher_path  = out_dir / "teacher_answer_preview.html"
    result_path   = out_dir / "sample_result_preview.html"
    report_path   = out_dir / "static_preview_report.json"
    manifest_path = out_dir / "static_preview_manifest.md"

    out_files = {
        "student_preview":       str(student_path),
        "teacher_preview":       str(teacher_path),
        "sample_result_preview": str(result_path),
        "report":                str(report_path),
        "manifest":              str(manifest_path),
    }

    report   = build_report(sp, tp, ar, out_files)
    manifest = build_manifest_md(report)

    student_path.write_text(student_html, encoding="utf-8")
    teacher_path.write_text(teacher_html, encoding="utf-8")
    result_path.write_text(result_html,   encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(manifest, encoding="utf-8")

    print(f"status                : {report['status']}")
    print(f"package_id            : {report['package_id']}")
    print(f"quiz_id               : {report['quiz_id']}")
    print(f"student_question_count: {report['student_question_count']}")
    print(f"teacher_answer_count  : {report['teacher_answer_count']}")
    print(f"answer_leakage_check  : {report['answer_leakage_check']}")
    print(f"placeholder_check     : {report['placeholder_check']}")
    print(f"output_folder         : {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <app_payloads_folder>")
    p = Path(sys.argv[1])
    if not p.is_dir():
        sys.exit(f"Error: not a directory: {p}")
    run(p)
