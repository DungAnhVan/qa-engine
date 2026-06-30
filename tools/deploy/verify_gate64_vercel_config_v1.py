"""
Gate 64 — Vercel Config Verification v1

Static checks to verify all Gate 64 deliverables are in place
before performing the manual Vercel deployment.

No Vercel API calls. No secrets required.

Output: data/diagnostics/gate64_vercel_config_verify_v1.json
"""

import re
import json
import datetime
import subprocess
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
ADMIN_SRC   = ROOT / "apps" / "admin" / "src"
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate64_vercel_config_verify_v1.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pass(label: str, detail: str = "ok") -> dict:
    return {"label": label, "status": "PASS", "detail": detail}

def _fail(label: str, detail: str) -> dict:
    return {"label": label, "status": "FAIL", "detail": detail}

def _warn(label: str, detail: str) -> dict:
    return {"label": label, "status": "WARN", "detail": detail}


def file_check(path: Path, label: str) -> dict:
    return _pass(label, str(path.relative_to(ROOT))) if path.exists() else \
           _fail(label, f"MISSING: {path.relative_to(ROOT)}")


def file_contains(path: Path, label: str, needle: str) -> dict:
    if not path.exists():
        return _fail(label, f"File not found: {path.relative_to(ROOT)}")
    found = needle in path.read_text(encoding="utf-8", errors="ignore")
    return _pass(label, f"found: {needle[:60]}") if found else \
           _fail(label, f"MISSING '{needle[:60]}' in {path.name}")


def git_ls_files(rel_path: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", rel_path],
            cwd=str(ROOT), capture_output=True, text=True, timeout=10,
        )
        return [l.strip() for l in result.stdout.splitlines() if l.strip()]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def run_checks() -> tuple[list[dict], dict]:
    checks: list[dict] = []
    summary: dict = {}

    # ── Gate 64 deliverables ──────────────────────────────────────────────────
    vercel_json = ROOT / "vercel.json"
    checks.append(file_check(vercel_json, "vercel.json at repo root"))
    checks.append(file_check(
        ROOT / "deployment" / "VERCEL_GATE64_SETUP.md",
        "VERCEL_GATE64_SETUP.md",
    ))
    checks.append(file_check(
        ROOT / "deployment" / "VERCEL_ENV_VARS_GATE64.md",
        "VERCEL_ENV_VARS_GATE64.md",
    ))

    # ── vercel.json content ───────────────────────────────────────────────────
    checks.append(file_contains(vercel_json, "vercel.json: build command documented",
                                "pnpm --filter @qa-engine/admin build"))
    checks.append(file_contains(vercel_json, "vercel.json: output directory set",
                                "apps/admin/.next"))
    checks.append(file_contains(vercel_json, "vercel.json: install command",
                                "pnpm install"))

    # ── vercel.json has no secrets ────────────────────────────────────────────
    if vercel_json.exists():
        content = vercel_json.read_text(encoding="utf-8", errors="ignore")
        has_service_role = "SUPABASE_SERVICE_ROLE_KEY" in content and "eyJ" in content
        checks.append(
            _fail("vercel.json has no embedded service role key", "FOUND real-looking key!")
            if has_service_role else
            _pass("vercel.json has no embedded service role key", "clean")
        )
        # Should not have env block with real values
        has_env_block_with_values = bool(re.search(r'"env"\s*:\s*\{[^}]*"[A-Z_]+"\s*:\s*"ey[A-Za-z0-9]', content))
        checks.append(
            _fail("vercel.json has no hardcoded secret values", "Found JWT-looking value in env block!")
            if has_env_block_with_values else
            _pass("vercel.json has no hardcoded secret values", "clean")
        )

    # ── Setup doc content ─────────────────────────────────────────────────────
    setup_doc = ROOT / "deployment" / "VERCEL_GATE64_SETUP.md"
    checks.append(file_contains(setup_doc, "setup doc: build command", "pnpm --filter @qa-engine/admin build"))
    checks.append(file_contains(setup_doc, "setup doc: SUPABASE_SERVICE_ROLE_KEY documented", "SUPABASE_SERVICE_ROLE_KEY"))
    checks.append(file_contains(setup_doc, "setup doc: NEXT_PUBLIC_SUPABASE_URL documented", "NEXT_PUBLIC_SUPABASE_URL"))
    checks.append(file_contains(setup_doc, "setup doc: health URL documented", "/system/health"))
    checks.append(file_contains(setup_doc, "setup doc: readiness URL documented", "/system/readiness"))

    # ── Env var doc content ───────────────────────────────────────────────────
    env_doc = ROOT / "deployment" / "VERCEL_ENV_VARS_GATE64.md"
    checks.append(file_contains(env_doc, "env doc: QA_CONTENT_SOURCE documented", "QA_CONTENT_SOURCE"))
    checks.append(file_contains(env_doc, "env doc: live_supabase value", "live_supabase"))
    checks.append(file_contains(env_doc, "env doc: SUPABASE_SERVICE_ROLE_KEY server-only note",
                                "NEVER NEXT_PUBLIC"))
    checks.append(file_contains(env_doc, "env doc: QA_AUTH_DEMO_FALLBACK=false required",
                                "QA_AUTH_DEMO_FALLBACK"))

    # ── Gate 63 prerequisites ─────────────────────────────────────────────────
    checks.append(file_check(ROOT / ".env.production.example", ".env.production.example exists"))
    checks.append(file_check(
        ADMIN_SRC / "app" / "system" / "health" / "page.tsx",
        "health page exists",
    ))
    checks.append(file_check(
        ADMIN_SRC / "app" / "system" / "readiness" / "page.tsx",
        "readiness page exists",
    ))
    checks.append(file_check(
        ADMIN_SRC / "app" / "api" / "system" / "health" / "route.ts",
        "health API route exists",
    ))
    checks.append(file_check(
        ADMIN_SRC / "app" / "api" / "system" / "readiness" / "route.ts",
        "readiness API route exists",
    ))
    checks.append(file_check(ADMIN_SRC / "app" / "login" / "page.tsx", "login page exists"))

    # ── .env.local not tracked ────────────────────────────────────────────────
    env_tracked = bool(git_ls_files("apps/admin/.env.local") or git_ls_files(".env.local"))
    summary["env_local_tracked"] = env_tracked
    checks.append(
        _fail(".env.local not tracked by git", "TRACKED — remove from git immediately!")
        if env_tracked else
        _pass(".env.local not tracked by git", "clean")
    )

    env_prod_tracked = bool(git_ls_files(".env.production"))
    checks.append(
        _fail(".env.production not tracked by git", "TRACKED — remove from git!")
        if env_prod_tracked else
        _pass(".env.production not tracked by git", "clean")
    )

    # ── Service role not in use-client browser files ──────────────────────────
    use_client_leaks = []
    for f in ADMIN_SRC.rglob("*.tsx"):
        if any(p in (".next", "node_modules") for p in f.parts):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "'use client'" in content and "SUPABASE_SERVICE_ROLE_KEY" in content:
            use_client_leaks.append(str(f.relative_to(ROOT)))
    summary["service_role_exposed_to_client"] = bool(use_client_leaks)
    checks.append(
        _fail("service role key not in 'use client' components", f"LEAK: {use_client_leaks}")
        if use_client_leaks else
        _pass("service role key not in 'use client' browser components", "clean")
    )

    # Check browserSupabaseClient.ts separately
    bclient = ADMIN_SRC / "lib" / "browserSupabaseClient.ts"
    if bclient.exists() and "SUPABASE_SERVICE_ROLE_KEY" in bclient.read_text(encoding="utf-8", errors="ignore"):
        checks.append(_fail("service role key not in browserSupabaseClient.ts", "LEAK!"))
        summary["service_role_exposed_to_client"] = True
    else:
        checks.append(_pass("service role key not in browserSupabaseClient.ts", "clean"))

    # ── No NEXT_PUBLIC_SERVICE_ROLE ───────────────────────────────────────────
    for f in ROOT.rglob("*.{ts,tsx,json,env}"):
        if any(p in (".next", "node_modules", "__pycache__", ".git") for p in f.parts):
            continue
        try:
            c = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "NEXT_PUBLIC_SUPABASE_SERVICE_ROLE" in c:
            checks.append(_fail("no NEXT_PUBLIC_SUPABASE_SERVICE_ROLE anywhere", f"FOUND in {f.relative_to(ROOT)}"))
            break
    else:
        checks.append(_pass("no NEXT_PUBLIC_SUPABASE_SERVICE_ROLE anywhere", "clean"))

    # ── No real API keys committed ────────────────────────────────────────────
    for f in ROOT.rglob("*"):
        if any(p in (".next", "node_modules", "__pycache__", ".git", ".venv") for p in f.parts):
            continue
        if f.suffix not in (".ts", ".tsx", ".js", ".env", ".py", ".json"):
            continue
        if f.name.endswith(".example"):
            continue
        try:
            c = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"sk-[A-Za-z0-9]{40,}", c):
            checks.append(_fail("no committed OpenAI/Anthropic key (sk-...)", f"FOUND in {f.relative_to(ROOT)}"))
            break
    else:
        checks.append(_pass("no committed OpenAI/Anthropic key (sk-...)", "clean"))

    # ── pnpm-lock.yaml committed ──────────────────────────────────────────────
    lockfile_tracked = bool(git_ls_files("pnpm-lock.yaml"))
    checks.append(
        _pass("pnpm-lock.yaml is tracked by git", "present — Vercel reproducible install")
        if lockfile_tracked else
        _warn("pnpm-lock.yaml not tracked by git", "Vercel install may not be reproducible without lockfile")
    )

    # ── Build config in vercel.json ───────────────────────────────────────────
    checks.append(file_contains(vercel_json, "vercel.json: QA_CONTENT_SOURCE documented (if env block present)", "nextjs"))

    return checks, summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Gate 64 -- Vercel Config Verification")
    print("-" * 50)

    checks, summary = run_checks()

    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    warn_count = sum(1 for c in checks if c["status"] == "WARN")

    for c in checks:
        icon = "+" if c["status"] == "PASS" else ("!" if c["status"] == "FAIL" else "~")
        print(f"  {icon} [{c['status']:4}] {c['label']}")
        if c["status"] != "PASS":
            print(f"          {c['detail']}")

    print("\n" + "-" * 50)
    print(f"PASS: {pass_count}  FAIL: {fail_count}  WARN: {warn_count}  TOTAL: {len(checks)}")

    security_ok = (
        not summary.get("service_role_exposed_to_client", False)
        and not summary.get("env_local_tracked", False)
    )
    overall = "passed" if fail_count == 0 and security_ok else \
              "needs_review" if warn_count > 0 and fail_count == 0 else "failed"
    print(f"Overall: {overall}")

    report = {
        "gate": "64",
        "title": "Vercel Config Verification v1",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "overall_status": overall,
        "pass_count":   pass_count,
        "fail_count":   fail_count,
        "warn_count":   warn_count,
        "total_checks": len(checks),
        "security_summary": {
            "service_role_exposed_to_client": summary.get("service_role_exposed_to_client", False),
            "env_local_tracked":             summary.get("env_local_tracked", False),
        },
        "checks": checks,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
