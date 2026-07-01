"""
Gate 69E -- Render AI Package Candidate Static Previews v1

Reads the student and teacher payloads and renders simple, readable HTML
preview files. No external JS. No secrets.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\render_ai_package_candidate_preview_v1.py

Output:
  data/ai/package_candidates/static_preview/student_ai_package_preview_v1.html
  data/ai/package_candidates/static_preview/teacher_ai_package_preview_v1.html
  data/ai/package_candidates/static_preview/ai_package_candidate_preview_report_v1.json
"""

import json
import sys
import datetime
import html as html_mod
from pathlib import Path

ROOT         = Path(__file__).resolve().parents[2]
PKG_DIR      = ROOT / "data" / "ai" / "package_candidates"
STUDENT_FILE = PKG_DIR / "student_ai_package_payload_v1.json"
TEACHER_FILE = PKG_DIR / "teacher_ai_package_payload_v1.json"
PREVIEW_DIR  = PKG_DIR / "static_preview"
REPORT_FILE  = ROOT / "data" / "diagnostics" / "ai_package_candidate_payload_export_report_v1.json"


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
      .badge-draft  { background: #dbeafe; color: #1e40af; }
      .badge-ok     { background: #d1fae5; color: #065f46; }
      .badge-warn   { background: #fee2e2; color: #991b1b; }
      .meta-table { border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }
      .meta-table td { padding: 4px 16px 4px 0; }
      .meta-table .label { color: #6b7280; white-space: nowrap; }
      .meta-table code { font-family: monospace; }
      .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px 24px; margin-bottom: 24px; }
      .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
      .card-title { font-size: 16px; font-weight: 700; margin: 0; }
      .card-meta { font-size: 12px; color: #6b7280; text-align: right; }
      .section-label { font-size: 12px; font-weight: 700; color: #374151; text-transform: uppercase;
                       letter-spacing: 0.05em; margin: 14px 0 6px; }
      .prompt-box { background: #f9fafb; padding: 12px 14px; border-radius: 4px; font-size: 14px; line-height: 1.7; }
      .answer-box { background: #f0fdf4; padding: 12px 14px; border-radius: 4px; font-size: 13px;
                    font-family: monospace; line-height: 1.7; }
      .notes-box  { background: #fffbeb; padding: 10px 14px; border-radius: 4px; font-size: 13px;
                    color: #4b5563; line-height: 1.6; }
      .rubric-list { padding-left: 20px; font-size: 13px; line-height: 1.8; }
      .rubric-list li { margin-bottom: 2px; }
      .marks { color: #6b7280; font-size: 12px; }
      .safety-tag { display: inline-block; padding: 1px 7px; border-radius: 3px; font-size: 11px;
                    font-weight: 700; margin-right: 6px; }
      .safe { background: #d1fae5; color: #065f46; }
      .unsafe { background: #fee2e2; color: #991b1b; }
      footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e7eb;
               font-size: 12px; color: #9ca3af; }
    </style>
    """


def _build_student_html(payload: dict) -> str:
    resources = payload.get("resources", [])
    pkg_status = payload.get("package_status", "draft_package_candidate")
    now_str = payload.get("generated_at", "")

    cards = ""
    for r in resources:
        instr = _esc(r.get("student_instructions", ""))
        instr_html = f'<div class="section-label">Instructions</div><p style="font-size:13px;color:#6b7280;margin:0 0 8px">{instr}</p>' if instr else ""
        cards += f"""
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">{_esc(r.get("title") or r.get("resource_id"))}</h2>
            <div class="card-meta">
              {_esc(r.get("resource_type", "question"))} &middot;
              {_esc(r.get("topic", ""))} &middot;
              {_esc(r.get("difficulty", ""))}
            </div>
          </div>
          {instr_html}
          <div class="section-label">Question</div>
          <div class="prompt-box">{_esc(r.get("student_prompt", ""))}</div>
          <p style="font-size:12px;color:#9ca3af;margin:10px 0 0">
            Estimated time: {_esc(r.get("estimated_time_minutes", ""))} min
            &middot; Skill: {_esc(r.get("skill_name", ""))}
          </p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Student AI Package Preview — Quanta Aptus</title>
  {_css()}
</head>
<body>
  <h1>
    Student Resource Preview
    <span class="badge badge-draft">DRAFT — NOT PUBLISHED</span>
  </h1>
  <p class="subtitle">
    Gate 69E — AI approved package candidate preview &middot; Generated {_esc(now_str[:19])}
  </p>
  <div class="banner">
    <strong>This is a draft preview only.</strong>
    These resources have not been published. Teacher final approval is required
    before any content is made available to students. Auto-publish is disabled.
  </div>
  <table class="meta-table"><tbody>
    <tr><td class="label">Package status</td><td><code>{_esc(pkg_status)}</code></td></tr>
    <tr><td class="label">Auto-publish</td><td><span class="badge badge-ok">DISABLED</span></td></tr>
    <tr><td class="label">Teacher final approval</td><td><span class="badge badge-ok">REQUIRED</span></td></tr>
    <tr><td class="label">Resource count</td><td>{len(resources)}</td></tr>
  </tbody></table>
  {cards}
  <footer>
    Quanta Aptus &middot; AI Package Candidate Preview &middot; Gate 69E
    &middot; No raw Cambridge source text &middot; No auto-publish
  </footer>
</body>
</html>"""


def _build_teacher_html(payload: dict) -> str:
    resources = payload.get("resources", [])
    pkg_status = payload.get("package_status", "draft_package_candidate")
    now_str = payload.get("generated_at", "")

    def _safety_tag(ok: bool, label: str) -> str:
        cls = "safe" if ok else "unsafe"
        return f'<span class="safety-tag {cls}">{_esc(label)}: {"YES" if ok else "NO"}</span>'

    cards = ""
    for r in resources:
        decl = r.get("safety_declaration", {})
        prov = r.get("provenance", {})

        rubric_items = "".join(
            f'<li><strong>{_esc(rb.get("criterion", ""))}</strong>'
            f' <span class="marks">[{_esc(rb.get("marks", ""))} mark(s)]</span>'
            + (f' — {_esc(rb.get("guidance", ""))}' if rb.get("guidance") else "")
            + "</li>"
            for rb in r.get("marking_rubric", [])
        )
        rubric_html = (
            f'<div class="section-label">Marking Rubric</div>'
            f'<ul class="rubric-list">{rubric_items}</ul>'
            if rubric_items else ""
        )

        notes = r.get("teacher_notes", "")
        notes_html = (
            f'<div class="section-label">Teacher Notes</div>'
            f'<div class="notes-box">{_esc(notes)}</div>'
            if notes else ""
        )

        cards += f"""
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">{_esc(r.get("title") or r.get("resource_id"))}</h2>
            <div class="card-meta">
              {_esc(r.get("resource_type", "question"))} &middot;
              {_esc(r.get("topic", ""))} &middot;
              {_esc(r.get("skill_name", ""))} &middot;
              {_esc(r.get("difficulty", ""))}
            </div>
          </div>
          <div class="section-label">Student Question</div>
          <div class="prompt-box">{_esc(r.get("student_prompt", ""))}</div>
          <div class="section-label">Answer Key</div>
          <div class="answer-box">{_esc(r.get("answer_key", ""))}</div>
          {rubric_html}
          {notes_html}
          <div class="section-label">Safety Declaration</div>
          <div>
            {_safety_tag(bool(decl.get("original_content")), "original_content")}
            {_safety_tag(bool(decl.get("no_raw_source_text_used")), "no_raw_source")}
            {_safety_tag(bool(decl.get("no_mark_scheme_copied")), "no_mark_scheme")}
          </div>
          <div class="section-label" style="margin-top:10px">Provenance</div>
          <p style="font-size:12px;color:#6b7280;margin:0">
            Origin: <code>{_esc(prov.get("origin", ""))}</code> &middot;
            Teacher approved: <code>{_esc(str(prov.get("approved_by_teacher_review", "")))}
            </code> &middot;
            No raw source: <code>{_esc(str(prov.get("no_raw_source_text_used", "")))}
            </code>
          </p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Teacher AI Package Preview — Quanta Aptus</title>
  {_css()}
</head>
<body>
  <h1>
    Teacher Resource Preview
    <span class="badge badge-draft">DRAFT — NOT PUBLISHED</span>
  </h1>
  <p class="subtitle">
    Gate 69E — AI approved package candidate (teacher view) &middot; Generated {_esc(now_str[:19])}
  </p>
  <div class="banner">
    <strong>Teacher view — contains answer keys and rubrics.</strong>
    This is a draft preview only. Teacher final approval (Gate 69F) required before publishing.
    Auto-publish is disabled. No Supabase writes performed.
  </div>
  <table class="meta-table"><tbody>
    <tr><td class="label">Package status</td><td><code>{_esc(pkg_status)}</code></td></tr>
    <tr><td class="label">Auto-publish</td><td><span class="badge badge-ok">DISABLED</span></td></tr>
    <tr><td class="label">Teacher final approval</td><td><span class="badge badge-ok">REQUIRED (Gate 69F)</span></td></tr>
    <tr><td class="label">Resource count</td><td>{len(resources)}</td></tr>
  </tbody></table>
  {cards}
  <footer>
    Quanta Aptus &middot; AI Package Candidate Teacher Preview &middot; Gate 69E
    &middot; No raw Cambridge source text &middot; No auto-publish
  </footer>
</body>
</html>"""


def main():
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("Gate 69E -- Render AI Package Candidate Previews v1")
    print("-" * 55)

    issues: list[str] = []

    for label, path in [("student payload", STUDENT_FILE), ("teacher payload", TEACHER_FILE)]:
        if not path.exists():
            print(f"  ! {label} not found: {path}")
            print("  ! Run export_ai_package_candidate_payloads_v1.py first.")
            report = {
                "status": "failed",
                "error": f"{label} not found",
                "generated_at": now,
            }
            REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"\nReport: {REPORT_FILE}")
            sys.exit(1)

    student_payload = json.loads(STUDENT_FILE.read_text(encoding="utf-8"))
    teacher_payload = json.loads(TEACHER_FILE.read_text(encoding="utf-8"))

    student_html_path = PREVIEW_DIR / "student_ai_package_preview_v1.html"
    teacher_html_path = PREVIEW_DIR / "teacher_ai_package_preview_v1.html"

    student_html_path.write_text(_build_student_html(student_payload), encoding="utf-8")
    teacher_html_path.write_text(_build_teacher_html(teacher_payload), encoding="utf-8")

    print(f"  + student preview: {student_html_path}")
    print(f"  + teacher preview: {teacher_html_path}")

    preview_report = {
        "status":            "passed",
        "student_html":      str(student_html_path.relative_to(ROOT)),
        "teacher_html":      str(teacher_html_path.relative_to(ROOT)),
        "resource_count":    student_payload.get("resource_count", 0),
        "auto_publish_enabled":   False,
        "supabase_write_performed": False,
        "teacher_final_publish_required": True,
        "generated_at":      now,
    }

    preview_report_file = PREVIEW_DIR / "ai_package_candidate_preview_report_v1.json"
    preview_report_file.write_text(json.dumps(preview_report, indent=2), encoding="utf-8")

    print(f"\nStatus: passed")
    print(f"Preview report: {preview_report_file}")


if __name__ == "__main__":
    main()
