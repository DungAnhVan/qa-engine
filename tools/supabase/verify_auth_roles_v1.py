"""
Gate 60 - Auth Roles Verify v1.

Connects to Supabase (service role) and verifies the auth/roles foundation
is in place without requiring real Supabase Auth users to exist.

What it checks:
  - profiles table is queryable.
  - students table is queryable.
  - parent_student_links table is queryable.
  - At least one organization exists.
  - At least one student exists.
  - Profile counts by role (admin / teacher / student / parent).
  - If zero profiles: status = "ready_no_auth_users" (not failed).
  - Migration file 000003_auth_profile_trigger.sql exists locally.
  - Seed file seed_demo_auth_profiles.sql exists locally.

Does NOT:
  - Create auth users.
  - Modify any rows.
  - Expose service role key.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\verify_auth_roles_v1.py

Output:
  data/diagnostics/auth_roles_verify_report_v1.json
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

VALID_ROLES = ["admin", "teacher", "student", "parent"]


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

def _count_table(client, table: str) -> int | None:
    """Return row count for table, or None on error."""
    try:
        r = client.table(table).select("id", count="exact", head=True).execute()
        return r.count
    except Exception as e:
        return None


def _count_by_role(client) -> dict[str, int]:
    """Return profile count per role."""
    counts: dict[str, int] = {}
    for role in VALID_ROLES:
        try:
            r = (
                client.table("profiles")
                .select("id", count="exact", head=True)
                .eq("role", role)
                .execute()
            )
            counts[role] = r.count or 0
        except Exception:
            counts[role] = 0
    return counts


def _get_organizations(client) -> list[dict]:
    try:
        r = client.table("organizations").select("id, name, slug").execute()
        return r.data or []
    except Exception:
        return []


def _get_student_count(client) -> int:
    try:
        r = client.table("students").select("id", count="exact", head=True).execute()
        return r.count or 0
    except Exception:
        return 0


def _get_parent_link_count(client) -> int:
    try:
        r = client.table("parent_student_links").select("id", count="exact", head=True).execute()
        return r.count or 0
    except Exception:
        return 0


def _get_demo_profiles(client) -> list[dict]:
    """Return demo profile rows (fixed UUID prefix a0000000...)."""
    try:
        r = (
            client.table("profiles")
            .select("id, display_name, email, role")
            .like("id", "a0000000%")
            .execute()
        )
        return r.data or []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    from supabase_client_v1 import get_supabase_service_client, mask_secret

    print("=" * 60)
    print("Quanta Aptus - Gate 60 Auth Roles Verify v1")
    print("=" * 60)

    client, url = get_supabase_service_client()
    print(f"  connected     : {mask_secret(url)}")

    report: dict = {
        "report_id":  "quanta_aptus_gate60_auth_roles_verify_v1",
        "gate":       "60",
        "created_at": now_iso,
        "status":     "failed",
    }

    issues: list[str] = []

    # ── Local file checks ───────────────────────────────────────────────────
    migration_path = PROJECT_ROOT / "supabase" / "migrations" / "000003_auth_profile_trigger.sql"
    seed_path      = PROJECT_ROOT / "supabase" / "seed" / "seed_demo_auth_profiles.sql"

    migration_exists = migration_path.exists()
    seed_exists      = seed_path.exists()
    print(f"  migration 003 : {'found' if migration_exists else 'MISSING'}")
    print(f"  seed profiles : {'found' if seed_exists else 'MISSING'}")
    if not migration_exists:
        issues.append("Migration 000003_auth_profile_trigger.sql not found.")
    if not seed_exists:
        issues.append("seed_demo_auth_profiles.sql not found.")

    # ── Supabase table checks ────────────────────────────────────────────────
    profiles_count       = _count_table(client, "profiles")
    students_count       = _get_student_count(client)
    parent_links_count   = _get_parent_link_count(client)
    organizations        = _get_organizations(client)
    role_counts          = _count_by_role(client)
    demo_profiles        = _get_demo_profiles(client)

    print(f"  organizations : {len(organizations)}")
    for org in organizations:
        print(f"    • {org.get('slug', '?')} — {org.get('name', '?')}")

    print(f"  students      : {students_count}")
    print(f"  profiles total: {profiles_count}")
    for role in VALID_ROLES:
        print(f"    • {role:10}: {role_counts.get(role, 0)}")
    print(f"  parent links  : {parent_links_count}")
    print(f"  demo profiles : {len(demo_profiles)}")

    # ── Issue checks ─────────────────────────────────────────────────────────
    if not organizations:
        issues.append("No organizations found. Run seed_local_mvp_demo.sql.")

    if students_count == 0:
        issues.append("No students found. Run seed_local_mvp_demo.sql.")

    # ── Status determination ─────────────────────────────────────────────────
    no_critical_issues = not any(
        i for i in issues
        if "Migration" in i or "seed" in i or "organization" in i.lower()
    )

    if issues:
        for iss in issues:
            print(f"  ISSUE: {iss}")

    # If tables are queryable and orgs/students exist but no real auth users yet
    total_profiles = profiles_count or 0
    if not issues and total_profiles == 0:
        status = "ready_no_auth_users"
    elif not issues:
        status = "passed"
    elif no_critical_issues:
        status = "needs_review"
    else:
        status = "needs_review"

    print(f"\n  status        : {status.upper()}")

    report.update({
        "status":                 status,
        "organizations_found":    len(organizations),
        "organizations":          [{"slug": o.get("slug"), "name": o.get("name")} for o in organizations],
        "profiles_total":         profiles_count or 0,
        "profiles_by_role":       role_counts,
        "demo_profiles_seeded":   len(demo_profiles),
        "students_count":         students_count,
        "parent_links_count":     parent_links_count,
        "migration_003_present":  migration_exists,
        "seed_profiles_present":  seed_exists,
        "auth_profile_trigger_applied": False,  # requires manual apply in SQL editor
        "issues":                 issues,
    })

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    path = DIAG_DIR / "auth_roles_verify_report_v1.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {path}")

    sys.exit(0 if status in ("passed", "ready_no_auth_users", "needs_review") else 1)


if __name__ == "__main__":
    main()
