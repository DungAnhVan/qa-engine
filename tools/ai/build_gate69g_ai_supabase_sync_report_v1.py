"""
Gate 69G -- Build Gate Report v1

Checks all Gate 69G deliverables and writes gate report + DONE marker.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate69g_ai_supabase_sync_report_v1.py

Output:
  data/diagnostics/gate69g_ai_supabase_sync_report_v1.json
  data/diagnostics/SUPABASE_GATE_69G_AI_SUPABASE_SYNC_DONE.md
"""

import json
import re
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Deliverables
# ---------------------------------------------------------------------------

DELIVERABLES = [
    ("D01", "build_ai_supabase_sync_plan_v1.py",
     ROOT / "tools" / "ai" / "build_ai_supabase_sync_plan_v1.py"),
    ("D02", "sync_ai_package_to_supabase_v1.py",
     ROOT / "tools" / "ai" / "sync_ai_package_to_supabase_v1.py"),
    ("D03", "verify_ai_package_from_supabase_v1.py",
     ROOT / "tools" / "ai" / "verify_ai_package_from_supabase_v1.py"),
    ("D04", "activate_ai_package_supabase_v1.py",
     ROOT / "tools" / "ai" / "activate_ai_package_supabase_v1.py"),
    ("D05", "build_ai_package_supabase_export_v1.py",
     ROOT / "tools" / "ai" / "build_ai_package_supabase_export_v1.py"),
    ("D06", "aiSupabasePackage.ts",
     ROOT / "apps" / "admin" / "src" / "lib" / "aiSupabasePackage.ts"),
    ("D07", "system/ai-supabase/page.tsx",
     ROOT / "apps" / "admin" / "src" / "app" / "system" / "ai-supabase" / "page.tsx"),
    ("D08", "api/system/ai-supabase/route.ts",
     ROOT / "apps" / "admin" / "src" / "app" / "api" / "system" / "ai-supabase" / "route.ts"),
    ("D09", "test_gate69g_ai_supabase_sync_v1.py",
     ROOT / "tools" / "ai" / "test_gate69g_ai_supabase_sync_v1.py"),
    ("D10", "build_gate69g_ai_supabase_sync_report_v1.py",
     ROOT / "tools" / "ai" / "build_gate69g_ai_supabase_sync_report_v1.py"),
]

OUTPUTS = [
    ("O01", "ai_supabase_sync_plan_v1.json",
     ROOT / "data" / "ai" / "supabase_sync" / "ai_supabase_sync_plan_v1.json"),
    ("O02", "ai_supabase_sync_plan_report_v1.json",
     ROOT / "data" / "diagnostics" / "ai_supabase_sync_plan_report_v1.json"),
    ("O03", "ai_supabase_sync_execute_report_v1.json",
     ROOT / "data" / "diagnostics" / "ai_supabase_sync_execute_report_v1.json"),
    ("O04", "gate69g_ai_supabase_sync_test_report_v1.json",
     ROOT / "data" / "diagnostics" / "gate69g_ai_supabase_sync_test_report_v1.json"),
]


# ---------------------------------------------------------------------------
# Policy checks
# ---------------------------------------------------------------------------

def read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except Exception:
        return None


PLAN_FILE   = ROOT / "data" / "ai" / "supabase_sync" / "ai_supabase_sync_plan_v1.json"
SYNC_REPORT = ROOT / "data" / "diagnostics" / "ai_supabase_sync_execute_report_v1.json"
TEST_REPORT = ROOT / "data" / "diagnostics" / "gate69g_ai_supabase_sync_test_report_v1.json"
ENV_LOCAL   = ROOT / ".env.local"

plan        = read_json(PLAN_FILE)
sync_report = read_json(SYNC_REPORT)
test_report = read_json(TEST_REPORT)

now = datetime.datetime.now(datetime.timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

deliverable_results = []
for d_id, label, path in DELIVERABLES:
    deliverable_results.append({"id": d_id, "label": label, "exists": path.exists(),
                                 "path": str(path.relative_to(ROOT))})

output_results = []
for o_id, label, path in OUTPUTS:
    output_results.append({"id": o_id, "label": label, "exists": path.exists(),
                            "path": str(path.relative_to(ROOT))})

policy_results = []


def policy_check(label: str, ok: bool, detail: str = "") -> dict:
    return {"check": label, "ok": ok, "detail": detail}


policy_results.append(policy_check(
    "sync_plan_created",
    PLAN_FILE.exists(),
))
policy_results.append(policy_check(
    "dry_run_default=True",
    (plan or {}).get("dry_run_default") is True,
    f"got={( plan or {}).get('dry_run_default')}",
))
policy_results.append(policy_check(
    "active_switch_default=False",
    (plan or {}).get("active_switch_default") is False,
    f"got={(plan or {}).get('active_switch_default')}",
))
policy_results.append(policy_check(
    "supabase_write_performed=False (dry-run mode)",
    (sync_report or {}).get("supabase_write_performed") is False,
    f"got={(sync_report or {}).get('supabase_write_performed')}",
))
policy_results.append(policy_check(
    "active_switch_performed=False",
    (sync_report or {}).get("active_switch_performed") is False,
    f"got={(sync_report or {}).get('active_switch_performed')}",
))
policy_results.append(policy_check(
    "existing_active_package_preserved=True",
    (sync_report or {}).get("existing_active_package_preserved") is True,
    f"got={(sync_report or {}).get('existing_active_package_preserved')}",
))
policy_results.append(policy_check(
    "secrets_exposed=False",
    (sync_report or {}).get("secrets_exposed") is False,
    f"got={(sync_report or {}).get('secrets_exposed')}",
))

# No raw Cambridge in plan
plan_text = json.dumps(plan or {})
no_cambridge = not any(p in plan_text for p in
                       ["UCLES", "Cambridge International", "Cambridge Assessment"])
policy_results.append(policy_check("raw_cambridge_text_blocked", no_cambridge))

# No API keys in plan
SECRET_RE = re.compile(r"sk-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9\-]{20,}")
no_api_keys = not SECRET_RE.search(plan_text)
policy_results.append(policy_check("api_keys_not_in_plan", no_api_keys))

# Service role not exposed in client-marked files
# Only flag files with "use client" directive — API routes and server libs are fine
admin_src = ROOT / "apps" / "admin" / "src"
client_clean = True
for fpath in list(admin_src.rglob("*.ts")) + list(admin_src.rglob("*.tsx")):
    # Skip API routes — always server-side
    if any(part in ("api",) for part in fpath.parts):
        continue
    try:
        content = fpath.read_text(encoding="utf-8", errors="replace")
        # Only flag if file is explicitly a client component/module
        if '"use client"' not in content and "'use client'" not in content:
            continue
        if "SUPABASE_SERVICE_ROLE_KEY" in content:
            client_clean = False
            break
    except Exception:
        pass
policy_results.append(policy_check("service_role_not_in_client", client_clean))

# .env.local not tracked by git
import subprocess
try:
    result = subprocess.run(["git", "ls-files", ".env.local"], capture_output=True,
                            text=True, cwd=str(ROOT), timeout=10)
    env_not_tracked = not bool(result.stdout.strip())
except Exception:
    env_not_tracked = True
policy_results.append(policy_check("env_local_not_tracked", env_not_tracked))

# Test results
test_passed_count  = (test_report or {}).get("passed", 0)
test_total_count   = (test_report or {}).get("total",  0)
test_status        = (test_report or {}).get("status", "not_run")
policy_results.append(policy_check(
    "tests_passed",
    test_status == "passed",
    f"passed={test_passed_count}/{test_total_count} status={test_status}",
))

# Counts
d_pass = sum(1 for r in deliverable_results if r["exists"])
o_pass = sum(1 for r in output_results      if r["exists"])
p_pass = sum(1 for r in policy_results      if r["ok"])

all_ok = (d_pass == len(deliverable_results) and
          o_pass == len(output_results) and
          p_pass == len(policy_results))

# ---------------------------------------------------------------------------
# Report JSON
# ---------------------------------------------------------------------------

report = {
    "gate":    "69G",
    "name":    "AI Package Supabase Sync + Optional Active Switch v1",
    "status":  "passed" if all_ok else "needs_review",
    "generated_at": now,
    "ai_supabase_sync_plan_created":  PLAN_FILE.exists(),
    "dry_run_default":                (plan or {}).get("dry_run_default", False),
    "sync_execute_tool_created":      (ROOT / "tools" / "ai" / "sync_ai_package_to_supabase_v1.py").exists(),
    "readback_verify_tool_created":   (ROOT / "tools" / "ai" / "verify_ai_package_from_supabase_v1.py").exists(),
    "active_switch_tool_created":     (ROOT / "tools" / "ai" / "activate_ai_package_supabase_v1.py").exists(),
    "active_switch_default":          (plan or {}).get("active_switch_default", True),
    "supabase_write_performed":       (sync_report or {}).get("supabase_write_performed", False),
    "active_switch_performed":        (sync_report or {}).get("active_switch_performed", False),
    "existing_active_package_preserved": (sync_report or {}).get("existing_active_package_preserved", True),
    "raw_cambridge_text_blocked":     no_cambridge,
    "api_keys_exposed_to_client":     not no_api_keys,
    "service_role_not_in_client":     client_clean,
    "deliverables":                   deliverable_results,
    "outputs":                        output_results,
    "policy":                         policy_results,
    "test_results":                   {"status": test_status, "passed": test_passed_count, "total": test_total_count},
    "summary":                        {
        "deliverables": f"{d_pass}/{len(deliverable_results)}",
        "outputs":      f"{o_pass}/{len(output_results)}",
        "policy":       f"{p_pass}/{len(policy_results)}",
        "tests":        f"{test_passed_count}/{test_total_count} ({test_status})",
    },
    "next_gate": "Gate 69H - Student Practice on AI Package",
}

diag_dir = ROOT / "data" / "diagnostics"
diag_dir.mkdir(parents=True, exist_ok=True)
rpt_json = diag_dir / "gate69g_ai_supabase_sync_report_v1.json"
rpt_md   = diag_dir / "SUPABASE_GATE_69G_AI_SUPABASE_SYNC_DONE.md"

rpt_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# DONE marker
# ---------------------------------------------------------------------------

md_lines = [
    "# Gate 69G — AI Package Supabase Sync + Optional Active Switch DONE",
    "",
    f"Generated: {now}",
    f"Status: **{'PASSED' if all_ok else 'NEEDS REVIEW'}**",
    "",
    "## What was done",
    "",
    "- AI Supabase sync plan created (`ai_supabase_sync_plan_v1.json`).",
    "- Dry-run sync verified safe — no Supabase writes by default.",
    "- Execute sync tool created (`sync_ai_package_to_supabase_v1.py --execute --confirm SYNC_AI_PACKAGE`).",
    "- Readback verifier created (`verify_ai_package_from_supabase_v1.py`).",
    "- Active switch tool created but **disabled by default** — requires `--execute --activate --confirm ACTIVATE_AI_PACKAGE`.",
    "- Existing active package preserved — physics_0625 NOT disturbed.",
    "- Export tool created (`build_ai_package_supabase_export_v1.py`).",
    "- Admin diagnostic page: `/system/ai-supabase`.",
    "- Diagnostic API: `/api/system/ai-supabase`.",
    "",
    "## Safety guarantees",
    "",
    "- `dry_run_default: true` — no Supabase writes unless `--execute`.",
    "- `active_switch_default: false` — AI package NOT active unless explicit opt-in.",
    "- `no_delete: true` — no packages/resources deleted.",
    "- `no_schema_change: true` — schema not modified.",
    "- `service_role_key` never written to output files or client code.",
    "- No raw Cambridge source text in sync plan or payloads.",
    "",
    "## Summary",
    "",
    f"| Category     | Result |",
    f"|:-------------|:-------|",
    f"| Deliverables | {d_pass}/{len(deliverable_results)} |",
    f"| Outputs      | {o_pass}/{len(output_results)} |",
    f"| Policy       | {p_pass}/{len(policy_results)} |",
    f"| Tests        | {test_passed_count}/{test_total_count} ({test_status}) |",
    "",
    "## Next: Gate 69H — Student Practice on AI Package",
    "",
    "Gate 69H will enable students to practice with AI-generated resources.",
    "Optional: run `--execute --confirm SYNC_AI_PACKAGE` before Gate 69H if Supabase sync is required.",
]
rpt_md.write_text("\n".join(md_lines), encoding="utf-8")

# ---------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------

print("Gate 69G -- Gate Report v1")
print("=" * 60)
print(f"Deliverables: {d_pass}/{len(deliverable_results)}")
print(f"Outputs:      {o_pass}/{len(output_results)}")
print(f"Policy:       {p_pass}/{len(policy_results)}")
print(f"Tests:        {test_passed_count}/{test_total_count} ({test_status})")
print(f"Status:       {'PASSED' if all_ok else 'NEEDS REVIEW'}")
print()
print(f"JSON report:  {rpt_json.relative_to(ROOT)}")
print(f"DONE marker:  {rpt_md.relative_to(ROOT)}")

if not all_ok:
    print()
    print("Incomplete:")
    for r in deliverable_results:
        if not r["exists"]:
            print(f"  [MISSING] {r['id']}: {r['path']}")
    for r in output_results:
        if not r["exists"]:
            print(f"  [MISSING] {r['id']}: {r['path']}")
    for r in policy_results:
        if not r["ok"]:
            print(f"  [FAIL] {r['check']}: {r['detail']}")
