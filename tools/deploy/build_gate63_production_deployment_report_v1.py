"""
Gate 63 — Production Deployment Report Builder v1

Reads the readiness check report (from check_gate63_production_readiness_v1.py)
and verifies all Gate 63 files are in place. Outputs a structured JSON report
and DONE marker if all critical checks pass.

Run check_gate63_production_readiness_v1.py first.

Output:
  data/diagnostics/gate63_production_deployment_report_v1.json
  data/diagnostics/SUPABASE_GATE_63_PRODUCTION_DEPLOYMENT_PREP_DONE.md (if passing)
"""

import json
import datetime
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
ADMIN_SRC   = ROOT / "apps" / "admin" / "src"
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
CHECK_FILE  = OUTPUT_DIR / "gate63_production_readiness_check_v1.json"
OUTPUT_FILE = OUTPUT_DIR / "gate63_production_deployment_report_v1.json"
DONE_FILE   = OUTPUT_DIR / "SUPABASE_GATE_63_PRODUCTION_DEPLOYMENT_PREP_DONE.md"

# ---------------------------------------------------------------------------
# File existence checks
# ---------------------------------------------------------------------------

DELIVERABLES = {
    "production_env_template_created":      ROOT / ".env.production.example",
    "health_page_created":                  ADMIN_SRC / "app" / "system" / "health" / "page.tsx",
    "readiness_page_created":               ADMIN_SRC / "app" / "system" / "readiness" / "page.tsx",
    "health_api_created":                   ADMIN_SRC / "app" / "api" / "system" / "health" / "route.ts",
    "readiness_api_created":                ADMIN_SRC / "app" / "api" / "system" / "readiness" / "route.ts",
    "deployment_checklist_created":         ROOT / "deployment" / "VERCEL_DEPLOYMENT_CHECKLIST.md",
    "security_predeploy_checklist_created": ROOT / "deployment" / "SECURITY_PREDEPLOY_CHECKLIST.md",
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Gate 63 -- Production Deployment Report")
    print("-" * 50)

    # Read check report if available
    check_report: dict = {}
    if CHECK_FILE.exists():
        try:
            check_report = json.loads(CHECK_FILE.read_text(encoding="utf-8"))
            print(f"  + Readiness check report loaded: {CHECK_FILE.name}")
        except Exception as exc:
            print(f"  ! Failed to load readiness check report: {exc}")
    else:
        print(f"  ? Readiness check report not found: {CHECK_FILE.name}")
        print(f"    Run: .venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate63_production_readiness_v1.py")

    # Deliverable file checks
    deliverable_status: dict[str, bool] = {}
    for key, path in DELIVERABLES.items():
        exists = path.exists()
        deliverable_status[key] = exists
        icon = "+" if exists else "!"
        print(f"  {icon} {key}: {'OK' if exists else 'MISSING'}")
        if not exists:
            print(f"      expected: {path.relative_to(ROOT)}")

    all_deliverables_present = all(deliverable_status.values())

    # Security summary from check report
    security = check_report.get("security_summary", {})
    service_role_exposed   = security.get("service_role_exposed_to_client", None)
    env_local_tracked      = security.get("env_local_tracked", None)
    raw_pdf_exposed        = security.get("raw_cambridge_pdf_exposed", None)

    if service_role_exposed is None:
        print("  ? security checks not yet run (check report missing)")

    # Determine overall status
    check_failed = check_report.get("fail_count", 0) > 0
    security_fail = (
        service_role_exposed is True or
        env_local_tracked is True or
        raw_pdf_exposed is True
    )

    ready_for_deploy = all_deliverables_present and not security_fail and not check_failed

    if check_report:
        check_status = check_report.get("overall_status", "unknown")
        status = "passed" if (check_status in ("passed", "needs_review") and all_deliverables_present and not security_fail) \
                 else "needs_review" if all_deliverables_present \
                 else "failed"
    else:
        status = "needs_review" if all_deliverables_present else "failed"

    print("\n" + "-" * 50)
    print(f"All deliverables present: {all_deliverables_present}")
    print(f"Service role exposed:     {service_role_exposed}")
    print(f"Env local tracked:        {env_local_tracked}")
    print(f"Raw PDF exposed:          {raw_pdf_exposed}")
    print(f"Ready for deploy:         {ready_for_deploy}")
    print(f"Status:                   {status}")

    report = {
        "gate": "63",
        "title": "Production Deployment Prep Report v1",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": status,
        # Deliverables
        **deliverable_status,
        # Security
        "service_role_exposed_to_client": service_role_exposed if service_role_exposed is not None else "not_checked",
        "env_local_tracked":             env_local_tracked if env_local_tracked is not None else "not_checked",
        "raw_cambridge_pdf_exposed":     raw_pdf_exposed if raw_pdf_exposed is not None else "not_checked",
        # Readiness
        "ready_for_deploy":    ready_for_deploy,
        "readiness_check_ran": bool(check_report),
        "check_fail_count":    check_report.get("fail_count", "not_checked"),
        "check_warn_count":    check_report.get("warn_count", "not_checked"),
        # Next gate
        "next_gate": "Gate 64 - Vercel Deployment",
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")

    if status in ("passed", "needs_review") and all_deliverables_present:
        done_content = f"""# Gate 63 -- Production Deployment Prep DONE

Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}

## Status: {status.upper()}

## Deliverables Completed

- Production env template created: `.env.production.example`
- Health page created: `apps/admin/src/app/system/health/page.tsx`
- Readiness page created: `apps/admin/src/app/system/readiness/page.tsx`
- Health API created: `apps/admin/src/app/api/system/health/route.ts`
- Readiness API created: `apps/admin/src/app/api/system/readiness/route.ts`
- Deployment checklist created: `deployment/VERCEL_DEPLOYMENT_CHECKLIST.md`
- Security pre-deploy checklist created: `deployment/SECURITY_PREDEPLOY_CHECKLIST.md`
- Pre-deploy scan script: `tools/deploy/check_gate63_production_readiness_v1.py`
- Report script: `tools/deploy/build_gate63_production_deployment_report_v1.py`

## Security Summary

- service_role_exposed_to_client: {service_role_exposed}
- env_local_tracked: {env_local_tracked}
- raw_cambridge_pdf_exposed: {raw_pdf_exposed}

## Pre-Deploy Manual Steps

1. Apply Supabase RLS migration in SQL Editor:
   `supabase/migrations/000004_rls_role_hardening.sql`

2. Set all env vars in Vercel dashboard (see `.env.production.example`)

3. Verify `.env.local` is NOT tracked:
   `git ls-files apps/admin/.env.local`

4. Run readiness check:
   `.venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate63_production_readiness_v1.py`

## Ready for Gate 64

Gate 64 — Vercel Deployment: perform the actual production deployment
using `deployment/VERCEL_DEPLOYMENT_CHECKLIST.md`.
"""
        DONE_FILE.write_text(done_content, encoding="utf-8")
        print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
