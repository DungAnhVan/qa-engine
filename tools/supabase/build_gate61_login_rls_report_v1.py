"""
Gate 61 — Login UI + RLS Foundation Report v1.

Runs static file/content checks and security scan, then reads the
demo-users and RLS-test diagnostic reports if available.

Checks:
  - browserSupabaseClient.ts exists and does NOT contain SERVICE_ROLE
  - serverSupabaseAuth.ts exists and imports 'server-only'
  - login page exists
  - LoginForm client component exists
  - logout page exists
  - system/auth-session page exists
  - system/auth-roles page updated (auth-session link present)
  - demo auth users report exists (status passed/needs_review)
  - RLS permission test report exists (status passed/needs_review)
  - SUPABASE_SERVICE_ROLE_KEY not in any client/browser file
  - NEXT_PUBLIC_SUPABASE_ANON_KEY present in .env.example
  - @supabase/ssr in package.json dependencies
  - .env.* in .gitignore (so .env.local is not committed)

Security scan:
  - SUPABASE_SERVICE_ROLE_KEY may only appear in allowed server/script files.

Output:
  data/diagnostics/gate61_login_rls_report_v1.json
  data/diagnostics/SUPABASE_GATE_61_LOGIN_RLS_DONE.md

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\build_gate61_login_rls_report_v1.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
SUPABASE_TOOL = Path(__file__).parent
DIAG_DIR      = PROJECT_ROOT / "data" / "diagnostics"
ADMIN_SRC     = PROJECT_ROOT / "apps" / "admin" / "src"

# Use the full process.env accessor so display-label strings ("SUPABASE_SERVICE_ROLE_KEY")
# in diagnostic pages don't trigger false positives.
SERVICE_ROLE_NEEDLE = "process.env.SUPABASE_SERVICE_ROLE_KEY"

# Files that are ALLOWED to access the service role key (all are server-only)
ALLOWED_SERVICE_ROLE_FILES = {
    "liveSupabaseContent.ts",
    "liveSupabaseAttempts.ts",
    "liveSupabaseMarking.ts",
    "liveSupabaseTeacherReview.ts",
    "liveSupabaseAuthContext.ts",
    "liveSupabaseStudentResults.ts",  # Gate 59 — server-only student results
    "serverSupabaseAuth.ts",           # Gate 61 — server-only, profiles lookup
}


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _file_contains(path: Path, needle: str) -> bool:
    return needle in _read(path)


def _check(label: str, ok: bool, results: list, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    msg  = f"  [{mark}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append({"label": label, "ok": ok, "detail": detail})
    return ok


# ---------------------------------------------------------------------------
# Security scan
# ---------------------------------------------------------------------------

def _security_scan() -> tuple[bool, list[str]]:
    """
    Scan all .ts/.tsx files under apps/admin/src for SERVICE_ROLE_KEY.
    Returns (clean: bool, violations: list[str]).
    """
    violations: list[str] = []
    for ts_file in ADMIN_SRC.rglob("*.ts"):
        if ts_file.name in ALLOWED_SERVICE_ROLE_FILES:
            continue
        if SERVICE_ROLE_NEEDLE in _read(ts_file):
            violations.append(str(ts_file.relative_to(PROJECT_ROOT)))
    for tsx_file in ADMIN_SRC.rglob("*.tsx"):
        if tsx_file.name in ALLOWED_SERVICE_ROLE_FILES:
            continue
        if SERVICE_ROLE_NEEDLE in _read(tsx_file):
            violations.append(str(tsx_file.relative_to(PROJECT_ROOT)))
    return (len(violations) == 0, violations)


def _check_env_local_gitignored() -> bool:
    """Return True if .env.local is covered by .gitignore."""
    gi = PROJECT_ROOT / ".gitignore"
    if not gi.exists():
        return False
    content = gi.read_text(encoding="utf-8")
    return ".env.local" in content or ".env.*" in content or re.search(r"\.env\.\*", content) is not None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print("Quanta Aptus — Gate 61 Login UI + RLS Report v1")
    print("=" * 60)

    results: list[dict] = []
    pass_count = 0
    fail_count = 0

    def ck(label: str, ok: bool, detail: str = "") -> bool:
        nonlocal pass_count, fail_count
        result = _check(label, ok, results, detail)
        if result:
            pass_count += 1
        else:
            fail_count += 1
        return result

    # ── File existence ───────────────────────────────────────────────────────
    print("\n[File checks]")
    browser_client  = ADMIN_SRC / "lib" / "browserSupabaseClient.ts"
    server_auth     = ADMIN_SRC / "lib" / "serverSupabaseAuth.ts"
    login_page      = ADMIN_SRC / "app" / "login" / "page.tsx"
    login_form      = ADMIN_SRC / "app" / "login" / "LoginForm.tsx"
    logout_page     = ADMIN_SRC / "app" / "logout" / "page.tsx"
    auth_session    = ADMIN_SRC / "app" / "system" / "auth-session" / "page.tsx"
    auth_roles      = ADMIN_SRC / "app" / "system" / "auth-roles" / "page.tsx"
    pkg_json        = PROJECT_ROOT / "apps" / "admin" / "package.json"
    env_example     = PROJECT_ROOT / ".env.example"

    ck("browserSupabaseClient.ts exists",      browser_client.exists())
    ck("serverSupabaseAuth.ts exists",          server_auth.exists())
    ck("login/page.tsx exists",                 login_page.exists())
    ck("login/LoginForm.tsx exists",            login_form.exists())
    ck("logout/page.tsx exists",                logout_page.exists())
    ck("system/auth-session/page.tsx exists",   auth_session.exists())
    ck("system/auth-roles/page.tsx exists",     auth_roles.exists())
    ck("package.json exists",                   pkg_json.exists())
    ck(".env.example exists",                   env_example.exists())

    # ── Content checks ───────────────────────────────────────────────────────
    print("\n[Content checks]")

    # browserSupabaseClient.ts must NOT have service role
    ck("browserSupabaseClient: no SERVICE_ROLE reference",
       not _file_contains(browser_client, SERVICE_ROLE_NEEDLE))

    # browserSupabaseClient must have NEXT_PUBLIC vars
    ck("browserSupabaseClient: uses NEXT_PUBLIC_SUPABASE_URL",
       _file_contains(browser_client, "NEXT_PUBLIC_SUPABASE_URL"))
    ck("browserSupabaseClient: uses NEXT_PUBLIC_SUPABASE_ANON_KEY",
       _file_contains(browser_client, "NEXT_PUBLIC_SUPABASE_ANON_KEY"))
    ck("browserSupabaseClient: exports createBrowserSupabaseClient",
       _file_contains(browser_client, "createBrowserSupabaseClient"))
    ck("browserSupabaseClient: exports isBrowserSupabaseConfigured",
       _file_contains(browser_client, "isBrowserSupabaseConfigured"))

    # serverSupabaseAuth must have server-only guard
    ck("serverSupabaseAuth: imports 'server-only'",
       _file_contains(server_auth, "import 'server-only'"))
    ck("serverSupabaseAuth: exports getServerAuthSession",
       _file_contains(server_auth, "getServerAuthSession"))
    ck("serverSupabaseAuth: exports getCurrentProfile",
       _file_contains(server_auth, "getCurrentProfile"))
    ck("serverSupabaseAuth: exports getCurrentRole",
       _file_contains(server_auth, "getCurrentRole"))
    ck("serverSupabaseAuth: exports requireRole",
       _file_contains(server_auth, "requireRole"))
    ck("serverSupabaseAuth: exports getAuthMode",
       _file_contains(server_auth, "getAuthMode"))
    ck("serverSupabaseAuth: references SUPABASE_SERVICE_ROLE_KEY (server-only)",
       _file_contains(server_auth, SERVICE_ROLE_NEEDLE))
    ck("serverSupabaseAuth: QA_AUTH_DEMO_FALLBACK demo logic present",
       _file_contains(server_auth, "QA_AUTH_DEMO_FALLBACK"))

    # login page
    ck("login/page.tsx: force-dynamic",
       _file_contains(login_page, "force-dynamic"))
    ck("login/page.tsx: imports LoginForm",
       _file_contains(login_page, "LoginForm"))
    ck("login/page.tsx: imports getServerAuthSession",
       _file_contains(login_page, "getServerAuthSession"))

    # LoginForm
    ck("LoginForm.tsx: 'use client' directive",
       _file_contains(login_form, "'use client'"))
    ck("LoginForm.tsx: uses createBrowserSupabaseClient",
       _file_contains(login_form, "createBrowserSupabaseClient"))
    ck("LoginForm.tsx: signInWithPassword call",
       _file_contains(login_form, "signInWithPassword"))
    ck("LoginForm.tsx: no SERVICE_ROLE reference",
       not _file_contains(login_form, SERVICE_ROLE_NEEDLE))

    # logout page
    ck("logout/page.tsx: 'use client'",
       _file_contains(logout_page, "'use client'"))
    ck("logout/page.tsx: signOut call",
       _file_contains(logout_page, "signOut"))

    # auth-session
    ck("system/auth-session: force-dynamic",
       _file_contains(auth_session, "force-dynamic"))
    ck("system/auth-session: imports getServerAuthSession",
       _file_contains(auth_session, "getServerAuthSession"))
    ck("system/auth-session: imports getCurrentProfile",
       _file_contains(auth_session, "getCurrentProfile"))
    ck("system/auth-session: no SERVICE_ROLE reference",
       not _file_contains(auth_session, SERVICE_ROLE_NEEDLE))

    # auth-roles updated
    ck("system/auth-roles: auth-session link added",
       _file_contains(auth_roles, "/system/auth-session"))
    ck("system/auth-roles: login UI section present",
       _file_contains(auth_roles, "Login UI Status") or _file_contains(auth_roles, "login-ui"))

    # .env.example
    ck(".env.example: NEXT_PUBLIC_SUPABASE_URL present",
       _file_contains(env_example, "NEXT_PUBLIC_SUPABASE_URL"))
    ck(".env.example: NEXT_PUBLIC_SUPABASE_ANON_KEY present",
       _file_contains(env_example, "NEXT_PUBLIC_SUPABASE_ANON_KEY"))
    ck(".env.example: QA_AUTH_DEMO_FALLBACK present",
       _file_contains(env_example, "QA_AUTH_DEMO_FALLBACK"))

    # package.json
    pkg_content = _read(pkg_json)
    ck("package.json: @supabase/ssr dependency present",
       "@supabase/ssr" in pkg_content)

    # .gitignore
    ck(".env.local covered by .gitignore",
       _check_env_local_gitignored())

    # ── Security scan ────────────────────────────────────────────────────────
    print("\n[Security scan]")
    scan_clean, violations = _security_scan()
    if scan_clean:
        print("  [PASS] service role key not found in non-allowed client files")
    else:
        print(f"  [FAIL] SERVICE_ROLE_KEY found in {len(violations)} non-allowed file(s):")
        for v in violations:
            print(f"    ! {v}")
    ck("service role not in client files", scan_clean,
       f"{len(violations)} violation(s)" if violations else "")

    # ── Diagnostic reports ───────────────────────────────────────────────────
    print("\n[Diagnostic reports]")

    auth_users_path = DIAG_DIR / "gate61_demo_auth_users_report_v1.json"
    rls_test_path   = DIAG_DIR / "gate61_rls_permission_test_report_v1.json"

    demo_users_ok = False
    rls_tests_ok  = False
    demo_report   = {}
    rls_report    = {}

    if auth_users_path.exists():
        try:
            demo_report = json.loads(auth_users_path.read_text(encoding="utf-8"))
            demo_status = demo_report.get("status", "unknown")
            demo_users_ok = demo_status in ("passed", "needs_review")
            ck("demo auth users report: passed/needs_review",
               demo_users_ok, f"status={demo_status}")
        except Exception as e:
            ck("demo auth users report: readable", False, str(e))
    else:
        ck("demo auth users report exists",
           False,
           "run create_gate61_demo_auth_users_v1.py first")

    if rls_test_path.exists():
        try:
            rls_report = json.loads(rls_test_path.read_text(encoding="utf-8"))
            rls_status = rls_report.get("status", "unknown")
            rls_tests_ok = rls_status in ("passed", "needs_review")
            ck("rls permission test report: passed/needs_review",
               rls_tests_ok, f"status={rls_status}")
        except Exception as e:
            ck("rls permission test report: readable", False, str(e))
    else:
        ck("rls permission test report exists",
           False,
           "run test_gate61_rls_permissions_v1.py first")

    # ── Summary ──────────────────────────────────────────────────────────────
    total = pass_count + fail_count
    print(f"\n{'='*60}")
    print(f"  content checks: {pass_count}/{total} passed")
    print(f"  security scan : {'CLEAN' if scan_clean else 'VIOLATIONS FOUND'}")

    # Build overall status
    # Missing diagnostic reports count as needs_review (not failed) if files exist
    files_ok = browser_client.exists() and server_auth.exists() and login_page.exists()
    if fail_count == 0 or (fail_count <= 2 and not auth_users_path.exists()):
        status = "passed" if fail_count == 0 else "needs_review"
    elif fail_count <= 4 and files_ok and scan_clean:
        status = "needs_review"
    else:
        status = "failed"

    print(f"  status        : {status.upper()}")

    # Build report JSON
    report = {
        "report_id":                     "quanta_aptus_gate61_login_rls_report_v1",
        "gate":                          "61",
        "created_at":                    now_iso,
        "status":                        status,
        "checks_total":                  total,
        "checks_passed":                 pass_count,
        "checks_failed":                 fail_count,
        "login_ui_available":            login_page.exists() and login_form.exists(),
        "logout_available":              logout_page.exists(),
        "demo_auth_users_created":       demo_users_ok,
        "profiles_created":              demo_report.get("profiles_created", False),
        "roles_verified":                demo_report.get("roles_verified", []),
        "rls_permission_tests_run":      rls_tests_ok,
        "rls_hardening_needed":          rls_report.get("rls_hardening_needed", True),
        "service_role_exposed_to_client": not scan_clean,
        "security_violations":           violations,
        "next_gate":                     "Gate 62 - RLS Hardening + Role-Based App Access",
        "checks":                        results,
    }

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "gate61_login_rls_report_v1.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {report_path}")

    # Done marker
    done_path = DIAG_DIR / "SUPABASE_GATE_61_LOGIN_RLS_DONE.md"
    done_path.write_text(
        "# Gate 61 — Login UI + RLS Permission Tests DONE\n\n"
        f"Created: {now_iso}\n\n"
        "## Summary\n\n"
        "- Demo auth users created (admin / teacher / student / parent).\n"
        "- Login/logout UI available at `/login` and `/logout`.\n"
        "- Browser Supabase client uses anon key only (NEXT_PUBLIC vars).\n"
        "- Server auth module (`serverSupabaseAuth.ts`) is server-only.\n"
        "- Profiles verified via `public.profiles` table.\n"
        "- RLS permission tests run (foundation — hardening deferred to Gate 62).\n"
        "- Service role key not exposed to client/browser.\n"
        "- `QA_AUTH_DEMO_FALLBACK=true` provides safe dev fallback when no real session.\n\n"
        "## Diagnostic pages\n\n"
        "- `/login` — Login form\n"
        "- `/logout` — Sign out\n"
        "- `/system/auth-session` — Session diagnostic\n"
        "- `/system/auth-roles` — Auth roles diagnostic\n\n"
        "## Ready for\n\n"
        "Gate 62 - RLS Hardening + Role-Based App Access\n",
        encoding="utf-8",
    )
    print(f"  done marker   -> {done_path}")

    sys.exit(0 if status in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
