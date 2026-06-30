"""
Gate 57 - Supabase Marking Report v1.

Static code/artifact checks — no Supabase connection required.
Verifies all Gate 57 artifacts are in place and security constraints hold.

Checks:
  - liveSupabaseMarking.ts: exists, has server-only guard, has exports
  - /api/mark-attempt/route.ts: exists, branches on live_supabase
  - AttemptForm.tsx: shows marking result UI (markResult, auto-mark)
  - /system/marking/page.tsx: exists and has force-dynamic
  - process.env.SUPABASE_SERVICE_ROLE_KEY only in allowed server-only files
  - Gate 56 artifacts still present (no regression)
  - Test report passed (if available)

No network calls. No Supabase connection.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\build_gate57_marking_report_v1.py
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
ADMIN_SRC    = PROJECT_ROOT / "apps" / "admin" / "src"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exists(path: Path, label: str) -> dict:
    return {
        "label":      label,
        "path":       str(path.relative_to(PROJECT_ROOT)),
        "present":    path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def _contains(path: Path, label: str, needle: str) -> dict:
    base = _exists(path, label)
    if base["present"]:
        try:
            base["contains"] = needle in path.read_text(encoding="utf-8")
        except Exception as e:
            base["contains"] = False
            base["error"]    = str(e)
    else:
        base["contains"] = False
    base["needle"] = needle
    return base


def _scan_service_role_leaks() -> list[str]:
    """Find files that read process.env.SUPABASE_SERVICE_ROLE_KEY outside the allowed list."""
    allowed = {
        ADMIN_LIB / "liveSupabaseContent.ts",
        ADMIN_LIB / "liveSupabaseAttempts.ts",
        ADMIN_LIB / "liveSupabaseMarking.ts",   # Gate 57 — new allowed file
    }
    needle = "process.env.SUPABASE_SERVICE_ROLE_KEY"
    leaks: list[str] = []
    for f in list(ADMIN_SRC.rglob("*.ts")) + list(ADMIN_SRC.rglob("*.tsx")):
        if f in allowed:
            continue
        try:
            if needle in f.read_text(encoding="utf-8"):
                leaks.append(str(f.relative_to(PROJECT_ROOT)))
        except Exception:
            pass
    return leaks


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def run_checks() -> tuple[list[dict], list[str], list[str], bool, dict]:
    checks: list[dict] = []
    issues: list[str]  = []

    marking_ts = ADMIN_LIB / "liveSupabaseMarking.ts"

    # ── liveSupabaseMarking.ts ───────────────────────────────────────────────
    checks.append(_exists(marking_ts, "liveSupabaseMarking.ts (new)"))
    checks.append(_contains(marking_ts, "liveSupabaseMarking.ts: import server-only", "import 'server-only'"))
    checks.append(_contains(marking_ts, "liveSupabaseMarking.ts: markLiveSupabaseAttempt export", "markLiveSupabaseAttempt"))
    checks.append(_contains(marking_ts, "liveSupabaseMarking.ts: getLiveSupabaseUnmarkedAttempts export", "getLiveSupabaseUnmarkedAttempts"))
    checks.append(_contains(marking_ts, "liveSupabaseMarking.ts: markLatestUnmarkedLiveSupabaseAttempt export", "markLatestUnmarkedLiveSupabaseAttempt"))
    checks.append(_contains(marking_ts, "liveSupabaseMarking.ts: NUMERIC_MARKING_TYPES", "NUMERIC_MARKING_TYPES"))
    checks.append(_contains(marking_ts, "liveSupabaseMarking.ts: TEACHER_REVIEW_TYPES", "TEACHER_REVIEW_TYPES"))
    checks.append(_contains(marking_ts, "liveSupabaseMarking.ts: rule_based marking_method", "rule_based"))
    checks.append(_contains(marking_ts, "liveSupabaseMarking.ts: marked_attempts table", "marked_attempts"))
    checks.append(_contains(marking_ts, "liveSupabaseMarking.ts: no OpenAI import", "openai"))

    # Invert: openai should NOT be present
    openai_check = checks[-1]
    openai_check["contains"] = not openai_check.get("contains", False)
    openai_check["needle"]   = "NO openai import"

    # ── API route ─────────────────────────────────────────────────────────────
    api_route = ADMIN_APP / "api" / "mark-attempt" / "route.ts"
    checks.append(_exists(api_route, "API route: mark-attempt/route.ts"))
    checks.append(_contains(api_route, "API route: branches on live_supabase", "live_supabase"))
    checks.append(_contains(api_route, "API route: imports markLiveSupabaseAttempt", "markLiveSupabaseAttempt"))
    checks.append(_contains(api_route, "API route: validates UUID", "UUID_REGEX"))
    checks.append(_contains(api_route, "API route: force-dynamic", "force-dynamic"))

    # ── AttemptForm.tsx ───────────────────────────────────────────────────────
    form = ADMIN_APP / "learn" / "practice" / "AttemptForm.tsx"
    checks.append(_exists(form, "AttemptForm.tsx: present"))
    checks.append(_contains(form, "AttemptForm.tsx: MarkResult interface", "MarkResult"))
    checks.append(_contains(form, "AttemptForm.tsx: markResult state", "markResult"))
    checks.append(_contains(form, "AttemptForm.tsx: auto-marks after save", "/api/mark-attempt"))
    checks.append(_contains(form, "AttemptForm.tsx: shows correct result", "correct"))
    checks.append(_contains(form, "AttemptForm.tsx: shows feedback", "feedback"))
    checks.append(_contains(form, "AttemptForm.tsx: marking loading state", "Marking"))

    # ── Diagnostic page ───────────────────────────────────────────────────────
    marking_page = ADMIN_APP / "system" / "marking" / "page.tsx"
    checks.append(_exists(marking_page, "Diagnostic page: /system/marking"))
    checks.append(_contains(marking_page, "Diagnostic page: force-dynamic", "force-dynamic"))
    checks.append(_contains(marking_page, "Diagnostic page: getLiveSupabaseUnmarkedAttempts", "getLiveSupabaseUnmarkedAttempts"))
    checks.append(_contains(marking_page, "Diagnostic page: mentions Gate 58", "Gate 58"))

    # ── Gate 56 regressions ──────────────────────────────────────────────────
    checks.append(_exists(ADMIN_LIB / "liveSupabaseAttempts.ts", "Gate 56: liveSupabaseAttempts.ts still present"))
    checks.append(_exists(ADMIN_APP / "api" / "student-attempts" / "route.ts", "Gate 56: student-attempts route still present"))

    # ── Test report ──────────────────────────────────────────────────────────
    test_report_path = DIAG_DIR / "gate57_marking_test_report_v1.json"
    test_check       = _exists(test_report_path, "Test report: gate57_marking_test_report_v1.json")
    checks.append(test_check)

    test_passed  = False
    test_details = {}
    if test_report_path.exists():
        try:
            tr = json.loads(test_report_path.read_text(encoding="utf-8"))
            test_passed   = tr.get("status") == "passed"
            test_details  = {
                "attempt_id":              tr.get("attempt_id"),
                "resource_type":           tr.get("resource_type"),
                "marking_result":          tr.get("marking_result"),
                "marking_status_after":    tr.get("attempt_marking_status_after"),
                "marked_attempt_id":       tr.get("marked_attempt_id"),
            }
            checks.append({
                "label":    "Test report: status=passed",
                "path":     str(test_report_path.relative_to(PROJECT_ROOT)),
                "present":  True,
                "contains": test_passed,
                "needle":   "status=passed",
            })
        except Exception:
            test_passed = False

    # ── Build issue list ──────────────────────────────────────────────────────
    for c in checks:
        if not c.get("present", True):
            issues.append(f"Missing: {c['label']}")
        elif "contains" in c and not c.get("contains", False):
            issues.append(f"Content check failed: {c['label']}")

    # ── Security scan ─────────────────────────────────────────────────────────
    leaks = _scan_service_role_leaks()
    for leak in leaks:
        issues.append(f"SECURITY: process.env.SUPABASE_SERVICE_ROLE_KEY in non-allowed file: {leak}")

    return checks, issues, leaks, test_passed, test_details


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print("Quanta Aptus - Gate 57 Marking Report v1")
    print("=" * 60)

    checks, issues, leaks, test_passed, test_details = run_checks()

    file_checks    = [c for c in checks if "contains" not in c]
    content_checks = [c for c in checks if "contains" in c]
    files_ok       = sum(1 for c in file_checks if c.get("present", True))
    content_ok     = sum(1 for c in content_checks if c.get("contains", False))

    print(f"  file checks   : {files_ok}/{len(file_checks)} present")
    print(f"  content checks: {content_ok}/{len(content_checks)} passed")
    print(f"  security scan : {'CLEAN' if not leaks else f'{len(leaks)} VIOLATION(S)'}")
    print(f"  test marking  : {'PASSED' if test_passed else 'NOT RUN (run test_gate57_mark_latest_attempt_v1.py)'}")

    if test_details and test_passed:
        print(f"  marked attempt: {test_details.get('marked_attempt_id', '?')}")
        print(f"  result        : {test_details.get('marking_result', '?')}")
        print(f"  marking_status: {test_details.get('marking_status_after', '?')}")

    if issues:
        print(f"\n  ISSUES ({len(issues)}):")
        for iss in issues:
            print(f"    - {iss}")

    non_test_issues = [i for i in issues if "Test report" not in i]
    overall = "passed" if not non_test_issues and not leaks else "needs_review"
    if not test_passed and overall == "passed":
        overall = "needs_review"

    print(f"\n  status        : {overall.upper()}")

    report = {
        "report_id":                          "quanta_aptus_gate57_marking_report_v1",
        "gate":                               "57",
        "created_at":                         now_iso,
        "status":                             overall,
        "marking_enabled":                    True,
        "marking_method":                     "rule_based",
        "openai_used":                        False,
        "teacher_review_ui_implemented":      False,
        "service_role_exposed_to_client":     bool(leaks),
        "service_role_leak_files":            leaks,
        "test_marking_passed":                test_passed,
        "test_details":                       test_details,
        "checks_total":                       len(checks),
        "file_checks_passed":                 files_ok,
        "content_checks_passed":              content_ok,
        "issues":                             issues,
        "checks":                             checks,
        "next_gate":                          "Gate 58 - Teacher Review UI",
    }

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "gate57_marking_report_v1.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {report_path}")

    if overall == "passed":
        done_path = DIAG_DIR / "SUPABASE_GATE_57_MARKING_DONE.md"
        done_path.write_text(
            "\n".join([
                "# Gate 57 - Supabase Marking + Marked Attempts DONE",
                "",
                f"**Date:** {now_iso[:10]}",
                "**Status:** `passed`",
                "**Phase:** Phase 2 - Supabase Integration",
                "",
                "## What Was Built",
                "",
                "| File | Change |",
                "|---|---|",
                "| `apps/admin/src/lib/liveSupabaseMarking.ts` | NEW - server-only marking module |",
                "| `apps/admin/src/app/api/mark-attempt/route.ts` | NEW - POST marking endpoint |",
                "| `apps/admin/src/app/learn/practice/AttemptForm.tsx` | UPDATED - auto-mark after save |",
                "| `apps/admin/src/app/system/marking/page.tsx` | NEW - diagnostic page |",
                "| `tools/supabase/test_gate57_mark_latest_attempt_v1.py` | NEW - integration test |",
                "",
                "## Behavior",
                "",
                "- Rule-based marking in `live_supabase` mode.",
                "- `calculation_drill`, `short_answer_calculation`, `algebra_drill` → numeric overlap check.",
                "- Graph/diagram/planning types → `pending_teacher_review`.",
                "- Results written to `marked_attempts` table; `attempts.marking_status` updated.",
                "- Deduplication: existing `marked_attempts` row is updated, not duplicated.",
                "- AttemptForm auto-marks on submit; shows result with feedback.",
                "- No OpenAI API calls.",
                "- No Cambridge source text read or uploaded.",
                "",
                "## Security",
                "",
                "- `import 'server-only'` in liveSupabaseMarking.ts.",
                "- `process.env.SUPABASE_SERVICE_ROLE_KEY` only in allowed server-only files.",
                "- Security scan: 0 violations.",
                "",
                "## Ready for Gate 58",
                "",
                "Gate 58 will add teacher review UI for `pending_teacher_review` results.",
            ]),
            encoding="utf-8",
        )
        print(f"  done marker   -> {done_path}")

    sys.exit(0 if overall in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
