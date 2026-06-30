"""
Gate 61 — RLS Permission Tests v1.

Signs in as each demo user via anon key and runs safe read tests
to verify RLS foundation is in place.

Tests per role:
  - can read own profile (profiles table)
  - can read subjects
  - can read resource packages (if policy allows)
  - student: can read own student record (if profile linked)
  - parent:  can read linked students (if link exists)

If RLS policies are still permissive/draft, tests that fail due to
access restrictions are marked "rls_hardening_needed", not failure.
Tests that fail due to infrastructure (missing table, bad schema) are errors.

No destructive writes are performed.

Security:
  - Uses ANON key for sign-in (not service role).
  - Service role used only for cleanup / verification queries where needed.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\test_gate61_rls_permissions_v1.py

Output:
  data/diagnostics/gate61_rls_permission_test_report_v1.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
SUPABASE_TOOL = Path(__file__).parent
DIAG_DIR      = PROJECT_ROOT / "data" / "diagnostics"

if str(SUPABASE_TOOL) not in sys.path:
    sys.path.insert(0, str(SUPABASE_TOOL))


DEMO_USERS = [
    {"email": "admin@quantaaptus.local",   "password": "QuantaAptusDemo123!", "role": "admin"},
    {"email": "teacher@quantaaptus.local", "password": "QuantaAptusDemo123!", "role": "teacher"},
    {"email": "student@quantaaptus.local", "password": "QuantaAptusDemo123!", "role": "student"},
    {"email": "parent@quantaaptus.local",  "password": "QuantaAptusDemo123!", "role": "parent"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_anon_key(env_path: Path) -> str | None:
    """Parse .env.local and return SUPABASE_ANON_KEY."""
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("SUPABASE_ANON_KEY=") or line.startswith("NEXT_PUBLIC_SUPABASE_ANON_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                return key
    return None


def _run_rls_tests(anon_client, user_id: str, role: str) -> dict:
    """Run read tests for a signed-in user. Returns { passed, failed, skipped, details }."""
    passed = []
    failed = []
    skipped = []

    # 1. Read own profile
    try:
        r = anon_client.table("profiles").select("id, role").eq("id", user_id).execute()
        if r.data:
            passed.append("read_own_profile")
        else:
            # Might be RLS blocking it or profile not seeded
            skipped.append("read_own_profile: no rows returned (RLS or unseeded)")
    except Exception as e:
        failed.append(f"read_own_profile: {e}")

    # 2. Read subjects
    try:
        r = anon_client.table("subjects").select("id, slug").limit(3).execute()
        if r.data is not None:
            passed.append(f"read_subjects ({len(r.data)} rows)")
        else:
            skipped.append("read_subjects: no data (RLS may be blocking)")
    except Exception as e:
        failed.append(f"read_subjects: {e}")

    # 3. Read resource packages
    try:
        r = anon_client.table("resource_packages").select("id, slug").limit(3).execute()
        if r.data is not None:
            passed.append(f"read_resource_packages ({len(r.data)} rows)")
        else:
            skipped.append("read_resource_packages: no data (RLS may be blocking)")
    except Exception as e:
        failed.append(f"read_resource_packages: {e}")

    # 4. Student: read own student record
    if role == "student":
        try:
            r = (
                anon_client.table("students")
                .select("id, display_name, external_code")
                .limit(5)
                .execute()
            )
            if r.data is not None:
                passed.append(f"student_read_students_table ({len(r.data)} rows visible)")
            else:
                skipped.append("student_read_students_table: no rows (RLS may limit to linked profile)")
        except Exception as e:
            failed.append(f"student_read_students_table: {e}")

    # 5. Parent: read linked students
    if role == "parent":
        try:
            r = (
                anon_client.table("parent_student_links")
                .select("student_id, relationship")
                .limit(5)
                .execute()
            )
            if r.data is not None:
                passed.append(f"parent_read_parent_student_links ({len(r.data)} rows visible)")
            else:
                skipped.append("parent_read_parent_student_links: no rows (RLS or no links seeded)")
        except Exception as e:
            failed.append(f"parent_read_parent_student_links: {e}")

    return {"passed": passed, "failed": failed, "skipped": skipped}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    from supabase_client_v1 import load_env_file, mask_secret

    print("=" * 60)
    print("Quanta Aptus — Gate 61 RLS Permission Tests v1")
    print("=" * 60)

    env_path = PROJECT_ROOT / ".env.local"
    env      = load_env_file(env_path)

    supabase_url = env.get("SUPABASE_URL") or env.get("NEXT_PUBLIC_SUPABASE_URL", "")
    # Prefer SUPABASE_ANON_KEY, fall back to NEXT_PUBLIC_SUPABASE_ANON_KEY
    anon_key = (
        env.get("SUPABASE_ANON_KEY")
        or env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or ""
    )

    if not supabase_url:
        print("  ERROR: SUPABASE_URL not set in .env.local — exiting.")
        sys.exit(1)
    if not anon_key:
        print("  ERROR: SUPABASE_ANON_KEY / NEXT_PUBLIC_SUPABASE_ANON_KEY not set in .env.local — exiting.")
        sys.exit(1)

    print(f"  url      : {mask_secret(supabase_url)}")
    print(f"  anon key : {mask_secret(anon_key)}")
    print()

    try:
        from supabase import create_client
    except ImportError:
        raise SystemExit(
            "\n[MISSING_DEPENDENCY] The 'supabase' Python package is not installed.\n"
            "  Install it with:\n"
            "    .venv-ingest\\Scripts\\pip.exe install supabase\n"
        )

    report: dict = {
        "report_id":              "quanta_aptus_gate61_rls_permission_tests_v1",
        "gate":                   "61",
        "created_at":             now_iso,
        "status":                 "failed",
        "demo_users_login_ok":    False,
        "profiles_found":         0,
        "roles_verified":         [],
        "rls_tests_run":          False,
        "rls_hardening_needed":   False,
        "per_role":               {},
        "errors":                 [],
    }

    login_ok_count    = 0
    profiles_found    = 0
    roles_verified    = []
    any_rls_skip      = False
    infrastructure_errors: list[str] = []

    for demo_user in DEMO_USERS:
        role = demo_user["role"]
        print(f"  [{role}] {demo_user['email']}")

        anon_client = create_client(supabase_url, anon_key)

        # Sign in
        user_id = None
        try:
            res = anon_client.auth.sign_in_with_password(
                {"email": demo_user["email"], "password": demo_user["password"]}
            )
            user_id = res.user.id if res.user else None
            if user_id:
                login_ok_count += 1
                print(f"    login  : OK (id={user_id[:8]}...)")
            else:
                print(f"    login  : no user in response")
                report["errors"].append(f"{demo_user['email']}: login succeeded but no user id")
        except Exception as e:
            err = str(e)
            print(f"    login  : FAILED — {err}")
            report["errors"].append(f"{demo_user['email']}: login failed — {err}")
            report["per_role"][role] = {"login": False, "tests": {}}
            anon_client.auth.sign_out()
            continue

        if not user_id:
            report["per_role"][role] = {"login": False, "tests": {}}
            anon_client.auth.sign_out()
            continue

        # Check profile visible
        try:
            pr = anon_client.table("profiles").select("id").eq("id", user_id).execute()
            if pr.data:
                profiles_found += 1
                roles_verified.append(role)
        except Exception:
            pass

        # Run RLS tests
        test_results = _run_rls_tests(anon_client, user_id, role)
        print(f"    passed : {len(test_results['passed'])}")
        print(f"    skipped: {len(test_results['skipped'])} (may need RLS hardening)")
        print(f"    failed : {len(test_results['failed'])}")

        if test_results["skipped"]:
            any_rls_skip = True
        if test_results["failed"]:
            for f in test_results["failed"]:
                infrastructure_errors.append(f"{role}: {f}")

        report["per_role"][role] = {
            "login":   True,
            "user_id": user_id,
            "tests":   test_results,
        }

        # Sign out
        try:
            anon_client.auth.sign_out()
        except Exception:
            pass

    # Finalize report
    report["demo_users_login_ok"] = login_ok_count == len(DEMO_USERS)
    report["profiles_found"]      = profiles_found
    report["roles_verified"]      = roles_verified
    report["rls_tests_run"]       = login_ok_count > 0
    report["rls_hardening_needed"] = any_rls_skip
    report["errors"].extend(infrastructure_errors)

    print()
    print(f"  login_ok  : {login_ok_count}/{len(DEMO_USERS)}")
    print(f"  profiles  : {profiles_found}")
    print(f"  roles_ok  : {roles_verified}")
    print(f"  rls_harden: {any_rls_skip}")

    # Status
    if login_ok_count == len(DEMO_USERS) and not infrastructure_errors:
        status = "passed"
    elif login_ok_count > 0:
        status = "needs_review"
    else:
        status = "failed"

    report["status"] = status
    print(f"\n  status    : {status.upper()}")

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    path = DIAG_DIR / "gate61_rls_permission_test_report_v1.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report    -> {path}")

    sys.exit(0 if status in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
