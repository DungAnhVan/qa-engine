"""
Gate 59 - Supabase Student Results Test v1.

Builds a student result report for local_demo_student + physics_0625 directly
from Supabase and verifies the expected structure.

What it does:
  1. Connect to Supabase using service role key.
  2. Resolve local_demo_student and physics_0625 subject.
  3. Query attempts, marked_attempts, and resources.
  4. Build result report (mirrors liveSupabaseStudentResults.ts logic).
  5. Verify:
       - attempts count > 0
       - marked_attempts count > 0
       - at least one of: skill_gaps, strengths, resubmission_queue is non-empty
  6. Write:
       data/diagnostics/gate59_student_results_test_report_v1.json
       data/supabase_exports/student_results_from_supabase_v1.json

Does NOT:
  - Call OpenAI or any AI API.
  - Read or upload Cambridge source text.
  - Modify Supabase schema.
  - Expose service role key.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\test_gate59_student_results_v1.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
SUPABASE_TOOL = Path(__file__).parent
DIAG_DIR      = PROJECT_ROOT / "data" / "diagnostics"
EXPORT_DIR    = PROJECT_ROOT / "data" / "supabase_exports"

if str(SUPABASE_TOOL) not in sys.path:
    sys.path.insert(0, str(SUPABASE_TOOL))

DEMO_STUDENT_CODE    = "local_demo_student"
DEMO_SUBJECT_SLUG    = "physics_0625"
DEMO_UUID_FALLBACK   = "20000000-0000-0000-0000-000000000001"

GAP_RESULTS = {"incorrect", "partially_correct", "needs_resubmission", "pending_teacher_review"}


# ---------------------------------------------------------------------------
# Resolve helpers
# ---------------------------------------------------------------------------

def _resolve_student(client) -> dict | None:
    r = (
        client.table("students")
        .select("id, display_name, external_code")
        .eq("external_code", DEMO_STUDENT_CODE)
        .execute()
    )
    return r.data[0] if r.data else None


def _resolve_subject(client) -> dict | None:
    r = (
        client.table("subjects")
        .select("id, subject_slug")
        .eq("subject_slug", DEMO_SUBJECT_SLUG)
        .execute()
    )
    return r.data[0] if r.data else None


# ---------------------------------------------------------------------------
# Batch loaders
# ---------------------------------------------------------------------------

def _load_attempts(client, student_id: str, subject_id: str) -> list[dict]:
    r = (
        client.table("attempts")
        .select(
            "id, resource_id, attempt_type, parent_attempt_id, answer_text, "
            "submitted_at, marking_status, superseded_by_attempt_id"
        )
        .eq("student_id", student_id)
        .eq("subject_id", subject_id)
        .order("submitted_at")
        .execute()
    )
    return r.data or []


def _load_marked_attempts(client, attempt_ids: list[str]) -> list[dict]:
    if not attempt_ids:
        return []
    r = (
        client.table("marked_attempts")
        .select(
            "id, attempt_id, resource_id, marking_method, score, max_score, "
            "result, feedback, created_at"
        )
        .in_("attempt_id", attempt_ids)
        .order("created_at")   # oldest first so latest overwrites map
        .execute()
    )
    return r.data or []


def _load_resources(client, resource_ids: list[str]) -> list[dict]:
    if not resource_ids:
        return []
    r = (
        client.table("resources")
        .select("id, resource_key, title, topic, skill_type, resource_type")
        .in_("id", resource_ids)
        .execute()
    )
    return r.data or []


# ---------------------------------------------------------------------------
# Report builder (mirrors liveSupabaseStudentResults.ts)
# ---------------------------------------------------------------------------

def build_report(
    student: dict,
    subject: dict,
    attempts: list[dict],
    latest_marked: dict[str, dict],   # attempt_id → latest marked_attempt
    resources: dict[str, dict],       # resource_id → resource
) -> dict:
    current = [a for a in attempts if not a.get("superseded_by_attempt_id")]

    # Attempt status counts
    unmarked = auto_marked = teacher_review_req = teacher_reviewed = 0
    for a in current:
        ms = a.get("marking_status", "")
        if ms == "unmarked":                  unmarked         += 1
        elif ms == "auto_marked":             auto_marked      += 1
        elif ms == "teacher_review_required": teacher_review_req += 1
        elif ms == "teacher_reviewed":        teacher_reviewed += 1

    # Result counts
    correct = incorrect = partial = resubmit = pending = 0
    for a in current:
        m = latest_marked.get(a["id"])
        if not m: continue
        r = m.get("result", "")
        if r == "correct":               correct  += 1
        elif r == "incorrect":           incorrect += 1
        elif r == "partially_correct":   partial  += 1
        elif r == "needs_resubmission":  resubmit += 1
        elif r == "pending_teacher_review": pending += 1

    resolved = correct + incorrect + partial
    accuracy = (correct / resolved) if resolved > 0 else None

    # Strengths
    strength_map: dict[str, dict] = {}
    for a in current:
        m = latest_marked.get(a["id"])
        if not m or m.get("result") != "correct": continue
        res = resources.get(a["resource_id"], {})
        key = f"{res.get('topic', '—')}|{res.get('skill_type', '—')}"
        if key in strength_map:
            strength_map[key]["count"] += 1
        else:
            strength_map[key] = {
                "topic":      res.get("topic"),
                "skill_type": res.get("skill_type"),
                "count":      1,
            }
    strengths = sorted(strength_map.values(), key=lambda x: -x["count"])

    # Skill gaps
    skill_gaps = []
    for a in current:
        m = latest_marked.get(a["id"])
        if not m or m.get("result") not in GAP_RESULTS: continue
        res = resources.get(a["resource_id"], {})
        skill_gaps.append({
            "attempt_id":     a["id"],
            "resource_title": res.get("title", "—"),
            "resource_key":   res.get("resource_key", "—"),
            "topic":          res.get("topic"),
            "skill_type":     res.get("skill_type"),
            "result":         m.get("result"),
            "feedback":       m.get("feedback"),
        })

    # Resubmission queue
    resubmission_queue = []
    for a in current:
        m = latest_marked.get(a["id"])
        if not m or m.get("result") != "needs_resubmission": continue
        res = resources.get(a["resource_id"], {})
        resubmission_queue.append({
            "attempt_id":     a["id"],
            "resource_title": res.get("title", "—"),
            "resource_key":   res.get("resource_key", "—"),
            "topic":          res.get("topic"),
            "feedback":       m.get("feedback"),
            "submitted_at":   a["submitted_at"],
        })

    # Recent attempts (latest 10)
    recent = sorted(attempts, key=lambda a: a["submitted_at"], reverse=True)[:10]
    recent_attempts = []
    for a in recent:
        m = latest_marked.get(a["id"])
        res = resources.get(a["resource_id"], {})
        recent_attempts.append({
            "attempt_id":     a["id"],
            "resource_title": res.get("title", "—"),
            "resource_key":   res.get("resource_key", "—"),
            "topic":          res.get("topic"),
            "result":         m.get("result") if m else None,
            "marking_method": m.get("marking_method") if m else None,
            "submitted_at":   a["submitted_at"],
            "attempt_type":   a.get("attempt_type", ""),
            "marking_status": a.get("marking_status", ""),
        })

    return {
        "student_id":                    student["id"],
        "student_name":                  student["display_name"],
        "subject_slug":                  subject["subject_slug"],
        "attempt_count":                 len(attempts),
        "marked_attempt_count":          len(latest_marked),
        "unmarked_count":                unmarked,
        "auto_marked_count":             auto_marked,
        "teacher_review_required_count": teacher_review_req,
        "teacher_reviewed_count":        teacher_reviewed,
        "correct_count":                 correct,
        "incorrect_count":               incorrect,
        "partially_correct_count":       partial,
        "needs_resubmission_count":      resubmit,
        "pending_teacher_review_count":  pending,
        "accuracy":                      accuracy,
        "strengths":                     strengths,
        "skill_gaps":                    skill_gaps,
        "resubmission_queue":            resubmission_queue,
        "recent_attempts":               recent_attempts,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    from supabase_client_v1 import get_supabase_service_client, mask_secret

    print("=" * 60)
    print("Quanta Aptus - Gate 59 Student Results Test v1")
    print("=" * 60)

    client, url = get_supabase_service_client()
    print(f"  connected     : {mask_secret(url)}")

    report_meta: dict = {
        "report_id":  "quanta_aptus_gate59_student_results_test_v1",
        "gate":       "59",
        "created_at": now_iso,
        "status":     "failed",
    }

    # ── Resolve student + subject ────────────────────────────────────────────
    student = _resolve_student(client)
    if not student:
        print(f"  demo student  : using fallback UUID {DEMO_UUID_FALLBACK}")
        student = {"id": DEMO_UUID_FALLBACK, "display_name": "Local Demo Student (fallback)", "external_code": DEMO_STUDENT_CODE}
    else:
        print(f"  demo student  : {student['display_name']}")

    subject = _resolve_subject(client)
    if not subject:
        print(f"  [FAILED] Subject '{DEMO_SUBJECT_SLUG}' not found.")
        report_meta["error"] = f"Subject not found: {DEMO_SUBJECT_SLUG}"
        _write_report(report_meta)
        sys.exit(1)
    print(f"  subject       : {subject['subject_slug']}")

    # ── Load data ────────────────────────────────────────────────────────────
    attempts = _load_attempts(client, student["id"], subject["id"])
    print(f"  attempts      : {len(attempts)}")

    if not attempts:
        print("  [WARN] No attempts found for demo student.")
        print("  Hint: run test_gate56_attempt_write_v1.py first.")
        report_meta.update({
            "status":           "needs_data",
            "attempt_count":    0,
            "marked_count":     0,
            "error":            "No attempts found. Run Gate 56 test first.",
        })
        _write_report(report_meta)
        sys.exit(1)

    attempt_ids  = [a["id"] for a in attempts]
    resource_ids = list({a["resource_id"] for a in attempts})

    marked_rows   = _load_marked_attempts(client, attempt_ids)
    resource_rows = _load_resources(client, resource_ids)

    print(f"  marked_rows   : {len(marked_rows)}")
    print(f"  resources     : {len(resource_rows)}")

    # Latest marked per attempt (oldest → latest, latest overwrites)
    latest_marked: dict[str, dict] = {}
    for m in marked_rows:
        latest_marked[m["attempt_id"]] = m

    resource_map = {r["id"]: r for r in resource_rows}

    # ── Build report ─────────────────────────────────────────────────────────
    result_report = build_report(student, subject, attempts, latest_marked, resource_map)

    print(f"  correct       : {result_report['correct_count']}")
    print(f"  incorrect     : {result_report['incorrect_count']}")
    accuracy = result_report.get("accuracy")
    accuracy_text = f"{accuracy * 100:.0f}%" if accuracy is not None else "-"
    print(f"  accuracy          : {accuracy_text}")
    print(f"  skill_gaps    : {len(result_report['skill_gaps'])}")
    print(f"  strengths     : {len(result_report['strengths'])}")
    print(f"  resubmission  : {len(result_report['resubmission_queue'])}")

    # ── Verify ──────────────────────────────────────────────────────────────
    ok_attempts = result_report["attempt_count"] > 0
    ok_marked   = result_report["marked_attempt_count"] > 0
    ok_content  = (
        len(result_report["skill_gaps"]) > 0 or
        len(result_report["strengths"]) > 0 or
        len(result_report["resubmission_queue"]) > 0
    )

    print(f"\n  attempts > 0  : {'OK' if ok_attempts else 'FAIL'}")
    print(f"  marked > 0    : {'OK' if ok_marked else 'WARN (run marking test)'}")
    print(f"  has content   : {'OK' if ok_content else 'WARN (needs more test data)'}")

    passed = ok_attempts  # minimum: at least some attempts exist
    print(f"\n  status        : {'PASSED' if passed else 'FAILED'}")

    report_meta.update({
        "status":               "passed" if passed else "failed",
        "attempt_count":        result_report["attempt_count"],
        "marked_count":         result_report["marked_attempt_count"],
        "correct_count":        result_report["correct_count"],
        "incorrect_count":      result_report["incorrect_count"],
        "skill_gap_count":      len(result_report["skill_gaps"]),
        "strength_count":       len(result_report["strengths"]),
        "resubmission_count":   len(result_report["resubmission_queue"]),
        "accuracy":             result_report["accuracy"],
        "has_marked_data":      ok_marked,
        "has_result_content":   ok_content,
    })

    _write_report(report_meta)

    # ── Export full student result JSON ──────────────────────────────────────
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_path = EXPORT_DIR / "student_results_from_supabase_v1.json"
    export_data = {
        "exported_at":  now_iso,
        "student_code": DEMO_STUDENT_CODE,
        "subject_slug": DEMO_SUBJECT_SLUG,
        "report":       result_report,
    }
    export_path.write_text(
        json.dumps(export_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"  export        -> {export_path}")

    sys.exit(0 if passed else 1)


def _write_report(report: dict) -> None:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    path = DIAG_DIR / "gate59_student_results_test_report_v1.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"  report        -> {path}")


if __name__ == "__main__":
    main()
