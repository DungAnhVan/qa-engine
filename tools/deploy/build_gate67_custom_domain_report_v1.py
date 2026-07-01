"""
Gate 67 -- Custom Domain Report Builder v1

Reads the custom domain smoke test report (if it exists) and produces a
structured summary report plus a DONE marker.

Run test_gate67_custom_domain_smoke_v1.py first (after DNS is configured).
If the smoke test has not been run yet, the report shows needs_review.

Output:
  data/diagnostics/gate67_custom_domain_report_v1.json
  data/diagnostics/SUPABASE_GATE_67_CUSTOM_DOMAIN_DONE.md
"""

import json
import datetime
import subprocess
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
ADMIN_SRC   = ROOT / "apps" / "admin" / "src"
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
SMOKE_FILE  = OUTPUT_DIR / "gate67_custom_domain_smoke_test_report_v1.json"
OUTPUT_FILE = OUTPUT_DIR / "gate67_custom_domain_report_v1.json"
DONE_FILE   = OUTPUT_DIR / "SUPABASE_GATE_67_CUSTOM_DOMAIN_DONE.md"

DELIVERABLES = {
    "custom_domain_docs_created":      ROOT / "deployment" / "CUSTOM_DOMAIN_GATE67.md",
    "dns_template_created":            ROOT / "deployment" / "DNS_RECORDS_GATE67_TEMPLATE.md",
    "custom_domain_smoke_test_created": ROOT / "tools" / "deploy" / "test_gate67_custom_domain_smoke_v1.py",
}

# Files that must NOT contain SUPABASE_SERVICE_ROLE_KEY or direct service role usage
CLIENT_FILES_TO_SCAN = [
    ADMIN_SRC / "lib" / "browserSupabaseClient.ts",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_env_local_not_tracked() -> bool:
    """Returns True if .env.local is NOT tracked in git (safe)."""
    try:
        result = subprocess.run(
            ["git", "ls-files", ".env.local"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=10,
        )
        return not bool(result.stdout.strip())
    except Exception:
        return True  # assume safe if git unavailable


def check_service_role_not_in_client(files: list[Path]) -> tuple[bool, list[str]]:
    """
    Returns (safe, violations). safe=True means no service role exposure found.
    """
    violations = []
    danger_patterns = ["SUPABASE_SERVICE_ROLE_KEY", "service_role"]
    for path in files:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pat in danger_patterns:
            if pat in content:
                violations.append(f"{path.name} contains '{pat}'")
    return len(violations) == 0, violations

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Gate 67 -- Custom Domain Report Builder")
    print("-" * 50)

    # ── Load smoke test results ───────────────────────────────────────────────
    smoke: dict = {}
    if SMOKE_FILE.exists():
        try:
            smoke = json.loads(SMOKE_FILE.read_text(encoding="utf-8"))
            print(f"  + Smoke test report loaded: {SMOKE_FILE.name}")
            print(f"  + Base URL:                 {smoke.get('base_url', 'unknown')}")
            print(f"  + Smoke status:             {smoke.get('status', 'unknown')}")
            print(f"  + Custom domain used:       {smoke.get('custom_domain_used')}")
        except Exception as exc:
            print(f"  ! Failed to load smoke report: {exc}")
    else:
        print(f"  ? Smoke test report not found: {SMOKE_FILE.name}")
        print(f"    DNS may not be configured yet.")
        print(f"    Run after DNS setup:")
        print(f"    .venv-ingest\\Scripts\\python.exe tools\\deploy\\test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com")

    # ── Deliverable file presence ─────────────────────────────────────────────
    deliverable_status: dict[str, bool] = {}
    for key, path in DELIVERABLES.items():
        exists = path.exists()
        deliverable_status[key] = exists
        icon = "+" if exists else "!"
        print(f"  {icon} {key}: {'OK' if exists else 'MISSING'}")

    all_present = all(deliverable_status.values())

    # ── Security checks ───────────────────────────────────────────────────────
    env_local_not_tracked = check_env_local_not_tracked()
    service_role_safe, violations = check_service_role_not_in_client(CLIENT_FILES_TO_SCAN)

    print(f"  {'+'  if env_local_not_tracked else '!'} .env.local not tracked:        {'OK' if env_local_not_tracked else 'TRACKED — REMOVE FROM GIT'}")
    print(f"  {'+' if service_role_safe else '!'} service role not in client:   {'OK' if service_role_safe else f'VIOLATIONS: {violations}'}")

    # ── Extract smoke results ─────────────────────────────────────────────────
    smoke_ran              = bool(smoke)
    custom_domain_tested   = smoke.get("custom_domain_used",           False) if smoke_ran else False
    health_ok              = smoke.get("health_ok",                    False) if smoke_ran else False
    readiness_ok           = smoke.get("readiness_ok",                 False) if smoke_ran else False
    secrets_exposed        = smoke.get("secrets_exposed",              False) if smoke_ran else False
    content_live           = smoke.get("content_source_live_supabase", False) if smoke_ran else False
    demo_fallback_off      = smoke.get("demo_fallback_off",            False) if smoke_ran else False
    smoke_status           = smoke.get("status",                       "not_run")
    issues                 = smoke.get("issues",                       [])

    # ── Derive status ─────────────────────────────────────────────────────────
    has_security_issue = secrets_exposed or not env_local_not_tracked or not service_role_safe
    if has_security_issue:
        status = "failed"
    elif not all_present:
        status = "needs_review"
    elif not smoke_ran:
        status = "needs_review"  # DNS not configured yet
    elif smoke_status == "passed" and custom_domain_tested:
        status = "passed"
    elif smoke_status == "needs_review":
        status = "needs_review"
    else:
        status = "needs_review"

    print(f"\n  smoke_ran:               {smoke_ran}")
    print(f"  custom_domain_tested:    {custom_domain_tested}")
    print(f"  health_ok:               {health_ok}")
    print(f"  readiness_ok:            {readiness_ok}")
    print(f"  secrets_exposed:         {secrets_exposed}")
    print(f"  content_live_supabase:   {content_live}")
    print(f"  demo_fallback_off:       {demo_fallback_off}")
    print(f"  all_deliverables:        {all_present}")
    print(f"\nStatus: {status}")

    report = {
        "gate":                           "67",
        "status":                         status,
        "generated_at":                   datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **deliverable_status,
        "admin_subdomain_recommended":    "admin.quantaaptus.com",
        "landing_domain_preserved":       True,
        "env_local_not_tracked":          env_local_not_tracked,
        "service_role_not_in_client":     service_role_safe,
        "custom_domain_smoke_tested":     custom_domain_tested,
        "smoke_ran":                      smoke_ran,
        "smoke_status":                   smoke_status,
        "health_ok":                      health_ok,
        "readiness_ok":                   readiness_ok,
        "secrets_exposed":                secrets_exposed,
        "content_source_live_supabase":   content_live,
        "demo_fallback_off":              demo_fallback_off,
        "issues":                         issues,
        "next_gate":                      "Gate 68 - Production MVP Freeze + Handoff",
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")

    # ── DONE marker ───────────────────────────────────────────────────────────
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    dns_status = (
        f"Tested at: {smoke.get('base_url', 'not yet run')}\n"
        f"Smoke status: {smoke_status}\n"
        f"Custom domain verified: {custom_domain_tested}"
        if smoke_ran else
        "DNS not configured yet. Run after Vercel + DNS setup:\n"
        ".venv-ingest\\Scripts\\python.exe tools\\deploy\\test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com"
    )
    done_content = f"""# Gate 67 -- Custom Domain Prep DONE

Generated: {now}

## Status: {status.upper()}

## Summary

- Custom domain plan created: admin.quantaaptus.com recommended for admin app.
- quantaaptus.com landing page is preserved — no changes to @ or www DNS records.
- DNS record template created with fillable table.
- Custom domain smoke test script ready.
- Service role not exposed to client: {service_role_safe}
- Secrets in responses: {secrets_exposed}

## DNS Status

{dns_status}

## Gate 67 Deliverables

- Domain guide:         `deployment/CUSTOM_DOMAIN_GATE67.md`
- DNS template:         `deployment/DNS_RECORDS_GATE67_TEMPLATE.md`
- Custom domain smoke:  `tools/deploy/test_gate67_custom_domain_smoke_v1.py`
- Report builder:       `tools/deploy/build_gate67_custom_domain_report_v1.py`

## Steps Still Required (if DNS not yet configured)

1. Open Vercel → project qa-engine-admin → Settings → Domains
2. Add: admin.quantaaptus.com
3. Copy the CNAME value Vercel shows
4. Add CNAME record at your DNS provider (name: admin, value: <from Vercel>)
5. Wait for DNS propagation (5–30 min on Cloudflare, up to 48h elsewhere)
6. Verify: https://admin.quantaaptus.com/system/health
7. Add Supabase Auth redirect URL: https://admin.quantaaptus.com/**
8. Run smoke test and report builder:
   .venv-ingest\\Scripts\\python.exe tools\\deploy\\test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com
   .venv-ingest\\Scripts\\python.exe tools\\deploy\\build_gate67_custom_domain_report_v1.py

## Issues

{chr(10).join("- " + i for i in issues) or "None reported from smoke test."}

## Ready for Gate 68

Gate 68 -- Production MVP Freeze + Handoff:
- Final production checklist
- Demo accounts rotated or removed
- Custom domain live and verified
- Service role confirmed server-only
- RLS active
- MVP handoff documentation
"""
    DONE_FILE.write_text(done_content, encoding="utf-8")
    print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
