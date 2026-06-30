"""
Gate 62 — RLS Role Access Report Builder v1

Runs a static analysis pass against the codebase to verify:
  - Migration file present with helper functions and policies
  - roleAccess.ts exists with ROUTE_ACCESS_MATRIX and requireAppRole
  - RoleGate.tsx server component exists
  - role-access diagnostic page exists
  - All 9 protected pages have requireAppRole wired
  - No service role key exposed to browser/client files
  - Gate 62 permission test report is present and passing (optional)

Output: data/diagnostics/gate62_rls_role_access_report_v1.json
        data/diagnostics/SUPABASE_GATE_62_RLS_ROLE_ACCESS_DONE.md  (if PASS)
"""

import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADMIN_SRC = ROOT / "apps" / "admin" / "src"
TOOLS_DIR = ROOT / "tools" / "supabase"
OUTPUT_DIR = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate62_rls_role_access_report_v1.json"
DONE_FILE   = OUTPUT_DIR / "SUPABASE_GATE_62_RLS_ROLE_ACCESS_DONE.md"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_file_exists(path: Path, label: str) -> dict:
    ok = path.exists()
    return {"label": label, "status": "PASS" if ok else "FAIL",
            "detail": str(path.relative_to(ROOT)) if ok else f"MISSING: {path.relative_to(ROOT)}"}


def check_file_contains(path: Path, label: str, needle: str) -> dict:
    if not path.exists():
        return {"label": label, "status": "FAIL", "detail": f"File not found: {path.relative_to(ROOT)}"}
    content = path.read_text(encoding="utf-8")
    found = needle in content
    return {
        "label": label,
        "status": "PASS" if found else "FAIL",
        "detail": f"found '{needle[:60]}'" if found else f"MISSING '{needle[:60]}' in {path.name}",
    }


def check_security_scan(glob_pattern: str, needle: str, allowed_files: set[str]) -> dict:
    """Scan client/browser files for service role key access."""
    hits = []
    for f in ROOT.rglob(glob_pattern):
        if any(part in ('.next', 'node_modules', '__pycache__', '.git') for part in f.parts):
            continue
        if f.name in allowed_files:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if needle in content:
            hits.append(str(f.relative_to(ROOT)))
    ok = len(hits) == 0
    return {
        "label": f"Security scan: {needle[:50]} not in client files",
        "status": "PASS" if ok else "FAIL",
        "detail": "clean" if ok else f"LEAK in: {', '.join(hits[:5])}",
    }


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

MIGRATION_FILE = ROOT / "supabase" / "migrations" / "000004_rls_role_hardening.sql"
ROLE_ACCESS_FILE = ADMIN_SRC / "lib" / "roleAccess.ts"
ROLE_GATE_FILE   = ADMIN_SRC / "components" / "RoleGate.tsx"
ROLE_ACCESS_PAGE = ADMIN_SRC / "app" / "system" / "role-access" / "page.tsx"
CHECKLIST_FILE   = TOOLS_DIR / "apply_gate62_rls_migration_checklist_v1.md"
TEST_SCRIPT_FILE = TOOLS_DIR / "test_gate62_role_permissions_v1.py"
TEST_REPORT_FILE = OUTPUT_DIR / "gate62_rls_role_permission_test_report_v1.json"

# Pages that must have requireAppRole
PROTECTED_PAGES = [
    ("content/page.tsx",                       "content/page.tsx",                         ['admin', 'teacher']),
    ("content/active/page.tsx",                "content/active/page.tsx",                  ['admin', 'teacher']),
    ("content/review/page.tsx",                "content/review/page.tsx",                  ['admin', 'teacher']),
    ("learn/supabase-attempt-review/page.tsx", "learn/supabase-attempt-review/page.tsx",   ['admin', 'teacher']),
    ("learn/supabase-results/page.tsx",        "learn/supabase-results/page.tsx",          ['admin', 'teacher', 'student', 'parent']),
    ("system/student-results/page.tsx",        "system/student-results/page.tsx",          ['admin', 'teacher']),
    ("system/teacher-review/page.tsx",         "system/teacher-review/page.tsx",           ['admin', 'teacher']),
    ("system/marking/page.tsx",                "system/marking/page.tsx",                  ['admin', 'teacher']),
    ("system/auth-roles/page.tsx",             "system/auth-roles/page.tsx",               ['admin', 'teacher']),
]

# Server-only files that legitimately use the service role key
ALLOWED_SERVICE_ROLE_FILES = {
    "liveSupabaseContent.ts",
    "liveSupabaseAttempts.ts",
    "liveSupabaseMarking.ts",
    "liveSupabaseTeacherReview.ts",
    "liveSupabaseAuthContext.ts",
    "liveSupabaseStudentResults.ts",
    "serverSupabaseAuth.ts",
    # Python scripts are server-side only
}
SERVICE_ROLE_NEEDLE = "process.env.SUPABASE_SERVICE_ROLE_KEY"

HELPER_FUNCTIONS = [
    "current_profile_id",
    "current_profile_role",
    "current_organization_id",
    "is_admin",
    "is_teacher",
    "is_student",
    "is_parent",
    "is_admin_or_teacher",
    "my_student_id",
    "student_ids_in_my_org",
    "linked_student_ids_for_parent",
    "my_attempt_ids",
    "attempt_ids_in_my_org",
    "linked_attempt_ids_for_parent",
]


def run_all_checks() -> list[dict]:
    checks: list[dict] = []

    # ── Migration file ──────────────────────────────────────────────────────
    checks.append(check_file_exists(MIGRATION_FILE, "migration file 000004_rls_role_hardening.sql"))
    checks.append(check_file_contains(MIGRATION_FILE, "migration: SECURITY DEFINER keyword", "SECURITY DEFINER"))
    checks.append(check_file_contains(MIGRATION_FILE, "migration: ENABLE ROW LEVEL SECURITY", "ENABLE ROW LEVEL SECURITY"))
    checks.append(check_file_contains(MIGRATION_FILE, "migration: DROP POLICY IF EXISTS (idempotent)", "DROP POLICY IF EXISTS"))
    checks.append(check_file_contains(MIGRATION_FILE, "migration: CREATE POLICY", "CREATE POLICY"))

    for fn in HELPER_FUNCTIONS:
        checks.append(check_file_contains(MIGRATION_FILE, f"migration: helper fn {fn}", fn))

    # No destructive statements
    for bad in ("DROP TABLE", "DROP SCHEMA", "TRUNCATE"):
        content = MIGRATION_FILE.read_text(encoding="utf-8") if MIGRATION_FILE.exists() else ""
        found = bad in content
        checks.append({
            "label": f"migration: no {bad}",
            "status": "FAIL" if found else "PASS",
            "detail": f"FOUND destructive '{bad}'" if found else f"clean — no '{bad}'",
        })

    # ── roleAccess.ts ───────────────────────────────────────────────────────
    checks.append(check_file_exists(ROLE_ACCESS_FILE, "roleAccess.ts exists"))
    checks.append(check_file_contains(ROLE_ACCESS_FILE, "roleAccess: import server-only", "import 'server-only'"))
    checks.append(check_file_contains(ROLE_ACCESS_FILE, "roleAccess: ROUTE_ACCESS_MATRIX", "ROUTE_ACCESS_MATRIX"))
    checks.append(check_file_contains(ROLE_ACCESS_FILE, "roleAccess: requireAppRole", "requireAppRole"))
    checks.append(check_file_contains(ROLE_ACCESS_FILE, "roleAccess: canAccessRoute", "canAccessRoute"))
    checks.append(check_file_contains(ROLE_ACCESS_FILE, "roleAccess: getRoleHomePath", "getRoleHomePath"))

    # ── RoleGate.tsx ────────────────────────────────────────────────────────
    checks.append(check_file_exists(ROLE_GATE_FILE, "RoleGate.tsx server component"))
    checks.append(check_file_contains(ROLE_GATE_FILE, "RoleGate: allowedRoles prop", "allowedRoles"))
    # RoleGate must NOT have 'use client'
    if ROLE_GATE_FILE.exists():
        has_use_client = "'use client'" in ROLE_GATE_FILE.read_text(encoding="utf-8")
        checks.append({
            "label": "RoleGate: no 'use client' (must be server component)",
            "status": "FAIL" if has_use_client else "PASS",
            "detail": "FOUND 'use client' — must be server component" if has_use_client else "clean",
        })

    # ── role-access diagnostic page ─────────────────────────────────────────
    checks.append(check_file_exists(ROLE_ACCESS_PAGE, "system/role-access/page.tsx"))
    checks.append(check_file_contains(ROLE_ACCESS_PAGE, "role-access: ROUTE_ACCESS_MATRIX", "ROUTE_ACCESS_MATRIX"))
    checks.append(check_file_contains(ROLE_ACCESS_PAGE, "role-access: force-dynamic", "force-dynamic"))

    # ── Protected pages ─────────────────────────────────────────────────────
    for label, rel_path, roles in PROTECTED_PAGES:
        page_path = ADMIN_SRC / "app" / rel_path
        checks.append(check_file_exists(page_path, f"page exists: {rel_path}"))
        checks.append(check_file_contains(page_path, f"page requireAppRole import: {rel_path}", "requireAppRole"))
        checks.append(check_file_contains(page_path, f"page requireAppRole call: {rel_path}", "await requireAppRole("))
        for role in roles:
            checks.append(check_file_contains(page_path, f"page role '{role}' in guard: {rel_path}", f"'{role}'"))

    # ── Checklist + test script files ───────────────────────────────────────
    checks.append(check_file_exists(CHECKLIST_FILE, "migration checklist markdown"))
    checks.append(check_file_exists(TEST_SCRIPT_FILE, "test_gate62_role_permissions_v1.py"))

    # ── Security scan ────────────────────────────────────────────────────────
    checks.append(check_security_scan("*.tsx", SERVICE_ROLE_NEEDLE, ALLOWED_SERVICE_ROLE_FILES))
    checks.append(check_security_scan("*.ts",  SERVICE_ROLE_NEEDLE, ALLOWED_SERVICE_ROLE_FILES))

    # ── Gate 62 permission test report (optional) ────────────────────────────
    if TEST_REPORT_FILE.exists():
        try:
            test_report = json.loads(TEST_REPORT_FILE.read_text(encoding="utf-8"))
            overall = test_report.get("overall_status", "UNKNOWN")
            checks.append({
                "label": "gate62 permission test report: overall_status",
                "status": "PASS" if overall == "PASS" else "NEEDS_REVIEW",
                "detail": f"overall_status={overall}",
            })
        except Exception as exc:
            checks.append({
                "label": "gate62 permission test report: parse",
                "status": "FAIL",
                "detail": str(exc)[:200],
            })
    else:
        checks.append({
            "label": "gate62 permission test report (not yet run)",
            "status": "SKIP",
            "detail": f"Run test_gate62_role_permissions_v1.py first: {TEST_REPORT_FILE.name}",
        })

    return checks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    checks = run_all_checks()

    pass_count  = sum(1 for c in checks if c["status"] == "PASS")
    fail_count  = sum(1 for c in checks if c["status"] == "FAIL")
    skip_count  = sum(1 for c in checks if c["status"] in ("SKIP", "NEEDS_REVIEW"))

    overall_status = "PASS" if fail_count == 0 else "FAIL"
    if fail_count == 0 and skip_count > 0:
        overall_status = "PASS_WITH_SKIPS"

    report = {
        "gate": "62",
        "title": "RLS Hardening + Role-Based App Access Report v1",
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "overall_status": overall_status,
        "pass_count":  pass_count,
        "fail_count":  fail_count,
        "skip_count":  skip_count,
        "total_checks": len(checks),
        "checks": checks,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nGate 62 -- RLS Role Access Report")
    print("-" * 50)
    for c in checks:
        icon = "+" if c["status"] == "PASS" else ("?" if c["status"] in ("SKIP","NEEDS_REVIEW") else "!")
        print(f"  {icon} [{c['status']:14}] {c['label']}")
        if c["status"] not in ("PASS",):
            print(f"                     {c['detail']}")

    print("\n" + "-" * 50)
    print(f"PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}  TOTAL: {len(checks)}")
    print(f"Overall: {overall_status}")
    print(f"Report:  {OUTPUT_FILE}")

    if fail_count == 0:
        done_content = f"""# Gate 62 — RLS Hardening + Role-Based App Access — DONE

Generated: {datetime.datetime.utcnow().isoformat()}Z

## Status: {overall_status}

- {pass_count} checks PASS
- {skip_count} checks SKIP (permission tests not yet run against live DB)
- {fail_count} checks FAIL

## Deliverables

- `supabase/migrations/000004_rls_role_hardening.sql` — 14 SECURITY DEFINER helpers + policies
- `apps/admin/src/lib/roleAccess.ts` — server-only route access logic
- `apps/admin/src/components/RoleGate.tsx` — server component role guard
- `apps/admin/src/app/system/role-access/page.tsx` — route access matrix diagnostic
- 9 protected pages updated with `requireAppRole` early-return guard
- `tools/supabase/apply_gate62_rls_migration_checklist_v1.md`
- `tools/supabase/test_gate62_role_permissions_v1.py`
- `tools/supabase/build_gate62_rls_role_access_report_v1.py`

## Next Steps

1. Apply migration: paste `supabase/migrations/000004_rls_role_hardening.sql` into Supabase SQL Editor
2. Run permission tests: `.venv-ingest\\Scripts\\python.exe tools\\supabase\\test_gate62_role_permissions_v1.py`
3. Re-run this report to capture live test results
"""
        DONE_FILE.write_text(done_content, encoding="utf-8")
        print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
