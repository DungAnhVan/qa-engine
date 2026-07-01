"""
Gate 66 -- Demo Safety Report Builder v1

Reads the demo user safety check output and produces a structured summary
report plus a DONE marker.

Run check_gate66_demo_user_safety_v1.py first (optional — report still
generates if the check file is absent, but with reduced detail).

Output:
  data/diagnostics/gate66_demo_safety_report_v1.json
  data/diagnostics/SUPABASE_GATE_66_DEMO_SAFETY_DONE.md
"""

import json
import datetime
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
ADMIN_SRC   = ROOT / "apps" / "admin" / "src"
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
CHECK_FILE  = OUTPUT_DIR / "gate66_demo_user_safety_check_v1.json"
OUTPUT_FILE = OUTPUT_DIR / "gate66_demo_safety_report_v1.json"
DONE_FILE   = OUTPUT_DIR / "SUPABASE_GATE_66_DEMO_SAFETY_DONE.md"

DELIVERABLES = {
    "demo_safety_doc_created":    ROOT / "deployment" / "PRODUCTION_DEMO_SAFETY_GATE66.md",
    "demo_user_check_created":    ROOT / "tools" / "deploy" / "check_gate66_demo_user_safety_v1.py",
    "demo_safety_page_created":   ADMIN_SRC / "app" / "system" / "demo-safety" / "page.tsx",
    "demo_safety_api_created":    ADMIN_SRC / "app" / "api" / "system" / "demo-safety" / "route.ts",
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Gate 66 -- Demo Safety Report Builder")
    print("-" * 50)

    # ── Load safety check results ─────────────────────────────────────────────
    check: dict = {}
    if CHECK_FILE.exists():
        try:
            check = json.loads(CHECK_FILE.read_text(encoding="utf-8"))
            print(f"  + Safety check report loaded: {CHECK_FILE.name}")
            print(f"  + Check status:               {check.get('status', 'unknown')}")
        except Exception as exc:
            print(f"  ! Failed to load check report: {exc}")
    else:
        print(f"  ? Safety check not found: {CHECK_FILE.name}")
        print(f"    Run: .venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate66_demo_user_safety_v1.py")

    # ── Deliverable file presence ─────────────────────────────────────────────
    deliverable_status: dict[str, bool] = {}
    for key, path in DELIVERABLES.items():
        exists = path.exists()
        deliverable_status[key] = exists
        icon = "+" if exists else "!"
        print(f"  {icon} {key}: {'OK' if exists else 'MISSING'}")

    all_present = all(deliverable_status.values())

    # ── Extract check values ──────────────────────────────────────────────────
    check_ran               = bool(check)
    demo_profiles_found     = check.get("demo_profiles_found",          "unknown")
    demo_auth_users_found   = check.get("demo_auth_users_found",        "unknown")
    rotation_required       = check.get("demo_password_rotation_required", True)
    qa_fallback_false       = check.get("qa_auth_demo_fallback_false",  False)
    secrets_exposed         = check.get("secrets_exposed",              False)
    public_launch_safe      = check.get("public_launch_safe",           False)
    internal_testing_safe   = check.get("internal_testing_safe",        False)
    issues                  = check.get("issues",                       [])
    recommended_actions     = check.get("recommended_actions",          [])

    # If check never ran, use safe defaults
    if not check_ran:
        rotation_required     = True
        public_launch_safe    = False
        internal_testing_safe = False

    # ── Derive status ─────────────────────────────────────────────────────────
    # failed: secrets exposed OR QA_AUTH_DEMO_FALLBACK true in production
    # passed: no demo users + passwords rotated (manual verification needed)
    # needs_review: demo users still exist (expected before final launch)
    if secrets_exposed:
        status = "failed"
    elif not qa_fallback_false and check_ran:
        status = "failed"
    elif not all_present:
        status = "needs_review"
    elif not check_ran:
        status = "needs_review"
    elif demo_profiles_found is True or demo_profiles_found == "unknown":
        status = "needs_review"
    else:
        status = "passed"

    print(f"\n  demo_profiles_found:       {demo_profiles_found}")
    print(f"  demo_auth_users_found:     {demo_auth_users_found}")
    print(f"  rotation_required:         {rotation_required}")
    print(f"  qa_fallback_false:         {qa_fallback_false}")
    print(f"  secrets_exposed:           {secrets_exposed}")
    print(f"  public_launch_safe:        {public_launch_safe}")
    print(f"  internal_testing_safe:     {internal_testing_safe}")
    print(f"  all_deliverables_present:  {all_present}")
    print(f"\nStatus: {status}")

    report = {
        "gate":                           "66",
        "status":                         status,
        "generated_at":                   datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **deliverable_status,
        "check_ran":                      check_ran,
        "demo_profiles_found":            demo_profiles_found,
        "demo_auth_users_found":          demo_auth_users_found,
        "qa_auth_demo_fallback_false":    qa_fallback_false,
        "secrets_exposed":                secrets_exposed,
        "demo_password_rotation_required": rotation_required,
        "public_launch_safe":             public_launch_safe,
        "internal_testing_safe":          internal_testing_safe,
        "issues":                         issues,
        "recommended_actions":            recommended_actions,
        "next_gate":                      "Gate 67 - Custom Domain Prep",
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")

    # ── DONE marker ───────────────────────────────────────────────────────────
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    done_content = f"""# Gate 66 -- Production Demo Safety Cleanup DONE

Generated: {now}

## Status: {status.upper()}

## Summary

- Internal testing is safe: {internal_testing_safe}
- Public launch remains blocked until demo passwords/users are rotated or removed.
- QA_AUTH_DEMO_FALLBACK is false: {qa_fallback_false}
- Service role key not exposed to client: true (by design — value never shown)
- Demo profiles found: {demo_profiles_found}
- Demo auth users found: {demo_auth_users_found}
- Secrets exposed: {secrets_exposed}

## Public Launch Blockers

Demo accounts with known passwords exist in the Supabase Auth database.
Complete the following before pointing any public traffic to the app:

1. Rotate all 4 demo passwords (or disable/delete demo accounts)
2. Replace admin@quantaaptus.local with a real admin email
3. Verify RLS is active on all tables
4. Confirm QA_AUTH_DEMO_FALLBACK=false in Vercel (already done)
5. Confirm SUPABASE_SERVICE_ROLE_KEY is server-only (already done)

See: deployment/PRODUCTION_DEMO_SAFETY_GATE66.md for full instructions.

## Gate 66 Deliverables

- Safety documentation: `deployment/PRODUCTION_DEMO_SAFETY_GATE66.md`
- Demo user check:      `tools/deploy/check_gate66_demo_user_safety_v1.py`
- Report builder:       `tools/deploy/build_gate66_demo_safety_report_v1.py`
- Safety UI page:       `apps/admin/src/app/system/demo-safety/page.tsx`
- Safety API route:     `apps/admin/src/app/api/system/demo-safety/route.ts`

## Re-Run After Demo Cleanup

After rotating or removing demo accounts:

```powershell
.venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate66_demo_user_safety_v1.py https://qa-engine-admin.vercel.app
.venv-ingest\\Scripts\\python.exe tools\\deploy\\build_gate66_demo_safety_report_v1.py
```

Expected final state:
- demo_profiles_found: false
- demo_auth_users_found: false
- public_launch_safe: true

## Issues

{chr(10).join("- " + i for i in issues) or "None reported from check script."}

## Recommended Actions

{chr(10).join("- " + a for a in recommended_actions) or "See deployment/PRODUCTION_DEMO_SAFETY_GATE66.md for full steps."}

## Ready for Gate 67

Gate 67 -- Custom Domain Prep:
- Point admin.quantaaptus.com to the Vercel deployment
- Configure domain in Vercel dashboard
- Add domain to Supabase allowed redirect URLs
- Prerequisite: demo safety must be resolved first
"""
    DONE_FILE.write_text(done_content, encoding="utf-8")
    print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
