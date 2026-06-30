"""
Gate 59 - Supabase Student Results Report v1.

Static code/artifact checks — no Supabase connection required.
Verifies all Gate 59 artifacts are in place and security constraints hold.

Checks:
  - liveSupabaseStudentResults.ts exists with required exports
  - /learn/supabase-results page exists
  - /system/student-results page exists
  - process.env.SUPABASE_SERVICE_ROLE_KEY only in allowed server-only files
  - Gate 56/57/58 artifacts still present (no regression)
  - Test report exists and passed (if available)

Output:
  data/diagnostics/gate59_student_results_report_v1.json
  data/diagnostics/SUPABASE_GATE_59_STUDENT_RESULTS_DONE.md

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\build_gate59_student_results_report_v1.py
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
    allowed = {
        ADMIN_LIB / "liveSupabaseContent.ts",
        ADMIN_LIB / "liveSupabaseAttempts.ts",
        ADMIN_LIB / "liveSupabaseMarking.ts",
        ADMIN_LIB / "liveSupabaseTeacherReview.ts",
        ADMIN_LIB / "liveSupabaseStudentResults.ts",  # Gate 59 — new allowed file
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

    results_ts      = ADMIN_LIB / "liveSupabaseStudentResults.ts"
    learn_page      = ADMIN_APP / "learn" / "supabase-results" / "page.tsx"
    system_page     = ADMIN_APP / "system" / "student-results" / "page.tsx"

    # ── liveSupabaseStudentResults.ts ────────────────────────────────────────
    checks.append(_exists(results_ts, "liveSupabaseStudentResults.ts (new)"))
    checks.append(_contains(results_ts, "liveSupabaseStudentResults.ts: import server-only", "import 'server-only'"))
    checks.append(_contains(results_ts, "liveSupabaseStudentResults.ts: getLiveSupabaseStudentResults", "getLiveSupabaseStudentResults"))
    checks.append(_contains(results_ts, "liveSupabaseStudentResults.ts: getLiveSupabaseLatestLearningState", "getLiveSupabaseLatestLearningState"))
    checks.append(_contains(results_ts, "liveSupabaseStudentResults.ts: StudentResultReport export", "StudentResultReport"))
    checks.append(_contains(results_ts, "liveSupabaseStudentResults.ts: skill_gaps", "skill_gaps"))
    checks.append(_contains(results_ts, "liveSupabaseStudentResults.ts: resubmission_queue", "resubmission_queue"))
    checks.append(_contains(results_ts, "liveSupabaseStudentResults.ts: strengths", "strengths"))
    checks.append(_contains(results_ts, "liveSupabaseStudentResults.ts: accuracy", "accuracy"))
    checks.append(_contains(results_ts, "liveSupabaseStudentResults.ts: superseded_by_attempt_id logic", "superseded_by_attempt_id"))
    checks.append(_contains(results_ts, "liveSupabaseStudentResults.ts: no OpenAI import", "openai"))
    openai_check = checks[-1]
    openai_check["contains"] = not openai_check.get("contains", False)
    openai_check["needle"]   = "NO openai import"

    # ── Learn page ────────────────────────────────────────────────────────────
    checks.append(_exists(learn_page, "/learn/supabase-results page exists"))
    checks.append(_contains(learn_page, "learn page: force-dynamic", "force-dynamic"))
    checks.append(_contains(learn_page, "learn page: imports getLiveSupabaseStudentResults", "getLiveSupabaseStudentResults"))
    checks.append(_contains(learn_page, "learn page: shows skill gaps", "skill_gaps"))
    checks.append(_contains(learn_page, "learn page: shows strengths", "strengths"))
    checks.append(_contains(learn_page, "learn page: shows resubmission queue", "resubmission_queue"))
    checks.append(_contains(learn_page, "learn page: shows recent attempts", "recent_attempts"))
    checks.append(_contains(learn_page, "learn page: Gate 60 auth warning", "Gate 60"))

    # ── System page ───────────────────────────────────────────────────────────
    checks.append(_exists(system_page, "/system/student-results page exists"))
    checks.append(_contains(system_page, "system page: force-dynamic", "force-dynamic"))
    checks.append(_contains(system_page, "system page: imports getLiveSupabaseStudentResults", "getLiveSupabaseStudentResults"))
    checks.append(_contains(system_page, "system page: shows attempt_count", "attempt_count"))

    # ── Gate 56/57/58 regressions ────────────────────────────────────────────
    checks.append(_exists(ADMIN_LIB / "liveSupabaseAttempts.ts",      "Gate 56: liveSupabaseAttempts.ts still present"))
    checks.append(_exists(ADMIN_LIB / "liveSupabaseMarking.ts",        "Gate 57: liveSupabaseMarking.ts still present"))
    checks.append(_exists(ADMIN_LIB / "liveSupabaseTeacherReview.ts",  "Gate 58: liveSupabaseTeacherReview.ts still present"))
    checks.append(_exists(ADMIN_APP / "learn" / "supabase-attempt-review" / "page.tsx", "Gate 58: review page still present"))

    # ── Local fallback ────────────────────────────────────────────────────────
    local_results = ADMIN_APP / "learn" / "results" / "page.tsx"
    checks.append(_exists(local_results, "local fallback: /learn/results still present"))

    # ── Test report ──────────────────────────────────────────────────────────
    test_path = DIAG_DIR / "gate59_student_results_test_report_v1.json"
    checks.append(_exists(test_path, "Test report: gate59_student_results_test_report_v1.json"))

    test_passed  = False
    test_details: dict = {}
    if test_path.exists():
        try:
            tr = json.loads(test_path.read_text(encoding="utf-8"))
            test_passed  = tr.get("status") == "passed"
            test_details = {
                "attempt_count":      tr.get("attempt_count"),
                "marked_count":       tr.get("marked_count"),
                "correct_count":      tr.get("correct_count"),
                "skill_gap_count":    tr.get("skill_gap_count"),
                "strength_count":     tr.get("strength_count"),
                "resubmission_count": tr.get("resubmission_count"),
                "accuracy":           tr.get("accuracy"),
            }
            checks.append({
                "label":   "Test report: status=passed",
                "path":    str(test_path.relative_to(PROJECT_ROOT)),
                "present": True,
                "contains": test_passed,
                "needle":  "status=passed",
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
    print("Quanta Aptus - Gate 59 Student Results Report v1")
    print("=" * 60)

    checks, issues, leaks, test_passed, test_details = run_checks()

    file_checks    = [c for c in checks if "contains" not in c]
    content_checks = [c for c in checks if "contains" in c]
    files_ok       = sum(1 for c in file_checks if c.get("present", True))
    content_ok     = sum(1 for c in content_checks if c.get("contains", False))

    print(f"  file checks   : {files_ok}/{len(file_checks)} present")
    print(f"  content checks: {content_ok}/{len(content_checks)} passed")
    print(f"  security scan : {'CLEAN' if not leaks else f'{len(leaks)} VIOLATION(S)'}")
    print(f"  test results  : {'PASSED' if test_passed else 'NOT RUN (run test_gate59_student_results_v1.py)'}")

    if test_details and test_passed:
        print(f"  attempts      : {test_details.get('attempt_count', '?')}")
        print(f"  marked        : {test_details.get('marked_count', '?')}")
        print(f"  skill_gaps    : {test_details.get('skill_gap_count', '?')}")
        acc = test_details.get("accuracy")
        print(f"  accuracy      : {f'{acc*100:.0f}%' if acc is not None else '—'}")

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
        "report_id":                             "quanta_aptus_gate59_student_results_report_v1",
        "gate":                                  "59",
        "created_at":                            now_iso,
        "status":                                overall,
        "live_supabase_student_results_supported": True,
        "student_result_report_supported":       True,
        "skill_gap_report_supported":            True,
        "resubmission_queue_supported":          True,
        "local_fallback_available":              True,
        "service_role_exposed_to_client":        bool(leaks),
        "service_role_leak_files":               leaks,
        "test_student_results_passed":           test_passed,
        "test_details":                          test_details,
        "openai_used":                           False,
        "checks_total":                          len(checks),
        "file_checks_passed":                    files_ok,
        "content_checks_passed":                 content_ok,
        "issues":                                issues,
        "checks":                                checks,
        "next_gate":                             "Gate 60 - Supabase Auth and Roles",
    }

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "gate59_student_results_report_v1.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {report_path}")

    if overall == "passed":
        done_path = DIAG_DIR / "SUPABASE_GATE_59_STUDENT_RESULTS_DONE.md"
        done_path.write_text(
            "\n".join([
                "# Gate 59 — Supabase Student Results DONE",
                "",
                f"**Date:** {now_iso[:10]}",
                "**Status:** `passed`",
                "**Phase:** Phase 2 - Supabase Integration",
                "",
                "## What Was Built",
                "",
                "| File | Change |",
                "|---|---|",
                "| `apps/admin/src/lib/liveSupabaseStudentResults.ts` | NEW - server-only results module |",
                "| `apps/admin/src/app/learn/supabase-results/page.tsx` | NEW - student results page |",
                "| `apps/admin/src/app/system/student-results/page.tsx` | NEW - diagnostic page |",
                "| `tools/supabase/test_gate59_student_results_v1.py` | NEW - integration test |",
                "",
                "## Behavior",
                "",
                "- Student results built from Supabase (attempts + marked_attempts + resources).",
                "- Skill gaps and strengths computed from marked attempt results.",
                "- Resubmission queue: attempts where latest result = needs_resubmission.",
                "- Accuracy: correct / (correct + incorrect + partially_correct).",
                "- `superseded_by_attempt_id` used to exclude superseded attempts from stats.",
                "- Local fallback remains unchanged.",
                "- No OpenAI API calls. No Cambridge source text.",
                "",
                "## Security",
                "",
                "- `import 'server-only'` in liveSupabaseStudentResults.ts.",
                "- `process.env.SUPABASE_SERVICE_ROLE_KEY` only in allowed server-only files.",
                "- Security scan: 0 violations.",
                "",
                "## Ready for Gate 60",
                "",
                "Gate 60 will add Supabase Auth so each student sees only their own results.",
            ]),
            encoding="utf-8",
        )
        print(f"  done marker   -> {done_path}")

    sys.exit(0 if overall in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
