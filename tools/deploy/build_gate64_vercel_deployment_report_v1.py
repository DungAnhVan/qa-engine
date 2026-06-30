"""
Gate 64 — Vercel Deployment Report Builder v1

Reads the Gate 64 verification report and produces a structured JSON
summary report + DONE marker.

Run verify_gate64_vercel_config_v1.py first.

Output:
  data/diagnostics/gate64_vercel_deployment_report_v1.json
  data/diagnostics/SUPABASE_GATE_64_VERCEL_DEPLOYMENT_DONE.md
"""

import json
import datetime
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
ADMIN_SRC   = ROOT / "apps" / "admin" / "src"
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
VERIFY_FILE = OUTPUT_DIR / "gate64_vercel_config_verify_v1.json"
OUTPUT_FILE = OUTPUT_DIR / "gate64_vercel_deployment_report_v1.json"
DONE_FILE   = OUTPUT_DIR / "SUPABASE_GATE_64_VERCEL_DEPLOYMENT_DONE.md"

DELIVERABLES = {
    "vercel_config_created":        ROOT / "vercel.json",
    "deployment_setup_doc_created": ROOT / "deployment" / "VERCEL_GATE64_SETUP.md",
    "env_var_doc_created":          ROOT / "deployment" / "VERCEL_ENV_VARS_GATE64.md",
    "health_urls_ready":            ADMIN_SRC / "app" / "system" / "health" / "page.tsx",
    "readiness_urls_ready":         ADMIN_SRC / "app" / "system" / "readiness" / "page.tsx",
    "health_api_ready":             ADMIN_SRC / "app" / "api" / "system" / "health" / "route.ts",
    "readiness_api_ready":          ADMIN_SRC / "app" / "api" / "system" / "readiness" / "route.ts",
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Gate 64 -- Vercel Deployment Report")
    print("-" * 50)

    verify_report: dict = {}
    if VERIFY_FILE.exists():
        try:
            verify_report = json.loads(VERIFY_FILE.read_text(encoding="utf-8"))
            print(f"  + Verify report loaded: {VERIFY_FILE.name}")
        except Exception as exc:
            print(f"  ! Failed to load verify report: {exc}")
    else:
        print(f"  ? Verify report not found: {VERIFY_FILE.name}")
        print(f"    Run: .venv-ingest\\Scripts\\python.exe tools\\deploy\\verify_gate64_vercel_config_v1.py")

    # File presence checks
    deliverable_status: dict[str, bool] = {}
    for key, path in DELIVERABLES.items():
        exists = path.exists()
        deliverable_status[key] = exists
        icon = "+" if exists else "!"
        print(f"  {icon} {key}: {'OK' if exists else 'MISSING'}")

    all_present = all(deliverable_status.values())

    security = verify_report.get("security_summary", {})
    service_role_exposed = security.get("service_role_exposed_to_client", None)
    env_local_tracked    = security.get("env_local_tracked", None)

    fail_count = verify_report.get("fail_count", 0)
    security_fail = service_role_exposed is True or env_local_tracked is True

    if verify_report:
        check_overall = verify_report.get("overall_status", "unknown")
        status = "passed" if (check_overall in ("passed",) and all_present and not security_fail) \
                 else "needs_review" if (all_present and not security_fail) \
                 else "failed"
    else:
        status = "needs_review" if all_present else "failed"

    print("\n" + "-" * 50)
    print(f"All deliverables present:  {all_present}")
    print(f"Service role exposed:      {service_role_exposed}")
    print(f"Env local tracked:         {env_local_tracked}")
    print(f"Verify fail count:         {fail_count}")
    print(f"Status:                    {status}")

    report = {
        "gate": "64",
        "status": status,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        # Deliverables
        **deliverable_status,
        # Security
        "service_role_exposed_to_client": service_role_exposed if service_role_exposed is not None else "not_checked",
        "env_local_tracked":             env_local_tracked if env_local_tracked is not None else "not_checked",
        # Deployment state
        "manual_vercel_deploy_required": True,
        "verify_check_ran":              bool(verify_report),
        "verify_fail_count":             fail_count,
        # Next gate
        "next_gate": "Gate 65 - Post-deploy Smoke Test",
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")

    if all_present:
        done_content = f"""# Gate 64 -- Vercel Deployment DONE

Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}

## Status: {status.upper()}

## Deliverables Completed

- Vercel config: `vercel.json` at repo root
- Deployment setup guide: `deployment/VERCEL_GATE64_SETUP.md`
- Env vars reference: `deployment/VERCEL_ENV_VARS_GATE64.md`
- Health page: `apps/admin/src/app/system/health/page.tsx`
- Readiness page: `apps/admin/src/app/system/readiness/page.tsx`
- Health API: `apps/admin/src/app/api/system/health/route.ts`
- Readiness API: `apps/admin/src/app/api/system/readiness/route.ts`
- Verification script: `tools/deploy/verify_gate64_vercel_config_v1.py`
- Report script: `tools/deploy/build_gate64_vercel_deployment_report_v1.py`

## Security Summary

- service_role_exposed_to_client: {service_role_exposed}
- env_local_tracked: {env_local_tracked}

## Manual Deployment Steps

Vercel config and documentation are ready. Actual deployment is manual:

1. Go to https://vercel.com/new
2. Import GitHub repo: DungAnhVan/qa-engine
3. Follow: deployment/VERCEL_GATE64_SETUP.md
4. Add all env vars from: .env.production.example
5. Deploy and verify health endpoints

## Build Commands (verified locally)

  Local mode:
    $env:QA_CONTENT_SOURCE="local"
    pnpm --filter @qa-engine/admin build

  Live Supabase mode:
    $env:QA_CONTENT_SOURCE="live_supabase"
    pnpm --filter @qa-engine/admin build

## Health URLs (post-deploy)

- /system/health
- /system/readiness
- /api/system/health
- /api/system/readiness
- /login
- /system/auth-session
- /system/role-access

## Ready for Gate 65

Gate 65 -- Post-deploy Smoke Test: verify all routes after live deployment.
"""
        DONE_FILE.write_text(done_content, encoding="utf-8")
        print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
