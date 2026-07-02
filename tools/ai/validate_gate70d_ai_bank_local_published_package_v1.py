"""
Gate 70D -- Validate AI Bank Local Published Package v1

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\validate_gate70d_ai_bank_local_published_package_v1.py
  .venv-ingest\\Scripts\\python.exe tools\\ai\\validate_gate70d_ai_bank_local_published_package_v1.py
      data\\ai\\published\\gate70d_ai_bank_package_v1\\publish_package_v1.json

Output:
  data/diagnostics/gate70d_ai_bank_local_published_package_validation_report_v1.json
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if len(sys.argv) < 2:
    pkg_path = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1" / "publish_package_v1.json"
else:
    p = Path(sys.argv[1])
    pkg_path = p if p.is_absolute() else ROOT / p

PKG_DIR    = pkg_path.parent
STUDENT_F  = PKG_DIR / "student_resource_payload_v1.json"
TEACHER_F  = PKG_DIR / "teacher_resource_payload_v1.json"
REPORT_FILE = ROOT / "data" / "diagnostics" / "gate70d_ai_bank_local_published_package_validation_report_v1.json"

print("Gate 70D -- Validate AI Bank Local Published Package v1")
print("=" * 60)
print(f"File: {pkg_path}")

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"sk-ant-[A-Za-z0-9\-]{20,}",
    r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    r"SUPABASE_SERVICE_ROLE_KEY\s*[:=]\s*\S{8,}",
    r"NEXT_PUBLIC_OPENAI",
    r"NEXT_PUBLIC_ANTHROPIC",
    r"NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY",
]

COPYRIGHT_PATTERNS = [
    "original_raw_block",
    "normalized_raw_block",
    "mark_scheme_text",
    "data/raw",
    "Question Answer Marks",
    "Cambridge International",
    "UCLES",
    "© Cambridge",
    "© Cambridge",
]

_CONTENT_FIELDS = ("student_prompt", "answer_key", "teacher_notes",
                   "student_instructions", "title", "skill_name", "learning_objective")

issues: list[str] = []
resource_results: list[dict] = []

if not pkg_path.exists():
    report = {
        "valid": False, "file_exists": False,
        "issues": ["Published package not found — run build_gate70d_ai_bank_local_published_package_v1.py first"],
        "resource_results": [], "safety_summary": {},
    }
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Status: NEEDS REVIEW (file not found)")
    sys.exit(0)

doc       = json.loads(pkg_path.read_text(encoding="utf-8"))
resources = doc.get("resources", [])
print(f"Resources: {len(resources)}")

# Doc-level checks
if doc.get("status") != "published_local_not_active":
    issues.append(f"status must be published_local_not_active, got: {doc.get('status')}")
if doc.get("active_content") is not False:
    issues.append("active_content must be False")
if doc.get("supabase_write_performed") is not False:
    issues.append("supabase_write_performed must be False")
if doc.get("ai_api_called") is not False:
    issues.append("ai_api_called must be False")
if doc.get("teacher_final_approval") is not True:
    issues.append("teacher_final_approval must be True")
if doc.get("resource_count", 0) == 0 or len(resources) == 0:
    issues.append("resource_count is 0 — no resources published")

# Payload files
if not STUDENT_F.exists():
    issues.append(f"student_resource_payload_v1.json not found at {STUDENT_F.relative_to(ROOT)}")
if not TEACHER_F.exists():
    issues.append(f"teacher_resource_payload_v1.json not found at {TEACHER_F.relative_to(ROOT)}")

# Secret scan — full JSON
secrets_clean   = True
copyright_clean = True
all_text        = json.dumps(doc)
for pat in SECRET_PATTERNS:
    if re.search(pat, all_text):
        issues.append(f"Secret pattern found: {pat[:50]}")
        secrets_clean = False

# Copyright scan — content text only
content_text = " ".join(str(r.get(f, "")) for r in resources for f in _CONTENT_FIELDS)
for pat in COPYRIGHT_PATTERNS:
    if pat in content_text:
        issues.append(f"Copyright pattern in content: {pat}")
        copyright_clean = False

# Resource-level checks
seen: set[str] = set()
for idx, res in enumerate(resources):
    r_issues: list[str] = []
    rid = res.get("resource_id", f"resource_{idx}")

    for field in ("resource_id", "student_prompt", "answer_key", "marking_rubric",
                  "safety_declaration", "provenance"):
        if field not in res:
            r_issues.append(f"missing: {field}")

    if not isinstance(res.get("student_prompt", ""), str) or not res.get("student_prompt", "").strip():
        r_issues.append("student_prompt empty")
    if not isinstance(res.get("answer_key", ""), str) or not res.get("answer_key", "").strip():
        r_issues.append("answer_key empty")
    if not isinstance(res.get("marking_rubric"), list) or len(res.get("marking_rubric", [])) == 0:
        r_issues.append("marking_rubric must be non-empty list")
    if not isinstance(res.get("safety_declaration"), dict):
        r_issues.append("safety_declaration must be a dict")

    prov = res.get("provenance", {})
    if not isinstance(prov, dict) or prov.get("gate70b_approved") is not True:
        r_issues.append("provenance.gate70b_approved is not True")

    if res.get("decision") in ("needs_revision", "reject"):
        r_issues.append(f"non-approved decision in published package: {res.get('decision')}")
    if res.get("status") in ("needs_revision", "rejected", "pending_review"):
        r_issues.append(f"non-approved status in published package: {res.get('status')}")

    if rid in seen:
        r_issues.append(f"duplicate resource_id: {rid}")
    seen.add(rid)

    ok = len(r_issues) == 0
    if not ok:
        issues.extend([f"{rid}: {i}" for i in r_issues])
    resource_results.append({"resource_id": rid, "status": "ok" if ok else "issues", "issues": r_issues})

res_ok   = sum(1 for r in resource_results if r["status"] == "ok")
res_fail = sum(1 for r in resource_results if r["status"] != "ok")
valid    = len(issues) == 0

print(f"Resources valid:   {res_ok}/{len(resources)}")
print(f"Secrets clean:     {secrets_clean}")
print(f"Copyright clean:   {copyright_clean}")
print(f"Student payload:   {STUDENT_F.exists()}")
print(f"Teacher payload:   {TEACHER_F.exists()}")
print(f"Issues:            {len(issues)}")
if issues:
    for iss in issues[:10]:
        print(f"  ! {iss}")

report = {
    "valid":           valid,
    "file_exists":     True,
    "resource_count":  len(resources),
    "resources_ok":    res_ok,
    "resources_fail":  res_fail,
    "issues":          issues,
    "resource_results": resource_results,
    "safety_summary": {
        "status":                    doc.get("status"),
        "active_content":            doc.get("active_content"),
        "supabase_write_performed":  doc.get("supabase_write_performed"),
        "ai_api_called":             doc.get("ai_api_called"),
        "teacher_final_approval":    doc.get("teacher_final_approval"),
        "secrets_clean":             secrets_clean,
        "copyright_clean":           copyright_clean,
        "student_payload_exists":    STUDENT_F.exists(),
        "teacher_payload_exists":    TEACHER_F.exists(),
    },
}

REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report: {REPORT_FILE.relative_to(ROOT)}")
print(f"Status: {'VALID' if valid else 'NEEDS REVIEW'}")
sys.exit(0 if valid else 1)
