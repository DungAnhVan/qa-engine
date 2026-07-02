"""
Gate 70D -- Render AI Bank Local Published Preview v1

Outputs:
  data/ai/published/gate70d_ai_bank_package_v1/static_preview/gate70d_student_ai_bank_published_preview_v1.html
  data/ai/published/gate70d_ai_bank_package_v1/static_preview/gate70d_teacher_ai_bank_published_preview_v1.html
  data/ai/published/gate70d_ai_bank_package_v1/static_preview/gate70d_ai_bank_published_preview_report_v1.json
"""

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PKG_DIR       = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1"
PKG_FILE      = PKG_DIR / "publish_package_v1.json"
STUDENT_FILE  = PKG_DIR / "student_resource_payload_v1.json"
TEACHER_FILE  = PKG_DIR / "teacher_resource_payload_v1.json"
PREVIEW_DIR   = PKG_DIR / "static_preview"
STUDENT_HTML  = PREVIEW_DIR / "gate70d_student_ai_bank_published_preview_v1.html"
TEACHER_HTML  = PREVIEW_DIR / "gate70d_teacher_ai_bank_published_preview_v1.html"
PREVIEW_REPORT = PREVIEW_DIR / "gate70d_ai_bank_published_preview_report_v1.json"

print("Gate 70D -- Render AI Bank Local Published Preview v1")
print("=" * 60)

if not PKG_FILE.exists():
    print("ERROR: Published package not found — run build_gate70d_ai_bank_local_published_package_v1.py first.")
    sys.exit(1)

pkg = json.loads(PKG_FILE.read_text(encoding="utf-8"))

if not STUDENT_FILE.exists() or not TEACHER_FILE.exists():
    print("ERROR: Payloads not found — run build_gate70d_ai_bank_local_published_package_v1.py first.")
    sys.exit(1)

student_payload = json.loads(STUDENT_FILE.read_text(encoding="utf-8"))
teacher_payload = json.loads(TEACHER_FILE.read_text(encoding="utf-8"))

_BASE_CSS = """
body{font-family:Georgia,serif;max-width:860px;margin:40px auto;padding:0 24px;line-height:1.7;color:#222}
h1{font-size:1.6rem;border-bottom:2px solid #333;padding-bottom:8px}
h2{font-size:1.05rem;color:#444;margin-top:28px}
.resource{border:1px solid #ccc;border-radius:6px;padding:20px;margin:24px 0;background:#fafafa}
.resource h3{font-size:1rem;margin:0 0 6px}
.tag{display:inline-block;font-size:.75rem;padding:2px 8px;border-radius:12px;margin-right:5px;font-family:monospace}
.ok{background:#d4edda;color:#155724}
.warn{background:#fff3cd;color:#856404}
.info{background:#d1ecf1;color:#0c5460}
.prompt-box{background:#fff;border:1px solid #ccc;border-radius:4px;padding:12px;margin:10px 0;white-space:pre-wrap;font-family:monospace;font-size:.9rem}
.rubric li{margin:3px 0}
.meta{font-size:.77rem;color:#888;margin-top:6px}
.banner{background:#fffbea;border:1px solid #f0c040;border-radius:6px;padding:12px 16px;margin-bottom:20px;font-size:.9rem}
.banner-ok{background:#f0fff4;border-color:#5aff8a}
.status-bar{background:#e9ecef;border-radius:4px;padding:10px 14px;margin-bottom:20px;font-size:.85rem;font-family:monospace}
"""

def _tag(text: str, cls: str = "info") -> str:
    return f'<span class="tag {cls}">{html.escape(str(text))}</span>'


def _status_bar(pkg: dict) -> str:
    return f"""<div class="status-bar">
  {_tag("status: " + pkg.get("status",""), "ok")}
  {_tag("active_content: " + str(pkg.get("active_content",False)), "warn" if pkg.get("active_content") else "ok")}
  {_tag("supabase_write: " + str(pkg.get("supabase_write_performed",False)), "ok")}
  {_tag("ai_api: " + str(pkg.get("ai_api_called",False)), "ok")}
  {_tag("teacher_approved: " + str(pkg.get("teacher_final_approval",False)), "ok")}
  {_tag("resources: " + str(pkg.get("resource_count",0)), "info")}
</div>"""


def _student_card(res: dict) -> str:
    title = html.escape(res.get("title", "Untitled"))
    topic = html.escape(res.get("topic", ""))
    rtype = html.escape(res.get("resource_type", "question"))
    diff  = html.escape(res.get("difficulty", "medium"))
    mins  = res.get("estimated_time_minutes", 10)
    instr = html.escape(res.get("student_instructions", ""))
    prompt = html.escape(res.get("student_prompt", ""))
    return f"""
<div class="resource">
  <h3>{title}</h3>
  {_tag(rtype,"info")} {_tag(diff,"info")} {_tag(f"{mins} min","info")}
  <p class="meta">Topic: {topic}</p>
  <h2>Instructions</h2>
  <p>{instr}</p>
  <h2>Question</h2>
  <div class="prompt-box">{prompt}</div>
</div>"""


def _teacher_card(res: dict) -> str:
    title   = html.escape(res.get("title", "Untitled"))
    topic   = html.escape(res.get("topic", ""))
    rtype   = html.escape(res.get("resource_type", "question"))
    diff    = html.escape(res.get("difficulty", "medium"))
    mins    = res.get("estimated_time_minutes", 10)
    prompt  = html.escape(res.get("student_prompt", ""))
    answer  = html.escape(res.get("answer_key", ""))
    notes   = html.escape(res.get("teacher_notes", ""))
    provider = html.escape(res.get("provider", "mock"))
    model   = html.escape(res.get("model", "mock"))
    prov    = res.get("provenance", {})
    rubric  = res.get("marking_rubric", [])
    rubric_html = "".join(
        f"<li>[{html.escape(str(r.get('marks','?')))}m] {html.escape(r.get('criterion',''))} — "
        f"<em>{html.escape(r.get('guidance',''))}</em></li>"
        for r in rubric
    )
    return f"""
<div class="resource">
  <h3>{title} <span style="color:#888;font-size:.85rem">[TEACHER VIEW]</span></h3>
  {_tag(rtype,"info")} {_tag(diff,"info")} {_tag(f"{mins}min","info")}
  {_tag(f"provider:{provider}","info")} {_tag(f"model:{model}","info")}
  <p class="meta">Topic: {topic}</p>
  <h2>Student Question</h2>
  <div class="prompt-box">{prompt}</div>
  <h2>Answer Key</h2>
  <div class="prompt-box">{answer}</div>
  <h2>Marking Rubric</h2>
  <ul class="rubric">{rubric_html}</ul>
  <h2>Teacher Notes</h2>
  <p>{notes}</p>
  <p class="meta">
    gate70b_approved: {_tag("yes" if prov.get("gate70b_approved") else "no","ok")}
    no_raw_source: {_tag("yes" if prov.get("no_raw_source_text_used") else "no","ok")}
    teacher_review: {_tag("yes" if prov.get("teacher_review_required") else "no","ok")}
  </p>
</div>"""


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>{_BASE_CSS}</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
{body}
</body>
</html>"""


PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

student_banner = """<div class="banner banner-ok">
  <strong>Gate 70D — Locally Published AI Bank Package</strong><br>
  This content has received final teacher approval and has been locally published.
  It is <strong>not</strong> active production content and has not been synced to Supabase.
  Gate 70E required for Supabase sync.
</div>"""

teacher_banner = """<div class="banner">
  <strong>Gate 70D — Teacher View (Confidential)</strong><br>
  Includes answer keys, marking rubric, and teacher notes.
  This package is locally published but NOT active production content.
  No Supabase write performed. Gate 70E required for Supabase sync.
</div>"""

status_bar = _status_bar(pkg)

student_cards = "".join(_student_card(r) for r in student_payload.get("resources", []))
teacher_cards = "".join(_teacher_card(r) for r in teacher_payload.get("resources", []))

STUDENT_HTML.write_text(_page(
    "Gate 70D — Student Preview (Published Local)",
    status_bar + student_banner + student_cards,
), encoding="utf-8")

TEACHER_HTML.write_text(_page(
    "Gate 70D — Teacher Preview (Published Local, Confidential)",
    status_bar + teacher_banner + teacher_cards,
), encoding="utf-8")

preview_report = {
    "student_preview": str(STUDENT_HTML.relative_to(ROOT)),
    "teacher_preview": str(TEACHER_HTML.relative_to(ROOT)),
    "student_resource_count": len(student_payload.get("resources", [])),
    "teacher_resource_count": len(teacher_payload.get("resources", [])),
    "status": "passed",
}
PREVIEW_REPORT.write_text(json.dumps(preview_report, indent=2), encoding="utf-8")

print(f"Student: {STUDENT_HTML.relative_to(ROOT)}")
print(f"Teacher: {TEACHER_HTML.relative_to(ROOT)}")
print(f"Report:  {PREVIEW_REPORT.relative_to(ROOT)}")
print("Status: PASSED")
sys.exit(0)
