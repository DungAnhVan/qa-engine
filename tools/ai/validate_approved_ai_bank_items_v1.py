"""
Gate 70B -- Validate Approved AI Bank Items v1

Validates the approved AI bank items file for schema integrity, safety fields,
no raw Cambridge text, no secrets, and required structural fields.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\validate_approved_ai_bank_items_v1.py \\
      data\\ai\\approved\\gate70b_approved_ai_bank_items_v1.json

Output:
  data/diagnostics/gate70b_approved_ai_bank_items_validation_report_v1.json
"""

import json
import re
import sys
from pathlib import Path

ROOT    = Path(__file__).resolve().parents[2]
OUT_FILE = ROOT / "data" / "diagnostics" / "gate70b_approved_ai_bank_items_validation_report_v1.json"

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if len(sys.argv) < 2:
    approved_path = ROOT / "data" / "ai" / "approved" / "gate70b_approved_ai_bank_items_v1.json"
else:
    p = Path(sys.argv[1])
    approved_path = p if p.is_absolute() else ROOT / p

print("Gate 70B -- Validate Approved AI Bank Items v1")
print("=" * 60)
print(f"File: {approved_path.relative_to(ROOT) if approved_path.is_relative_to(ROOT) else approved_path}")

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"sk-ant-[A-Za-z0-9\-]{20,}",
    r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    r"SUPABASE_SERVICE_ROLE_KEY\s*[:=]\s*\S{8,}",
    r"NEXT_PUBLIC_OPENAI",
    r"NEXT_PUBLIC_ANTHROPIC",
]

COPYRIGHT_PATTERNS = [
    "original_raw_block",
    "normalized_raw_block",
    "mark_scheme_text",
    "data/raw",
    "Question Answer Marks",
    "Cambridge International Examinations",
    "UCLES",
    "© Cambridge",
    "© Cambridge",
]

REQUIRED_ITEM_FIELDS = {
    "bank_id", "resource_id", "review_item_id",
    "student_prompt", "answer_key", "marking_rubric",
    "safety_declaration", "teacher_review_required",
    "auto_publish_enabled", "supabase_write_performed",
    "status", "decision",
}

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

issues: list[str] = []
item_results: list[dict] = []

if not approved_path.exists():
    report = {
        "valid": False, "file_exists": False,
        "total_items": 0, "items_ok": 0, "items_fail": 0,
        "issues": ["Approved items file not found — run apply_ai_bank_review_decisions_v1.py first"],
        "item_results": [],
        "safety_summary": {},
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Status: NEEDS REVIEW (file not found)")
    sys.exit(0)

doc   = json.loads(approved_path.read_text(encoding="utf-8"))
items: list[dict] = doc.get("items", [])
print(f"Items: {len(items)}")

# Doc-level checks
if doc.get("auto_publish_enabled") is not False:
    issues.append("doc.auto_publish_enabled is not False")
if doc.get("supabase_write_performed") is not False:
    issues.append("doc.supabase_write_performed is not False")
if doc.get("ai_api_called") is not False:
    issues.append("doc.ai_api_called is not False")

# Item count
if len(items) == 0:
    issues.append("No approved items — apply at least one approve decision first")

secrets_clean   = True
copyright_clean = True
all_text        = json.dumps(doc)

# Secret scan on full doc
for pat in SECRET_PATTERNS:
    if re.search(pat, all_text):
        issues.append(f"Secret pattern found: {pat[:50]}")
        secrets_clean = False

# Copyright scan: scan only authored text fields (not policy key names)
# This avoids false positives from safety_declaration keys like "no_mark_scheme_text"
_CONTENT_FIELDS = ("student_prompt", "answer_key", "generated_text", "review_notes", "learning_objective")
content_text = " ".join(
    str(item.get(f, "")) for item in items for f in _CONTENT_FIELDS
)
for pat in COPYRIGHT_PATTERNS:
    if pat in content_text:
        issues.append(f"Copyright pattern in content text: {pat}")
        copyright_clean = False

# Item-level checks
for idx, item in enumerate(items):
    item_issues: list[str] = []
    iid = item.get("bank_id", f"item_{idx}")

    # Required fields
    for field in REQUIRED_ITEM_FIELDS:
        if field not in item:
            item_issues.append(f"missing: {field}")

    # student_prompt must be non-empty string
    sp = item.get("student_prompt", "")
    if not isinstance(sp, str) or not sp.strip():
        item_issues.append("student_prompt is empty or not a string")

    # answer_key must be non-empty string
    ak = item.get("answer_key", "")
    if not isinstance(ak, str) or not ak.strip():
        item_issues.append("answer_key is empty or not a string")

    # marking_rubric must be non-empty list
    mr = item.get("marking_rubric", [])
    if not isinstance(mr, list) or len(mr) == 0:
        item_issues.append("marking_rubric must be a non-empty list")

    # safety_declaration must be a dict
    sd = item.get("safety_declaration", {})
    if not isinstance(sd, dict):
        item_issues.append("safety_declaration must be a dict")

    # Safety policy fields
    if item.get("teacher_review_required") is not True:
        item_issues.append("teacher_review_required is not True")
    if item.get("auto_publish_enabled") is not False:
        item_issues.append("auto_publish_enabled is not False")
    if item.get("supabase_write_performed") is not False:
        item_issues.append("supabase_write_performed is not False")

    # Status must be approved
    if item.get("status") not in ("approved_pending_package", "approved"):
        item_issues.append(f"unexpected status: {item.get('status')}")

    # Decision must not be rejected or needs_revision
    if item.get("decision") == "reject":
        item_issues.append("rejected item found in approved file")
    if item.get("decision") == "needs_revision":
        item_issues.append("needs_revision item found in approved file")

    ok = len(item_issues) == 0
    if not ok:
        issues.extend([f"{iid}: {i}" for i in item_issues])
    item_results.append({"bank_id": iid, "status": "ok" if ok else "issues", "issues": item_issues})

items_ok   = sum(1 for r in item_results if r["status"] == "ok")
items_fail = sum(1 for r in item_results if r["status"] != "ok")
valid      = len(issues) == 0

print(f"Items valid:    {items_ok}/{len(items)}")
print(f"Secrets clean:  {secrets_clean}")
print(f"Copyright clean: {copyright_clean}")
print(f"Issues:         {len(issues)}")
if issues:
    for iss in issues[:10]:
        print(f"  ! {iss}")

report = {
    "valid":       valid,
    "file_exists": True,
    "total_items": len(items),
    "items_ok":    items_ok,
    "items_fail":  items_fail,
    "issues":      issues,
    "item_results": item_results,
    "safety_summary": {
        "teacher_review_required_all": all(e.get("teacher_review_required") for e in items),
        "auto_publish_disabled_all":   all(not e.get("auto_publish_enabled") for e in items),
        "supabase_write_blocked_all":  all(not e.get("supabase_write_performed") for e in items),
        "secrets_clean":               secrets_clean,
        "copyright_clean":             copyright_clean,
    },
}

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report: {OUT_FILE.relative_to(ROOT)}")
print(f"Status: {'VALID' if valid else 'NEEDS REVIEW'}")
sys.exit(0 if valid else 1)
