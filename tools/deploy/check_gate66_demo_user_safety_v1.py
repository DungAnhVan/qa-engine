"""
Gate 66 -- Demo User Safety Check v1

Checks whether demo accounts still exist in Supabase and verifies the
production environment is configured safely for internal testing.

Usage:
  # Local check only (needs .env.local or system env with Supabase credentials)
  .venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate66_demo_user_safety_v1.py

  # With production URL check
  .venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate66_demo_user_safety_v1.py https://qa-engine-admin.vercel.app

Output: data/diagnostics/gate66_demo_user_safety_check_v1.json

Security notes:
  - Service role key is read from env/file but NEVER printed.
  - Masked as first6...last4 in log output only.
  - Secrets are not written to the report file.
"""

import sys
import json
import os
import re
import time
import datetime
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

ROOT       = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate66_demo_user_safety_check_v1.json"

DEMO_EMAILS = [
    "admin@quantaaptus.local",
    "teacher@quantaaptus.local",
    "student@quantaaptus.local",
    "parent@quantaaptus.local",
]

REQUEST_TIMEOUT = 15

# Security patterns — same as smoke test
SECURITY_PATTERNS = [
    re.compile(r'eyJ[A-Za-z0-9+/=_-]{300,}'),
    re.compile(r'sk-[A-Za-z0-9]{40,}'),
    re.compile(r'sk-ant-[A-Za-z0-9\-_]{50,}'),
]

# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------

def load_env_local() -> dict[str, str]:
    """Parse .env.local at repo root; returns key→value dict."""
    env_path = ROOT / ".env.local"
    result: dict[str, str] = {}
    if not env_path.exists():
        return result
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip().strip('"').strip("'")
        result[k.strip()] = v
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
    """
    GET a Supabase REST or Auth Admin endpoint.
    Returns (status_code, parsed_json, error_message).
    """
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
    """
    GET a public endpoint; returns (status_code, parsed_json_or_None, error).
    """
    req = urllib.request.Request(url, headers={"User-Agent": "QA-Gate66-SafetyCheck/1.0"})
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
# Demo profile check
# ---------------------------------------------------------------------------

def check_demo_profiles(supabase_url: str, service_role_key: str) -> tuple[list[dict], str | None]:
    """
    Query the profiles table for each demo email.
    Returns (found_profiles, error_message_or_None).
    """
    found = []
    last_error = None
    for email in DEMO_EMAILS:
        encoded_email = urllib.parse.quote(email, safe="")
        url = (
            f"{supabase_url}/rest/v1/profiles"
            f"?select=id,email,role"
            f"&email=eq.{encoded_email}"
        )
        status, data, err = supabase_get(url, service_role_key)
        if err:
            last_error = f"profiles check error for {email}: {err}"
            continue
        if isinstance(data, list) and data:
            row = data[0]
            found.append({
                "email": row.get("email", email),
                "role":  row.get("role", "unknown"),
            })
    return found, last_error

# ---------------------------------------------------------------------------
# Demo auth user check
# ---------------------------------------------------------------------------

def check_demo_auth_users(supabase_url: str, service_role_key: str) -> tuple[list[dict] | None, str | None]:
    """
    Query Supabase Auth Admin API for demo users.
    Returns (found_users_or_None, error_message_or_None).
    None means the API was unavailable (not a failure condition).
    """
    url = f"{supabase_url}/auth/v1/admin/users?per_page=100"
    status, data, err = supabase_get(url, service_role_key)
    if err or data is None:
        return None, err or "auth admin API unavailable"
    users = data.get("users", []) if isinstance(data, dict) else []
    demo_found = [
        {"email": u.get("email"), "id": u.get("id")}
        for u in users
        if u.get("email") in DEMO_EMAILS
    ]
    return demo_found, None

# ---------------------------------------------------------------------------
# Production URL check
# ---------------------------------------------------------------------------

def check_production_url(base_url: str) -> dict:
    """
    Call /api/system/health and /api/system/readiness on the production URL.
    Returns a summary dict.
    """
    result: dict = {
        "url_checked":              base_url,
        "health_ok":                False,
        "readiness_ok":             False,
        "demo_fallback_false":      False,
        "content_source_live":      False,
        "secrets_exposed":          False,
        "secret_findings":          [],
        "health_status_code":       0,
        "readiness_status_code":    0,
        "readiness_api_status":     None,
    }

    # Health
    h_code, h_data, _ = public_get(f"{base_url}/api/system/health")
    result["health_status_code"] = h_code
    if h_code == 200 and isinstance(h_data, dict):
        result["health_ok"]            = h_data.get("status") == "ok"
        result["demo_fallback_false"]  = h_data.get("demo_fallback") == "false"
        result["content_source_live"]  = h_data.get("content_source") == "live_supabase"

    # Readiness
    r_code, r_data, _ = public_get(f"{base_url}/api/system/readiness")
    result["readiness_status_code"] = r_code
    if r_code == 200 and isinstance(r_data, dict):
        result["readiness_ok"]         = r_data.get("status") in ("ready", "needs_review")
        result["readiness_api_status"] = r_data.get("status")

    # Demo safety API
    ds_code, ds_data, _ = public_get(f"{base_url}/api/system/demo-safety")
    result["demo_safety_status_code"] = ds_code
    result["demo_safety_api_status"]  = ds_data.get("status") if isinstance(ds_data, dict) else None

    # Security scan across all responses
    all_bodies: list[str] = []
    for path in ("/api/system/health", "/api/system/readiness"):
        try:
            req = urllib.request.Request(
                f"{base_url}{path}",
                headers={"User-Agent": "QA-Gate66-SafetyCheck/1.0"}
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                all_bodies.append(resp.read(64 * 1024).decode("utf-8", errors="replace"))
        except Exception:
            pass
    for body in all_bodies:
        for pat in SECURITY_PATTERNS:
            if pat.search(body):
                result["secrets_exposed"] = True
                result["secret_findings"].append(pat.pattern[:40])

    return result

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    base_url = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
    if base_url and not base_url.startswith("http"):
        print(f"ERROR: URL must start with http(s): {base_url}")
        sys.exit(1)

    print("Gate 66 -- Demo User Safety Check")
    print(f"Production URL: {base_url or '(not provided)'}")
    print("-" * 60)

    # ── Load credentials ──────────────────────────────────────────────────────
    env_local = load_env_local()
    supabase_url     = resolve_env("SUPABASE_URL", env_local) \
                    or resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
    service_role_key = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)
    local_demo_fallback = resolve_env("QA_AUTH_DEMO_FALLBACK", env_local)

    print(f"  SUPABASE_URL:            {'found' if supabase_url else 'NOT FOUND'}")
    print(f"  SERVICE_ROLE_KEY:        {mask_key(service_role_key)}")
    print(f"  Local DEMO_FALLBACK:     {local_demo_fallback!r}")

    # ── Demo profiles check ───────────────────────────────────────────────────
    demo_profiles_found: list[dict] | bool = False
    demo_profiles_error: str | None = None
    if supabase_url and service_role_key:
        print("\n  Checking profiles table for demo emails...")
        profiles, err = check_demo_profiles(supabase_url, service_role_key)
        demo_profiles_error = err
        if err and not profiles:
            print(f"  ! profiles check error: {err}")
            demo_profiles_found = "unknown"
        else:
            demo_profiles_found = profiles
            for p in profiles:
                print(f"  ! FOUND profile: {p['email']} (role: {p['role']})")
            if not profiles:
                print("  + No demo profiles found in profiles table")
    else:
        print("\n  Skipping profiles check — Supabase credentials not available")
        demo_profiles_found = "unknown"

    # ── Auth admin check ──────────────────────────────────────────────────────
    demo_auth_users_found: list[dict] | None | bool | str = "unknown"
    if supabase_url and service_role_key:
        print("\n  Checking Supabase Auth admin API for demo users...")
        auth_users, auth_err = check_demo_auth_users(supabase_url, service_role_key)
        if auth_users is None:
            print(f"  ? Auth admin API unavailable: {auth_err}")
            demo_auth_users_found = "unknown"
        else:
            demo_auth_users_found = auth_users
            for u in auth_users:
                print(f"  ! FOUND auth user: {u['email']}")
            if not auth_users:
                print("  + No demo auth users found via admin API")

    # ── QA_AUTH_DEMO_FALLBACK check ───────────────────────────────────────────
    print("\n  QA_AUTH_DEMO_FALLBACK:")
    print(f"    .env.local:  {local_demo_fallback!r}")
    local_fallback_ok = local_demo_fallback == "false"
    if not local_fallback_ok:
        print(f"  ! WARNING: QA_AUTH_DEMO_FALLBACK is '{local_demo_fallback}' in .env.local - must be false for production")
    else:
        print(f"  + OK: false in .env.local")

    # ── Production URL check ──────────────────────────────────────────────────
    prod_result: dict = {}
    production_url_checked = False
    if base_url:
        print(f"\n  Checking production URL: {base_url}")
        prod_result = check_production_url(base_url)
        production_url_checked = True
        print(f"    health:           {prod_result.get('health_status_code')} {'OK' if prod_result.get('health_ok') else 'FAIL'}")
        print(f"    readiness:        {prod_result.get('readiness_status_code')} {prod_result.get('readiness_api_status', 'N/A')}")
        print(f"    demo_fallback:    {'false (OK)' if prod_result.get('demo_fallback_false') else 'NOT false (WARNING)'}")
        print(f"    content_source:   {'live_supabase' if prod_result.get('content_source_live') else 'NOT live'}")
        print(f"    secrets_exposed:  {prod_result.get('secrets_exposed')}")
        print(f"    demo-safety API:  {prod_result.get('demo_safety_api_status', 'N/A')}")

    # ── Derive status ─────────────────────────────────────────────────────────
    secrets_exposed      = prod_result.get("secrets_exposed", False)
    prod_fallback_false  = prod_result.get("demo_fallback_false", True) if production_url_checked else True
    # Accept production URL confirmation even if .env.local doesn't have the flag
    effective_fallback_false = local_fallback_ok or (production_url_checked and prod_fallback_false)
    qa_fallback_false        = effective_fallback_false

    rotation_required = True  # always true while demo accounts exist

    issues: list[str] = []
    recommended_actions: list[str] = []

    if secrets_exposed:
        issues.append("Secrets found in production API responses — CRITICAL")

    if production_url_checked and not prod_fallback_false:
        issues.append("QA_AUTH_DEMO_FALLBACK is not false in production — must be fixed")

    if not local_fallback_ok:
        issues.append(f"QA_AUTH_DEMO_FALLBACK is '{local_demo_fallback}' in .env.local")

    profiles_exist = isinstance(demo_profiles_found, list) and len(demo_profiles_found) > 0
    auth_exist = isinstance(demo_auth_users_found, list) and len(demo_auth_users_found) > 0

    if profiles_exist:
        issues.append(f"{len(demo_profiles_found)} demo profile(s) found in Supabase")
        recommended_actions.append("Rotate demo account passwords or disable/delete demo users")
        recommended_actions.append("Create real admin@quantaaptus.com account before removing demo admin")

    if auth_exist:
        issues.append(f"{len(demo_auth_users_found)} demo auth user(s) found in Supabase Auth")

    recommended_actions.append("Verify QA_AUTH_DEMO_FALLBACK=false in Vercel environment variables")
    recommended_actions.append("Verify SUPABASE_SERVICE_ROLE_KEY is server-only in Vercel (no NEXT_PUBLIC_ prefix)")
    recommended_actions.append("Do NOT point admin.quantaaptus.com until passwords are rotated")

    public_launch_safe = (
        not profiles_exist
        and not auth_exist
        and not secrets_exposed
        and qa_fallback_false
    )

    internal_testing_safe = (
        qa_fallback_false
        and not secrets_exposed
        and (not production_url_checked or prod_fallback_false)
    )

    # status: failed only for secrets or non-false demo_fallback in prod
    if secrets_exposed or (production_url_checked and not prod_fallback_false):
        status = "failed"
    elif profiles_exist or auth_exist or demo_profiles_found == "unknown":
        status = "needs_review"  # expected before final launch
    elif not qa_fallback_false:
        status = "needs_review"
    else:
        status = "passed"

    print("\n" + "-" * 60)
    print(f"demo_profiles_found:          {demo_profiles_found}")
    print(f"demo_auth_users_found:        {demo_auth_users_found}")
    print(f"qa_auth_demo_fallback_false:  {qa_fallback_false}")
    print(f"secrets_exposed:              {secrets_exposed}")
    print(f"public_launch_safe:           {public_launch_safe}")
    print(f"internal_testing_safe:        {internal_testing_safe}")
    print(f"Status:                       {status}")
    if issues:
        print("Issues:")
        for i in issues:
            print(f"  - {i}")

    report = {
        "gate":                           "66",
        "title":                          "Demo User Safety Check v1",
        "generated_at":                   datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status":                         status,
        "demo_profiles_found":            demo_profiles_found,
        "demo_auth_users_found":          (
            demo_auth_users_found if isinstance(demo_auth_users_found, (bool, str))
            else bool(demo_auth_users_found) if isinstance(demo_auth_users_found, list) and not demo_auth_users_found
            else True if isinstance(demo_auth_users_found, list) and demo_auth_users_found
            else "unknown"
        ),
        "demo_profiles_detail":           demo_profiles_found if isinstance(demo_profiles_found, list) else [],
        "demo_password_rotation_required": rotation_required,
        "qa_auth_demo_fallback_false":    qa_fallback_false,
        "production_url_checked":         production_url_checked,
        "production_url":                 base_url,
        "production_health_ok":           prod_result.get("health_ok", None),
        "production_readiness_ok":        prod_result.get("readiness_ok", None),
        "production_demo_fallback_false": prod_result.get("demo_fallback_false", None),
        "secrets_exposed":                secrets_exposed,
        "public_launch_safe":             public_launch_safe,
        "internal_testing_safe":          internal_testing_safe,
        "issues":                         issues,
        "recommended_actions":            recommended_actions,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
