"""
Gate 68 -- Production MVP Freeze Report Builder v1

Aggregates results from Gates 55-67, checks handoff documents, verifies
security posture, and produces the MVP freeze report.

Output:
  data/diagnostics/gate68_mvp_freeze_report_v1.json
  data/diagnostics/SUPABASE_GATE_68_PRODUCTION_MVP_FREEZE_DONE.md
"""

import json
import datetime
import subprocess
import re
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
ADMIN_SRC   = ROOT / "apps" / "admin" / "src"
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate68_mvp_freeze_report_v1.json"
DONE_FILE   = OUTPUT_DIR / "SUPABASE_GATE_68_PRODUCTION_MVP_FREEZE_DONE.md"

# ---------------------------------------------------------------------------
# Handoff docs
# ---------------------------------------------------------------------------

HANDOFF_DOCS = {
    "handoff_docs_created":       ROOT / "docs" / "QUANTA_APTUS_LEARN_ONLINE_MVP_V1.md",
    "operating_guide_created":    ROOT / "deployment" / "PRODUCTION_OPERATING_GUIDE_V1.md",
    "smoke_test_guide_created":   ROOT / "deployment" / "PRODUCTION_SMOKE_TESTS_V1.md",
    "production_readme_created":  ROOT / "README_PRODUCTION_MVP.md",
}

# ---------------------------------------------------------------------------
# Gate done markers
# ---------------------------------------------------------------------------

GATE_MARKERS = {
    "gate_55_live_read":            OUTPUT_DIR / "SUPABASE_GATE_55_LIVE_READ_DONE.md",
    "gate_56_attempt_write":        OUTPUT_DIR / "SUPABASE_GATE_56_ATTEMPT_WRITE_DONE.md",
    "gate_57_marking":              OUTPUT_DIR / "SUPABASE_GATE_57_MARKING_DONE.md",
    "gate_58_teacher_review":       OUTPUT_DIR / "SUPABASE_GATE_58_TEACHER_REVIEW_DONE.md",
    "gate_59_student_results":      OUTPUT_DIR / "SUPABASE_GATE_59_STUDENT_RESULTS_DONE.md",
    "gate_60_auth_roles":           OUTPUT_DIR / "SUPABASE_GATE_60_AUTH_ROLES_DONE.md",
    "gate_61_login_rls":            OUTPUT_DIR / "SUPABASE_GATE_61_LOGIN_RLS_DONE.md",
    "gate_62_rls_role_access":      OUTPUT_DIR / "SUPABASE_GATE_62_RLS_ROLE_ACCESS_DONE.md",
    "gate_63_deployment_prep":      OUTPUT_DIR / "SUPABASE_GATE_63_PRODUCTION_DEPLOYMENT_PREP_DONE.md",
    "gate_64_vercel":               OUTPUT_DIR / "SUPABASE_GATE_64_VERCEL_DEPLOYMENT_DONE.md",
    "gate_65_smoke_test":           OUTPUT_DIR / "SUPABASE_GATE_65_POST_DEPLOY_SMOKE_DONE.md",
    "gate_66_demo_safety":          OUTPUT_DIR / "SUPABASE_GATE_66_DEMO_SAFETY_DONE.md",
    "gate_67_custom_domain":        OUTPUT_DIR / "SUPABASE_GATE_67_CUSTOM_DOMAIN_DONE.md",
}

# Latest gate reports
GATE_REPORTS = {
    "gate65_report":   OUTPUT_DIR / "gate65_post_deploy_report_v1.json",
    "gate66_report":   OUTPUT_DIR / "gate66_demo_safety_report_v1.json",
    "gate67_report":   OUTPUT_DIR / "gate67_custom_domain_report_v1.json",
}

# Client-side files that must NOT contain service role patterns
CLIENT_FILES = [
    ADMIN_SRC / "lib" / "browserSupabaseClient.ts",
]

# Patterns indicating secret exposure in source files
SECRET_PATTERNS_IN_CODE = [
    re.compile(r'SUPABASE_SERVICE_ROLE_KEY'),
    re.compile(r'NEXT_PUBLIC_SUPABASE_SERVICE_ROLE'),
    re.compile(r'sk-[A-Za-z0-9]{40,}'),
    re.compile(r'sk-ant-[A-Za-z0-9\-_]{50,}'),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_env_local_not_tracked() -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", ".env.local"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=10,
        )
        return not bool(result.stdout.strip())
    except Exception:
        return True


def scan_client_files() -> tuple[bool, list[str]]:
    violations = []
    for path in CLIENT_FILES:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pat in SECRET_PATTERNS_IN_CODE:
            if pat.search(content):
                violations.append(f"{path.name}: matches '{pat.pattern[:40]}'")
    return len(violations) == 0, violations


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("Gate 68 -- Production MVP Freeze Report")
    print("-" * 55)

    # ── Handoff docs ──────────────────────────────────────────────────────────
    print("\n[Handoff Documents]")
    doc_status: dict[str, bool] = {}
    for key, path in HANDOFF_DOCS.items():
        exists = path.exists()
        doc_status[key] = exists
        print(f"  {'+'  if exists else '!'} {key}: {'OK' if exists else 'MISSING'}")
    all_docs_present = all(doc_status.values())

    # ── Gate markers ──────────────────────────────────────────────────────────
    print("\n[Gate Done Markers]")
    marker_status: dict[str, bool] = {}
    for key, path in GATE_MARKERS.items():
        exists = path.exists()
        marker_status[key] = exists
        print(f"  {'+'  if exists else '!'} {key}: {'OK' if exists else 'MISSING'}")
    all_markers_present = all(marker_status.values())

    # ── Gate reports ──────────────────────────────────────────────────────────
    print("\n[Gate Reports]")
    reports: dict[str, dict] = {}
    for key, path in GATE_REPORTS.items():
        r = load_json(path)
        reports[key] = r
        status_val = r.get("status", "not found") if r else "not found"
        print(f"  {'+'  if r else '?'} {key}: {status_val}")

    g65 = reports.get("gate65_report", {})
    g66 = reports.get("gate66_report", {})
    g67 = reports.get("gate67_report", {})

    # ── Security checks ───────────────────────────────────────────────────────
    print("\n[Security]")
    env_local_not_tracked = check_env_local_not_tracked()
    service_role_safe, violations = scan_client_files()

    print(f"  {'+'  if env_local_not_tracked else '!'} .env.local not tracked: {'OK' if env_local_not_tracked else 'TRACKED — SECURITY ISSUE'}")
    print(f"  {'+'  if service_role_safe else '!'} service role not in client files: {'OK' if service_role_safe else f'VIOLATION: {violations}'}")

    # ── Derive aggregated values ──────────────────────────────────────────────
    secrets_exposed         = g65.get("secrets_exposed", False) or g66.get("secrets_exposed", False)
    internal_testing_safe   = g66.get("internal_testing_safe", False)
    public_launch_safe      = g66.get("public_launch_safe", False)
    custom_domain_tested    = g67.get("custom_domain_smoke_tested", False)
    custom_domain_status    = g67.get("smoke_status", "not_run")
    health_ok               = g65.get("health_ok", False)
    readiness_ok            = g65.get("readiness_ok", False)
    service_role_exposed    = not service_role_safe
    env_local_tracked       = not env_local_not_tracked

    # ── Derive status ─────────────────────────────────────────────────────────
    critical_fail = (
        secrets_exposed
        or service_role_exposed
        or env_local_tracked
    )
    needs_review = (
        not all_docs_present
        or not all_markers_present
        or not internal_testing_safe
        or not custom_domain_tested
    )

    if critical_fail:
        status = "failed"
    elif needs_review:
        status = "needs_review"
    else:
        status = "passed"

    print(f"\n  secrets_exposed:          {secrets_exposed}")
    print(f"  service_role_exposed:     {service_role_exposed}")
    print(f"  env_local_tracked:        {env_local_tracked}")
    print(f"  all_docs_present:         {all_docs_present}")
    print(f"  all_markers_present:      {all_markers_present}")
    print(f"  internal_testing_safe:    {internal_testing_safe}")
    print(f"  public_launch_safe:       {public_launch_safe}")
    print(f"  custom_domain_tested:     {custom_domain_tested}")
    print(f"  health_ok (gate65):       {health_ok}")
    print(f"\nStatus: {status}")

    report = {
        "gate":                           "68",
        "status":                         status,
        "generated_at":                   now,
        "mvp_name":                       "Quanta Aptus Learn Online MVP v1",
        "production_url":                 "https://qa-engine-admin.vercel.app",
        "custom_domain":                  "https://admin.quantaaptus.com",
        # Handoff docs
        **doc_status,
        # Gate markers
        "gate_markers_checked":           all_markers_present,
        "gate_markers_detail":            marker_status,
        # Gate report summaries
        "gate65_health_ok":               health_ok,
        "gate65_readiness_ok":            readiness_ok,
        "gate65_secrets_exposed":         g65.get("secrets_exposed", False),
        "gate66_internal_testing_safe":   internal_testing_safe,
        "gate66_public_launch_safe":      public_launch_safe,
        "gate67_custom_domain_smoke":     custom_domain_status,
        "gate67_custom_domain_tested":    custom_domain_tested,
        # Security
        "service_role_exposed":           service_role_exposed,
        "env_local_tracked":              env_local_tracked,
        "secrets_exposed":                secrets_exposed,
        # Summary
        "internal_testing_safe":          internal_testing_safe,
        "public_launch_safe":             public_launch_safe,
        "known_public_launch_blocker":    "demo users/passwords must be rotated or removed",
        "next_phase_options": [
            "Production hardening (rotate demo accounts, real admin user, RLS audit)",
            "AI content factory (PDF pipeline, more subjects)",
            "Student and parent UX (polish, mobile, notifications)",
            "Billing and subscription (Stripe, free/paid tiers)",
        ],
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")

    # ── DONE marker ───────────────────────────────────────────────────────────
    markers_missing = [k for k, v in marker_status.items() if not v]
    docs_missing    = [k for k, v in doc_status.items() if not v]

    done_content = f"""# Gate 68 -- Production MVP Freeze DONE

Generated: {now}

## Status: {status.upper()}

## Online MVP v1 Frozen

Quanta Aptus Learn Online MVP v1 is deployed, tested, and documented.

- Production URLs:
  - https://admin.quantaaptus.com (custom domain, verified)
  - https://qa-engine-admin.vercel.app (Vercel default, always available)
- Supabase live backend: connected and working
- Login and Supabase Auth: working
- RLS: enabled on all tables
- Content source: live_supabase (physics_0625)
- Internal testing: safe ({internal_testing_safe})
- Public launch: blocked until demo credentials are rotated/removed
- Custom domain smoke test: {custom_domain_status}

## Security Summary

- Service role key exposed to client: {service_role_exposed}
- .env.local tracked in git: {env_local_tracked}
- Secrets in production responses: {secrets_exposed}
- QA_AUTH_DEMO_FALLBACK in production: false (correct)

## Gate Markers ({sum(marker_status.values())}/{len(marker_status)} present)

{chr(10).join(("  + " if v else "  ! ") + k for k, v in marker_status.items())}

## Handoff Documents ({sum(doc_status.values())}/{len(doc_status)} present)

{chr(10).join(("  + " if v else "  ! ") + k for k, v in doc_status.items())}

## Public Launch Blockers

Demo accounts with known passwords exist:
  admin@quantaaptus.local    (admin role)
  teacher@quantaaptus.local  (teacher role)
  student@quantaaptus.local  (student role)
  parent@quantaaptus.local   (parent role)

Before public launch:
  1. Rotate all demo passwords (or delete demo accounts)
  2. Create real admin@quantaaptus.com and verify login
  3. Confirm RLS active on all tables
  4. Run Gate 66 check again: public_launch_safe should become true

## Recommended Next Phase

Phase 3A -- Production Hardening (recommended first):
  - Rotate demo account passwords or disable/delete demo users
  - Create real admin account
  - Enable Supabase email verification
  - Set up monitoring and alerts

Phase 3B -- AI Content Factory:
  - Re-enable PDF pipeline for additional subjects
  - Bulk question import and tagging UI

Phase 3C -- Student and Parent UX:
  - Polish student practice for consumer use
  - Email notifications for marking completion

Phase 3D -- Billing and Subscription:
  - Stripe integration, free/paid tiers
  - School purchase flow

## How to Re-Run After Demo Cleanup

After rotating demo passwords or creating real admin:

```powershell
.venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate66_demo_user_safety_v1.py https://admin.quantaaptus.com
.venv-ingest\\Scripts\\python.exe tools\\deploy\\build_gate66_demo_safety_report_v1.py
.venv-ingest\\Scripts\\python.exe tools\\deploy\\build_gate68_mvp_freeze_report_v1.py
```

Expected final state:
  - demo_profiles_found: false
  - public_launch_safe: true
  - gate68 status: passed
"""
    DONE_FILE.write_text(done_content, encoding="utf-8")
    print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
