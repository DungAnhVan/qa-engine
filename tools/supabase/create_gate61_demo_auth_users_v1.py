"""
Gate 61 — Create Demo Auth Users v1.

Creates 4 demo Supabase Auth users (admin/teacher/student/parent) and
verifies that public.profiles rows were auto-created by the trigger in
migration 000003_auth_profile_trigger.sql.

If the trigger has not been applied yet, inserts/updates profiles manually
and records a warning so the report still passes.

Demo credentials (local dev only — NEVER use in production):
  admin@quantaaptus.local    / QuantaAptusDemo123!
  teacher@quantaaptus.local  / QuantaAptusDemo123!
  student@quantaaptus.local  / QuantaAptusDemo123!
  parent@quantaaptus.local   / QuantaAptusDemo123!

Security:
  - Uses service role key (server-side only, never exposed to browser).
  - Prints masked key. Never prints the full key.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\create_gate61_demo_auth_users_v1.py

Output:
  data/diagnostics/gate61_demo_auth_users_report_v1.json
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

DEMO_PASSWORD = "QuantaAptusDemo123!"

DEMO_USERS = [
    {
        "email":        "admin@quantaaptus.local",
        "display_name": "Demo Admin",
        "role":         "admin",
    },
    {
        "email":        "teacher@quantaaptus.local",
        "display_name": "Demo Teacher",
        "role":         "teacher",
    },
    {
        "email":        "student@quantaaptus.local",
        "display_name": "Demo Student",
        "role":         "student",
    },
    {
        "email":        "parent@quantaaptus.local",
        "display_name": "Demo Parent",
        "role":         "parent",
    },
]

VALID_ROLES = ["admin", "teacher", "student", "parent"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_org_id(client) -> str | None:
    """Return the quanta-aptus-local-demo organization id, or None."""
    try:
        r = (
            client.table("organizations")
            .select("id")
            .eq("slug", "quanta-aptus-local-demo")
            .limit(1)
            .execute()
        )
        if r.data:
            return r.data[0]["id"]
    except Exception:
        pass
    return None


def _create_or_update_auth_user(client, user: dict) -> dict:
    """
    Create auth user via admin API.  Returns a result dict with:
      { email, user_id, created, updated, error }
    """
    result = {"email": user["email"], "user_id": None, "created": False, "updated": False, "error": None}
    try:
        # Try create first
        res = client.auth.admin.create_user(
            {
                "email":         user["email"],
                "password":      DEMO_PASSWORD,
                "email_confirm": True,
                "user_metadata": {
                    "display_name": user["display_name"],
                    "role":         user["role"],
                },
            }
        )
        result["user_id"] = res.user.id
        result["created"] = True
        print(f"    + created  : {user['email']} (id={res.user.id[:8]}...)")
    except Exception as e:
        err_str = str(e)
        # Already registered → look up by email
        if "already registered" in err_str.lower() or "already exists" in err_str.lower() or "duplicate" in err_str.lower():
            try:
                # List users and find by email
                list_res = client.auth.admin.list_users()
                users = list_res if isinstance(list_res, list) else list_res.users
                found = next((u for u in users if u.email == user["email"]), None)
                if found:
                    # Update password + metadata
                    client.auth.admin.update_user_by_id(
                        found.id,
                        {
                            "password":      DEMO_PASSWORD,
                            "email_confirm": True,
                            "user_metadata": {
                                "display_name": user["display_name"],
                                "role":         user["role"],
                            },
                        },
                    )
                    result["user_id"] = found.id
                    result["updated"] = True
                    print(f"    ~ updated  : {user['email']} (id={found.id[:8]}...)")
                else:
                    result["error"] = f"Exists but could not locate: {err_str}"
                    print(f"    ! lookup   : {user['email']} — {result['error']}")
            except Exception as inner:
                result["error"] = str(inner)
                print(f"    ! error    : {user['email']} — {result['error']}")
        else:
            result["error"] = err_str
            print(f"    ! error    : {user['email']} — {result['error']}")
    return result


def _ensure_profile(client, user_id: str, user: dict, org_id: str | None) -> bool:
    """
    Verify or manually insert the profiles row for this auth user.
    Returns True if profile exists/was created, False on error.
    """
    try:
        r = client.table("profiles").select("id, role").eq("id", user_id).execute()
        if r.data:
            return True  # trigger already created it
    except Exception:
        pass
    # Insert manually (trigger not applied yet)
    try:
        client.table("profiles").upsert(
            {
                "id":              user_id,
                "organization_id": org_id,
                "display_name":    user["display_name"],
                "email":           user["email"],
                "role":            user["role"],
            },
            on_conflict="id",
        ).execute()
        return True
    except Exception as e:
        print(f"      ! profile upsert failed for {user['email']}: {e}")
        return False


def _count_profiles_by_role(client) -> dict[str, int]:
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    from supabase_client_v1 import get_supabase_service_client, mask_secret

    print("=" * 60)
    print("Quanta Aptus — Gate 61 Create Demo Auth Users v1")
    print("=" * 60)

    client, url = get_supabase_service_client()
    print(f"  connected     : {mask_secret(url)}")
    print(f"  demo password : {DEMO_PASSWORD[:6]}...")
    print()

    report: dict = {
        "report_id":  "quanta_aptus_gate61_demo_auth_users_v1",
        "gate":       "61",
        "created_at": now_iso,
        "status":     "failed",
        "demo_users": [],
        "profiles_created": False,
        "roles_verified":   [],
        "trigger_applied":  False,
        "warnings":         [],
        "errors":           [],
    }

    org_id = _get_org_id(client)
    print(f"  organization  : {org_id[:8] + '...' if org_id else 'NOT FOUND (profiles will have null org)'}")
    if not org_id:
        report["warnings"].append("Demo organization not found — profiles will have null organization_id.")

    print()
    print("  Creating auth users:")
    user_results = []
    for demo_user in DEMO_USERS:
        res = _create_or_update_auth_user(client, demo_user)
        user_results.append(res)
        if res["error"]:
            report["errors"].append(f"{demo_user['email']}: {res['error']}")

    print()
    print("  Verifying / ensuring profiles:")
    trigger_applied_count = 0
    for i, demo_user in enumerate(DEMO_USERS):
        uid = user_results[i].get("user_id")
        if not uid:
            print(f"    - skip     : {demo_user['email']} (no user_id)")
            continue
        # Check if trigger auto-created profile
        try:
            r = client.table("profiles").select("id, role").eq("id", uid).execute()
            if r.data:
                trigger_applied_count += 1
                print(f"    ✓ profile  : {demo_user['email']} (trigger or seed)")
                continue
        except Exception:
            pass
        # Profile missing — insert manually
        print(f"    + inserting: {demo_user['email']} (trigger not yet applied)")
        _ensure_profile(client, uid, demo_user, org_id)
        report["warnings"].append(
            f"Profile for {demo_user['email']} not found after auth user create — "
            "inserted manually. Apply migration 000003 to enable automatic profile creation."
        )

    report["trigger_applied"] = trigger_applied_count == len(DEMO_USERS)

    print()
    print("  Profile counts by role:")
    role_counts = _count_profiles_by_role(client)
    roles_verified = []
    for role in VALID_ROLES:
        count = role_counts.get(role, 0)
        print(f"    {role:10}: {count}")
        if count > 0:
            roles_verified.append(role)

    report["roles_verified"] = roles_verified

    # Populate demo_users in report (mask passwords)
    for i, demo_user in enumerate(DEMO_USERS):
        res = user_results[i]
        report["demo_users"].append(
            {
                "email":        demo_user["email"],
                "role":         demo_user["role"],
                "display_name": demo_user["display_name"],
                "user_id":      res.get("user_id"),
                "created":      res.get("created", False),
                "updated":      res.get("updated", False),
                "error":        res.get("error"),
            }
        )

    profiles_ok = len(roles_verified) >= 4
    report["profiles_created"] = profiles_ok

    # Status
    has_errors = bool(report["errors"])
    if not has_errors and profiles_ok:
        status = "passed"
    elif profiles_ok:
        status = "needs_review"
    else:
        status = "failed"

    report["status"] = status
    print(f"\n  status        : {status.upper()}")
    if report["warnings"]:
        for w in report["warnings"]:
            print(f"  WARNING: {w}")

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    path = DIAG_DIR / "gate61_demo_auth_users_report_v1.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {path}")

    sys.exit(0 if status in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
