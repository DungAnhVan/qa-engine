"""
Gate 69A -- Credential Safety Check v1

Verifies production credential posture:
  - Real admin profile exists (optional: --real-admin-email)
  - Demo profiles still exist (expected until cleaned up)
  - Demo auth users still exist (checked via admin API)
  - QA_AUTH_DEMO_FALLBACK is false in production
  - No secrets exposed in production API responses

Usage:
  # Local check only
  .venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate69a_credential_safety_v1.py

  # With production URL and real admin email
  .venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate69a_credential_safety_v1.py \\
      https://admin.quantaaptus.com --real-admin-email your@email.com

Output:
  data/diagnostics/gate69a_credential_safety_check_v1.json

Security:
  - Service role key is NEVER printed; masked as first6...last4.
  - Report contains no secrets.
"""

import sys
import json
import os
import re
import argparse
import datetime
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate69a_credential_safety_check_v1.json"

DEMO_EMAILS = [
    "admin@quantaaptus.local",
    "teacher@quantaaptus.local",
    "student@quantaaptus.local",
    "parent@quantaaptus.local",
]

REQUEST_TIMEOUT = 15

SECURITY_PATTERNS = [
    re.compile(r'eyJ[A-Za-z0-9+/=_-]{300,}'),
    re.compile(r'sb_sec_[A-Za-z0-9_\-]{20,}'),
    re.compile(r'sk-[A-Za-z0-9]{40,}'),
    re.compile(r'sk-ant-[A-Za-z0-9\-_]{50,}'),
    re.compile(r'SUPABASE_SERVICE_ROLE_KEY\s*=\s*\S{10,}'),
]

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

def supabase_get(url: str, service_role_key: str) -> tuple[int, dict | list | None, str | None]:
    req = urllib.request.Request(url, headers={
        "apikey":        service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Accept":        "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(body), None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(4096).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return exc.code, None, f"HTTP {exc.code}: {body[:200]}"
    except Exception as exc:
        return 0, None, str(exc)[:200]


def public_get(url: str) -> tuple[int, dict | None, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "QA-Gate69A-CredSafetyCheck/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read(128 * 1024).decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body), None
            except Exception:
                return resp.status, None, None
    except urllib.error.HTTPError as exc:
        return exc.code, None, f"HTTP {exc.code}"
    except Exception as exc:
        return 0, None, str(exc)[:200]

# ---------------------------------------------------------------------------
# Profile checks
# ---------------------------------------------------------------------------

def check_demo_profiles(supabase_url: str, service_role_key: str) -> tuple[list[dict], str | None]:
    found = []
    last_error = None
    for email in DEMO_EMAILS:
        encoded = urllib.parse.quote(email, safe="")
        url = f"{supabase_url}/rest/v1/profiles?select=id,email,role&email=eq.{encoded}"
        status, data, err = supabase_get(url, service_role_key)
        if err:
            last_error = f"profiles error for {email}: {err}"
            continue
        if isinstance(data, list) and data:
            row = data[0]
            found.append({"email": row.get("email", email), "role": row.get("role", "unknown")})
    return found, last_error


def check_real_admin_profile(
    supabase_url: str,
    service_role_key: str,
    email: str,
) -> tuple[bool, str | None]:
    encoded = urllib.parse.quote(email, safe="")
    url = f"{supabase_url}/rest/v1/profiles?select=id,email,role&email=eq.{encoded}&role=eq.admin"
    status, data, err = supabase_get(url, service_role_key)
    if err:
        return False, err
    return bool(isinstance(data, list) and data), None


def count_admin_profiles(supabase_url: str, service_role_key: str) -> tuple[int, str | None]:
    url = f"{supabase_url}/rest/v1/profiles?select=id&role=eq.admin"
    headers = {
        "apikey":        service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Accept":        "application/json",
        "Prefer":        "count=exact",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body) if body.strip() else []
            return len(data) if isinstance(data, list) else 0, None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(4096).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return 0, f"HTTP {exc.code}: {body[:200]}"
    except Exception as exc:
        return 0, str(exc)[:200]

# ---------------------------------------------------------------------------
# Auth admin check
# ---------------------------------------------------------------------------

def check_demo_auth_users(supabase_url: str, service_role_key: str) -> tuple[list[dict] | str, str | None]:
    url = f"{supabase_url}/auth/v1/admin/users?per_page=200"
    status, data, err = supabase_get(url, service_role_key)
    if err or not isinstance(data, dict):
        return "unknown", err or "auth admin API unavailable"
    users = data.get("users", [])
    demo_found = [
        {"email": u.get("email"), "id": u.get("id"), "banned": u.get("banned", False)}
        for u in users
        if u.get("email") in DEMO_EMAILS
    ]
    return demo_found, None


def check_real_admin_auth_user(
    supabase_url: str,
    service_role_key: str,
    email: str,
) -> tuple[bool | str, str | None]:
    url = f"{supabase_url}/auth/v1/admin/users?per_page=200"
    status, data, err = supabase_get(url, service_role_key)
    if err or not isinstance(data, dict):
        return "unknown", err or "auth admin API unavailable"
    for user in data.get("users", []):
        if user.get("email", "").lower() == email.lower():
            return True, None
    return False, None

# ---------------------------------------------------------------------------
# Production URL check
# ---------------------------------------------------------------------------

def check_production_url(base_url: str) -> dict:
    result: dict = {
        "url_checked":           base_url,
        "health_ok":             False,
        "demo_fallback_false":   False,
        "content_source_live":   False,
        "cred_safety_api_ok":    False,
        "secrets_exposed":       False,
        "secret_findings":       [],
        "health_status_code":    0,
        "cred_safety_status":    None,
    }

    # Health check
    h_code, h_data, _ = public_get(f"{base_url}/api/system/health")
    result["health_status_code"] = h_code
    if h_code == 200 and isinstance(h_data, dict):
        result["health_ok"]          = h_data.get("status") == "ok"
        result["demo_fallback_false"] = h_data.get("demo_fallback") == "false"
        result["content_source_live"] = h_data.get("content_source") == "live_supabase"

    # Credential safety API
    cs_code, cs_data, _ = public_get(f"{base_url}/api/system/credential-safety")
    result["cred_safety_status_code"] = cs_code
    if cs_code == 200 and isinstance(cs_data, dict):
        result["cred_safety_api_ok"]  = True
        result["cred_safety_status"]  = cs_data.get("status")
        if not result["demo_fallback_false"]:
            result["demo_fallback_false"] = cs_data.get("qa_auth_demo_fallback") == False  # noqa: E712

    # Demo safety fallback
    ds_code, ds_data, _ = public_get(f"{base_url}/api/system/demo-safety")
    if ds_code == 200 and isinstance(ds_data, dict) and not result["demo_fallback_false"]:
        result["demo_fallback_false"] = ds_data.get("qa_auth_demo_fallback") is True

    # Security scan
    for path in ("/api/system/health", "/api/system/demo-safety", "/api/system/credential-safety"):
        try:
            req = urllib.request.Request(
                f"{base_url}{path}",
                headers={"User-Agent": "QA-Gate69A-CredSafetyCheck/1.0"},
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                body = resp.read(64 * 1024).decode("utf-8", errors="replace")
            for pat in SECURITY_PATTERNS:
                if pat.search(body):
                    result["secrets_exposed"] = True
                    result["secret_findings"].append(pat.pattern[:50])
        except Exception:
            pass

    return result

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description="Gate 69A -- Credential Safety Check")
    parser.add_argument("base_url",              nargs="?", help="Production base URL (optional)")
    parser.add_argument("--real-admin-email",    help="Real admin email to verify")
    args = parser.parse_args()

    base_url        = args.base_url.rstrip("/") if args.base_url else None
    real_admin_email = args.real_admin_email

    if base_url and not base_url.startswith("http"):
        print(f"ERROR: URL must start with http(s): {base_url}")
        sys.exit(1)

    print("Gate 69A -- Credential Safety Check")
    print(f"Production URL:    {base_url or '(not provided)'}")
    print(f"Real admin email:  {real_admin_email or '(not provided)'}")
    print("-" * 60)

    env_local = load_env_local()
    supabase_url     = resolve_env("SUPABASE_URL", env_local) or resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
    service_role_key = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)

    print(f"  SUPABASE_URL:      {'found' if supabase_url else 'NOT FOUND'}")
    print(f"  SERVICE_ROLE_KEY:  {mask_key(service_role_key)}")

    issues: list[str] = []
    recommended: list[str] = []

    # ── Profile checks ────────────────────────────────────────────────────────
    admin_profile_count     = 0
    real_admin_verified     = False
    real_admin_auth_found: bool | str = "unknown"
    demo_profiles: list[dict] = []
    demo_auth_users: list[dict] | str = "unknown"

    if supabase_url and service_role_key:
        print("\n[Profiles]")
        admin_profile_count, count_err = count_admin_profiles(supabase_url, service_role_key)
        print(f"  Admin profiles count: {admin_profile_count}")
        if count_err:
            issues.append(f"Admin profile count error: {count_err}")

        if real_admin_email:
            ok, err = check_real_admin_profile(supabase_url, service_role_key, real_admin_email)
            real_admin_verified = ok
            print(f"  Real admin profile ({real_admin_email}): {'FOUND - admin' if ok else 'NOT FOUND'}")
            if err:
                issues.append(f"Real admin profile check error: {err}")
            if not ok:
                recommended.append(f"Create real admin profile for {real_admin_email} with role=admin")

        print("\n[Demo Profiles]")
        demo_profiles, demo_err = check_demo_profiles(supabase_url, service_role_key)
        for p in demo_profiles:
            print(f"  ! Demo profile: {p['email']} (role={p['role']})")
        if not demo_profiles:
            print("  + No demo profiles found")
        if demo_err:
            issues.append(f"Demo profile check error: {demo_err}")

        print("\n[Auth Users]")
        demo_auth_users, auth_err = check_demo_auth_users(supabase_url, service_role_key)
        if demo_auth_users == "unknown":
            print(f"  ? Auth admin API unavailable: {auth_err}")
        else:
            active_demo = [u for u in demo_auth_users if not u.get("banned")]
            banned_demo = [u for u in demo_auth_users if u.get("banned")]
            for u in active_demo:
                print(f"  ! Active demo auth user: {u['email']}")
            for u in banned_demo:
                print(f"  ~ Banned demo auth user: {u['email']}")
            if not demo_auth_users:
                print("  + No demo auth users found")

        if real_admin_email:
            ok2, err2 = check_real_admin_auth_user(supabase_url, service_role_key, real_admin_email)
            real_admin_auth_found = ok2
            print(f"  Real admin auth user ({real_admin_email}): {'FOUND' if ok2 is True else 'NOT FOUND' if ok2 is False else 'unknown'}")
            if ok2 is False:
                recommended.append(f"Create Supabase Auth user for {real_admin_email}")
    else:
        print("\n  Skipping Supabase checks -- credentials not available")
        issues.append("Supabase credentials not available; profile checks skipped")

    # ── Local QA_AUTH_DEMO_FALLBACK ────────────────────────────────────────────
    local_demo_fallback = resolve_env("QA_AUTH_DEMO_FALLBACK", env_local)
    local_fallback_ok = local_demo_fallback == "false"
    print(f"\n[QA_AUTH_DEMO_FALLBACK] local: {local_demo_fallback!r}")

    # ── Production URL check ──────────────────────────────────────────────────
    prod_result: dict = {}
    production_url_checked = False
    if base_url:
        print(f"\n[Production URL] {base_url}")
        prod_result = check_production_url(base_url)
        production_url_checked = True
        print(f"  health:              {prod_result.get('health_status_code')} {'OK' if prod_result.get('health_ok') else 'FAIL'}")
        print(f"  demo_fallback_false: {prod_result.get('demo_fallback_false')}")
        print(f"  content_source:      {'live_supabase' if prod_result.get('content_source_live') else 'NOT live'}")
        print(f"  cred_safety_api:     {prod_result.get('cred_safety_status', 'N/A')}")
        print(f"  secrets_exposed:     {prod_result.get('secrets_exposed')}")

    # ── Derive aggregates ─────────────────────────────────────────────────────
    secrets_exposed = prod_result.get("secrets_exposed", False)
    prod_fallback_false = prod_result.get("demo_fallback_false", True) if production_url_checked else True
    qa_auth_demo_fallback_false = local_fallback_ok or (production_url_checked and prod_fallback_false)

    demo_profiles_exist = len(demo_profiles) > 0
    demo_auth_active = (
        isinstance(demo_auth_users, list)
        and any(not u.get("banned") for u in demo_auth_users)
    )
    demo_users_still_exist = demo_profiles_exist or demo_auth_active
    demo_password_rotation_required = demo_users_still_exist

    if not real_admin_email:
        real_admin_verified = None  # type: ignore[assignment]

    public_launch_safe = (
        real_admin_verified is True
        and not demo_users_still_exist
        and not secrets_exposed
        and qa_auth_demo_fallback_false
    )

    # Collect issues
    if secrets_exposed:
        issues.append("Secrets found in production API responses — CRITICAL")
    if production_url_checked and not prod_fallback_false:
        issues.append("QA_AUTH_DEMO_FALLBACK is not false in production")
    if not qa_auth_demo_fallback_false:
        issues.append("QA_AUTH_DEMO_FALLBACK is not false (local nor production confirmed)")
    if real_admin_email and not real_admin_verified:
        issues.append(f"Real admin profile not found for {real_admin_email}")
    if demo_profiles_exist:
        issues.append(f"{len(demo_profiles)} demo profile(s) still exist in Supabase")
        recommended.append("Rotate demo passwords or disable demo users after confirming real admin works")

    if not recommended:
        recommended.append("Verify QA_AUTH_DEMO_FALLBACK=false in Vercel env vars")
        recommended.append("Confirm SUPABASE_SERVICE_ROLE_KEY is server-only (no NEXT_PUBLIC_ prefix)")

    # Status logic
    if secrets_exposed or (production_url_checked and not prod_fallback_false) or \
       (real_admin_email and not real_admin_verified and admin_profile_count == 0):
        status = "failed"
    elif not real_admin_email or not real_admin_verified or demo_users_still_exist:
        status = "needs_review"
    else:
        status = "passed"

    print("\n" + "-" * 60)
    print(f"admin_profile_count:          {admin_profile_count}")
    print(f"real_admin_verified:          {real_admin_verified}")
    print(f"demo_users_still_exist:       {demo_users_still_exist}")
    print(f"demo_password_rotation_req:   {demo_password_rotation_required}")
    print(f"qa_auth_demo_fallback_false:  {qa_auth_demo_fallback_false}")
    print(f"secrets_exposed:              {secrets_exposed}")
    print(f"public_launch_safe:           {public_launch_safe}")
    print(f"Status:                       {status}")
    if issues:
        print("Issues:")
        for i in issues:
            print(f"  - {i}")

    report = {
        "gate":                           "69A",
        "title":                          "Credential Safety Check v1",
        "status":                         status,
        "generated_at":                   datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "admin_profile_count":            admin_profile_count,
        "real_admin_email_checked":       real_admin_email,
        "real_admin_verified":            real_admin_verified,
        "real_admin_auth_found":          real_admin_auth_found,
        "demo_profiles_found":            demo_profiles,
        "demo_auth_users_found":          (
            "unknown" if demo_auth_users == "unknown"
            else bool(demo_auth_users)
        ),
        "demo_users_still_exist":         demo_users_still_exist,
        "demo_password_rotation_required": demo_password_rotation_required,
        "qa_auth_demo_fallback_false":    qa_auth_demo_fallback_false,
        "production_url_checked":         production_url_checked,
        "production_url":                 base_url,
        "production_health_ok":           prod_result.get("health_ok"),
        "production_cred_safety_status":  prod_result.get("cred_safety_status"),
        "secrets_exposed":                secrets_exposed,
        "public_launch_safe":             public_launch_safe,
        "issues":                         issues,
        "recommended_actions":            recommended,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
