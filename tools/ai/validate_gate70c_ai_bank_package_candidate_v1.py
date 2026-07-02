"""
Gate 70C -- Validate AI Bank Package Candidate v1

Validates the package candidate for schema integrity, safety fields,
no raw Cambridge text in content, and no secrets.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\validate_gate70c_ai_bank_package_candidate_v1.py \\
      data\\ai\\package_candidates\\gate70c_ai_bank_package_candidate_v1.json

Output:
  data/diagnostics/gate70c_ai_bank_package_candidate_validation_report_v1.json
"""

import json
import re
import sys
from pathlib import Path

ROOT     = Path(__file__).resolve().parents[2]
OUT_FILE = ROOT / "data" / "diagnostics" / "gate70c_ai_bank_package_candidate_validation_report_v1.json"

if len(sys.argv) < 2:
    pkg_path = ROOT / "data" / "ai" / "package_candidates" / "gate70c_ai_bank_package_candidate_v1.json"
else:
    p = Path(sys.argv[1])
    pkg_path = p if p.is_absolute() else ROOT / p

print("Gate 70C -- Validate AI Bank Package Candidate v1")
print("=" * 60)
print(f"File: {pkg_path}")

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
    "Cambridge International",
    "UCLES",
    "© Cambridge",
    "© Cambridge",
]

REQUIRED_RESOURCE_FIELDS = {
    "resource_id", "bank_item_id", "student_prompt", "answer_key",
    "marking_rubric", "safety_declaration", "provenance",
    "resource_type", "topic", "difficulty",
}

issues: list[str] = []
resource_results: list[dict] = []

if not pkg_path.exists():
    report = {
        "valid": False, "file_exists": False, "resource_count": 0,
        "issues": ["Package candidate not found — run build_gate70c_ai_bank_package_candidate_v1.py first"],
        "resource_results": [], "safety_summary": {},
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Status: NEEDS REVIEW (file not found)")
    sys.exit(0)

doc = json.loads(pkg_path.read_text(encoding="utf-8"))
resources: list[dict] = doc.get("resources", [])
print(f"Resources: {len(resources)}")

# Doc-level checks
if doc.get("status") != "draft_package_candidate":
    issues.append(f"status is not draft_package_candidate: got {doc.get('status')}")
if doc.get("resource_count", 0) == 0 or len(resources) == 0:
    issues.append("resource_count is 0 — no resources in package")
if doc.get("teacher_final_publish_required") is not True:
    issues.append("teacher_final_publish_required is not True")
if doc.get("auto_publish_enabled") is not False:
    issues.append("auto_publish_enabled is not False")
if doc.get("supabase_write_performed") is not False:
    issues.append("supabase_write_performed is not False")
if doc.get("ai_api_called") is not False:
    issues.append("ai_api_called is not False")

secrets_clean   = True
copyright_clean = True

# Secret scan: full JSON (secrets should never appear anywhere)
all_text = json.dumps(doc)
for pat in SECRET_PATTERNS:
    if re.search(pat, all_text):
        issues.append(f"Secret pattern found: {pat[:50]}")
        secrets_clean = False

# Copyright scan: content text fields only (avoid false positives from key names)
_CONTENT_FIELDS = ("student_prompt", "answer_key", "teacher_notes",
                   "student_instructions", "title", "skill_name", "learning_objective")
content_text = " ".join(
    str(r.get(f, "")) for r in resources for f in _CONTENT_FIELDS
)
for pat in COPYRIGHT_PATTERNS:
    if pat in content_text:
        issues.append(f"Copyright pattern in content: {pat}")
        copyright_clean = False

# Resource-level checks
seen_resource_ids: set[str] = set()
for idx, res in enumerate(resources):
    r_issues: list[str] = []
    rid = res.get("resource_id", f"resource_{idx}")

    # Required fields
    for field in REQUIRED_RESOURCE_FIELDS:
        if field not in res:
            r_issues.append(f"missing: {field}")

    # student_prompt non-empty
    sp = res.get("student_prompt", "")
    if not isinstance(sp, str) or not sp.strip():
        r_issues.append("student_prompt empty")

    # answer_key non-empty
    ak = res.get("answer_key", "")
    if not isinstance(ak, str) or not ak.strip():
        r_issues.append("answer_key empty")

    # marking_rubric non-empty list
    mr = res.get("marking_rubric", [])
    if not isinstance(mr, list) or len(mr) == 0:
        r_issues.append("marking_rubric must be non-empty list")

    # safety_declaration dict
    if not isinstance(res.get("safety_declaration"), dict):
        r_issues.append("safety_declaration must be a dict")

    # provenance.gate70b_approved
    prov = res.get("provenance", {})
    if not isinstance(prov, dict) or prov.get("gate70b_approved") is not True:
        r_issues.append("provenance.gate70b_approved is not True")

    # No pending/revision/rejected
    if res.get("decision") in ("needs_revision", "reject"):
        r_issues.append(f"non-approved decision found: {res.get('decision')}")
    if res.get("status") in ("needs_revision", "rejected", "pending_review"):
        r_issues.append(f"non-approved status found: {res.get('status')}")

    # resource_id unique
    if rid in seen_resource_ids:
        r_issues.append(f"duplicate resource_id: {rid}")
    seen_resource_ids.add(rid)

    ok = len(r_issues) == 0
    if not ok:
        issues.extend([f"{rid}: {i}" for i in r_issues])
    resource_results.append({"resource_id": rid, "status": "ok" if ok else "issues", "issues": r_issues})

res_ok   = sum(1 for r in resource_results if r["status"] == "ok")
res_fail = sum(1 for r in resource_results if r["status"] != "ok")
valid    = len(issues) == 0

print(f"Resources valid:  {res_ok}/{len(resources)}")
print(f"Secrets clean:    {secrets_clean}")
print(f"Copyright clean:  {copyright_clean}")
print(f"Issues:           {len(issues)}")
if issues:
    for iss in issues[:10]:
        print(f"  ! {iss}")

report = {
    "valid":          valid,
    "file_exists":    True,
    "resource_count": len(resources),
    "resources_ok":   res_ok,
    "resources_fail": res_fail,
    "issues":         issues,
    "resource_results": resource_results,
    "safety_summary": {
        "teacher_final_publish_required": doc.get("teacher_final_publish_required"),
        "auto_publish_enabled":           doc.get("auto_publish_enabled"),
        "supabase_write_performed":       doc.get("supabase_write_performed"),
        "ai_api_called":                  doc.get("ai_api_called"),
        "secrets_clean":                  secrets_clean,
        "copyright_clean":                copyright_clean,
    },
}

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report: {OUT_FILE.relative_to(ROOT)}")
print(f"Status: {'VALID' if valid else 'NEEDS REVIEW'}")
sys.exit(0 if valid else 1)
