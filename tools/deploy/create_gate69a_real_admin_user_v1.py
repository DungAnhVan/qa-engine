"""
Gate 69A -- Create Real Admin User v1

Creates a real admin user in Supabase Auth and verifies/inserts a matching
profile row with role=admin.

Usage:
  # Dry-run (default) -- no changes made
  .venv-ingest\\Scripts\\python.exe tools\\deploy\\create_gate69a_real_admin_user_v1.py \\
      --email your@email.com --password-env QA_REAL_ADMIN_PASSWORD

  # Execute -- requires --execute flag
  # Set password in shell session (do not commit this value):
  $env:QA_REAL_ADMIN_PASSWORD=<your-strong-password>
  .venv-ingest\\Scripts\\python.exe tools\\deploy\\create_gate69a_real_admin_user_v1.py \\
      --email your@email.com --password-env QA_REAL_ADMIN_PASSWORD \\
      --display-name "Quanta Aptus Admin" --execute

Security rules:
  - Password is read from an environment variable; NEVER from a CLI arg.
  - Password is NEVER printed or written to any file.
  - Service role key is masked (first6...last4) in log output only.
  - Report file contains NO secrets.

Output:
  data/diagnostics/gate69a_real_admin_user_report_v1.json
"""

import sys
import json
import os
import argparse
import datetime
import urllib.request
import urllib.error
from pathlib import Path

ROOT       = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate69a_real_admin_user_report_v1.json"

DEMO_EMAILS = {
    "admin@quantaaptus.local",
    "teacher@quantaaptus.local",
    "student@quantaaptus.local",
    "parent@quantaaptus.local",
}

REQUEST_TIMEOUT = 20

# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------

def load_env_local() -> dict[str, str]:
    env_path = ROOT / ".env.local"
    result: dict[str, str] = {}
    if not env_path.exists():
        return result
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def resolve_env(key: str, env_local: dict[str, str]) -> str | None:
    return os.environ.get(key) or env_local.get(key) or None


def mask_key(key: str | None) -> str:
    if not key:
        return "(not set)"
    if len(key) < 10:
        return "***"
    return key[:6] + "..." + key[-4:]

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def supabase_request(
    method: str,
    url: str,
    service_role_key: str,
    body: dict | None = None,
) -> tuple[int, dict | list | None, str | None]:
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {
        "apikey":        service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw) if raw.strip() else {}, None
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read(4096).decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        return exc.code, None, f"HTTP {exc.code}: {raw[:300]}"
    except Exception as exc:
        return 0, None, str(exc)[:200]

# ---------------------------------------------------------------------------
# Supabase auth admin
# ---------------------------------------------------------------------------

def find_auth_user(supabase_url: str, service_role_key: str, email: str) -> dict | None:
    """
    Search Supabase Auth admin API for a user by email.
    Returns the user dict or None if not found.
    """
    url = f"{supabase_url}/auth/v1/admin/users?per_page=200"
    status, data, err = supabase_request("GET", url, service_role_key)
    if err or not isinstance(data, dict):
        return None
    for user in data.get("users", []):
        if user.get("email", "").lower() == email.lower():
            return user
    return None


def create_auth_user(
    supabase_url: str,
    service_role_key: str,
    email: str,
    password: str,
    display_name: str,
) -> tuple[str | None, str | None]:
    """
    Create a Supabase Auth user.
    Returns (user_id, error_message).
    """
    url = f"{supabase_url}/auth/v1/admin/users"
    body = {
        "email":          email,
        "password":       password,
        "email_confirm":  True,
        "user_metadata":  {
            "role":         "admin",
            "display_name": display_name,
        },
    }
    status, data, err = supabase_request("POST", url, service_role_key, body)
    if err:
        return None, err
    if isinstance(data, dict) and data.get("id"):
        return data["id"], None
    return None, f"Unexpected response (status={status}): {str(data)[:200]}"

# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------

def find_profile(supabase_url: str, service_role_key: str, user_id: str) -> dict | None:
    url = f"{supabase_url}/rest/v1/profiles?id=eq.{user_id}&select=id,email,role,display_name"
    status, data, err = supabase_request("GET", url, service_role_key)
    if err or not isinstance(data, list):
        return None
    return data[0] if data else None


def upsert_profile(
    supabase_url: str,
    service_role_key: str,
    user_id: str,
    email: str,
    display_name: str,
) -> tuple[bool, str | None]:
    """
    Insert or update the profile row with role=admin.
    Returns (success, error_message).
    """
    url = f"{supabase_url}/rest/v1/profiles?on_conflict=id"
    body = {
        "id":           user_id,
        "email":        email,
        "display_name": display_name,
        "role":         "admin",
    }
    headers_extra = {"Prefer": "resolution=merge-duplicates,return=representation"}
    data_raw = json.dumps(body).encode("utf-8")
    headers = {
        "apikey":        service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        **headers_extra,
    }
    req = urllib.request.Request(url, data=data_raw, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return True, None
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read(4096).decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        return False, f"HTTP {exc.code}: {raw[:300]}"
    except Exception as exc:
        return False, str(exc)[:200]

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description="Gate 69A -- Create Real Admin User")
    parser.add_argument("--email",        required=True,  help="Real admin email address")
    parser.add_argument("--password-env", required=True,  help="Env var name that holds the password")
    parser.add_argument("--display-name", default="Quanta Aptus Admin", help="Display name")
    parser.add_argument("--execute",      action="store_true", help="Run for real (default: dry-run)")
    args = parser.parse_args()

    email        = args.email.strip().lower()
    display_name = args.display_name.strip()
    dry_run      = not args.execute

    print("Gate 69A -- Create Real Admin User")
    print(f"Email:        {email}")
    print(f"Display name: {display_name}")
    print(f"Dry-run:      {dry_run}")
    print("-" * 60)

    # Safety: refuse to overwrite a demo email
    if email in DEMO_EMAILS:
        print(f"ERROR: {email} is a demo account. This script creates real admin users only.")
        sys.exit(1)

    # Password — read from env var named by --password-env; never echoed
    password_env_name = args.password_env
    password = os.environ.get(password_env_name)
    if not password:
        if dry_run:
            print(f"  Password env: {password_env_name!r} not set (OK for dry-run)")
        else:
            print(f"ERROR: Environment variable {password_env_name!r} is not set or empty.")
            print("  Set it before running:")
            print(f"    $env:{password_env_name}=<your-strong-password>")
            sys.exit(1)
    else:
        print(f"  Password env: {password_env_name!r} is set ({len(password)} chars) -- not printed")

    # Load Supabase credentials
    env_local = load_env_local()
    supabase_url     = resolve_env("SUPABASE_URL", env_local) or resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
    service_role_key = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)

    print(f"  SUPABASE_URL:      {'found' if supabase_url else 'NOT FOUND'}")
    print(f"  SERVICE_ROLE_KEY:  {mask_key(service_role_key)}")

    if not supabase_url or not service_role_key:
        print("\nERROR: Supabase credentials not available.")
        print("  Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are in .env.local or system env.")
        _write_report(email, dry_run, False, False, ["Supabase credentials not available"])
        sys.exit(1)

    # ── Dry-run mode ──────────────────────────────────────────────────────────
    if dry_run:
        print("\n[DRY-RUN] No changes will be made.")
        print("  Would: look up auth user by email")
        print("  Would: create auth user if not found")
        print("  Would: verify/upsert profile row with role=admin")
        print("  Password: NOT printed, NOT written to any file")
        _write_report(email, dry_run=True, auth_ok=None, profile_ok=None, issues=[])
        print(f"\nReport (dry-run): {OUTPUT_FILE}")
        print("\nTo execute:")
        print(f"  $env:{password_env_name}='<password>'")
        print(f"  .venv-ingest\\Scripts\\python.exe tools\\deploy\\create_gate69a_real_admin_user_v1.py \\")
        print(f"    --email {email} --password-env {password_env_name} --display-name \"{display_name}\" --execute")
        return

    # ── Execute mode ──────────────────────────────────────────────────────────
    issues: list[str] = []

    # 1. Check for existing auth user
    print("\n[Step 1] Looking up auth user...")
    existing = find_auth_user(supabase_url, service_role_key, email)
    user_id: str | None = None
    auth_created_or_found = False

    if existing:
        user_id = existing.get("id")
        print(f"  + Auth user already exists: id={user_id}")
        auth_created_or_found = True
    else:
        print("  Auth user not found — creating...")
        user_id, create_err = create_auth_user(supabase_url, service_role_key, email, password, display_name)
        if create_err:
            print(f"  ! Failed to create auth user: {create_err}")
            issues.append(f"Auth user creation failed: {create_err}")
        else:
            print(f"  + Auth user created: id={user_id}")
            auth_created_or_found = True

    # 2. Upsert profile
    profile_admin_verified = False
    if user_id:
        print("\n[Step 2] Upserting profile row with role=admin...")
        ok, upsert_err = upsert_profile(supabase_url, service_role_key, user_id, email, display_name)
        if not ok:
            print(f"  ! Profile upsert failed: {upsert_err}")
            issues.append(f"Profile upsert failed: {upsert_err}")
        else:
            # Verify
            profile = find_profile(supabase_url, service_role_key, user_id)
            if profile and profile.get("role") == "admin":
                print(f"  + Profile verified: role=admin, email={profile.get('email')}")
                profile_admin_verified = True
            else:
                print(f"  ! Profile role unexpected: {profile}")
                issues.append("Profile found but role is not admin after upsert")
    else:
        issues.append("Skipped profile upsert — no user_id available")

    # 3. Summary
    status = "passed" if auth_created_or_found and profile_admin_verified and not issues else \
             "needs_review" if auth_created_or_found else "failed"

    print("\n" + "-" * 60)
    print(f"auth_user_created_or_found:  {auth_created_or_found}")
    print(f"profile_admin_verified:      {profile_admin_verified}")
    print(f"password_printed:            False")
    print(f"Status:                      {status}")
    if issues:
        for i in issues:
            print(f"  ! {i}")

    _write_report(email, dry_run=False, auth_ok=auth_created_or_found, profile_ok=profile_admin_verified, issues=issues)
    print(f"\nReport: {OUTPUT_FILE}")

    if status == "passed":
        print("\nNext steps:")
        print(f"  1. Sign in at https://admin.quantaaptus.com/login with {email}")
        print("  2. Check https://admin.quantaaptus.com/system/auth-session — role must be 'admin'")
        print("  3. Run check_gate69a_credential_safety_v1.py to verify overall safety")


def _write_report(
    email: str,
    dry_run: bool,
    auth_ok: bool | None,
    profile_ok: bool | None,
    issues: list[str],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if auth_ok is None and dry_run:
        status = "needs_review"
    elif auth_ok and profile_ok and not issues:
        status = "passed"
    elif auth_ok:
        status = "needs_review"
    else:
        status = "failed"

    report = {
        "gate":                        "69A",
        "title":                       "Create Real Admin User v1",
        "status":                      status,
        "dry_run":                     dry_run,
        "real_admin_email":            email,
        "auth_user_created_or_found":  auth_ok,
        "profile_admin_verified":      profile_ok,
        "password_printed":            False,
        "issues":                      issues,
        "generated_at":                datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
