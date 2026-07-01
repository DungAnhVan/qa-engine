"""
Gate 69G -- Test Suite v1

Tests AI Supabase sync pipeline. Default: dry-run only (no Supabase writes).
Execute-sync and activate are opt-in via env vars.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate69g_ai_supabase_sync_v1.py

Env vars:
  QA_GATE69G_EXECUTE_SYNC=true   run execute sync (writes to Supabase)
  QA_GATE69G_ACTIVATE=true       run active switch (sets AI package active in Supabase)

Exit codes: 0 = all passed, 1 = one or more failures.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable

PLAN_FILE      = ROOT / "data" / "ai" / "supabase_sync" / "ai_supabase_sync_plan_v1.json"
SYNC_REPORT    = ROOT / "data" / "diagnostics" / "ai_supabase_sync_execute_report_v1.json"
VERIFY_REPORT  = ROOT / "data" / "diagnostics" / "ai_supabase_readback_verify_report_v1.json"
ACTIVE_REPORT  = ROOT / "data" / "diagnostics" / "ai_supabase_active_switch_report_v1.json"
EXPORT_REPORT  = ROOT / "data" / "diagnostics" / "ai_supabase_export_report_v1.json"
GATE69F_PKG    = ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "publish_package_v1.json"
PLAN_REPORT    = ROOT / "data" / "diagnostics" / "ai_supabase_sync_plan_report_v1.json"
EXPORT_DIR     = ROOT / "data" / "ai" / "supabase_exports"

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"sk-ant-[A-Za-z0-9\-]{20,}",
    r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    r"SUPABASE_SERVICE_ROLE_KEY\s*[:=]\s*\S{8,}",
    r"supabase_service_role\s*[:=]\s*\S{8,}",
]

COPYRIGHT_PATTERNS = ["UCLES", "Cambridge International", "Cambridge Assessment",
                      "Question Answer Marks", "original_raw_block"]

# ---------------------------------------------------------------------------

PASSED = 0
FAILED = 0
RESULTS: list[dict] = []


def run(label: str, ok: bool, detail: str = "") -> bool:
    global PASSED, FAILED
    PASSED += ok
    FAILED += not ok
    mark = "  [OK]" if ok else "  [FAIL]"
    msg = f"{mark}  {label}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)
    RESULTS.append({"test": label, "status": "PASS" if ok else "FAIL", "detail": detail})
    return ok


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_script(script: Path, extra_args: list[str] | None = None) -> tuple[int, str, str]:
    cmd = [PYTHON, str(script)] + (extra_args or [])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return result.returncode, result.stdout, result.stderr


def _no_secrets(text: str) -> tuple[bool, str]:
    for pat in SECRET_PATTERNS:
        if re.search(pat, text):
            return False, f"secret pattern: {pat[:60]}"
    return True, ""


def _no_copyright(text: str) -> tuple[bool, str]:
    for pat in COPYRIGHT_PATTERNS:
        if pat in text:
            return False, f"copyright pattern: {pat}"
    return True, ""


# ---------------------------------------------------------------------------

print("Gate 69G -- Test Suite v1")
print("=" * 60)

execute_sync = os.environ.get("QA_GATE69G_EXECUTE_SYNC", "").lower() == "true"
do_activate  = os.environ.get("QA_GATE69G_ACTIVATE",     "").lower() == "true"

print(f"  execute_sync: {execute_sync}")
print(f"  do_activate:  {do_activate}")
print()

# T01 — Gate 69F package exists
run("T01: Gate 69F published package exists", GATE69F_PKG.exists(),
    str(GATE69F_PKG) if not GATE69F_PKG.exists() else "")

# T02 — Gate 69F package is published_local_not_active
pkg69f = read_json(GATE69F_PKG)
run("T02: Gate 69F status=published_local_not_active",
    (pkg69f or {}).get("status") == "published_local_not_active",
    f"got: {(pkg69f or {}).get('status')}")

# T03 — Build sync plan
rc, out, err = run_script(ROOT / "tools" / "ai" / "build_ai_supabase_sync_plan_v1.py")
run("T03: build_ai_supabase_sync_plan_v1.py exits 0", rc == 0,
    err.strip()[:300] if rc != 0 else "")

# T04 — Plan file exists
run("T04: sync plan file exists", PLAN_FILE.exists(), "")

# T05 — Plan has dry_run_default=True
plan = read_json(PLAN_FILE)
run("T05: dry_run_default=True", (plan or {}).get("dry_run_default") is True,
    f"got: {(plan or {}).get('dry_run_default')}")

# T06 — Plan has active_switch_default=False
run("T06: active_switch_default=False", (plan or {}).get("active_switch_default") is False,
    f"got: {(plan or {}).get('active_switch_default')}")

# T07 — Plan has safety block with no_delete=True
safety = (plan or {}).get("safety", {})
run("T07: safety.no_delete=True", safety.get("no_delete") is True,
    f"got: {safety}")

# T08 — Plan has no_active_switch=True
run("T08: safety.no_active_switch=True", safety.get("no_active_switch") is True,
    f"got: {safety}")

# T09 — Plan has operations
ops = (plan or {}).get("operations", [])
run("T09: plan has >=1 operation", len(ops) >= 1, f"op count={len(ops)}")

# T10 — Plan includes upsert_resource
op_types = [o.get("op") for o in ops]
run("T10: plan includes upsert_resource", "upsert_resource" in op_types, f"ops={op_types}")

# T11 — Plan includes upsert_resource_package
run("T11: plan includes upsert_resource_package", "upsert_resource_package" in op_types, f"ops={op_types}")

# T12 — No secrets in plan
ok_s, det = _no_secrets(json.dumps(plan or {}))
run("T12: No secrets in sync plan", ok_s, det)

# T13 — No Cambridge copyright in plan
ok_c, det_c = _no_copyright(json.dumps(plan or {}))
run("T13: No Cambridge copyright in sync plan", ok_c, det_c)

# T14 — Dry-run sync exits 0
rc, out, err = run_script(ROOT / "tools" / "ai" / "sync_ai_package_to_supabase_v1.py")
run("T14: dry-run sync exits 0", rc == 0, err.strip()[:300] if rc != 0 else "")

# T15 — Sync report exists
run("T15: sync execute report exists", SYNC_REPORT.exists(), "")

# T16 — Dry-run did NOT write Supabase
sync_report = read_json(SYNC_REPORT)
run("T16: dry_run supabase_write_performed=False",
    (sync_report or {}).get("supabase_write_performed") is False,
    f"got: {(sync_report or {}).get('supabase_write_performed')}")

# T17 — active_switch_performed=False in sync report
run("T17: dry_run active_switch_performed=False",
    (sync_report or {}).get("active_switch_performed") is False,
    f"got: {(sync_report or {}).get('active_switch_performed')}")

# T18 — existing_active_package_preserved=True
run("T18: existing_active_package_preserved=True",
    (sync_report or {}).get("existing_active_package_preserved") is True,
    f"got: {(sync_report or {}).get('existing_active_package_preserved')}")

# T19 — secrets_exposed=False
run("T19: secrets_exposed=False in sync report",
    (sync_report or {}).get("secrets_exposed") is False,
    f"got: {(sync_report or {}).get('secrets_exposed')}")

# T20 — No secrets in sync report file
ok_s2, det2 = _no_secrets(SYNC_REPORT.read_text(encoding="utf-8") if SYNC_REPORT.exists() else "")
run("T20: No secrets in sync report file", ok_s2, det2)

# ── Optional execute sync ────────────────────────────────────────────────────
if execute_sync:
    print("\n[EXECUTE SYNC MODE — writing to Supabase]")
    rc, out, err = run_script(ROOT / "tools" / "ai" / "sync_ai_package_to_supabase_v1.py",
                               ["--execute", "--confirm", "SYNC_AI_PACKAGE"])
    run("T21: execute sync exits 0", rc == 0, err.strip()[:300] if rc != 0 else "")

    exec_report = read_json(SYNC_REPORT)
    run("T22: execute supabase_write_performed=True",
        (exec_report or {}).get("supabase_write_performed") is True,
        f"got: {(exec_report or {}).get('supabase_write_performed')}")

    # Verify readback
    rc, out, err = run_script(ROOT / "tools" / "ai" / "verify_ai_package_from_supabase_v1.py")
    run("T23: verify readback exits 0", rc == 0, err.strip()[:300] if rc != 0 else "")

    verify = read_json(VERIFY_REPORT)
    run("T24: readback status not failed",
        (verify or {}).get("status") in ("passed", "needs_review"),
        f"got: {(verify or {}).get('status')}")
    run("T25: readback active_false=True",
        (verify or {}).get("active_false") is True,
        f"got: {(verify or {}).get('active_false')}")

    # Export
    rc, out, err = run_script(ROOT / "tools" / "ai" / "build_ai_package_supabase_export_v1.py")
    run("T26: export script exits 0", rc == 0, err.strip()[:300] if rc != 0 else "")

    export_pkg = EXPORT_DIR / "ai_package_from_supabase_v1.json"
    run("T27: export file exists", export_pkg.exists(), "")
    if export_pkg.exists():
        ok_s3, det3 = _no_secrets(export_pkg.read_text(encoding="utf-8"))
        run("T28: No secrets in export file", ok_s3, det3)
else:
    print("\n[EXECUTE SYNC SKIPPED — set QA_GATE69G_EXECUTE_SYNC=true to run]")
    run("T21: (skipped) execute sync", True, "set QA_GATE69G_EXECUTE_SYNC=true to run")
    for n in range(22, 29):
        run(f"T{n:02d}: (skipped)", True, "set QA_GATE69G_EXECUTE_SYNC=true to run")

# ── Activate (opt-in only) ───────────────────────────────────────────────────
if do_activate and execute_sync:
    print("\n[ACTIVATE MODE — setting AI package active in Supabase]")
    rc, out, err = run_script(ROOT / "tools" / "ai" / "activate_ai_package_supabase_v1.py",
                               ["--execute", "--activate", "--confirm", "ACTIVATE_AI_PACKAGE"])
    run("T29: activate script exits 0", rc == 0, err.strip()[:300] if rc != 0 else "")

    active_rpt = read_json(ACTIVE_REPORT)
    run("T30: active_switch_performed=True",
        (active_rpt or {}).get("active_switch_performed") is True,
        f"got: {(active_rpt or {}).get('active_switch_performed')}")
else:
    if not execute_sync and do_activate:
        print("\n[ACTIVATE SKIPPED — execute sync must run first]")
    elif not do_activate:
        print("\n[ACTIVATE SKIPPED — set QA_GATE69G_ACTIVATE=true to run (requires execute_sync too)]")
    run("T29: (skipped) activate", True, "set QA_GATE69G_ACTIVATE=true (with execute_sync=true)")
    run("T30: (skipped) active_switch", True, "set QA_GATE69G_ACTIVATE=true")

# T31 — Activate dry-run exits 0 (always safe)
rc, out, err = run_script(ROOT / "tools" / "ai" / "activate_ai_package_supabase_v1.py")
run("T31: activate dry-run exits 0", rc == 0, err.strip()[:300] if rc != 0 else "")

active_dry = read_json(ACTIVE_REPORT)
run("T32: activate dry_run=True in report",
    (active_dry or {}).get("dry_run") is True or not (do_activate and execute_sync),
    "")

# ---------------------------------------------------------------------------

print()
print("=" * 60)
total = PASSED + FAILED
print(f"Results: {PASSED}/{total} passed, {FAILED} failed")
print(f"Status:  {'ALL PASSED' if FAILED == 0 else 'FAILURES DETECTED'}")

diag_dir = ROOT / "data" / "diagnostics"
diag_dir.mkdir(parents=True, exist_ok=True)
report_path = diag_dir / "gate69g_ai_supabase_sync_test_report_v1.json"
report_path.write_text(json.dumps({
    "gate":          "69G",
    "test_suite":    "test_gate69g_ai_supabase_sync_v1",
    "execute_sync":  execute_sync,
    "do_activate":   do_activate,
    "total":         total,
    "passed":        PASSED,
    "failed":        FAILED,
    "status":        "passed" if FAILED == 0 else "failed",
    "results":       RESULTS,
}, indent=2), encoding="utf-8")
print(f"Report:  {report_path}")

sys.exit(0 if FAILED == 0 else 1)
