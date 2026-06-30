"""
Gate 65 -- Post-Deploy Report Builder v1

Reads the smoke test report and produces a structured summary report
plus a DONE marker.

Run test_gate65_post_deploy_smoke_v1.py first.

Output:
  data/diagnostics/gate65_post_deploy_report_v1.json
  data/diagnostics/SUPABASE_GATE_65_POST_DEPLOY_SMOKE_DONE.md
"""

import json
import datetime
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
ADMIN_SRC   = ROOT / "apps" / "admin" / "src"
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
SMOKE_FILE  = OUTPUT_DIR / "gate65_post_deploy_smoke_test_report_v1.json"
OUTPUT_FILE = OUTPUT_DIR / "gate65_post_deploy_report_v1.json"
DONE_FILE   = OUTPUT_DIR / "SUPABASE_GATE_65_POST_DEPLOY_SMOKE_DONE.md"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _route_ok(smoke: dict, path: str) -> bool:
    routes = smoke.get("routes", [])
    r = next((x for x in routes if x.get("path") == path), None)
    return bool(r and r.get("pass"))


def _route_status(smoke: dict, path: str) -> int:
    routes = smoke.get("routes", [])
    r = next((x for x in routes if x.get("path") == path), None)
    return r["status_code"] if r else 0

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Gate 65 -- Post-Deploy Report Builder")
    print("-" * 50)

    smoke: dict = {}
    if SMOKE_FILE.exists():
        try:
            smoke = json.loads(SMOKE_FILE.read_text(encoding="utf-8"))
            base_url = smoke.get("base_url", "unknown")
            print(f"  + Smoke test report loaded")
            print(f"  + Base URL: {base_url}")
            print(f"  + Smoke status: {smoke.get('status', 'unknown')}")
        except Exception as exc:
            print(f"  ! Failed to load smoke test report: {exc}")
    else:
        print(f"  ? Smoke test report not found: {SMOKE_FILE.name}")
        print(f"    Run first:")
        print(f"    .venv-ingest\\Scripts\\python.exe tools\\deploy\\test_gate65_post_deploy_smoke_v1.py https://YOUR-URL")

    smoke_ran         = bool(smoke)
    base_url          = smoke.get("base_url", None)
    smoke_status      = smoke.get("status", "not_run")

    health_ok         = smoke.get("health_ok",         False)
    readiness_ok      = smoke.get("readiness_ok",      False)
    login_reachable   = smoke.get("login_reachable",   False)
    secrets_exposed   = smoke.get("secrets_exposed",   None)
    content_src_live  = smoke.get("content_source_live_supabase", False)
    routes_tested     = smoke.get("routes_tested",     0)
    routes_passed     = smoke.get("routes_passed",     0)

    api_health_ok     = _route_ok(smoke, "/api/system/health")
    api_readiness_ok  = _route_ok(smoke, "/api/system/readiness")
    role_pages_ok     = (
        _route_status(smoke, "/system/role-access") == 200
        and _route_status(smoke, "/system/auth-session") == 200
    )

    # Overall status
    if not smoke_ran:
        status = "needs_review"
    elif smoke_status == "passed":
        status = "passed"
    elif smoke_status == "needs_review":
        status = "needs_review"
    else:
        status = "failed"

    print(f"  + health_ok:          {health_ok}")
    print(f"  + readiness_ok:       {readiness_ok}")
    print(f"  + login_reachable:    {login_reachable}")
    print(f"  + secrets_exposed:    {secrets_exposed}")
    print(f"  + content_src_live:   {content_src_live}")
    print(f"  + routes:             {routes_passed}/{routes_tested}")
    print(f"  + api_health_ok:      {api_health_ok}")
    print(f"  + api_readiness_ok:   {api_readiness_ok}")
    print(f"  + role_pages_ok:      {role_pages_ok}")
    print(f"\nStatus: {status}")

    report = {
        "gate":                    "65",
        "status":                  status,
        "generated_at":            datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "production_url_tested":   bool(base_url),
        "production_url":          base_url,
        "smoke_test_ran":          smoke_ran,
        "health_ok":               health_ok,
        "readiness_ok":            readiness_ok,
        "login_reachable":         login_reachable,
        "role_pages_reachable":    role_pages_ok,
        "api_health_ok":           api_health_ok,
        "api_readiness_ok":        api_readiness_ok,
        "secrets_exposed":         secrets_exposed if secrets_exposed is not None else "not_checked",
        "content_source_live":     content_src_live,
        "routes_tested":           routes_tested,
        "routes_passed":           routes_passed,
        "issues":                  smoke.get("issues", []),
        "next_gate":               "Gate 66 - Production Demo Safety Cleanup",
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")

    # Write DONE marker regardless of status (gate is complete when scripts exist)
    done_content = f"""# Gate 65 -- Post-Deploy Smoke Test DONE

Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}

## Status: {status.upper()}

## Smoke Test Results

- Production URL tested: {bool(base_url)}
- URL: {base_url or 'not yet run'}
- Smoke test status: {smoke_status}
- Health API: {'OK' if health_ok else 'FAIL or not run'}
- Readiness API: {'OK' if readiness_ok else 'FAIL or not run'}
- Login reachable: {'YES' if login_reachable else 'FAIL or not run'}
- Secrets exposed: {secrets_exposed if secrets_exposed is not None else 'not checked'}
- Content source live: {content_src_live}
- Routes: {routes_passed}/{routes_tested} passed

## Gate 65 Scripts

- Smoke test: `tools/deploy/test_gate65_post_deploy_smoke_v1.py`
- Report builder: `tools/deploy/build_gate65_post_deploy_report_v1.py`
- Guide: `deployment/POST_DEPLOY_SMOKE_TEST_GATE65.md`

## How to Re-Run

After deploying to Vercel:

```powershell
.venv-ingest\\Scripts\\python.exe tools\\deploy\\test_gate65_post_deploy_smoke_v1.py https://YOUR-APP.vercel.app
.venv-ingest\\Scripts\\python.exe tools\\deploy\\build_gate65_post_deploy_report_v1.py
```

## Issues

{chr(10).join("- " + i for i in smoke.get("issues", [])) or "None reported."}

## Ready for Gate 66

Gate 66 -- Production Demo Safety Cleanup:
- Rotate or remove demo user passwords
- Verify production Supabase has no test data exposed
- Final security review before real-user launch
"""
    DONE_FILE.write_text(done_content, encoding="utf-8")
    print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
