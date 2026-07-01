"""
Gate 70A -- Validate AI Question Bank v1

Validates the AI question bank JSON for:
  - Schema integrity (required fields present)
  - Safety fields (teacher_review_required=True, auto_publish_enabled=False, supabase_write_performed=False)
  - No secrets in bank items
  - No raw Cambridge copyright text in generated text

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\validate_ai_question_bank_v1.py

Output:
  data/diagnostics/ai_question_bank_validation_v1.json
"""

import json
import re
import sys
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[2]
BANK_FILE = ROOT / "data" / "ai" / "question_bank" / "ai_generated_question_bank_v1.json"
OUT_FILE  = ROOT / "data" / "diagnostics" / "ai_question_bank_validation_v1.json"

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"sk-ant-[A-Za-z0-9\-]{20,}",
    r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    r"SUPABASE_SERVICE_ROLE_KEY\s*[:=]\s*\S{8,}",
]

COPYRIGHT_PATTERNS = [
    "UCLES", "Cambridge International Examinations",
    "Question Answer Marks", "original_raw_block",
]

REQUIRED_ITEM_FIELDS = {
    "bank_id", "request_id", "batch_id", "generated_at",
    "subject_slug", "topic", "generated_text",
    "status", "teacher_review_required", "auto_publish_enabled", "supabase_write_performed",
}

print("Gate 70A -- Validate AI Question Bank v1")
print("=" * 60)

issues: list[str] = []
item_results: list[dict] = []

if not BANK_FILE.exists():
    print(f"Bank file not found: {BANK_FILE.relative_to(ROOT)}")
    report = {
        "valid":          False,
        "bank_exists":    False,
        "total_items":    0,
        "issues":         ["Bank file not found — run run_live_ai_generation_to_bank_v1.py first"],
        "item_results":   [],
        "safety_summary": {},
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Status: NEEDS REVIEW (bank not found)")
    sys.exit(0)

bank = json.loads(BANK_FILE.read_text(encoding="utf-8"))
items: list[dict] = bank.get("items", [])

print(f"Bank items: {len(items)}")

# Bank-level checks
if bank.get("teacher_review_required") is not True:
    issues.append("bank.teacher_review_required is not True")
if bank.get("auto_publish_enabled") is not False:
    issues.append("bank.auto_publish_enabled is not False")
if bank.get("supabase_write_performed") is not False:
    issues.append("bank.supabase_write_performed is not False")

# Item-level checks
secrets_clean   = True
copyright_clean = True

for idx, item in enumerate(items):
    item_issues: list[str] = []
    bank_id = item.get("bank_id", f"item_{idx}")

    # Required fields
    for field in REQUIRED_ITEM_FIELDS:
        if field not in item:
            item_issues.append(f"missing field: {field}")

    # Safety fields
    if item.get("teacher_review_required") is not True:
        item_issues.append("teacher_review_required is not True")
    if item.get("auto_publish_enabled") is not False:
        item_issues.append("auto_publish_enabled is not False")
    if item.get("supabase_write_performed") is not False:
        item_issues.append("supabase_write_performed is not False")
    if item.get("status") != "generated_needs_teacher_review":
        item_issues.append(f"unexpected status: {item.get('status')}")

    # Secret scan
    item_text = json.dumps(item)
    for pat in SECRET_PATTERNS:
        if re.search(pat, item_text):
            item_issues.append(f"secret pattern found: {pat[:40]}")
            secrets_clean = False

    # Copyright scan (generated text only)
    generated_text = item.get("generated_text", "")
    for pat in COPYRIGHT_PATTERNS:
        if pat in generated_text:
            item_issues.append(f"copyright pattern in generated_text: {pat}")
            copyright_clean = False

    ok = len(item_issues) == 0
    if not ok:
        issues.extend([f"{bank_id}: {i}" for i in item_issues])

    item_results.append({
        "bank_id": bank_id,
        "status":  "ok" if ok else "issues",
        "issues":  item_issues,
    })

items_ok      = sum(1 for r in item_results if r["status"] == "ok")
items_fail    = sum(1 for r in item_results if r["status"] != "ok")
bank_valid    = len(issues) == 0

print(f"Items valid: {items_ok}/{len(items)}")
print(f"Secrets clean: {secrets_clean}")
print(f"Copyright clean: {copyright_clean}")
print(f"Issues: {len(issues)}")
if issues:
    for iss in issues[:10]:
        print(f"  ! {iss}")

report = {
    "valid":          bank_valid,
    "bank_exists":    True,
    "total_items":    len(items),
    "items_ok":       items_ok,
    "items_fail":     items_fail,
    "issues":         issues,
    "item_results":   item_results,
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
print(f"Status: {'VALID' if bank_valid else 'NEEDS REVIEW'}")
sys.exit(0 if bank_valid else 1)
