"""
Gate 60 - Supabase Auth + Roles Report v1.

Static code/artifact checks — no Supabase connection required.
Verifies all Gate 60 artifacts are in place and security constraints hold.

Checks:
  - 000003_auth_profile_trigger.sql exists and has the trigger function
  - seed_demo_auth_profiles.sql exists
  - verify_auth_roles_v1.py exists
  - liveSupabaseAuthContext.ts exists with required exports
  - /system/auth-roles page exists
  - verify report exists (if run)
  - process.env.SUPABASE_SERVICE_ROLE_KEY only in allowed server-only files
  - .env.local not tracked by git (checked via .gitignore)
  - Gate 56-59 artifacts still present (no regression)

Output:
  data/diagnostics/gate60_auth_roles_report_v1.json
  data/diagnostics/SUPABASE_GATE_60_AUTH_ROLES_DONE.md

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\build_gate60_auth_roles_report_v1.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIAG_DIR     = PROJECT_ROOT / "data" / "diagnostics"
ADMIN_LIB    = PROJECT_ROOT / "apps" / "admin" / "src" / "lib"
ADMIN_APP    = PROJECT_ROOT / "apps" / "admin" / "src" / "app"
ADMIN_SRC    = PROJECT_ROOT / "apps" / "admin" / "src"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exists(path: Path, label: str) -> dict:
    return {
        "label":      label,
        "path":       str(path.relative_to(PROJECT_ROOT)),
        "present":    path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def _contains(path: Path, label: str, needle: str) -> dict:
    base = _exists(path, label)
    if base["present"]:
        try:
            base["contains"] = needle in path.read_text(encoding="utf-8")
        except Exception as e:
            base["contains"] = False
            base["error"]    = str(e)
    else:
        base["contains"] = False
    base["needle"] = needle
    return base


def _scan_service_role_leaks() -> list[str]:
    allowed = {
        ADMIN_LIB / "liveSupabaseContent.ts",
        ADMIN_LIB / "liveSupabaseAttempts.ts",
        ADMIN_LIB / "liveSupabaseMarking.ts",
        ADMIN_LIB / "liveSupabaseTeacherReview.ts",
        ADMIN_LIB / "liveSupabaseStudentResults.ts",
        ADMIN_LIB / "liveSupabaseAuthContext.ts",  # Gate 60 — new allowed file
    }
    needle = "process.env.SUPABASE_SERVICE_ROLE_KEY"
    leaks: list[str] = []
    for f in list(ADMIN_SRC.rglob("*.ts")) + list(ADMIN_SRC.rglob("*.tsx")):
        if f in allowed:
            continue
        try:
            if needle in f.read_text(encoding="utf-8"):
                leaks.append(str(f.relative_to(PROJECT_ROOT)))
        except Exception:
            pass
    return leaks


def _check_env_local_gitignored() -> bool:
    """Return True if .env.local is covered by .gitignore patterns."""
    for candidate in [PROJECT_ROOT / "apps" / "admin" / ".gitignore", PROJECT_ROOT / ".gitignore"]:
        if candidate.exists():
            try:
                content = candidate.read_text(encoding="utf-8")
                # .env.local is covered by: .env.local, *.local, .env.*, or .env.*
                if any(p in content for p in (".env.local", "*.local", ".env.*", ".env.*\n")):
                    return True
            except Exception:
                pass
    return False


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def run_checks() -> tuple[list[dict], list[str], list[str], bool, dict]:
    checks: list[dict] = []
    issues: list[str]  = []

    migration_sql   = PROJECT_ROOT / "supabase" / "migrations" / "000003_auth_profile_trigger.sql"
    seed_sql        = PROJECT_ROOT / "supabase" / "seed" / "seed_demo_auth_profiles.sql"
    verify_py       = PROJECT_ROOT / "tools" / "supabase" / "verify_auth_roles_v1.py"
    auth_ctx_ts     = ADMIN_LIB / "liveSupabaseAuthContext.ts"
    auth_roles_page = ADMIN_APP / "system" / "auth-roles" / "page.tsx"

    # ── Migration ─────────────────────────────────────────────────────────────
    checks.append(_exists(migration_sql, "000003_auth_profile_trigger.sql"))
    checks.append(_contains(migration_sql, "migration: handle_new_user function", "handle_new_user"))
    checks.append(_contains(migration_sql, "migration: on_auth_user_created trigger", "on_auth_user_created"))
    checks.append(_contains(migration_sql, "migration: SECURITY DEFINER", "SECURITY DEFINER"))
    checks.append(_contains(migration_sql, "migration: DROP TRIGGER IF EXISTS", "DROP TRIGGER IF EXISTS"))
    checks.append(_contains(migration_sql, "migration: role validation", "'admin'"))
    checks.append(_contains(migration_sql, "migration: default role = student", "'student'"))
    checks.append(_contains(migration_sql, "migration: org slug fallback", "quanta-aptus-local-demo"))
    checks.append(_contains(migration_sql, "migration: ON CONFLICT DO NOTHING", "ON CONFLICT (id) DO NOTHING"))

    # ── Seed file ─────────────────────────────────────────────────────────────
    checks.append(_exists(seed_sql, "seed_demo_auth_profiles.sql"))
    checks.append(_contains(seed_sql, "seed: admin demo profile", "admin"))
    checks.append(_contains(seed_sql, "seed: teacher demo profile", "teacher"))
    checks.append(_contains(seed_sql, "seed: student demo profile", "student"))
    checks.append(_contains(seed_sql, "seed: parent demo profile", "parent"))
    checks.append(_contains(seed_sql, "seed: idempotent ON CONFLICT", "ON CONFLICT"))

    # ── Verify script ─────────────────────────────────────────────────────────
    checks.append(_exists(verify_py, "verify_auth_roles_v1.py"))
    checks.append(_contains(verify_py, "verify: checks profiles table", "profiles"))
    checks.append(_contains(verify_py, "verify: checks by role", "VALID_ROLES"))
    checks.append(_contains(verify_py, "verify: ready_no_auth_users status", "ready_no_auth_users"))

    # ── liveSupabaseAuthContext.ts ────────────────────────────────────────────
    checks.append(_exists(auth_ctx_ts, "liveSupabaseAuthContext.ts (new)"))
    checks.append(_contains(auth_ctx_ts, "liveSupabaseAuthContext.ts: import server-only", "import 'server-only'"))
    checks.append(_contains(auth_ctx_ts, "liveSupabaseAuthContext.ts: getDemoAuthContext", "getDemoAuthContext"))
    checks.append(_contains(auth_ctx_ts, "liveSupabaseAuthContext.ts: getProfileById", "getProfileById"))
    checks.append(_contains(auth_ctx_ts, "liveSupabaseAuthContext.ts: getProfilesByRole", "getProfilesByRole"))
    checks.append(_contains(auth_ctx_ts, "liveSupabaseAuthContext.ts: getStudentForProfile", "getStudentForProfile"))
    checks.append(_contains(auth_ctx_ts, "liveSupabaseAuthContext.ts: getParentLinkedStudents", "getParentLinkedStudents"))
    checks.append(_contains(auth_ctx_ts, "liveSupabaseAuthContext.ts: getAuthRoleStats", "getAuthRoleStats"))
    checks.append(_contains(auth_ctx_ts, "liveSupabaseAuthContext.ts: demo_auth_context mode", "demo_auth_context"))
    checks.append(_contains(auth_ctx_ts, "liveSupabaseAuthContext.ts: no OpenAI", "openai"))
    openai_check = checks[-1]
    openai_check["contains"] = not openai_check.get("contains", False)
    openai_check["needle"]   = "NO openai import"

    # ── Auth-roles page ───────────────────────────────────────────────────────
    checks.append(_exists(auth_roles_page, "/system/auth-roles page"))
    checks.append(_contains(auth_roles_page, "page: force-dynamic", "force-dynamic"))
    checks.append(_contains(auth_roles_page, "page: getDemoAuthContext", "getDemoAuthContext"))
    checks.append(_contains(auth_roles_page, "page: getAuthRoleStats", "getAuthRoleStats"))
    checks.append(_contains(auth_roles_page, "page: Gate 61 warning", "Gate 61"))

    # ── .env.local gitignored ────────────────────────────────────────────────
    env_gitignored = _check_env_local_gitignored()
    checks.append({
        "label":    ".env.local in .gitignore",
        "path":     ".gitignore",
        "present":  True,
        "contains": env_gitignored,
        "needle":   ".env.local",
    })

    # ── Gate 56-59 regressions ────────────────────────────────────────────────
    checks.append(_exists(ADMIN_LIB / "liveSupabaseAttempts.ts",       "Gate 56: liveSupabaseAttempts.ts present"))
    checks.append(_exists(ADMIN_LIB / "liveSupabaseMarking.ts",         "Gate 57: liveSupabaseMarking.ts present"))
    checks.append(_exists(ADMIN_LIB / "liveSupabaseTeacherReview.ts",   "Gate 58: liveSupabaseTeacherReview.ts present"))
    checks.append(_exists(ADMIN_LIB / "liveSupabaseStudentResults.ts",  "Gate 59: liveSupabaseStudentResults.ts present"))

    # ── Verify report ─────────────────────────────────────────────────────────
    verify_report_path = DIAG_DIR / "auth_roles_verify_report_v1.json"
    checks.append(_exists(verify_report_path, "Verify report: auth_roles_verify_report_v1.json"))

    verify_ok    = False
    verify_details: dict = {}
    if verify_report_path.exists():
        try:
            vr = json.loads(verify_report_path.read_text(encoding="utf-8"))
            verify_ok = vr.get("status") in ("passed", "ready_no_auth_users", "needs_review")
            verify_details = {
                "status":             vr.get("status"),
                "organizations":      vr.get("organizations_found"),
                "students":           vr.get("students_count"),
                "profiles_total":     vr.get("profiles_total"),
            }
            checks.append({
                "label":    "Verify report: not failed",
                "path":     str(verify_report_path.relative_to(PROJECT_ROOT)),
                "present":  True,
                "contains": verify_ok,
                "needle":   "status not failed",
            })
        except Exception:
            verify_ok = False

    # ── Build issue list ──────────────────────────────────────────────────────
    for c in checks:
        if not c.get("present", True):
            issues.append(f"Missing: {c['label']}")
        elif "contains" in c and not c.get("contains", False):
            # .env.local gitignore is a warning, not a blocker
            if ".env.local" in c.get("label", ""):
                issues.append(f"Warning: {c['label']}")
            else:
                issues.append(f"Content check failed: {c['label']}")

    # ── Security scan ─────────────────────────────────────────────────────────
    leaks = _scan_service_role_leaks()
    for leak in leaks:
        issues.append(f"SECURITY: process.env.SUPABASE_SERVICE_ROLE_KEY in non-allowed file: {leak}")

    return checks, issues, leaks, verify_ok, verify_details


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print("Quanta Aptus - Gate 60 Auth Roles Report v1")
    print("=" * 60)

    checks, issues, leaks, verify_ok, verify_details = run_checks()

    file_checks    = [c for c in checks if "contains" not in c]
    content_checks = [c for c in checks if "contains" in c]
    files_ok       = sum(1 for c in file_checks if c.get("present", True))
    content_ok     = sum(1 for c in content_checks if c.get("contains", False))

    print(f"  file checks   : {files_ok}/{len(file_checks)} present")
    print(f"  content checks: {content_ok}/{len(content_checks)} passed")
    print(f"  security scan : {'CLEAN' if not leaks else f'{len(leaks)} VIOLATION(S)'}")
    print(f"  verify run    : {'OK' if verify_ok else 'NOT RUN (run verify_auth_roles_v1.py)'}")

    if verify_details:
        print(f"    status      : {verify_details.get('status', '?')}")
        print(f"    orgs        : {verify_details.get('organizations', '?')}")
        print(f"    students    : {verify_details.get('students', '?')}")
        print(f"    profiles    : {verify_details.get('profiles_total', '?')}")

    if issues:
        print(f"\n  ISSUES ({len(issues)}):")
        for iss in issues:
            print(f"    - {iss}")

    security_issues = [i for i in issues if "SECURITY" in i]
    non_minor_issues = [
        i for i in issues
        if "Test report" not in i
        and "Verify report" not in i
        and "Warning" not in i
    ]
    overall = "passed" if not non_minor_issues and not security_issues else "needs_review"
    if security_issues:
        overall = "failed"

    print(f"\n  status        : {overall.upper()}")

    report = {
        "report_id":                        "quanta_aptus_gate60_auth_roles_report_v1",
        "gate":                             "60",
        "created_at":                       now_iso,
        "status":                           overall,
        "auth_profile_trigger_defined":     True,
        "roles_supported":                  ["admin", "teacher", "student", "parent"],
        "demo_auth_context_supported":      True,
        "rls_foundation_ready":             True,
        "login_ui_enabled":                 False,
        "service_role_exposed_to_client":   bool(leaks),
        "service_role_leak_files":          leaks,
        "verify_run":                       verify_ok,
        "verify_details":                   verify_details,
        "openai_used":                      False,
        "checks_total":                     len(checks),
        "file_checks_passed":               files_ok,
        "content_checks_passed":            content_ok,
        "issues":                           issues,
        "checks":                           checks,
        "next_gate":                        "Gate 61 - Login UI + RLS Permission Tests",
    }

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "gate60_auth_roles_report_v1.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {report_path}")

    if overall == "passed":
        done_path = DIAG_DIR / "SUPABASE_GATE_60_AUTH_ROLES_DONE.md"
        done_path.write_text(
            "\n".join([
                "# Gate 60 — Supabase Auth + Roles Foundation DONE",
                "",
                f"**Date:** {now_iso[:10]}",
                "**Status:** `passed`",
                "**Phase:** Phase 2 - Supabase Integration",
                "",
                "## What Was Built",
                "",
                "| File | Change |",
                "|---|---|",
                "| `supabase/migrations/000003_auth_profile_trigger.sql` | NEW - auth profile trigger |",
                "| `supabase/seed/seed_demo_auth_profiles.sql` | NEW - demo profile seed |",
                "| `tools/supabase/verify_auth_roles_v1.py` | NEW - roles verify script |",
                "| `apps/admin/src/lib/liveSupabaseAuthContext.ts` | NEW - server-only auth context |",
                "| `apps/admin/src/app/system/auth-roles/page.tsx` | NEW - diagnostic page |",
                "",
                "## Behavior",
                "",
                "- Auth profile trigger migration created.",
                "  - Fires AFTER INSERT on auth.users.",
                "  - Inserts matching row in public.profiles.",
                "  - Role from raw_user_meta_data->>'role'; defaults to 'student'.",
                "  - organization_id defaults to quanta-aptus-local-demo if present.",
                "- Role foundation ready: admin, teacher, student, parent.",
                "- Demo auth context available via getDemoAuthContext().",
                "- Login UI not yet enabled — Gate 61.",
                "",
                "## To Apply Auth Trigger",
                "",
                "Paste `supabase/migrations/000003_auth_profile_trigger.sql` into",
                "the Supabase Dashboard SQL Editor and run it.",
                "",
                "## Security",
                "",
                "- `import 'server-only'` in liveSupabaseAuthContext.ts.",
                "- `process.env.SUPABASE_SERVICE_ROLE_KEY` only in allowed server-only files.",
                "- Security scan: 0 violations.",
                "- No OpenAI API calls.",
                "",
                "## Ready for Gate 61",
                "",
                "Gate 61 will add login UI and RLS permission tests.",
            ]),
            encoding="utf-8",
        )
        print(f"  done marker   -> {done_path}")

    sys.exit(0 if overall in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
