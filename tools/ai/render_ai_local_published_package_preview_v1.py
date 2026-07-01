"""
Gate 69F -- Render AI Local Published Package Static Previews v1

Reads student and teacher published payloads and renders HTML previews.
No external JS. No secrets.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\render_ai_local_published_package_preview_v1.py

Output:
  data/ai/published/ai_resource_package_v1/static_preview/student_ai_published_package_preview_v1.html
  data/ai/published/ai_resource_package_v1/static_preview/teacher_ai_published_package_preview_v1.html
  data/ai/published/ai_resource_package_v1/static_preview/ai_published_package_preview_report_v1.json
"""

import json
import sys
import datetime
import html as html_mod
from pathlib import Path

ROOT         = Path(__file__).resolve().parents[2]
PUBLISHED_DIR = ROOT / "data" / "ai" / "published" / "ai_resource_package_v1"
STUDENT_FILE  = PUBLISHED_DIR / "student_resource_payload_v1.json"
TEACHER_FILE  = PUBLISHED_DIR / "teacher_resource_payload_v1.json"
PREVIEW_DIR   = PUBLISHED_DIR / "static_preview"


def _esc(text: object) -> str:
    return html_mod.escape(str(text) if text is not None else "")


def _css() -> str:
    return """
    <style>
      body { font-family: system-ui, sans-serif; max-width: 860px; margin: 40px auto; padding: 0 24px; color: #1f2937; }
      h1 { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
      .subtitle { color: #6b7280; font-size: 13px; margin-bottom: 24px; }
      .banner { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px;
                border-radius: 4px; font-size: 13px; color: #92400e; margin-bottom: 24px; }
      .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px;
               font-weight: 700; margin-left: 8px; vertical-align: middle; }
      .badge-local  { background: #ede9fe; color: #4c1d95; }
      .badge-ok     { background: #d1fae5; color: #065f46; }
      .meta-table { border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }
      .meta-table td { padding: 4px 16px 4px 0; }
      .meta-table .label { color: #6b7280; white-space: nowrap; }
      .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px 24px; margin-bottom: 24px; }
      .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
      .card-title { font-size: 16px; font-weight: 700; margin: 0; }
      .card-meta { font-size: 12px; color: #6b7280; text-align: right; }
      .section-label { font-size: 12px; font-weight: 700; color: #374151; text-transform: uppercase;
                       letter-spacing: 0.05em; margin: 12px 0 6px; }
      .prompt-box { background: #f9fafb; padding: 12px 14px; border-radius: 4px; font-size: 14px; line-height: 1.7; }
      .answer-box { background: #f0fdf4; padding: 12px 14px; border-radius: 4px; font-size: 13px;
                    font-family: monospace; line-height: 1.7; }
      .notes-box  { background: #fffbeb; padding: 10px 14px; border-radius: 4px; font-size: 13px;
                    color: #4b5563; line-height: 1.6; }
      .rubric-list { padding-left: 20px; font-size: 13px; line-height: 1.8; }
      .safety-tag { display: inline-block; padding: 1px 7px; border-radius: 3px; font-size: 11px;
                    font-weight: 700; margin-right: 6px; }
      .safe { background: #d1fae5; color: #065f46; }
      footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e7eb;
               font-size: 12px; color: #9ca3af; }
    </style>"""


def _build_student_html(payload: dict, now_str: str) -> str:
    resources = payload.get("resources", [])
    cards = ""
    for r in resources:
        instr = _esc(r.get("student_instructions", ""))
        instr_html = (f'<div class="section-label">Instructions</div>'
                      f'<p style="font-size:13px;color:#6b7280;margin:0 0 8px">{instr}</p>'
                      if instr else "")
        cards += f"""
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">{_esc(r.get("title") or r.get("resource_id"))}</h2>
            <div class="card-meta">
              {_esc(r.get("resource_type","question"))} · {_esc(r.get("topic",""))} · {_esc(r.get("difficulty",""))}
            </div>
          </div>
          {instr_html}
          <div class="section-label">Question</div>
          <div class="prompt-box">{_esc(r.get("student_prompt",""))}</div>
          <p style="font-size:12px;color:#9ca3af;margin:10px 0 0">
            Skill: {_esc(r.get("skill_name",""))} · Est. {_esc(r.get("estimated_time_minutes",""))} min
          </p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Student AI Published Package Preview — Quanta Aptus</title>
  {_css()}
</head>
<body>
  <h1>Student Resource Preview
    <span class="badge badge-local">LOCAL — NOT ACTIVE</span>
  </h1>
  <p class="subtitle">Gate 69F — AI locally published package (student view) · Generated {_esc(now_str[:19])}</p>
  <div class="banner">
    <strong>This AI package is locally published but not active production content.</strong>
    Gate 69G required for Supabase sync and active content switch.
    Auto-publish disabled. No Supabase writes performed.
  </div>
  <table class="meta-table"><tbody>
    <tr><td class="label">Package status</td><td><code>published_local_not_active</code></td></tr>
    <tr><td class="label">Active content</td><td><span class="badge badge-ok">FALSE</span></td></tr>
    <tr><td class="label">Supabase write</td><td><span class="badge badge-ok">NOT PERFORMED</span></td></tr>
    <tr><td class="label">Teacher final approval</td><td><span class="badge badge-ok">TRUE</span></td></tr>
    <tr><td class="label">Resources</td><td>{len(resources)}</td></tr>
  </tbody></table>
  {cards}
  <footer>Quanta Aptus · AI Local Published Package Preview · Gate 69F · Not active content · No Supabase write</footer>
</body></html>"""


def _build_teacher_html(payload: dict, now_str: str) -> str:
    resources = payload.get("resources", [])

    def _stag(ok: bool, label: str) -> str:
        cls = "safe" if ok else "unsafe"
        return f'<span class="safety-tag {cls}">{_esc(label)}: {"YES" if ok else "NO"}</span>'

    cards = ""
    for r in resources:
        decl = r.get("safety_declaration", {})
        prov = r.get("provenance", {})
        rubric_html = ""
        if r.get("marking_rubric"):
            items = "".join(
                f'<li><strong>{_esc(rb.get("criterion",""))}</strong>'
                f' <span style="color:#6b7280;font-size:12px">[{_esc(rb.get("marks",""))} mark(s)]</span>'
                + (f' — {_esc(rb.get("guidance",""))}' if rb.get("guidance") else "") + "</li>"
                for rb in r.get("marking_rubric", [])
            )
            rubric_html = f'<div class="section-label">Marking Rubric</div><ul class="rubric-list">{items}</ul>'

        notes_html = ""
        if r.get("teacher_notes"):
            notes_html = (f'<div class="section-label">Teacher Notes</div>'
                          f'<div class="notes-box">{_esc(r["teacher_notes"])}</div>')

        cards += f"""
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">{_esc(r.get("title") or r.get("resource_id"))}</h2>
            <div class="card-meta">
              {_esc(r.get("resource_type","question"))} · {_esc(r.get("topic",""))} ·
              {_esc(r.get("skill_name",""))} · {_esc(r.get("difficulty",""))}
            </div>
          </div>
          <div class="section-label">Student Question</div>
          <div class="prompt-box">{_esc(r.get("student_prompt",""))}</div>
          <div class="section-label">Answer Key</div>
          <div class="answer-box">{_esc(r.get("answer_key",""))}</div>
          {rubric_html}
          {notes_html}
          <div class="section-label">Safety Declaration</div>
          <div>
            {_stag(bool(decl.get("original_content")), "original_content")}
            {_stag(bool(decl.get("no_raw_source_text_used")), "no_raw_source")}
            {_stag(bool(decl.get("no_mark_scheme_copied")), "no_mark_scheme")}
          </div>
          <p style="font-size:11px;color:#9ca3af;margin:8px 0 0">
            Provenance: origin={_esc(prov.get("origin",""))} · teacher_approved={_esc(str(prov.get("approved_by_teacher_review","")))}
          </p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Teacher AI Published Package Preview — Quanta Aptus</title>
  {_css()}
</head>
<body>
  <h1>Teacher Resource Preview
    <span class="badge badge-local">LOCAL — NOT ACTIVE</span>
  </h1>
  <p class="subtitle">Gate 69F — AI locally published package (teacher view) · Generated {_esc(now_str[:19])}</p>
  <div class="banner">
    <strong>Teacher view — contains answer keys and rubrics. Not active content.</strong>
    Gate 69G required for Supabase sync and active content switch. No Supabase writes performed.
  </div>
  <table class="meta-table"><tbody>
    <tr><td class="label">Package status</td><td><code>published_local_not_active</code></td></tr>
    <tr><td class="label">Active content</td><td><span class="badge badge-ok">FALSE</span></td></tr>
    <tr><td class="label">Supabase write</td><td><span class="badge badge-ok">NOT PERFORMED</span></td></tr>
    <tr><td class="label">Teacher final approval</td><td><span class="badge badge-ok">TRUE</span></td></tr>
    <tr><td class="label">Resources</td><td>{len(resources)}</td></tr>
  </tbody></table>
  {cards}
  <footer>Quanta Aptus · AI Local Published Package Teacher Preview · Gate 69F · Not active content</footer>
</body></html>"""


def main():
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("Gate 69F -- Render AI Local Published Package Previews v1")
    print("-" * 55)

    for label, path in [("student payload", STUDENT_FILE), ("teacher payload", TEACHER_FILE)]:
        if not path.exists():
            print(f"  ! {label} not found: {path}")
            sys.exit(1)

    student = json.loads(STUDENT_FILE.read_text(encoding="utf-8"))
    teacher = json.loads(TEACHER_FILE.read_text(encoding="utf-8"))

    student_html = PREVIEW_DIR / "student_ai_published_package_preview_v1.html"
    teacher_html = PREVIEW_DIR / "teacher_ai_published_package_preview_v1.html"

    student_html.write_text(_build_student_html(student, now), encoding="utf-8")
    teacher_html.write_text(_build_teacher_html(teacher, now), encoding="utf-8")

    print(f"  + student preview: {student_html}")
    print(f"  + teacher preview: {teacher_html}")

    report = {
        "status":            "passed",
        "student_html":      str(student_html.relative_to(ROOT)),
        "teacher_html":      str(teacher_html.relative_to(ROOT)),
        "resource_count":    student.get("resource_count", 0),
        "active_content":    False,
        "supabase_write_performed": False,
        "teacher_final_approval": True,
        "generated_at":      now,
    }
    report_path = PREVIEW_DIR / "ai_published_package_preview_report_v1.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nStatus: passed")
    print(f"Preview report: {report_path}")


if __name__ == "__main__":
    main()
