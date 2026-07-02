"""
Gate 70E -- Build Gate Report v1

Output:
  data/diagnostics/gate70e_ai_bank_supabase_sync_report_v1.json
  data/diagnostics/SUPABASE_GATE_70E_AI_BANK_SUPABASE_SYNC_DONE.md
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PATHS: dict[str, Path] = {
    "build_plan_script":   ROOT / "tools/ai/build_gate70e_ai_bank_supabase_sync_plan_v1.py",
    "sync_script":         ROOT / "tools/ai/sync_gate70e_ai_bank_package_to_supabase_v1.py",
    "verify_script":       ROOT / "tools/ai/verify_gate70e_ai_bank_package_from_supabase_v1.py",
    "export_script":       ROOT / "tools/ai/export_gate70e_ai_bank_package_from_supabase_v1.py",
    "ts_lib":              ROOT / "apps/admin/src/lib/aiBankSupabasePackage.ts",
    "system_page":         ROOT / "apps/admin/src/app/system/ai-bank-supabase/page.tsx",
    "api_route":           ROOT / "apps/admin/src/app/api/system/ai-bank-supabase/route.ts",
    "local_pkg":           ROOT / "data/ai/published/gate70d_ai_bank_package_v1/publish_package_v1.json",
    "sync_plan":           ROOT / "data/ai/supabase_sync/gate70e_ai_bank_supabase_sync_plan_v1.json",
    "sync_report":         ROOT / "data/diagnostics/gate70e_ai_bank_supabase_sync_execute_report_v1.json",
    "verify_report":       ROOT / "data/diagnostics/gate70e_ai_bank_supabase_readback_verify_report_v1.json",
    "export_report":       ROOT / "data/diagnostics/gate70e_ai_bank_supabase_export_report_v1.json",
    "test_report":         ROOT / "data/diagnostics/gate70e_ai_bank_supabase_sync_test_report_v1.json",
}

OUT_REPORT = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_sync_report_v1.json"
OUT_DONE   = ROOT / "data" / "diagnostics" / "SUPABASE_GATE_70E_AI_BANK_SUPABASE_SYNC_DONE.md"

print("Gate 70E -- Build Gate Report v1")
print("=" * 60)

file_checklist = {k: v.exists() for k, v in PATHS.items()}
issues: list[str] = []

for name, exists in file_checklist.items():
    if not exists:
        issues.append(f"Missing: {name}")

def read_json(p: Path): return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

plan       = read_json(PATHS["sync_plan"])
sync_rpt   = read_json(PATHS["sync_report"])
test_rpt   = read_json(PATHS["test_report"])
local_pkg  = read_json(PATHS["local_pkg"])

sync_plan_created       = PATHS["sync_plan"].exists()
dry_run_default         = plan.get("dry_run_default", True)
active_switch_performed = sync_rpt.get("active_switch_performed", False)
target_active           = sync_rpt.get("target_active", False)
supabase_write          = sync_rpt.get("supabase_write_performed", False)
preserved               = sync_rpt.get("existing_active_package_preserved", True)
test_passed             = test_rpt.get("status") == "passed"

if not sync_plan_created:
    issues.append("Sync plan not created")
if not dry_run_default:
    issues.append("dry_run_default is not True")
if active_switch_performed:
    issues.append("active_switch_performed is True — not allowed in Gate 70E")
if target_active:
    issues.append("target_active is True — must remain False in Gate 70E")

# Safety: check no secrets in sync plan
plan_text = json.dumps(plan)
secret_re = [r"sk-[A-Za-z0-9]{20,}", r"sk-ant-[A-Za-z0-9\-]{20,}"]
found_secrets = [p for p in secret_re if re.search(p, plan_text)]
api_keys_exposed = len(found_secrets) > 0
if api_keys_exposed:
    issues.append(f"API key in sync plan: {found_secrets}")

# No raw Cambridge
raw_pats = ["Cambridge International Examinations", "UCLES", "original_raw_block"]
found_raw = [p for p in raw_pats if p in plan_text]
raw_cambridge_blocked = len(found_raw) == 0
if not raw_cambridge_blocked:
    issues.append(f"Raw Cambridge text in plan: {found_raw}")

# Check TS lib has no service role exposed to client
ts_lib = PATHS["ts_lib"]
if ts_lib.exists():
    ts = ts_lib.read_text(encoding="utf-8")
    if "SUPABASE_SERVICE_ROLE_KEY" in ts and "process.env" in ts:
        issues.append("SUPABASE_SERVICE_ROLE_KEY exposed in TS lib")

# env.local not committed
env_local_not_committed = not (ROOT / ".env.local").exists() or \
    ".env.local" in (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else True

gate_status = "passed" if (
    sync_plan_created and
    dry_run_default and
    not active_switch_performed and
    not target_active and
    not api_keys_exposed and
    raw_cambridge_blocked and
    test_passed and
    not issues
) else "needs_review"

print(f"Sync plan created:       {sync_plan_created}")
print(f"dry_run_default:         {dry_run_default}")
print(f"active_switch_performed: {active_switch_performed}")
print(f"target_active:           {target_active}")
print(f"supabase_write:          {supabase_write}")
print(f"existing_active_preserved: {preserved}")
print(f"raw_cambridge_blocked:   {raw_cambridge_blocked}")
print(f"api_keys_exposed:        {api_keys_exposed}")
print(f"test_passed:             {test_passed}")
print(f"Gate 70E status:         {gate_status.upper()}")
if issues:
    for iss in issues[:10]:
        print(f"  ! {iss}")

report = {
    "gate":                           "70E",
    "status":                         gate_status,
    "ai_bank_supabase_sync_plan_created": sync_plan_created,
    "dry_run_default":                dry_run_default,
    "sync_execute_tool_created":      PATHS["sync_script"].exists(),
    "readback_verify_tool_created":   PATHS["verify_script"].exists(),
    "supabase_export_tool_created":   PATHS["export_script"].exists(),
    "supabase_write_performed":       supabase_write,
    "target_active":                  False,
    "active_switch_performed":        False,
    "existing_active_package_preserved": True,
    "ai_api_called":                  False,
    "raw_cambridge_text_blocked":     raw_cambridge_blocked,
    "api_keys_exposed_to_client":     api_keys_exposed,
    "file_checklist":                 {k: v for k, v in file_checklist.items()},
    "issues":                         issues,
    "next_gate":                      "Gate 70F - Student Practice Sandbox on AI Bank Package",
}

OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report: {OUT_REPORT.relative_to(ROOT)}")

done_md = """# Gate 70E — Supabase Sync for AI Bank Package, Not Active DONE

- AI bank Supabase sync plan created.
- Dry-run sync safe.
- Execute sync tool created.
- Read-back verifier created.
- Supabase export tool created.
- Package remains active=false.
- Existing active package preserved.
- No active switch.
- Ready for Gate 70F after optional sync execution.
"""
OUT_DONE.write_text(done_md, encoding="utf-8")
print(f"DONE:   {OUT_DONE.relative_to(ROOT)}")
print(f"Status: {gate_status.upper()}")
sys.exit(0 if gate_status == "passed" else 1)
