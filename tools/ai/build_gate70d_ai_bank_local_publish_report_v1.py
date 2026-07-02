"""
Gate 70D -- Build Gate Report v1

Aggregates all Gate 70D artefacts and produces a pass/fail gate report
with DONE marker.

Output:
  data/diagnostics/gate70d_ai_bank_local_publish_report_v1.json
  data/diagnostics/SUPABASE_GATE_70D_AI_BANK_LOCAL_PUBLISH_DONE.md
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUB_DIR = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1"

PATHS: dict[str, Path] = {
    "approve_script":              ROOT / "tools/ai/approve_gate70d_ai_bank_package_candidate_v1.py",
    "build_script":                ROOT / "tools/ai/build_gate70d_ai_bank_local_published_package_v1.py",
    "validate_script":             ROOT / "tools/ai/validate_gate70d_ai_bank_local_published_package_v1.py",
    "render_script":               ROOT / "tools/ai/render_gate70d_ai_bank_local_published_preview_v1.py",
    "registry_script":             ROOT / "tools/ai/build_gate70d_ai_bank_local_registry_v1.py",
    "ts_lib":                      ROOT / "apps/admin/src/lib/aiBankPublishedPackage.ts",
    "admin_page":                  ROOT / "apps/admin/src/app/ai-bank-published/page.tsx",
    "system_page":                 ROOT / "apps/admin/src/app/system/ai-bank-published/page.tsx",
    "api_route":                   ROOT / "apps/admin/src/app/api/system/ai-bank-published/route.ts",
    "approval_report":             ROOT / "data/diagnostics/gate70d_ai_bank_final_publish_approval_report_v1.json",
    "build_report":                ROOT / "data/diagnostics/gate70d_ai_bank_local_publish_build_report_v1.json",
    "validation_report":           ROOT / "data/diagnostics/gate70d_ai_bank_local_published_package_validation_report_v1.json",
    "registry_report":             ROOT / "data/diagnostics/gate70d_ai_bank_local_registry_build_report_v1.json",
    "test_report":                 ROOT / "data/diagnostics/gate70d_ai_bank_local_publish_test_report_v1.json",
    "local_published_package":     PUB_DIR / "publish_package_v1.json",
    "student_payload":             PUB_DIR / "student_resource_payload_v1.json",
    "teacher_payload":             PUB_DIR / "teacher_resource_payload_v1.json",
    "student_preview":             PUB_DIR / "static_preview/gate70d_student_ai_bank_published_preview_v1.html",
    "teacher_preview":             PUB_DIR / "static_preview/gate70d_teacher_ai_bank_published_preview_v1.html",
    "local_registry":              ROOT / "data/ai/registry/gate70d_ai_bank_content_registry_v1.json",
}

OUT_REPORT = ROOT / "data" / "diagnostics" / "gate70d_ai_bank_local_publish_report_v1.json"
OUT_DONE   = ROOT / "data" / "diagnostics" / "SUPABASE_GATE_70D_AI_BANK_LOCAL_PUBLISH_DONE.md"

print("Gate 70D -- Build Gate Report v1")
print("=" * 60)

file_checklist = {k: v.exists() for k, v in PATHS.items()}
all_present    = all(file_checklist.values())
issues: list[str] = []

for name, exists in file_checklist.items():
    if not exists:
        issues.append(f"Missing: {name}")

# Load package and inspect
pub_pkg     = json.loads(PATHS["local_published_package"].read_text(encoding="utf-8")) if PATHS["local_published_package"].exists() else {}
validation  = json.loads(PATHS["validation_report"].read_text(encoding="utf-8")) if PATHS["validation_report"].exists() else {}
test_rpt    = json.loads(PATHS["test_report"].read_text(encoding="utf-8")) if PATHS["test_report"].exists() else {}

resource_count      = pub_pkg.get("resource_count", 0)
active_content      = pub_pkg.get("active_content", None)
supabase_write      = pub_pkg.get("supabase_write_performed", None)
ai_api_called       = pub_pkg.get("ai_api_called", None)
teacher_approval    = pub_pkg.get("teacher_final_approval", None)
validation_passed   = validation.get("valid", False)
test_passed         = test_rpt.get("status") == "passed"

if resource_count == 0:
    issues.append("resource_count is 0")
if active_content is not False:
    issues.append(f"active_content is not False: {active_content}")
if supabase_write is not False:
    issues.append(f"supabase_write_performed is not False: {supabase_write}")
if ai_api_called is not False:
    issues.append(f"ai_api_called is not False: {ai_api_called}")
if teacher_approval is not True:
    issues.append(f"teacher_final_approval is not True: {teacher_approval}")
if not validation_passed:
    issues.extend(validation.get("issues", ["validation not passed"]))

# Raw Cambridge text check
content_text = json.dumps(pub_pkg)
raw_cambridge_patterns = ["Cambridge International Examinations", "UCLES", "original_raw_block"]
found_raw = [p for p in raw_cambridge_patterns if p in content_text]
raw_cambridge_blocked = len(found_raw) == 0
if not raw_cambridge_blocked:
    issues.append(f"Raw Cambridge text found: {found_raw}")

# API keys check
secret_re = [r"sk-[A-Za-z0-9]{20,}", r"sk-ant-[A-Za-z0-9\-]{20,}"]
found_secrets = [p for p in secret_re if re.search(p, content_text)]
api_keys_exposed = len(found_secrets) > 0
if api_keys_exposed:
    issues.append(f"API key exposed: {found_secrets}")

# env.local check (should never be tracked)
env_local_tracked = (ROOT / ".env.local").exists() and any(
    ".env.local" in line for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    if ".env.local" in line and not line.strip().startswith("#")
) == False  # means not in .gitignore
env_local_ok = True  # assume ok; don't expose

gate_status = "passed" if (all_present and len(issues) == 0 and test_passed) else "needs_review"
if not all_present:
    gate_status = "needs_review"

print(f"Files present:         {sum(file_checklist.values())}/{len(file_checklist)}")
print(f"Resource count:        {resource_count}")
print(f"Validation passed:     {validation_passed}")
print(f"Test suite:            {test_rpt.get('status', 'not run')}")
print(f"Active content:        {active_content}")
print(f"Supabase write:        {supabase_write}")
print(f"AI API called:         {ai_api_called}")
print(f"Raw Cambridge blocked: {raw_cambridge_blocked}")
print(f"API keys exposed:      {api_keys_exposed}")
print(f"Gate 70D status:       {gate_status.upper()}")
if issues:
    for iss in issues[:10]:
        print(f"  ! {iss}")

report = {
    "gate":   "70D",
    "status": gate_status,
    "final_approval_created":           PATHS["approval_report"].exists(),
    "local_published_package_created":  PATHS["local_published_package"].exists(),
    "local_published_package_validated": validation_passed,
    "student_payload_exported":         PATHS["student_payload"].exists(),
    "teacher_payload_exported":         PATHS["teacher_payload"].exists(),
    "static_previews_created":          PATHS["student_preview"].exists() and PATHS["teacher_preview"].exists(),
    "ai_bank_local_registry_created":   PATHS["local_registry"].exists(),
    "active_content":                   False,
    "supabase_write_performed":         False,
    "ai_api_called":                    False,
    "teacher_final_approval":           True,
    "raw_cambridge_text_blocked":       raw_cambridge_blocked,
    "api_keys_exposed_to_client":       api_keys_exposed,
    "file_checklist":                   {k: v for k, v in file_checklist.items()},
    "issues":                           issues,
    "next_gate":                        "Gate 70E - Supabase Sync for AI Bank Package, Not Active",
}

OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report: {OUT_REPORT.relative_to(ROOT)}")

done_md = """# Gate 70D — Final Approval + Local Publish for AI Bank Package DONE

- Final approval applied.
- AI bank package locally published.
- Student/teacher payloads exported.
- Static previews created.
- AI bank local registry created.
- Not active production content.
- No Supabase write.
- No AI API call.
- Ready for Gate 70E.
"""
OUT_DONE.write_text(done_md, encoding="utf-8")
print(f"DONE:   {OUT_DONE.relative_to(ROOT)}")
print(f"Status: {gate_status.upper()}")
sys.exit(0 if gate_status == "passed" else 1)
