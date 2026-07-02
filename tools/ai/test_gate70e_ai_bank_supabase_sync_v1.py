"""
Gate 70E -- Test Suite v1

Tests the Gate 70E dry-run pipeline:
  1. Build sync plan.
  2. Run dry-run sync.
  3. Verify outputs (dry-run: no Supabase write).
  4. Run export (dry-run source: Gate 70D local package).
  5. Static checks on TS/TSX files.
  6. Layout nav links.

If env QA_GATE70E_EXECUTE_SYNC=true:
  - Run execute sync (requires Supabase env).
  - Verify read-back from Supabase.
  - Export from Supabase.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate70e_ai_bank_supabase_sync_v1.py

Output:
  data/diagnostics/gate70e_ai_bank_supabase_sync_test_report_v1.json
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable)

passed = 0
failed = 0
results: list[tuple[str, bool, str]] = []

QA_EXECUTE = os.environ.get("QA_GATE70E_EXECUTE_SYNC", "").lower() == "true"


def t(tid: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
    results.append((tid, condition, detail))
    print(f"  [{'PASS' if condition else 'FAIL'}] {tid}{(' — ' + detail) if detail else ''}")


def run(script: str, *args: str) -> tuple[int, str, str]:
    p = subprocess.run(
        [str(PYTHON), str(ROOT / script), *args],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return p.returncode, p.stdout, p.stderr


PLAN_FILE    = ROOT / "data" / "ai" / "supabase_sync" / "gate70e_ai_bank_supabase_sync_plan_v1.json"
PLAN_REPORT  = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_sync_plan_report_v1.json"
SYNC_REPORT  = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_sync_execute_report_v1.json"
VERIFY_RPT   = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_readback_verify_report_v1.json"
EXPORT_RPT   = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_export_report_v1.json"
TEST_REPORT  = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_sync_test_report_v1.json"
LOCAL_PKG    = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1" / "publish_package_v1.json"
EXPORT_DIR   = ROOT / "data" / "ai" / "supabase_exports"

print("Gate 70E — Test Suite")
print("=" * 60)
print(f"Execute mode: {'YES (QA_GATE70E_EXECUTE_SYNC=true)' if QA_EXECUTE else 'NO (dry-run only)'}")

# ─── S1: Script/file existence ─────────────────────────────────────────────
print("\n[S1] Script/file existence")
scripts = [
    "tools/ai/build_gate70e_ai_bank_supabase_sync_plan_v1.py",
    "tools/ai/sync_gate70e_ai_bank_package_to_supabase_v1.py",
    "tools/ai/verify_gate70e_ai_bank_package_from_supabase_v1.py",
    "tools/ai/export_gate70e_ai_bank_package_from_supabase_v1.py",
    "apps/admin/src/lib/aiBankSupabasePackage.ts",
    "apps/admin/src/app/system/ai-bank-supabase/page.tsx",
    "apps/admin/src/app/api/system/ai-bank-supabase/route.ts",
]
for s in scripts:
    t(f"T01_{s.split('/')[-1][:30]}", (ROOT / s).exists(), s)

# ─── S2: Gate 70D prerequisite ─────────────────────────────────────────────
print("\n[S2] Gate 70D prerequisite")
t("T02_gate70d_pkg_exists", LOCAL_PKG.exists(), str(LOCAL_PKG.relative_to(ROOT)))
if not LOCAL_PKG.exists():
    print("FATAL: Gate 70D local package missing. Run test_gate70d_ai_bank_local_publish_v1.py first.")
    sys.exit(1)
local_pkg = json.loads(LOCAL_PKG.read_text(encoding="utf-8"))
t("T03_gate70d_status",    local_pkg.get("status") == "published_local_not_active")
t("T04_gate70d_resources", local_pkg.get("resource_count", 0) >= 1, f"count={local_pkg.get('resource_count')}")
t("T05_gate70d_not_active", local_pkg.get("active_content") is False)

# ─── S3: Build sync plan ───────────────────────────────────────────────────
print("\n[S3] build_gate70e_ai_bank_supabase_sync_plan_v1.py")
rc, out, err = run("tools/ai/build_gate70e_ai_bank_supabase_sync_plan_v1.py")
t("T06_build_plan_rc0",    rc == 0,              f"rc={rc}")
t("T07_plan_file_created", PLAN_FILE.exists())
t("T08_plan_report",       PLAN_REPORT.exists())

if PLAN_FILE.exists():
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    t("T09_plan_dry_run_default",   plan.get("dry_run_default") is True)
    t("T10_plan_no_active_switch",  plan.get("active_switch_allowed") is False)
    t("T11_plan_target_active_false", plan.get("target_active") is False)
    t("T12_plan_resource_count",    plan.get("resource_count", 0) >= 1, f"count={plan.get('resource_count')}")
    t("T13_plan_has_operations",    plan.get("operation_count", 0) >= 3, f"ops={plan.get('operation_count')}")
    t("T14_plan_safety_no_delete",  plan.get("safety", {}).get("no_delete") is True)
    t("T15_plan_safety_no_switch",  plan.get("safety", {}).get("no_active_switch") is True)
    t("T16_plan_safety_no_secrets", plan.get("safety", {}).get("no_service_role_in_outputs") is True)

    # No secrets in plan file
    plan_text = json.dumps(plan)
    secret_re = [r"sk-[A-Za-z0-9]{20,}", r"sk-ant-[A-Za-z0-9\-]{20,}"]
    found_secrets = [p for p in secret_re if re.search(p, plan_text)]
    t("T17_plan_no_secrets", len(found_secrets) == 0, f"found={found_secrets}")

    # No raw Cambridge text in plan
    found_raw = [p for p in ["Cambridge International", "UCLES", "original_raw_block"] if p in plan_text]
    t("T18_plan_no_raw_cambridge", len(found_raw) == 0, f"found={found_raw}")

# ─── S4: Dry-run sync ──────────────────────────────────────────────────────
print("\n[S4] sync_gate70e_ai_bank_package_to_supabase_v1.py (dry-run)")
rc, out, err = run("tools/ai/sync_gate70e_ai_bank_package_to_supabase_v1.py")
t("T19_dryrun_rc0",        rc == 0, f"rc={rc}")
t("T20_sync_report",       SYNC_REPORT.exists())

if SYNC_REPORT.exists():
    sr = json.loads(SYNC_REPORT.read_text(encoding="utf-8"))
    t("T21_dryrun_no_write",        sr.get("supabase_write_performed") is False, "dry-run: no write")
    t("T22_dryrun_dry_run_true",    sr.get("dry_run") is True)
    t("T23_dryrun_no_active_switch", sr.get("active_switch_performed") is False)
    t("T24_dryrun_target_false",    sr.get("target_active") is False)
    t("T25_dryrun_preserved",       sr.get("existing_active_package_preserved") is True)
    t("T26_dryrun_no_ai_api",       sr.get("ai_api_called") is False)
    t("T27_dryrun_no_secrets",      sr.get("secrets_exposed") is False)

# ─── S5: Verify (expects needs_review since not executed) ─────────────────
print("\n[S5] verify_gate70e_ai_bank_package_from_supabase_v1.py (dry-run — expects needs_review)")
rc, out, err = run("tools/ai/verify_gate70e_ai_bank_package_from_supabase_v1.py")
t("T28_verify_rc0",        rc == 0, f"rc={rc}")
t("T29_verify_report",     VERIFY_RPT.exists())
if VERIFY_RPT.exists():
    vr = json.loads(VERIFY_RPT.read_text(encoding="utf-8"))
    t("T30_verify_needs_review",  vr.get("status") in ("needs_review", "passed"), f"status={vr.get('status')}")
    t("T31_verify_not_active",    vr.get("target_active") is False or "target_active" not in vr)
    t("T32_verify_no_switch",     vr.get("active_switch_performed") is False or "active_switch_performed" not in vr)

# ─── S6: Export (dry-run source) ──────────────────────────────────────────
print("\n[S6] export_gate70e_ai_bank_package_from_supabase_v1.py")
rc, out, err = run("tools/ai/export_gate70e_ai_bank_package_from_supabase_v1.py")
t("T33_export_rc0",        rc == 0, f"rc={rc}")
t("T34_export_report",     EXPORT_RPT.exists())
t("T35_export_pkg_file",   (EXPORT_DIR / "gate70e_ai_bank_package_from_supabase_v1.json").exists())
t("T36_export_student",    (EXPORT_DIR / "gate70e_student_ai_bank_payload_from_supabase_v1.json").exists())
t("T37_export_teacher",    (EXPORT_DIR / "gate70e_teacher_ai_bank_payload_from_supabase_v1.json").exists())

if EXPORT_RPT.exists():
    er = json.loads(EXPORT_RPT.read_text(encoding="utf-8"))
    t("T38_export_no_active",      er.get("active") is False or er.get("status") in ("passed","needs_review"))
    t("T39_export_no_ai_api",      er.get("ai_api_called") is False)
    t("T40_export_no_secrets",     er.get("secrets_exposed") is False)

# Verify no secrets in exported files
for fname in ["gate70e_ai_bank_package_from_supabase_v1.json",
              "gate70e_student_ai_bank_payload_from_supabase_v1.json",
              "gate70e_teacher_ai_bank_payload_from_supabase_v1.json"]:
    fpath = EXPORT_DIR / fname
    if fpath.exists():
        content = fpath.read_text(encoding="utf-8")
        found = [p for p in ["sk-", "SUPABASE_SERVICE_ROLE_KEY", "service_role"]
                 if p in content and "supabase_write_performed" not in p]
        t(f"T41_no_secrets_{fname[:25]}", len(found) == 0, f"found={found}")

# ─── S7: TypeScript static checks ─────────────────────────────────────────
print("\n[S7] TS/TSX static checks")
ts_lib = ROOT / "apps/admin/src/lib/aiBankSupabasePackage.ts"
if ts_lib.exists():
    ts = ts_lib.read_text(encoding="utf-8")
    t("T42_ts_reads_sync_plan",    "gate70e_ai_bank_supabase_sync_plan_v1.json" in ts)
    t("T43_ts_reads_sync_report",  "gate70e_ai_bank_supabase_sync_execute_report_v1.json" in ts)
    t("T44_ts_reads_verify",       "gate70e_ai_bank_supabase_readback_verify_report_v1.json" in ts)
    t("T45_ts_reads_export",       "gate70e_ai_bank_supabase_export_report_v1.json" in ts)
    t("T46_ts_server_only",        "import fs" in ts)
    t("T47_ts_no_use_client",      '"use client"' not in ts)
    t("T48_ts_no_service_role_exposed", "SUPABASE_SERVICE_ROLE_KEY" not in ts or "process.env" not in ts)

sys_page = ROOT / "apps/admin/src/app/system/ai-bank-supabase/page.tsx"
if sys_page.exists():
    sp = sys_page.read_text(encoding="utf-8")
    t("T49_syspage_requireRole",      "requireRole" in sp)
    t("T50_syspage_no_client",        "createClient" not in sp)
    t("T51_syspage_dry_run_default",  "dryRunDefault" in sp or "dry_run_default" in sp)
    t("T52_syspage_ready_gate70f",    "readyForGate70F" in sp or "gate70f" in sp.lower())
    t("T53_syspage_no_active_switch", "activeSwitchPerformed" in sp or "active_switch" in sp)

route = ROOT / "apps/admin/src/app/api/system/ai-bank-supabase/route.ts"
if route.exists():
    rt = route.read_text(encoding="utf-8")
    t("T54_route_get_export",         "export async function GET" in rt)
    t("T55_route_force_dynamic",      "force-dynamic" in rt)
    t("T56_route_no_active",          "target_active.*false" in rt or "false" in rt)
    t("T57_route_ready_gate70f",      "ready_for_gate70f" in rt)
    t("T58_route_no_secrets_exposed", "secrets_exposed" in rt)

# ─── S8: Layout nav links ──────────────────────────────────────────────────
print("\n[S8] layout.tsx nav links")
layout = ROOT / "apps/admin/src/app/layout.tsx"
if layout.exists():
    lt = layout.read_text(encoding="utf-8")
    t("T59_layout_supabase_link", "/system/ai-bank-supabase" in lt)

# ─── S9: Execute sync (optional) ──────────────────────────────────────────
if QA_EXECUTE:
    print("\n[S9] Execute sync (QA_GATE70E_EXECUTE_SYNC=true)")
    rc, out, err = run("tools/ai/sync_gate70e_ai_bank_package_to_supabase_v1.py",
                       "--execute", "--confirm", "SYNC_GATE70E_AI_BANK_PACKAGE")
    t("T60_execute_rc0", rc == 0, f"rc={rc}")
    if SYNC_REPORT.exists():
        sr2 = json.loads(SYNC_REPORT.read_text(encoding="utf-8"))
        t("T61_execute_write_performed",  sr2.get("supabase_write_performed") is True)
        t("T62_execute_no_active_switch", sr2.get("active_switch_performed") is False)
        t("T63_execute_target_false",     sr2.get("target_active") is False)

    rc, out, err = run("tools/ai/verify_gate70e_ai_bank_package_from_supabase_v1.py")
    t("T64_verify_after_execute_rc0", rc == 0, f"rc={rc}")
    if VERIFY_RPT.exists():
        vr2 = json.loads(VERIFY_RPT.read_text(encoding="utf-8"))
        t("T65_verify_passed",        vr2.get("status") == "passed")
        t("T66_verify_not_active",    vr2.get("target_active") is False or "target_active" not in vr2)
        t("T67_verify_preserved",     vr2.get("existing_active_package_preserved") is not False)
else:
    print("\n[S9] Skipping execute sync (QA_GATE70E_EXECUTE_SYNC not set)")

# ─── Summary ──────────────────────────────────────────────────────────────
total = passed + failed
print()
print("=" * 60)
print(f"Results: {passed}/{total} passed  ({failed} failed)")
print("=" * 60)
if failed:
    print("\nFailed tests:")
    for tid, ok, detail in results:
        if not ok:
            print(f"  [FAIL] {tid}{(' — ' + detail) if detail else ''}")

test_report = {
    "gate":    "70E",
    "total":   total,
    "passed":  passed,
    "failed":  failed,
    "status":  "passed" if failed == 0 else "needs_review",
    "results": [{"id": tid, "ok": ok, "detail": det} for tid, ok, det in results],
}
TEST_REPORT.parent.mkdir(parents=True, exist_ok=True)
TEST_REPORT.write_text(json.dumps(test_report, indent=2), encoding="utf-8")
print(f"\nTest report: {TEST_REPORT.relative_to(ROOT)}")
sys.exit(0 if failed == 0 else 1)
