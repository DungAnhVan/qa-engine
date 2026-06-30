"""
Gate 63 — Production Readiness Check v1

Static analysis pass: scans the codebase for security issues and verifies
all Gate 63 deliverables are in place before production deployment.

No Supabase connection required. Checks files, code patterns, and git state.

Output: data/diagnostics/gate63_production_readiness_check_v1.json
"""

import os
import re
import json
import datetime
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADMIN_SRC   = ROOT / "apps" / "admin" / "src"
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate63_production_readiness_check_v1.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pass(label: str, detail: str = "ok") -> dict:
    return {"label": label, "status": "PASS", "detail": detail}

def _fail(label: str, detail: str) -> dict:
    return {"label": label, "status": "FAIL", "detail": detail}

def _warn(label: str, detail: str) -> dict:
    return {"label": label, "status": "WARN", "detail": detail}

def _skip(label: str, detail: str) -> dict:
    return {"label": label, "status": "SKIP", "detail": detail}


def file_check(path: Path, label: str) -> dict:
    return _pass(label) if path.exists() else _fail(label, f"MISSING: {path.relative_to(ROOT)}")


def git_ls_files(rel_path: str) -> list[str]:
    """Return list of git-tracked files matching the pattern."""
    try:
        result = subprocess.run(
            ["git", "ls-files", rel_path],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def scan_files_for_pattern(pattern: str, glob_pattern: str, allowed_files: set[str]) -> list[str]:
    """Return relative paths of files containing pattern (excluding allowed_files)."""
    hits = []
    for f in ROOT.rglob(glob_pattern):
        if any(part in (".next", "node_modules", "__pycache__", ".git") for part in f.parts):
            continue
        if f.name in allowed_files:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(pattern, content):
            hits.append(str(f.relative_to(ROOT)))
    return hits


# ---------------------------------------------------------------------------
# Service role key allowed files
# ---------------------------------------------------------------------------

SERVER_ONLY_FILES = {
    "liveSupabaseContent.ts",
    "liveSupabaseAttempts.ts",
    "liveSupabaseMarking.ts",
    "liveSupabaseTeacherReview.ts",
    "liveSupabaseAuthContext.ts",
    "liveSupabaseStudentResults.ts",
    "serverSupabaseAuth.ts",
}

# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def run_checks() -> tuple[list[dict], dict[str, bool]]:
    checks: list[dict] = []
    summary: dict[str, bool] = {}

    # ── Gate 63 deliverables ──────────────────────────────────────────────────
    checks.append(file_check(ROOT / ".env.production.example",
                              "production env template (.env.production.example)"))

    checks.append(file_check(ADMIN_SRC / "app" / "system" / "health" / "page.tsx",
                              "health page (system/health/page.tsx)"))

    checks.append(file_check(ADMIN_SRC / "app" / "system" / "readiness" / "page.tsx",
                              "readiness page (system/readiness/page.tsx)"))

    checks.append(file_check(ADMIN_SRC / "app" / "api" / "system" / "health" / "route.ts",
                              "health API route (api/system/health/route.ts)"))

    checks.append(file_check(ADMIN_SRC / "app" / "api" / "system" / "readiness" / "route.ts",
                              "readiness API route (api/system/readiness/route.ts)"))

    checks.append(file_check(ROOT / "deployment" / "VERCEL_DEPLOYMENT_CHECKLIST.md",
                              "Vercel deployment checklist"))

    checks.append(file_check(ROOT / "deployment" / "SECURITY_PREDEPLOY_CHECKLIST.md",
                              "security pre-deploy checklist"))

    # ── Gate 62 prerequisites ─────────────────────────────────────────────────
    checks.append(file_check(
        ROOT / "supabase" / "migrations" / "000004_rls_role_hardening.sql",
        "Gate 62 RLS migration file",
    ))
    checks.append(file_check(
        ROOT / "data" / "diagnostics" / "SUPABASE_GATE_62_RLS_ROLE_ACCESS_DONE.md",
        "Gate 62 done marker",
    ))
    checks.append(file_check(ADMIN_SRC / "lib" / "roleAccess.ts",     "roleAccess.ts exists"))
    checks.append(file_check(ADMIN_SRC / "lib" / "serverSupabaseAuth.ts", "serverSupabaseAuth.ts exists"))
    checks.append(file_check(ADMIN_SRC / "lib" / "browserSupabaseClient.ts", "browserSupabaseClient.ts exists"))
    checks.append(file_check(ADMIN_SRC / "app" / "login" / "page.tsx", "login page exists"))

    # ── .env.local not tracked ────────────────────────────────────────────────
    env_local_tracked_ts = git_ls_files("apps/admin/.env.local")
    env_local_tracked_root = git_ls_files(".env.local")
    env_tracked = bool(env_local_tracked_ts or env_local_tracked_root)
    summary["env_local_tracked"] = env_tracked
    checks.append(
        _fail(".env.local not tracked by git", f"TRACKED: {env_local_tracked_ts + env_local_tracked_root}")
        if env_tracked else
        _pass(".env.local not tracked by git", "clean — not in git")
    )

    env_prod_tracked = git_ls_files(".env.production")
    summary["env_production_tracked"] = bool(env_prod_tracked)
    checks.append(
        _fail(".env.production not tracked by git", f"TRACKED: {env_prod_tracked}")
        if env_prod_tracked else
        _pass(".env.production not tracked by git", "clean — not in git")
    )

    # ── Service role key in 'use client' files (true browser leaks) ──────────
    # Server components and API routes may safely check Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY)
    # to report key presence. Only 'use client' files are true browser-bundle leaks.
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
    service_role_exposed = bool(use_client_leaks)
    summary["service_role_exposed_to_client"] = service_role_exposed
    checks.append(
        _fail("service role key not in 'use client' browser components", f"LEAK: {use_client_leaks}")
        if use_client_leaks else
        _pass("service role key not in 'use client' browser components", "clean")
    )

    # ── browserSupabaseClient.ts must not touch service role ─────────────────
    browser_client = ADMIN_SRC / "lib" / "browserSupabaseClient.ts"
    browser_client_leak = (
        browser_client.exists()
        and "SUPABASE_SERVICE_ROLE_KEY" in browser_client.read_text(encoding="utf-8", errors="ignore")
    )
    checks.append(
        _fail("service role key not in browserSupabaseClient.ts", "LEAK in browser client module")
        if browser_client_leak else
        _pass("service role key not in browserSupabaseClient.ts", "clean")
    )

    # ── No NEXT_PUBLIC_SERVICE_ROLE style leaks ───────────────────────────────
    next_public_leaks = scan_files_for_pattern(
        r"NEXT_PUBLIC_SUPABASE_SERVICE_ROLE",
        "*.{ts,tsx,js,jsx,json}",
        set(),
    )
    checks.append(
        _fail("no NEXT_PUBLIC_SUPABASE_SERVICE_ROLE variable", f"FOUND: {next_public_leaks[:3]}")
        if next_public_leaks else
        _pass("no NEXT_PUBLIC_SUPABASE_SERVICE_ROLE variable", "clean")
    )

    # ── No raw API keys committed ─────────────────────────────────────────────
    openai_key_leaks = scan_files_for_pattern(r"sk-[A-Za-z0-9]{30,}", "*.{ts,tsx,py,env}", set())
    openai_key_leaks = [f for f in openai_key_leaks if ".env.example" not in f]
    checks.append(
        _fail("no OpenAI/Anthropic API key pattern (sk-...)", f"FOUND in: {openai_key_leaks[:3]}")
        if openai_key_leaks else
        _pass("no OpenAI/Anthropic API key pattern", "clean")
    )

    # ── No raw Cambridge PDF referenced from app routes ───────────────────────
    raw_pdf_refs = []
    for f in ADMIN_SRC.rglob("*.{ts,tsx}"):
        if any(p in (".next", "node_modules") for p in f.parts):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r'data[/\\]raw[/\\].*\.pdf', content, re.IGNORECASE):
            raw_pdf_refs.append(str(f.relative_to(ROOT)))
    summary["raw_cambridge_pdf_exposed"] = bool(raw_pdf_refs)
    checks.append(
        _fail("no raw Cambridge PDF path referenced in app routes", f"FOUND: {raw_pdf_refs[:3]}")
        if raw_pdf_refs else
        _pass("no raw Cambridge PDF path referenced in app routes", "clean")
    )

    # ── data/raw not imported by admin build ──────────────────────────────────
    data_raw_imports = scan_files_for_pattern(r'["\']\.\..*data[/\\]raw', "*.{ts,tsx}", set())
    checks.append(
        _warn("data/raw not imported by admin app", f"imports found: {data_raw_imports[:3]}")
        if data_raw_imports else
        _pass("data/raw not imported by admin app", "clean")
    )

    # ── Production env template checks ───────────────────────────────────────
    env_template = ROOT / ".env.production.example"
    if env_template.exists():
        content = env_template.read_text(encoding="utf-8")
        has_real_service_role = bool(re.search(r"SUPABASE_SERVICE_ROLE_KEY=ey[A-Za-z0-9+/]{10,}", content))
        checks.append(
            _fail("production env template has no real service role value",
                  "FOUND real-looking service role key in template!")
            if has_real_service_role else
            _pass("production env template has no real service role value", "clean — placeholders only")
        )
        checks.append(
            _pass("production env template has QA_CONTENT_SOURCE=live_supabase")
            if "QA_CONTENT_SOURCE=live_supabase" in content else
            _fail("production env template has QA_CONTENT_SOURCE=live_supabase",
                  "not found in template")
        )
        checks.append(
            _pass("production env template has QA_AUTH_DEMO_FALLBACK=false")
            if "QA_AUTH_DEMO_FALLBACK=false" in content else
            _fail("production env template has QA_AUTH_DEMO_FALLBACK=false",
                  "not found in template")
        )
    else:
        checks.append(_skip("production env template content checks", ".env.production.example not found"))

    # ── Global summary ────────────────────────────────────────────────────────
    summary.setdefault("env_local_tracked",           False)
    summary.setdefault("service_role_exposed_to_client", service_role_exposed)
    summary.setdefault("raw_cambridge_pdf_exposed",   bool(raw_pdf_refs))
    summary.setdefault("env_production_tracked",      False)

    return checks, summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Gate 63 -- Production Readiness Check")
    print("-" * 50)

    checks, summary = run_checks()

    pass_count = sum(1 for c in checks if c["status"] == "PASS")
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    warn_count = sum(1 for c in checks if c["status"] == "WARN")
    skip_count = sum(1 for c in checks if c["status"] == "SKIP")

    for c in checks:
        icon = "+" if c["status"] == "PASS" else ("!" if c["status"] == "FAIL" else ("~" if c["status"] == "WARN" else "?"))
        print(f"  {icon} [{c['status']:4}] {c['label']}")
        if c["status"] != "PASS":
            print(f"          {c['detail']}")

    print("\n" + "-" * 50)
    print(f"PASS: {pass_count}  FAIL: {fail_count}  WARN: {warn_count}  SKIP: {skip_count}  TOTAL: {len(checks)}")

    security_ok = (
        not summary.get("service_role_exposed_to_client")
        and not summary.get("env_local_tracked")
        and not summary.get("raw_cambridge_pdf_exposed")
        and not summary.get("env_production_tracked")
    )
    overall = "passed" if fail_count == 0 and security_ok else ("needs_review" if fail_count == 0 else "failed")
    print(f"Overall: {overall}")

    report = {
        "gate": "63",
        "title": "Production Readiness Check v1",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "overall_status": overall,
        "pass_count":  pass_count,
        "fail_count":  fail_count,
        "warn_count":  warn_count,
        "skip_count":  skip_count,
        "total_checks": len(checks),
        "security_summary": {
            "service_role_exposed_to_client": summary.get("service_role_exposed_to_client", False),
            "env_local_tracked":             summary.get("env_local_tracked", False),
            "raw_cambridge_pdf_exposed":     summary.get("raw_cambridge_pdf_exposed", False),
            "env_production_tracked":        summary.get("env_production_tracked", False),
        },
        "checks": checks,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report:  {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
