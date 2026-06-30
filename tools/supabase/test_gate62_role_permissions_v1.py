"""
Gate 62 — RLS Role Permission Tests v1

Signs in as each demo auth user with the anon key and tests table-level RLS
policies. Failures indicate a missing or incorrect policy.

Requires:
  NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local
  (or SUPABASE_URL + SUPABASE_ANON_KEY as fallback)

Output: data/diagnostics/gate62_rls_role_permission_test_report_v1.json
"""

import os
import json
import datetime
from pathlib import Path

try:
    from supabase import create_client
except ImportError:
    print("ERROR: supabase-py not installed. Run: pip install supabase")
    raise

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / "apps" / "admin" / ".env.local"

def _load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

_env = _load_env(ENV_FILE)

SUPABASE_URL = (
    _env.get("NEXT_PUBLIC_SUPABASE_URL")
    or _env.get("SUPABASE_URL")
    or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    or os.environ.get("SUPABASE_URL", "")
)
ANON_KEY = (
    _env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    or _env.get("SUPABASE_ANON_KEY")
    or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    or os.environ.get("SUPABASE_ANON_KEY", "")
)

DEMO_PASSWORD = "QuantaAptusDemo123!"

DEMO_USERS = [
    {"email": "admin@quantaaptus.local",   "role": "admin"},
    {"email": "teacher@quantaaptus.local", "role": "teacher"},
    {"email": "student@quantaaptus.local", "role": "student"},
    {"email": "parent@quantaaptus.local",  "role": "parent"},
]

OUTPUT_DIR = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate62_rls_role_permission_test_report_v1.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mask_key(key: str) -> str:
    if not key or len(key) < 12:
        return "***"
    return key[:6] + "..." + key[-4:]


def _check(label: str, fn) -> dict:
    """Run a single RLS check. Returns {label, status, detail}."""
    try:
        result = fn()
        data = result.data
        if data is None:
            return {"label": label, "status": "PASS", "detail": "no error, data=None"}
        if isinstance(data, list):
            return {"label": label, "status": "PASS", "detail": f"{len(data)} row(s)"}
        return {"label": label, "status": "PASS", "detail": str(data)[:120]}
    except Exception as exc:
        msg = str(exc)
        if "permission denied" in msg.lower() or "row level security" in msg.lower() or "insufficient" in msg.lower():
            return {"label": label, "status": "BLOCKED_BY_RLS", "detail": msg[:200]}
        return {"label": label, "status": "ERROR", "detail": msg[:200]}


def _check_blocked(label: str, fn) -> dict:
    """
    Run an RLS check that SHOULD be blocked.
    PASS = correctly blocked, FAIL = unexpectedly allowed.
    """
    try:
        result = fn()
        data = result.data
        if data is None or (isinstance(data, list) and len(data) == 0):
            # RLS filtered to empty — this is the expected behaviour
            return {"label": label, "status": "PASS", "detail": "correctly empty (RLS filtered)"}
        return {
            "label": label,
            "status": "FAIL",
            "detail": f"expected empty/blocked but got {len(data) if isinstance(data, list) else 1} row(s)",
        }
    except Exception as exc:
        msg = str(exc)
        if "permission denied" in msg.lower() or "row level security" in msg.lower():
            return {"label": label, "status": "PASS", "detail": "correctly blocked: " + msg[:120]}
        return {"label": label, "status": "ERROR", "detail": msg[:200]}


# ---------------------------------------------------------------------------
# Per-role test suites
# ---------------------------------------------------------------------------

def run_admin_checks(client) -> list[dict]:
    checks = []
    checks.append(_check("read own profile",   lambda: client.table("profiles").select("id,role").limit(1).execute()))
    checks.append(_check("read all profiles",  lambda: client.table("profiles").select("id,role").limit(5).execute()))
    checks.append(_check("read subjects",      lambda: client.table("subjects").select("id,slug").limit(3).execute()))
    checks.append(_check("read resources",     lambda: client.table("resources").select("id").limit(3).execute()))
    checks.append(_check("read all attempts",  lambda: client.table("attempts").select("id").limit(3).execute()))
    checks.append(_check("read marked_attempts", lambda: client.table("marked_attempts").select("id").limit(3).execute()))
    checks.append(_check("read teacher_reviews", lambda: client.table("teacher_reviews").select("id").limit(3).execute()))
    return checks


def run_teacher_checks(client) -> list[dict]:
    checks = []
    checks.append(_check("read own profile",      lambda: client.table("profiles").select("id,role").limit(1).execute()))
    checks.append(_check("read subjects",         lambda: client.table("subjects").select("id,slug").limit(3).execute()))
    checks.append(_check("read resources",        lambda: client.table("resources").select("id").limit(3).execute()))
    checks.append(_check("read attempts (org)",   lambda: client.table("attempts").select("id").limit(3).execute()))
    checks.append(_check("read marked_attempts",  lambda: client.table("marked_attempts").select("id").limit(3).execute()))
    checks.append(_check("read teacher_reviews",  lambda: client.table("teacher_reviews").select("id").limit(3).execute()))
    # Teachers should NOT see profiles outside their org — we can't easily test cross-org here,
    # but at minimum reading their own org profiles should work
    checks.append(_check("read same-org profiles (limited)", lambda: client.table("profiles").select("id,role").limit(5).execute()))
    return checks


def run_student_checks(client) -> list[dict]:
    checks = []
    checks.append(_check("read own profile",     lambda: client.table("profiles").select("id,role").limit(1).execute()))
    checks.append(_check("read subjects",        lambda: client.table("subjects").select("id,slug").limit(3).execute()))
    checks.append(_check("read resources",       lambda: client.table("resources").select("id").limit(3).execute()))
    checks.append(_check("read own attempts",    lambda: client.table("attempts").select("id").limit(3).execute()))
    checks.append(_check("read own marked_attempts", lambda: client.table("marked_attempts").select("id").limit(3).execute()))
    # Students should NOT see teacher_reviews at all
    checks.append(_check_blocked("teacher_reviews blocked for student", lambda: client.table("teacher_reviews").select("id").limit(3).execute()))
    # Students should NOT see other profiles
    checks.append(_check_blocked("other profiles blocked for student", lambda: client.table("profiles").select("id,role").limit(10).execute()))
    return checks


def run_parent_checks(client) -> list[dict]:
    checks = []
    checks.append(_check("read own profile",     lambda: client.table("profiles").select("id,role").limit(1).execute()))
    checks.append(_check("read subjects",        lambda: client.table("subjects").select("id,slug").limit(3).execute()))
    checks.append(_check("read resources",       lambda: client.table("resources").select("id").limit(3).execute()))
    # Parents can read linked student attempts — returns empty if no link set up
    checks.append(_check("read linked student attempts (may be empty)", lambda: client.table("attempts").select("id").limit(3).execute()))
    checks.append(_check("read linked student marked_attempts", lambda: client.table("marked_attempts").select("id").limit(3).execute()))
    # Parents should NOT see teacher_reviews
    checks.append(_check_blocked("teacher_reviews blocked for parent", lambda: client.table("teacher_reviews").select("id").limit(3).execute()))
    # Parents should NOT see other profiles
    checks.append(_check_blocked("other profiles blocked for parent", lambda: client.table("profiles").select("id,role").limit(10).execute()))
    return checks


ROLE_RUNNERS = {
    "admin":   run_admin_checks,
    "teacher": run_teacher_checks,
    "student": run_student_checks,
    "parent":  run_parent_checks,
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not SUPABASE_URL or not ANON_KEY:
        print("ERROR: SUPABASE_URL or SUPABASE_ANON_KEY not found in .env.local")
        return

    print(f"Supabase URL : {SUPABASE_URL}")
    print(f"Anon key     : {mask_key(ANON_KEY)}")
    print()

    results = []

    for user in DEMO_USERS:
        email = user["email"]
        role  = user["role"]
        print(f"--- {role.upper()} ({email}) ---")

        user_result: dict = {
            "email": email,
            "expected_role": role,
            "status": "unknown",
            "checks": [],
        }

        try:
            client = create_client(SUPABASE_URL, ANON_KEY)
            auth_resp = client.auth.sign_in_with_password({"email": email, "password": DEMO_PASSWORD})
            if not auth_resp.user:
                user_result["status"] = "LOGIN_FAILED"
                user_result["error"] = "No user returned from sign_in_with_password"
                print(f"  LOGIN FAILED\n")
                results.append(user_result)
                continue

            print(f"  Logged in as {auth_resp.user.id[:8]}…")
            runner = ROLE_RUNNERS.get(role)
            checks = runner(client) if runner else []

            pass_count  = sum(1 for c in checks if c["status"] == "PASS")
            fail_count  = sum(1 for c in checks if c["status"] in ("FAIL", "ERROR"))
            block_count = sum(1 for c in checks if c["status"] == "BLOCKED_BY_RLS")

            user_result["checks"] = checks
            user_result["pass_count"]  = pass_count
            user_result["fail_count"]  = fail_count
            user_result["block_count"] = block_count
            user_result["status"] = "PASS" if fail_count == 0 and block_count == 0 else "NEEDS_REVIEW"

            for c in checks:
                icon = "✓" if c["status"] == "PASS" else ("✗" if c["status"] in ("FAIL","ERROR") else "⚠")
                print(f"  {icon} [{c['status']}] {c['label']}")
                if c["status"] not in ("PASS",):
                    print(f"      {c['detail']}")

            client.auth.sign_out()

        except Exception as exc:
            user_result["status"] = "ERROR"
            user_result["error"] = str(exc)[:300]
            print(f"  ERROR: {exc}")

        results.append(user_result)
        print()

    overall_status = "PASS" if all(r["status"] == "PASS" for r in results) else "NEEDS_REVIEW"

    report = {
        "gate": "62",
        "title": "RLS Role Permission Tests v1",
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "supabase_url": SUPABASE_URL,
        "overall_status": overall_status,
        "users_tested": len(results),
        "results": results,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written: {OUTPUT_FILE}")
    print(f"Overall status: {overall_status}")


if __name__ == "__main__":
    main()
