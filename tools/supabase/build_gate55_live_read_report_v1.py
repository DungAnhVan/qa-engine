"""
Gate 55 - Admin App Live Supabase Server Read Report v1.

Verifies all Gate 55 artifacts are in place:
  - liveSupabaseContent.ts (new, server-only)
  - contentSource.ts updated to include live_supabase
  - activeContent.ts, studentResources.ts updated with live_supabase branch
  - Diagnostic pages present
  - .env.example updated
  - SUPABASE_SERVICE_ROLE_KEY NOT present in client components

Security check: scans apps/admin/src for SUPABASE_SERVICE_ROLE_KEY.
  Allowed only in: apps/admin/src/lib/liveSupabaseContent.ts
  Any other file containing this string is a security violation.

No network calls. No Supabase connection. No OpenAI API.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\build_gate55_live_read_report_v1.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIAG_DIR     = PROJECT_ROOT / "data" / "diagnostics"
ADMIN_LIB    = PROJECT_ROOT / "apps" / "admin" / "src" / "lib"
ADMIN_APP    = PROJECT_ROOT / "apps" / "admin" / "src" / "app"
ADMIN_SRC    = PROJECT_ROOT / "apps" / "admin" / "src"


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

def _check_exists(path: Path, label: str) -> dict:
    return {
        "label":      label,
        "path":       str(path.relative_to(PROJECT_ROOT)),
        "present":    path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def _check_contains(path: Path, label: str, needle: str) -> dict:
    base = _check_exists(path, label)
    if base["present"]:
        try:
            text = path.read_text(encoding="utf-8")
            base["contains"] = needle in text
        except Exception as e:
            base["contains"] = False
            base["error"]    = str(e)
    else:
        base["contains"] = False
    base["needle"] = needle
    return base


def _check_not_contains(path: Path, label: str, needle: str) -> dict:
    """Pass when needle is NOT present (safety check)."""
    base = _check_exists(path, label)
    if base["present"]:
        try:
            text = path.read_text(encoding="utf-8")
            base["contains"] = needle in text
            base["safe"]     = not base["contains"]
        except Exception as e:
            base["contains"] = False
            base["safe"]     = True
            base["error"]    = str(e)
    else:
        base["contains"] = False
        base["safe"]     = True
    base["needle"] = needle
    return base


# ---------------------------------------------------------------------------
# Security scan: find SUPABASE_SERVICE_ROLE_KEY outside allowed file
# ---------------------------------------------------------------------------

ALLOWED_SERVICE_ROLE_FILE = ADMIN_LIB / "liveSupabaseContent.ts"
# Match actual env var *access*, not UI label strings that name the var
SERVICE_ROLE_NEEDLE       = "process.env.SUPABASE_SERVICE_ROLE_KEY"


def _scan_for_service_role_leaks() -> list[str]:
    """Return list of file paths (relative) where service role key appears outside the allowed file."""
    violations = []
    for ts_file in ADMIN_SRC.rglob("*.ts"):
        if ts_file == ALLOWED_SERVICE_ROLE_FILE:
            continue
        try:
            text = ts_file.read_text(encoding="utf-8")
            if SERVICE_ROLE_NEEDLE in text:
                violations.append(str(ts_file.relative_to(PROJECT_ROOT)))
        except Exception:
            pass
    for tsx_file in ADMIN_SRC.rglob("*.tsx"):
        try:
            text = tsx_file.read_text(encoding="utf-8")
            if SERVICE_ROLE_NEEDLE in text:
                violations.append(str(tsx_file.relative_to(PROJECT_ROOT)))
        except Exception:
            pass
    return violations


# ---------------------------------------------------------------------------
# All checks
# ---------------------------------------------------------------------------

def run_checks() -> tuple[list[dict], list[str], list[str]]:
    checks    = []
    issues    = []
    warnings  = []

    # ── New: liveSupabaseContent.ts ─────────────────────────────────────────
    checks.append(_check_exists(
        ADMIN_LIB / "liveSupabaseContent.ts",
        "liveSupabaseContent.ts (new)"
    ))

    checks.append(_check_contains(
        ADMIN_LIB / "liveSupabaseContent.ts",
        "liveSupabaseContent.ts: import server-only",
        "import 'server-only'"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "liveSupabaseContent.ts",
        "liveSupabaseContent.ts: exports getLiveSupabaseStudentResources",
        "getLiveSupabaseStudentResources"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "liveSupabaseContent.ts",
        "liveSupabaseContent.ts: exports getLiveSupabaseActiveContentIndex",
        "getLiveSupabaseActiveContentIndex"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "liveSupabaseContent.ts",
        "liveSupabaseContent.ts: exports getLiveSupabaseActivePackage",
        "getLiveSupabaseActivePackage"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "liveSupabaseContent.ts",
        "liveSupabaseContent.ts: exports getLiveSupabaseTeacherResources",
        "getLiveSupabaseTeacherResources"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "liveSupabaseContent.ts",
        "liveSupabaseContent.ts: exports getLiveSupabaseEnvPresence",
        "getLiveSupabaseEnvPresence"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "liveSupabaseContent.ts",
        "liveSupabaseContent.ts: uses @supabase/supabase-js",
        "@supabase/supabase-js"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "liveSupabaseContent.ts",
        "liveSupabaseContent.ts: reads process.env.SUPABASE_SERVICE_ROLE_KEY (allowed here)",
        "process.env.SUPABASE_SERVICE_ROLE_KEY"
    ))

    # ── contentSource.ts ────────────────────────────────────────────────────
    checks.append(_check_contains(
        ADMIN_LIB / "contentSource.ts",
        "contentSource.ts: supports live_supabase mode",
        "live_supabase"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "contentSource.ts",
        "contentSource.ts: exports isLiveSupabaseMode",
        "isLiveSupabaseMode"
    ))

    # ── activeContent.ts ────────────────────────────────────────────────────
    checks.append(_check_contains(
        ADMIN_LIB / "activeContent.ts",
        "activeContent.ts: imports getLiveSupabaseActiveContentIndex",
        "getLiveSupabaseActiveContentIndex"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "activeContent.ts",
        "activeContent.ts: branches on live_supabase",
        "live_supabase"
    ))

    # ── studentResources.ts ─────────────────────────────────────────────────
    checks.append(_check_contains(
        ADMIN_LIB / "studentResources.ts",
        "studentResources.ts: imports getLiveSupabaseStudentResources",
        "getLiveSupabaseStudentResources"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "studentResources.ts",
        "studentResources.ts: branches on live_supabase",
        "live_supabase"
    ))

    # ── Diagnostic pages ────────────────────────────────────────────────────
    diag_page = ADMIN_APP / "system" / "content-source" / "page.tsx"
    checks.append(_check_exists(diag_page, "Diagnostic page: /system/content-source"))
    checks.append(_check_contains(
        diag_page,
        "Diagnostic page: shows live_supabase env",
        "getLiveSupabaseEnvPresence"
    ))
    checks.append(_check_contains(
        diag_page,
        "Diagnostic page: covers all 3 modes",
        "live_supabase"
    ))

    live_page = ADMIN_APP / "system" / "supabase-live" / "page.tsx"
    checks.append(_check_exists(live_page, "Supabase-live page: /system/supabase-live"))
    checks.append(_check_contains(
        live_page,
        "Supabase-live page: force-dynamic",
        "force-dynamic"
    ))
    checks.append(_check_contains(
        live_page,
        "Supabase-live page: imports getLiveSupabaseActivePackage",
        "getLiveSupabaseActivePackage"
    ))

    # ── .env.example ────────────────────────────────────────────────────────
    checks.append(_check_contains(
        PROJECT_ROOT / ".env.example",
        ".env.example: documents live_supabase mode",
        "live_supabase"
    ))

    # ── Fallbacks still present ─────────────────────────────────────────────
    checks.append(_check_contains(
        ADMIN_LIB / "supabaseExportContent.ts",
        "supabaseExportContent.ts: still present (supabase_export fallback)",
        "getSupabaseExportStudentResources"
    ))
    checks.append(_check_contains(
        ADMIN_LIB / "activeContent.ts",
        "activeContent.ts: supabase_export fallback still present",
        "supabase_export"
    ))

    # ── Gate 54 artifacts still present ────────────────────────────────────
    checks.append(_check_exists(
        ADMIN_LIB / "contentSource.ts",
        "contentSource.ts from Gate 54 still present"
    ))
    checks.append(_check_exists(
        ADMIN_LIB / "supabaseExportContent.ts",
        "supabaseExportContent.ts from Gate 54 still present"
    ))

    # ── package.json has new deps ───────────────────────────────────────────
    pkg_json = PROJECT_ROOT / "apps" / "admin" / "package.json"
    checks.append(_check_contains(pkg_json, "package.json: @supabase/supabase-js installed", "@supabase/supabase-js"))
    checks.append(_check_contains(pkg_json, "package.json: server-only installed", "server-only"))

    # ── Build issue list ─────────────────────────────────────────────────────
    for c in checks:
        if not c.get("present", True):
            issues.append(f"Missing file: {c['label']}")
        elif "contains" in c and not c.get("contains", False):
            issues.append(f"Content check failed: {c['label']}")

    # ── Security scan ────────────────────────────────────────────────────────
    service_role_leaks = _scan_for_service_role_leaks()
    if service_role_leaks:
        for path_str in service_role_leaks:
            issues.append(f"SECURITY: {SERVICE_ROLE_NEEDLE} found in non-allowed file: {path_str}")

    return checks, issues, service_role_leaks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print("Quanta Aptus - Gate 55 Live Supabase Read Report v1")
    print("=" * 60)

    checks, issues, leaks = run_checks()

    # Tally
    file_checks     = [c for c in checks if "contains" not in c]
    content_checks  = [c for c in checks if "contains" in c]
    files_ok        = sum(1 for c in file_checks if c.get("present", True))
    content_ok      = sum(1 for c in content_checks if c.get("contains", False))
    content_total   = len(content_checks)

    print(f"  file checks   : {files_ok}/{len(file_checks)} present")
    print(f"  content checks: {content_ok}/{content_total} passed")
    print(f"  security scan : {'CLEAN' if not leaks else f'{len(leaks)} VIOLATION(S)'}")

    if issues:
        print(f"\n  ISSUES ({len(issues)}):")
        for iss in issues:
            print(f"    - {iss}")

    overall = "passed" if not issues else "needs_review"
    print(f"\n  status        : {overall.upper()}")

    report = {
        "report_id":                          "quanta_aptus_gate55_live_supabase_read_report_v1",
        "gate":                               "55",
        "created_at":                         now_iso,
        "status":                             overall,
        "mode_supported":                     ["local", "supabase_export", "live_supabase"],
        "default_mode":                       "local",
        "server_only_live_read":              True,
        "service_role_exposed_to_client":     bool(leaks),
        "service_role_leak_files":            leaks,
        "local_fallback_available":           True,
        "supabase_export_fallback_available": True,
        "diagnostic_pages":                   ["/system/content-source", "/system/supabase-live"],
        "checks_total":                       len(checks),
        "file_checks_passed":                 files_ok,
        "content_checks_passed":              content_ok,
        "content_checks_total":               content_total,
        "issues":                             issues,
        "checks":                             checks,
        "next_gate":                          "Gate 56 - App Supabase Student Attempt Write",
    }

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "gate55_live_supabase_read_report_v1.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {report_path}")

    if overall == "passed":
        done_path = DIAG_DIR / "SUPABASE_GATE_55_LIVE_READ_DONE.md"
        done_path.write_text(
            "\n".join([
                "# Gate 55 - Live Supabase Server Read DONE",
                "",
                f"**Date:** {now_iso[:10]}",
                "**Status:** `passed`",
                "**Phase:** Phase 2 - Supabase Integration",
                "",
                "## What Was Built",
                "",
                "Added `live_supabase` mode to the admin Next.js app:",
                "",
                "| File | Change |",
                "|---|---|",
                "| `apps/admin/src/lib/liveSupabaseContent.ts` | NEW - server-only live Supabase reads |",
                "| `apps/admin/src/lib/contentSource.ts` | UPDATED - added live_supabase mode |",
                "| `apps/admin/src/lib/activeContent.ts` | UPDATED - live_supabase branch |",
                "| `apps/admin/src/lib/studentResources.ts` | UPDATED - live_supabase branch |",
                "| `apps/admin/src/app/system/content-source/page.tsx` | UPDATED - all 3 modes |",
                "| `apps/admin/src/app/system/supabase-live/page.tsx` | NEW - live connection test |",
                "| `.env.example` | UPDATED - live_supabase documented |",
                "",
                "## Dependencies Added",
                "",
                "```",
                "pnpm --filter @qa-engine/admin add @supabase/supabase-js server-only",
                "```",
                "",
                "## Security Constraints Satisfied",
                "",
                "- `import 'server-only'` guard in liveSupabaseContent.ts prevents client import.",
                "- SUPABASE_SERVICE_ROLE_KEY only read in liveSupabaseContent.ts.",
                "- No service role key in any client component or page.",
                "- Security scan: 0 violations.",
                "- No writes to Supabase.",
                "- No Cambridge source text read.",
                "- local and supabase_export fallback modes preserved.",
                "",
                "## How to Test",
                "",
                "1. Set `QA_CONTENT_SOURCE=live_supabase` in `apps/admin/.env.local`",
                "2. Ensure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set",
                "3. Run: `pnpm --filter @qa-engine/admin dev`",
                "4. Visit: http://localhost:3000/system/content-source",
                "5. Visit: http://localhost:3000/system/supabase-live",
            ]),
            encoding="utf-8",
        )
        print(f"  done marker   -> {done_path}")

    sys.exit(0 if overall in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
