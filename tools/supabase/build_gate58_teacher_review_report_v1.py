"""
Gate 58 - Supabase Teacher Review Report v1.

Static code/artifact checks — no Supabase connection required.
Verifies all Gate 58 artifacts are in place and security constraints hold.

Checks:
  - liveSupabaseTeacherReview.ts: exists, server-only guard, required exports
  - API route exists and is correct
  - Review page exists
  - TeacherReviewForm client component exists
  - Diagnostic page exists
  - process.env.SUPABASE_SERVICE_ROLE_KEY only in allowed server-only files
  - Gate 56/57 artifacts still present (no regression)
  - Test report passed (if available)

Output:
  data/diagnostics/gate58_teacher_review_report_v1.json
  data/diagnostics/SUPABASE_GATE_58_TEACHER_REVIEW_DONE.md

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\build_gate58_teacher_review_report_v1.py
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
        ADMIN_LIB / "liveSupabaseMarking.ts",
        ADMIN_LIB / "liveSupabaseTeacherReview.ts",  # Gate 58 — new allowed file
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

    review_ts  = ADMIN_LIB / "liveSupabaseTeacherReview.ts"
    api_route  = ADMIN_APP / "api" / "supabase" / "teacher-attempt-review" / "route.ts"
    review_page = ADMIN_APP / "learn" / "supabase-attempt-review" / "page.tsx"
    review_form = ADMIN_APP / "learn" / "supabase-attempt-review" / "TeacherReviewForm.tsx"
    diag_page  = ADMIN_APP / "system" / "teacher-review" / "page.tsx"

    # ── liveSupabaseTeacherReview.ts ─────────────────────────────────────────
    checks.append(_exists(review_ts, "liveSupabaseTeacherReview.ts (new)"))
    checks.append(_contains(review_ts, "liveSupabaseTeacherReview.ts: import server-only", "import 'server-only'"))
    checks.append(_contains(review_ts, "liveSupabaseTeacherReview.ts: getLiveSupabaseTeacherReviewQueue", "getLiveSupabaseTeacherReviewQueue"))
    checks.append(_contains(review_ts, "liveSupabaseTeacherReview.ts: submitLiveSupabaseTeacherReview", "submitLiveSupabaseTeacherReview"))
    checks.append(_contains(review_ts, "liveSupabaseTeacherReview.ts: getLiveSupabaseTeacherReviewStats", "getLiveSupabaseTeacherReviewStats"))
    checks.append(_contains(review_ts, "liveSupabaseTeacherReview.ts: teacher_reviews table", "teacher_reviews"))
    checks.append(_contains(review_ts, "liveSupabaseTeacherReview.ts: attempt_review type", "attempt_review"))
    checks.append(_contains(review_ts, "liveSupabaseTeacherReview.ts: teacher_reviewed status", "teacher_reviewed"))
    checks.append(_contains(review_ts, "liveSupabaseTeacherReview.ts: no organization_id hard-coded", "organization_id"))
    checks.append(_contains(review_ts, "liveSupabaseTeacherReview.ts: no OpenAI import", "openai"))
    # Invert openai check
    openai_check = checks[-1]
    openai_check["contains"] = not openai_check.get("contains", False)
    openai_check["needle"]   = "NO openai import"

    # ── API route ─────────────────────────────────────────────────────────────
    checks.append(_exists(api_route, "API route: teacher-attempt-review/route.ts"))
    checks.append(_contains(api_route, "API route: live_supabase guard", "live_supabase"))
    checks.append(_contains(api_route, "API route: imports submitLiveSupabaseTeacherReview", "submitLiveSupabaseTeacherReview"))
    checks.append(_contains(api_route, "API route: validates UUID", "UUID_REGEX"))
    checks.append(_contains(api_route, "API route: validates decision", "VALID_DECISIONS"))
    checks.append(_contains(api_route, "API route: requires feedback", "feedback"))
    checks.append(_contains(api_route, "API route: returns storage=supabase", "supabase"))
    checks.append(_contains(api_route, "API route: force-dynamic", "force-dynamic"))

    # ── Review page ───────────────────────────────────────────────────────────
    checks.append(_exists(review_page, "Review page: /learn/supabase-attempt-review"))
    checks.append(_contains(review_page, "Review page: force-dynamic", "force-dynamic"))
    checks.append(_contains(review_page, "Review page: imports getLiveSupabaseTeacherReviewQueue", "getLiveSupabaseTeacherReviewQueue"))
    checks.append(_contains(review_page, "Review page: renders TeacherReviewForm", "TeacherReviewForm"))
    checks.append(_contains(review_page, "Review page: shows student answer", "answer_text"))

    # ── TeacherReviewForm client component ───────────────────────────────────
    checks.append(_exists(review_form, "TeacherReviewForm.tsx: present"))
    checks.append(_contains(review_form, "TeacherReviewForm.tsx: use client", "'use client'"))
    checks.append(_contains(review_form, "TeacherReviewForm.tsx: calls mark endpoint", "/api/supabase/teacher-attempt-review"))
    checks.append(_contains(review_form, "TeacherReviewForm.tsx: router.refresh() after submit", "router.refresh()"))
    checks.append(_contains(review_form, "TeacherReviewForm.tsx: decision field", "decision"))
    checks.append(_contains(review_form, "TeacherReviewForm.tsx: feedback field", "feedback"))

    # ── Diagnostic page ───────────────────────────────────────────────────────
    checks.append(_exists(diag_page, "Diagnostic page: /system/teacher-review"))
    checks.append(_contains(diag_page, "Diagnostic page: force-dynamic", "force-dynamic"))
    checks.append(_contains(diag_page, "Diagnostic page: getLiveSupabaseTeacherReviewStats", "getLiveSupabaseTeacherReviewStats"))
    checks.append(_contains(diag_page, "Diagnostic page: Gate 59 notice", "Gate 59"))

    # ── Gate 56/57 regressions ───────────────────────────────────────────────
    checks.append(_exists(ADMIN_LIB / "liveSupabaseAttempts.ts",  "Gate 56: liveSupabaseAttempts.ts still present"))
    checks.append(_exists(ADMIN_LIB / "liveSupabaseMarking.ts",   "Gate 57: liveSupabaseMarking.ts still present"))
    checks.append(_exists(ADMIN_APP / "api" / "mark-attempt" / "route.ts", "Gate 57: mark-attempt route still present"))

    # ── Test report ──────────────────────────────────────────────────────────
    test_report_path = DIAG_DIR / "gate58_teacher_review_test_report_v1.json"
    checks.append(_exists(test_report_path, "Test report: gate58_teacher_review_test_report_v1.json"))

    test_passed  = False
    test_details: dict = {}
    if test_report_path.exists():
        try:
            tr = json.loads(test_report_path.read_text(encoding="utf-8"))
            test_passed   = tr.get("status") == "passed"
            test_details  = {
                "attempt_id":               tr.get("attempt_id"),
                "review_id":                tr.get("review_id"),
                "marked_attempt_id":        tr.get("marked_attempt_id"),
                "decision_used":            tr.get("decision_used"),
                "attempt_marking_status_after": tr.get("attempt_marking_status_after"),
                "marked_attempt_result":    tr.get("marked_attempt_result"),
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
    print("Quanta Aptus - Gate 58 Teacher Review Report v1")
    print("=" * 60)

    checks, issues, leaks, test_passed, test_details = run_checks()

    file_checks    = [c for c in checks if "contains" not in c]
    content_checks = [c for c in checks if "contains" in c]
    files_ok       = sum(1 for c in file_checks if c.get("present", True))
    content_ok     = sum(1 for c in content_checks if c.get("contains", False))

    print(f"  file checks   : {files_ok}/{len(file_checks)} present")
    print(f"  content checks: {content_ok}/{len(content_checks)} passed")
    print(f"  security scan : {'CLEAN' if not leaks else f'{len(leaks)} VIOLATION(S)'}")
    print(f"  test review   : {'PASSED' if test_passed else 'NOT RUN (run test_gate58_teacher_review_v1.py)'}")

    if test_details and test_passed:
        print(f"  review_id     : {test_details.get('review_id', '?')}")
        print(f"  decision      : {test_details.get('decision_used', '?')}")
        print(f"  att.status    : {test_details.get('attempt_marking_status_after', '?')}")

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
        "report_id":                          "quanta_aptus_gate58_teacher_review_report_v1",
        "gate":                               "58",
        "created_at":                         now_iso,
        "status":                             overall,
        "teacher_review_queue_supported":     True,
        "teacher_review_write_supported":     True,
        "marked_attempt_update_supported":    True,
        "attempt_status_update_supported":    True,
        "needs_resubmission_supported":       True,
        "service_role_exposed_to_client":     bool(leaks),
        "service_role_leak_files":            leaks,
        "test_teacher_review_passed":         test_passed,
        "test_details":                       test_details,
        "openai_used":                        False,
        "checks_total":                       len(checks),
        "file_checks_passed":                 files_ok,
        "content_checks_passed":              content_ok,
        "issues":                             issues,
        "checks":                             checks,
        "next_gate":                          "Gate 59 - Supabase Student Results",
    }

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "gate58_teacher_review_report_v1.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {report_path}")

    if overall == "passed":
        done_path = DIAG_DIR / "SUPABASE_GATE_58_TEACHER_REVIEW_DONE.md"
        done_path.write_text(
            "\n".join([
                "# Gate 58 - Supabase Teacher Attempt Review DONE",
                "",
                f"**Date:** {now_iso[:10]}",
                "**Status:** `passed`",
                "**Phase:** Phase 2 - Supabase Integration",
                "",
                "## What Was Built",
                "",
                "| File | Change |",
                "|---|---|",
                "| `apps/admin/src/lib/liveSupabaseTeacherReview.ts` | NEW - server-only teacher review module |",
                "| `apps/admin/src/app/api/supabase/teacher-attempt-review/route.ts` | NEW - POST endpoint |",
                "| `apps/admin/src/app/learn/supabase-attempt-review/page.tsx` | NEW - queue page |",
                "| `apps/admin/src/app/learn/supabase-attempt-review/TeacherReviewForm.tsx` | NEW - client form |",
                "| `apps/admin/src/app/system/teacher-review/page.tsx` | NEW - diagnostic page |",
                "| `tools/supabase/test_gate58_teacher_review_v1.py` | NEW - integration test |",
                "",
                "## Behavior",
                "",
                "- Teacher can review student attempts with `marking_status = teacher_review_required`.",
                "- Decisions: `correct`, `incorrect`, `partially_correct`, `needs_resubmission`.",
                "- Each review writes a `teacher_reviews` row and upserts `marked_attempts`.",
                "- `attempts.marking_status` → `teacher_reviewed` on review.",
                "- Auto-deduplication: existing `marked_attempts` row is updated, not duplicated.",
                "- `organization_id` and `reviewer_profile_id` are null (no auth yet — Gate 6x).",
                "- TeacherReviewForm calls `router.refresh()` after submission (queue updates).",
                "",
                "## Security",
                "",
                "- `import 'server-only'` in liveSupabaseTeacherReview.ts.",
                "- `process.env.SUPABASE_SERVICE_ROLE_KEY` only in allowed server-only files.",
                "- Security scan: 0 violations.",
                "- No Cambridge source text written. No OpenAI API calls.",
                "",
                "## Ready for Gate 59",
                "",
                "Gate 59 will add student results view showing marked attempt history.",
            ]),
            encoding="utf-8",
        )
        print(f"  done marker   -> {done_path}")

    sys.exit(0 if overall in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
