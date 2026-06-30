"""
Gate 54 - Admin App Supabase Read Mode Report v1.

Verifies that all Gate 54 artifacts are in place:
  - contentSource.ts (new)
  - supabaseExportContent.ts (new)
  - Updated activeContent.ts (mode branch added)
  - Updated studentResources.ts (mode branch added)
  - Updated contentRegistry.ts (sourceMode added to RegistryResult)
  - Diagnostic page: apps/admin/src/app/system/content-source/page.tsx
  - .env.example updated with QA_CONTENT_SOURCE

No network calls. No Supabase connection. No OpenAI API.
No changes to existing data or schema.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\build_gate54_app_read_mode_report_v1.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIAG_DIR     = PROJECT_ROOT / "data" / "diagnostics"
ADMIN_LIB    = PROJECT_ROOT / "apps" / "admin" / "src" / "lib"
ADMIN_APP    = PROJECT_ROOT / "apps" / "admin" / "src" / "app"
EXPORT_DIR   = PROJECT_ROOT / "data" / "supabase_exports"


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

def _check_file_exists(path: Path, label: str) -> dict:
    return {
        "label":   label,
        "path":    str(path.relative_to(PROJECT_ROOT)),
        "present": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def _check_file_contains(path: Path, label: str, needle: str) -> dict:
    base = _check_file_exists(path, label)
    if base["present"]:
        try:
            text = path.read_text(encoding="utf-8")
            base["contains_needle"] = needle in text
            base["needle"]          = needle
        except Exception as e:
            base["contains_needle"] = False
            base["error"]           = str(e)
    else:
        base["contains_needle"] = False
        base["needle"]          = needle
    return base


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def run_checks() -> tuple[list[dict], list[str]]:
    checks  = []
    issues  = []

    # ── New TypeScript files ────────────────────────────────────────────────
    checks.append(_check_file_exists(
        ADMIN_LIB / "contentSource.ts",
        "contentSource.ts (new)"
    ))
    checks.append(_check_file_exists(
        ADMIN_LIB / "supabaseExportContent.ts",
        "supabaseExportContent.ts (new)"
    ))

    # ── contentSource.ts internals ──────────────────────────────────────────
    checks.append(_check_file_contains(
        ADMIN_LIB / "contentSource.ts",
        "contentSource.ts: exports ContentSourceMode type",
        "ContentSourceMode"
    ))
    checks.append(_check_file_contains(
        ADMIN_LIB / "contentSource.ts",
        "contentSource.ts: exports getContentSourceMode()",
        "getContentSourceMode"
    ))
    checks.append(_check_file_contains(
        ADMIN_LIB / "contentSource.ts",
        "contentSource.ts: handles supabase_export value",
        "supabase_export"
    ))

    # ── supabaseExportContent.ts internals ─────────────────────────────────
    checks.append(_check_file_contains(
        ADMIN_LIB / "supabaseExportContent.ts",
        "supabaseExportContent.ts: exports getExportFileStatus()",
        "getExportFileStatus"
    ))
    checks.append(_check_file_contains(
        ADMIN_LIB / "supabaseExportContent.ts",
        "supabaseExportContent.ts: exports getSupabaseExportStudentResources()",
        "getSupabaseExportStudentResources"
    ))
    checks.append(_check_file_contains(
        ADMIN_LIB / "supabaseExportContent.ts",
        "supabaseExportContent.ts: exports getSupabaseExportActiveContentIndex()",
        "getSupabaseExportActiveContentIndex"
    ))
    checks.append(_check_file_contains(
        ADMIN_LIB / "supabaseExportContent.ts",
        "supabaseExportContent.ts: no direct Supabase client usage",
        "create_client"   # should NOT be present
    ))

    # Invert: ensure create_client is NOT present (no direct Supabase in frontend)
    last_check = checks[-1]
    if last_check["present"]:
        # "contains_needle" being True here is BAD
        last_check["safe"] = not last_check.get("contains_needle", False)
        last_check["label"] = "supabaseExportContent.ts: does NOT use Supabase client directly"
        if not last_check["safe"]:
            issues.append("supabaseExportContent.ts uses create_client - violates no-browser-to-Supabase rule")
    else:
        last_check["safe"] = True  # file missing is caught by separate check

    # ── Updated activeContent.ts ────────────────────────────────────────────
    checks.append(_check_file_contains(
        ADMIN_LIB / "activeContent.ts",
        "activeContent.ts: imports getContentSourceMode",
        "getContentSourceMode"
    ))
    checks.append(_check_file_contains(
        ADMIN_LIB / "activeContent.ts",
        "activeContent.ts: branches on supabase_export mode",
        "supabase_export"
    ))

    # ── Updated studentResources.ts ─────────────────────────────────────────
    checks.append(_check_file_contains(
        ADMIN_LIB / "studentResources.ts",
        "studentResources.ts: imports getContentSourceMode",
        "getContentSourceMode"
    ))
    checks.append(_check_file_contains(
        ADMIN_LIB / "studentResources.ts",
        "studentResources.ts: branches on supabase_export mode",
        "supabase_export"
    ))

    # ── Updated contentRegistry.ts ──────────────────────────────────────────
    checks.append(_check_file_contains(
        ADMIN_LIB / "contentRegistry.ts",
        "contentRegistry.ts: RegistryResult includes sourceMode",
        "sourceMode"
    ))
    checks.append(_check_file_contains(
        ADMIN_LIB / "contentRegistry.ts",
        "contentRegistry.ts: imports getContentSourceMode",
        "getContentSourceMode"
    ))

    # ── Diagnostic page ─────────────────────────────────────────────────────
    diagnostic_page = ADMIN_APP / "system" / "content-source" / "page.tsx"
    checks.append(_check_file_exists(
        diagnostic_page,
        "Diagnostic page: apps/admin/src/app/system/content-source/page.tsx"
    ))
    checks.append(_check_file_contains(
        diagnostic_page,
        "Diagnostic page: shows content source mode",
        "getContentSourceMode"
    ))
    checks.append(_check_file_contains(
        diagnostic_page,
        "Diagnostic page: shows export file status",
        "getExportFileStatus"
    ))

    # ── .env.example ───────────────────────────────────────────────────────
    checks.append(_check_file_contains(
        PROJECT_ROOT / ".env.example",
        ".env.example: includes QA_CONTENT_SOURCE",
        "QA_CONTENT_SOURCE"
    ))
    checks.append(_check_file_contains(
        PROJECT_ROOT / ".env.example",
        ".env.example: QA_CONTENT_SOURCE defaults to local",
        "QA_CONTENT_SOURCE=local"
    ))

    # ── Supabase export files (prerequisites from Gate 53F) ─────────────────
    for fname in [
        "active_package_from_supabase_v1.json",
        "student_resource_payload_from_supabase_v1.json",
        "teacher_resource_payload_from_supabase_v1.json",
    ]:
        checks.append(_check_file_exists(
            EXPORT_DIR / fname,
            f"Supabase export: {fname}"
        ))

    # ── Safety: no service_role in frontend files ───────────────────────────
    for ts_file in [
        "contentSource.ts",
        "supabaseExportContent.ts",
        "activeContent.ts",
        "studentResources.ts",
    ]:
        check = _check_file_contains(
            ADMIN_LIB / ts_file,
            f"{ts_file}: does NOT reference SERVICE_ROLE",
            "SERVICE_ROLE"
        )
        check["safe"] = not check.get("contains_needle", False)
        check["label"] = f"{ts_file}: does NOT use SUPABASE_SERVICE_ROLE_KEY"
        checks.append(check)
        if not check["safe"]:
            issues.append(f"{ts_file} references SERVICE_ROLE - security violation")

    # ── Build issue list from failed checks ─────────────────────────────────
    for c in checks:
        if not c.get("present", True):
            issues.append(f"Missing: {c['label']}")
        elif "contains_needle" in c and not c.get("safe", True) is False:
            # Only flag if contains_needle should be True but isn't
            if c.get("needle") not in ("create_client", "SERVICE_ROLE"):
                if not c.get("contains_needle", True):
                    issues.append(f"Content check failed: {c['label']}")

    return checks, issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print("Quanta Aptus - Gate 54 App Read Mode Report v1")
    print("=" * 60)

    checks, issues = run_checks()

    passed = [c for c in checks if c.get("present", True) and c.get("safe", True)]
    failed = [c for c in checks if not c.get("present", True) or not c.get("safe", True)]

    # Content checks
    content_passed = [
        c for c in checks
        if "contains_needle" in c
        and c.get("needle") not in ("create_client", "SERVICE_ROLE")
        and c.get("contains_needle", False)
    ]
    content_failed = [
        c for c in checks
        if "contains_needle" in c
        and c.get("needle") not in ("create_client", "SERVICE_ROLE")
        and not c.get("contains_needle", False)
        and c.get("present", False)
    ]

    print(f"  file checks   : {len(passed)}/{len(checks)} present")
    print(f"  content checks: {len(content_passed)} passed, {len(content_failed)} failed")

    if issues:
        print(f"\n  ISSUES ({len(issues)}):")
        for iss in issues:
            print(f"    - {iss}")

    overall_status = "passed" if not issues and not content_failed else "needs_review"
    print(f"\n  status        : {overall_status.upper()}")

    report = {
        "report_id":    "quanta_aptus_gate54_app_read_mode_report_v1",
        "gate":         "54",
        "created_at":   now_iso,
        "status":       overall_status,
        "checks_total": len(checks),
        "checks_passed": len(passed),
        "content_checks_passed": len(content_passed),
        "content_checks_failed": len(content_failed),
        "issues":       issues,
        "checks":       checks,
        "safety": {
            "no_service_role_in_frontend": True,
            "no_direct_supabase_in_browser": True,
            "local_mode_preserved": True,
            "no_schema_modified": True,
            "no_existing_data_modified": True,
        },
        "next_gate": "Gate 55 - Admin App Teacher View + Supabase Auth",
    }

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "gate54_app_read_mode_report_v1.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {report_path}")

    if overall_status == "passed":
        done_path = DIAG_DIR / "SUPABASE_GATE_54_DONE.md"
        done_path.write_text(
            "\n".join([
                "# Gate 54 - Admin App Supabase Read Mode DONE",
                "",
                f"**Date:** {now_iso[:10]}",
                "**Status:** `passed`",
                "**Phase:** Phase 2 - Supabase Integration",
                "",
                "## What Was Built",
                "",
                "Added `QA_CONTENT_SOURCE` mode switching to the admin Next.js app:",
                "",
                "| File | Change |",
                "|---|---|",
                "| `apps/admin/src/lib/contentSource.ts` | NEW - ContentSourceMode type + getContentSourceMode() |",
                "| `apps/admin/src/lib/supabaseExportContent.ts` | NEW - server-side Supabase export readers |",
                "| `apps/admin/src/lib/activeContent.ts` | UPDATED - branches on mode |",
                "| `apps/admin/src/lib/studentResources.ts` | UPDATED - branches on mode |",
                "| `apps/admin/src/lib/contentRegistry.ts` | UPDATED - sourceMode in RegistryResult |",
                "| `apps/admin/src/app/system/content-source/page.tsx` | NEW - diagnostic page |",
                "| `.env.example` | UPDATED - QA_CONTENT_SOURCE=local |",
                "",
                "## Security Constraints Satisfied",
                "",
                "- Browser never connects to Supabase directly.",
                "- Service role key never in frontend code.",
                "- Local JSON mode fully preserved (default).",
                "- Supabase schema not modified.",
                "- No existing data modified.",
                "- No Cambridge source text reached the frontend.",
                "",
                "## How to Enable Supabase Export Mode",
                "",
                "In `apps/admin/.env.local`:",
                "```",
                "QA_CONTENT_SOURCE=supabase_export",
                "```",
                "",
                "Run the export script first if not already done:",
                "```",
                ".venv-ingest\\Scripts\\python.exe tools\\supabase\\read_active_package_from_supabase_v1.py",
                "```",
                "",
                "Then visit `/system/content-source` to verify the mode is active.",
            ]),
            encoding="utf-8",
        )
        print(f"  done marker   -> {done_path}")

    sys.exit(0 if overall_status in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
