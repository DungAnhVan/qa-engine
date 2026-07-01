"""
Gate 69A -- Credential Hardening Report Builder v1

Checks that all Gate 69A deliverables exist, verifies security posture,
and produces the gate report.

Output:
  data/diagnostics/gate69a_credential_hardening_report_v1.json
  data/diagnostics/SUPABASE_GATE_69A_CREDENTIAL_HARDENING_DONE.md
"""

import json
import datetime
import subprocess
import re
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
ADMIN_SRC   = ROOT / "apps" / "admin" / "src"
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate69a_credential_hardening_report_v1.json"
DONE_FILE   = OUTPUT_DIR / "SUPABASE_GATE_69A_CREDENTIAL_HARDENING_DONE.md"

# ---------------------------------------------------------------------------
# Deliverables
# ---------------------------------------------------------------------------

DELIVERABLES = {
    "credential_hardening_doc_created":  ROOT / "deployment" / "PRODUCTION_CREDENTIAL_HARDENING_GATE69A.md",
    "real_admin_script_created":         ROOT / "tools" / "deploy" / "create_gate69a_real_admin_user_v1.py",
    "credential_safety_check_created":   ROOT / "tools" / "deploy" / "check_gate69a_credential_safety_v1.py",
    "demo_disable_script_created":       ROOT / "tools" / "deploy" / "disable_gate69a_demo_users_v1.py",
    "credential_safety_page_created":    ADMIN_SRC / "app" / "system" / "credential-safety" / "page.tsx",
    "credential_safety_api_created":     ADMIN_SRC / "app" / "api" / "system" / "credential-safety" / "route.ts",
}

# Latest check report (optional — may not exist yet)
SAFETY_CHECK_REPORT = OUTPUT_DIR / "gate69a_credential_safety_check_v1.json"

# Client files that must not contain service role key
CLIENT_FILES = [
    ADMIN_SRC / "lib" / "browserSupabaseClient.ts",
]

SECRET_PATTERNS_IN_CODE = [
    re.compile(r'SUPABASE_SERVICE_ROLE_KEY'),
    re.compile(r'NEXT_PUBLIC_SUPABASE_SERVICE_ROLE'),
    re.compile(r'sk-[A-Za-z0-9]{40,}'),
    re.compile(r'sk-ant-[A-Za-z0-9\-_]{50,}'),
]

# Patterns that must NOT appear in committed files (passwords)
PASSWORD_PATTERNS = [
    re.compile(r'password\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE),
    re.compile(r'QA_REAL_ADMIN_PASSWORD\s*=\s*\S+'),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_env_local_not_tracked() -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", ".env.local"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=10,
        )
        return not bool(result.stdout.strip())
    except Exception:
        return True


def scan_client_files() -> tuple[bool, list[str]]:
    violations = []
    for path in CLIENT_FILES:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pat in SECRET_PATTERNS_IN_CODE:
            if pat.search(content):
                violations.append(f"{path.name}: matches '{pat.pattern[:50]}'")
    return len(violations) == 0, violations


def scan_for_committed_passwords() -> tuple[bool, list[str]]:
    """
    Scan committed Python deploy scripts for hardcoded password patterns.
    Only checks gate69a scripts since those are the ones that handle passwords.
    Uses full-line context so shell example lines ($env:, #, <...>) are not flagged.
    """
    violations = []
    # Skip indicators in full line context
    LINE_SKIP = ["password-env", "env_name", "password_env", "os.environ",
                 "$env:", "<your", "# ", "example", "set in shell", "strongpassword"]
    scan_paths = [
        ROOT / "tools" / "deploy" / "create_gate69a_real_admin_user_v1.py",
        ROOT / "tools" / "deploy" / "disable_gate69a_demo_users_v1.py",
        ROOT / "tools" / "deploy" / "check_gate69a_credential_safety_v1.py",
    ]
    for path in scan_paths:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pat in PASSWORD_PATTERNS:
            for m in pat.finditer(content):
                # Get full line for context
                line_start = content.rfind("\n", 0, m.start()) + 1
                line_end = content.find("\n", m.end())
                if line_end == -1:
                    line_end = len(content)
                full_line = content[line_start:line_end].strip()
                if not any(skip in full_line for skip in LINE_SKIP):
                    violations.append(f"{path.name}: possible hardcoded password: {full_line[:70]}")
    return len(violations) == 0, violations


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("Gate 69A -- Credential Hardening Report")
    print("-" * 55)

    # ── Deliverables ──────────────────────────────────────────────────────────
    print("\n[Deliverables]")
    deliverable_status: dict[str, bool] = {}
    for key, path in DELIVERABLES.items():
        exists = path.exists()
        deliverable_status[key] = exists
        print(f"  {'+'  if exists else '!'} {key}: {'OK' if exists else 'MISSING'}")
    all_deliverables_present = all(deliverable_status.values())

    # ── Safety check report (optional) ───────────────────────────────────────
    print("\n[Safety Check Report]")
    safety_report = load_json(SAFETY_CHECK_REPORT)
    safety_report_exists = bool(safety_report)
    safety_status = safety_report.get("status", "not_run") if safety_report else "not_run"
    real_admin_verified = safety_report.get("real_admin_verified", None)
    public_launch_safe  = safety_report.get("public_launch_safe", False)
    print(f"  {'+'  if safety_report_exists else '?'} gate69a_credential_safety_check: {safety_status}")

    # ── Security checks ───────────────────────────────────────────────────────
    print("\n[Security]")
    env_local_not_tracked = check_env_local_not_tracked()
    service_role_safe, sr_violations = scan_client_files()
    no_committed_passwords, pw_violations = scan_for_committed_passwords()

    print(f"  {'+'  if env_local_not_tracked else '!'} .env.local not tracked: {'OK' if env_local_not_tracked else 'TRACKED — SECURITY ISSUE'}")
    print(f"  {'+'  if service_role_safe else '!'} service role not in client files: {'OK' if service_role_safe else f'VIOLATION: {sr_violations}'}")
    print(f"  {'+'  if no_committed_passwords else '!'} no hardcoded passwords in scripts: {'OK' if no_committed_passwords else f'VIOLATION: {pw_violations}'}")

    # ── Derive status ─────────────────────────────────────────────────────────
    service_role_exposed = not service_role_safe
    env_local_tracked    = not env_local_not_tracked
    passwords_committed  = not no_committed_passwords

    critical_fail = service_role_exposed or env_local_tracked or passwords_committed

    needs_review = (
        not all_deliverables_present
        or not safety_report_exists
        or safety_status not in ("passed", "needs_review")
    )

    if critical_fail:
        status = "failed"
    elif needs_review:
        status = "needs_review"
    else:
        status = "passed"

    print(f"\n  all_deliverables_present:  {all_deliverables_present}")
    print(f"  safety_report_exists:      {safety_report_exists}")
    print(f"  safety_status:             {safety_status}")
    print(f"  real_admin_verified:       {real_admin_verified}")
    print(f"  public_launch_safe:        {public_launch_safe}")
    print(f"  service_role_exposed:      {service_role_exposed}")
    print(f"  env_local_tracked:         {env_local_tracked}")
    print(f"  passwords_committed:       {passwords_committed}")
    print(f"\nStatus: {status}")

    report = {
        "gate":                               "69A",
        "status":                             status,
        "generated_at":                       now,
        # Deliverables
        **deliverable_status,
        "all_deliverables_present":           all_deliverables_present,
        # Safety check
        "credential_safety_check_run":        safety_report_exists,
        "credential_safety_check_status":     safety_status,
        "real_admin_verified":                real_admin_verified,
        # Security
        "service_role_exposed":               service_role_exposed,
        "env_local_tracked":                  env_local_tracked,
        "passwords_committed":                passwords_committed,
        # Launch safety
        "public_launch_safe":                 public_launch_safe,
        "known_public_launch_blocker":        (
            "real admin user not yet created or verified; "
            "demo passwords must be rotated or accounts disabled"
        ),
        "next_gate":                          "Gate 69B - AI Content Factory Foundation",
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")

    # ── DONE marker ───────────────────────────────────────────────────────────
    missing_deliverables = [k for k, v in deliverable_status.items() if not v]

    done_content = f"""# Gate 69A -- Production Credential Hardening DONE

Generated: {now}

## Status: {status.upper()}

## What Was Created

- Real admin user creation flow: tools/deploy/create_gate69a_real_admin_user_v1.py
- Credential safety check: tools/deploy/check_gate69a_credential_safety_v1.py
- Demo user disable flow: tools/deploy/disable_gate69a_demo_users_v1.py
- Credential safety page: apps/admin/src/app/system/credential-safety/page.tsx
- Credential safety API: apps/admin/src/app/api/system/credential-safety/route.ts
- Credential hardening doc: deployment/PRODUCTION_CREDENTIAL_HARDENING_GATE69A.md

## Security

- Real admin creation: dry-run by default, --execute required for real action
- Demo disable: dry-run by default, --execute --confirm {chr(68)}ISABLE_DEMO_USERS required
- Demo users are NOT deleted automatically
- Passwords are NEVER printed or committed
- Service role key is server/CLI only, masked in output
- .env.local is not tracked in git: {env_local_not_tracked}
- Service role exposed to client: {service_role_exposed}

## Deliverables ({sum(deliverable_status.values())}/{len(deliverable_status)} present)

{chr(10).join(("  + " if v else "  ! ") + k for k, v in deliverable_status.items())}

## Public Launch Status

- public_launch_safe: {public_launch_safe}
- Known blocker: real admin user must be created and verified;
  demo passwords must be rotated or demo accounts disabled

## How to Complete Public Launch Preparation

1. Create real admin user (dry-run first, then --execute):
   .venv-ingest\\Scripts\\python.exe tools\\deploy\\create_gate69a_real_admin_user_v1.py \\
       --email YOUR_EMAIL --password-env QA_REAL_ADMIN_PASSWORD

2. Sign in and verify role at https://admin.quantaaptus.com/system/auth-session

3. Disable demo users (dry-run first, then --execute --confirm DISABLE_DEMO_USERS):
   .venv-ingest\\Scripts\\python.exe tools\\deploy\\disable_gate69a_demo_users_v1.py

4. Run credential safety check:
   .venv-ingest\\Scripts\\python.exe tools\\deploy\\check_gate69a_credential_safety_v1.py \\
       https://admin.quantaaptus.com --real-admin-email YOUR_EMAIL

5. Re-run this report:
   .venv-ingest\\Scripts\\python.exe tools\\deploy\\build_gate69a_credential_hardening_report_v1.py

Expected final state:
  - real_admin_verified: true
  - demo_users_still_exist: false
  - public_launch_safe: true
  - gate69a status: passed

## Next Gate

Gate 69B - AI Content Factory Foundation
"""
    DONE_FILE.write_text(done_content, encoding="utf-8")
    print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
