"""
Gate 69A -- Disable Demo Users v1

Disables (bans) demo accounts in Supabase Auth.

Default: DRY-RUN -- shows what would be done, makes no changes.

To run for real, you must provide BOTH flags:
  --execute
  --confirm DISABLE_DEMO_USERS

Rules:
  - NEVER deletes users.
  - NEVER disables the real admin email if it matches a demo email accidentally.
  - If Supabase Auth ban API is not supported, outputs manual instructions.
  - Password is NEVER printed.
  - Service role key is NEVER printed (masked only).

Usage:
  # Dry-run (safe)
  .venv-ingest\\Scripts\\python.exe tools\\deploy\\disable_gate69a_demo_users_v1.py

  # Execute
  .venv-ingest\\Scripts\\python.exe tools\\deploy\\disable_gate69a_demo_users_v1.py \\
      --execute --confirm DISABLE_DEMO_USERS

  # Protect a real admin email from being accidentally targeted
  .venv-ingest\\Scripts\\python.exe tools\\deploy\\disable_gate69a_demo_users_v1.py \\
      --execute --confirm DISABLE_DEMO_USERS --protect-email your@real.email.com

Output:
  data/diagnostics/gate69a_demo_user_disable_report_v1.json
"""

import sys
import json
import os
import argparse
import datetime
import urllib.request
import urllib.error
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate69a_demo_user_disable_report_v1.json"

DEMO_EMAILS = [
    "admin@quantaaptus.local",
    "teacher@quantaaptus.local",
    "student@quantaaptus.local",
    "parent@quantaaptus.local",
]

CONFIRM_TOKEN = "DISABLE_DEMO_USERS"
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
# Auth admin
# ---------------------------------------------------------------------------

def list_demo_auth_users(
    supabase_url: str,
    service_role_key: str,
    protect_email: str | None,
) -> tuple[list[dict], str | None]:
    url = f"{supabase_url}/auth/v1/admin/users?per_page=200"
    status, data, err = supabase_request("GET", url, service_role_key)
    if err or not isinstance(data, dict):
        return [], err or "auth admin API unavailable"
    users = data.get("users", [])
    targets = []
    for u in users:
        email = u.get("email", "")
        if email not in DEMO_EMAILS:
            continue
        if protect_email and email.lower() == protect_email.lower():
            continue
        targets.append({
            "id":     u.get("id"),
            "email":  email,
            "banned": u.get("banned", False),
        })
    return targets, None


def ban_user(supabase_url: str, service_role_key: str, user_id: str) -> tuple[bool, str | None]:
    """
    Attempt to ban a user via Supabase Auth admin PATCH.
    Sets ban_duration to 'none' which some Supabase versions interpret as ban.
    Also tries setting is_sso_user=false and banned=true via admin API.
    """
    url = f"{supabase_url}/auth/v1/admin/users/{user_id}"
    body = {"ban_duration": "876000h"}  # ~100 years; effectively permanent ban
    status, data, err = supabase_request("PUT", url, service_role_key, body)
    if err:
        # Some versions use PATCH
        status, data, err2 = supabase_request("PATCH", url, service_role_key, body)
        if err2:
            return False, f"PUT: {err} | PATCH: {err2}"
    if isinstance(data, dict) and (data.get("id") or status in (200, 204)):
        return True, None
    return False, f"Unexpected response status={status}"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description="Gate 69A -- Disable Demo Users")
    parser.add_argument("--execute",       action="store_true", help="Execute (default: dry-run)")
    parser.add_argument("--confirm",       help=f"Must equal '{CONFIRM_TOKEN}' to execute")
    parser.add_argument("--protect-email", help="Email to never target even if in demo list")
    args = parser.parse_args()

    dry_run = not args.execute
    confirmed = args.confirm == CONFIRM_TOKEN
    protect_email = args.protect_email

    print("Gate 69A -- Disable Demo Users")
    print(f"Dry-run:       {dry_run}")
    print(f"Confirmed:     {confirmed}")
    if protect_email:
        print(f"Protect email: {protect_email}")
    print("-" * 60)

    if args.execute and not confirmed:
        print(f"ERROR: --execute requires --confirm {CONFIRM_TOKEN}")
        print("  Re-run with both flags to proceed.")
        sys.exit(1)

    env_local = load_env_local()
    supabase_url     = resolve_env("SUPABASE_URL", env_local) or resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
    service_role_key = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)

    print(f"  SUPABASE_URL:      {'found' if supabase_url else 'NOT FOUND'}")
    print(f"  SERVICE_ROLE_KEY:  {mask_key(service_role_key)}")

    if not supabase_url or not service_role_key:
        print("\nERROR: Supabase credentials not available.")
        _write_report(dry_run, DEMO_EMAILS, [], True, ["Supabase credentials not available"])
        sys.exit(1)

    # List demo users
    print("\n[Listing demo auth users]")
    targets, list_err = list_demo_auth_users(supabase_url, service_role_key, protect_email)

    manual_action_required = False
    issues: list[str] = []

    if list_err and not targets:
        print(f"  ? Auth admin API unavailable: {list_err}")
        print("\n  MANUAL ACTION REQUIRED:")
        print("  Supabase Dashboard -> Authentication -> Users")
        for email in DEMO_EMAILS:
            if protect_email and email.lower() == protect_email.lower():
                continue
            print(f"    Ban or delete: {email}")
        manual_action_required = True
        issues.append(f"Auth admin API unavailable: {list_err}")
    else:
        for t in targets:
            status_label = "already banned" if t["banned"] else "active"
            print(f"  {'~' if t['banned'] else '!'} {t['email']} ({status_label})")

    # Dry-run exit
    if dry_run:
        print("\n[DRY-RUN] No changes made.")
        active_targets = [t for t in targets if not t.get("banned")]
        if active_targets:
            print(f"  Would ban {len(active_targets)} active demo user(s):")
            for t in active_targets:
                print(f"    {t['email']}")
        else:
            print("  No active demo users to ban.")
        print("\n  To execute:")
        print("    .venv-ingest\\Scripts\\python.exe tools\\deploy\\disable_gate69a_demo_users_v1.py \\")
        if protect_email:
            print(f"      --protect-email {protect_email} \\")
        print(f"      --execute --confirm {CONFIRM_TOKEN}")
        _write_report(dry_run=True, targeted=DEMO_EMAILS, disabled=[], manual=manual_action_required, issues=issues)
        print(f"\nReport (dry-run): {OUTPUT_FILE}")
        return

    # Execute
    disabled: list[str] = []
    skipped_already_banned: list[str] = []

    for t in targets:
        if t["banned"]:
            print(f"  ~ {t['email']} -- already banned, skipping")
            skipped_already_banned.append(t["email"])
            continue
        print(f"  Banning {t['email']} (id={t['id']})...")
        ok, err = ban_user(supabase_url, service_role_key, t["id"])
        if ok:
            print(f"  + Banned: {t['email']}")
            disabled.append(t["email"])
        else:
            print(f"  ! Failed to ban {t['email']}: {err}")
            print("    Manual action required: Supabase Dashboard -> Authentication -> Users -> Ban user")
            issues.append(f"Ban failed for {t['email']}: {err}")
            manual_action_required = True

    status = "passed" if disabled and not issues else "needs_review" if manual_action_required else "passed"

    print("\n" + "-" * 60)
    print(f"demo_users_targeted:  {[t['email'] for t in targets]}")
    print(f"demo_users_disabled:  {disabled}")
    print(f"manual_action_req:    {manual_action_required}")
    print(f"Status:               {status}")

    if manual_action_required:
        print("\n  Manual steps for any failed bans:")
        print("  1. Go to https://supabase.com -> your project")
        print("  2. Authentication -> Users")
        print("  3. Find each @quantaaptus.local user")
        print("  4. Click user -> Ban user")
        print("  5. Confirm old passwords no longer work")

    _write_report(
        dry_run=False,
        targeted=[t["email"] for t in targets],
        disabled=disabled,
        manual=manual_action_required,
        issues=issues,
    )
    print(f"\nReport: {OUTPUT_FILE}")


def _write_report(
    dry_run: bool,
    targeted: list[str],
    disabled: list[str],
    manual: bool,
    issues: list[str],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if dry_run:
        status = "needs_review"
    elif disabled and not issues and not manual:
        status = "passed"
    else:
        status = "needs_review"

    report = {
        "gate":                  "69A",
        "title":                 "Disable Demo Users v1",
        "status":                status,
        "dry_run":               dry_run,
        "demo_users_targeted":   targeted,
        "demo_users_disabled":   disabled,
        "manual_action_required": manual,
        "issues":                issues,
        "generated_at":          datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
