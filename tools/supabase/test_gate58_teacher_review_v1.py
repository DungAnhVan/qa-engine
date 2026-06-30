"""
Gate 58 - Supabase Teacher Review Test v1.

Finds or creates a teacher_review_required attempt, submits a teacher review,
then verifies the database state.

What it does:
  1. Connect to Supabase using service role key.
  2. Find latest attempt with marking_status = teacher_review_required.
  3. If none found:
       - Find a graphing_drill or diagram_or_graph_drill resource.
       - Insert a test attempt (answer_text = 'Gate 58 test answer').
       - Insert/update marked_attempts result = pending_teacher_review.
       - Set attempts.marking_status = teacher_review_required.
  4. Submit teacher review:
       decision  = needs_resubmission
       feedback  = "Gate 58 test review: please resubmit with labelled axes and plotted points."
       notes     = "Automated Gate 58 test"
       score     = null (not applicable for needs_resubmission)
  5. Verify:
       - teacher_reviews row exists with correct decision.
       - marked_attempts result = needs_resubmission.
       - attempts.marking_status = teacher_reviewed.
  6. Write data/diagnostics/gate58_teacher_review_test_report_v1.json.

Does NOT:
  - Call OpenAI or any AI API.
  - Read or upload Cambridge source text.
  - Modify Supabase schema.
  - Expose service role key.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\test_gate58_teacher_review_v1.py [attempt_uuid]

Default: picks latest teacher_review_required attempt (or creates one).
Pass an explicit attempt UUID to use a specific attempt.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
SUPABASE_TOOL = Path(__file__).parent
DIAG_DIR      = PROJECT_ROOT / "data" / "diagnostics"

if str(SUPABASE_TOOL) not in sys.path:
    sys.path.insert(0, str(SUPABASE_TOOL))

DEMO_STUDENT_EXTERNAL_CODE = "local_demo_student"
DEMO_STUDENT_UUID_FALLBACK = "20000000-0000-0000-0000-000000000001"
TEST_SUBJECT_SLUG          = "physics_0625"
TEST_ANSWER_TEXT           = "Gate 58 test answer — graphing drill placeholder"
TEST_DECISION              = "needs_resubmission"
TEST_FEEDBACK              = "Gate 58 test review: please resubmit with labelled axes and plotted points."
TEST_NOTES                 = "Automated Gate 58 test"

TEACHER_REVIEW_RESOURCE_TYPES = [
    "graphing_drill",
    "diagram_or_graph_drill",
    "experiment_planning_task",
    "planning_marking_checklist",
    "graph_marking_checklist",
    "marking_checklist",
    "data_interpretation_drill",
    "worked_example",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_demo_student(client) -> dict | None:
    r = (
        client.table("students")
        .select("id, display_name, external_code")
        .eq("external_code", DEMO_STUDENT_EXTERNAL_CODE)
        .execute()
    )
    return r.data[0] if r.data else None


def _get_latest_teacher_review_required_attempt(client) -> dict | None:
    r = (
        client.table("attempts")
        .select("id, student_id, resource_id, subject_id, answer_text, marking_status, submitted_at")
        .eq("marking_status", "teacher_review_required")
        .order("submitted_at", desc=True)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None


def _find_teacher_review_resource(client) -> dict | None:
    """Find a resource with a type that requires teacher review."""
    for rtype in TEACHER_REVIEW_RESOURCE_TYPES:
        r = (
            client.table("resources")
            .select("id, resource_key, title, topic, skill_type, resource_type, subject_id")
            .eq("resource_type", rtype)
            .limit(1)
            .execute()
        )
        if r.data:
            return r.data[0]
    return None


def _create_test_attempt(client, student_id: str, resource: dict) -> dict | None:
    """Insert a test attempt and mark it as teacher_review_required."""
    # Insert attempt
    r = (
        client.table("attempts")
        .insert({
            "student_id":        student_id,
            "resource_id":       resource["id"],
            "subject_id":        resource.get("subject_id"),
            "attempt_type":      "first_attempt",
            "parent_attempt_id": None,
            "answer_text":       TEST_ANSWER_TEXT,
            "answer_json":       {"test": True, "source": "gate58_test_script"},
            "confidence_level":  "low",
            "marking_status":    "teacher_review_required",
        })
        .select("id, submitted_at, marking_status, student_id, resource_id, subject_id")
        .execute()
    )
    if not r.data:
        return None
    attempt = r.data[0]

    # Insert marked_attempts with pending_teacher_review
    client.table("marked_attempts").insert({
        "attempt_id":     attempt["id"],
        "student_id":     student_id,
        "resource_id":    resource["id"],
        "subject_id":     resource.get("subject_id"),
        "marking_method": "rule_based",
        "score":          None,
        "max_score":      None,
        "result":         "pending_teacher_review",
        "feedback":       "This response requires teacher review.",
        "skill_gap": {
            "topic":         resource.get("topic", ""),
            "skill_type":    resource.get("skill_type", ""),
            "resource_type": resource.get("resource_type", ""),
            "reason":        "Requires teacher assessment for this resource type.",
        },
    }).execute()

    return attempt


def _find_existing_marked_attempt(client, attempt_id: str) -> dict | None:
    r = (
        client.table("marked_attempts")
        .select("id")
        .eq("attempt_id", attempt_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None


def _submit_teacher_review(
    client,
    attempt: dict,
    resource_id: str,
    decision: str,
    feedback: str,
    notes: str,
    score=None,
) -> dict | None:
    """Insert teacher_reviews row, upsert marked_attempts, update attempts."""
    # 1. Insert teacher_reviews
    tr_r = (
        client.table("teacher_reviews")
        .insert({
            "organization_id":     None,
            "reviewer_profile_id": None,
            "review_type":         "attempt_review",
            "resource_id":         resource_id,
            "attempt_id":          attempt["id"],
            "decision":            decision,
            "score":               score,
            "feedback":            feedback,
            "notes":               notes,
        })
        .select("id")
        .execute()
    )
    if not tr_r.data:
        return None
    review_id = tr_r.data[0]["id"]

    # 2. Upsert marked_attempts
    existing = _find_existing_marked_attempt(client, attempt["id"])
    marked_payload = {
        "attempt_id":     attempt["id"],
        "student_id":     attempt["student_id"],
        "resource_id":    resource_id,
        "subject_id":     attempt.get("subject_id"),
        "marking_method": "teacher",
        "score":          score,
        "max_score":      1 if score is not None else None,
        "result":         decision,
        "feedback":       feedback,
        "skill_gap": {
            "decision": decision,
            "reason":   feedback,
        },
    }

    if existing:
        ma_r = (
            client.table("marked_attempts")
            .update(marked_payload)
            .eq("id", existing["id"])
            .select("id")
            .execute()
        )
        marked_attempt_id = ma_r.data[0]["id"] if ma_r.data else existing["id"]
    else:
        ma_r = (
            client.table("marked_attempts")
            .insert(marked_payload)
            .select("id")
            .execute()
        )
        marked_attempt_id = ma_r.data[0]["id"] if ma_r.data else None

    # 3. Update attempts.marking_status
    client.table("attempts").update({"marking_status": "teacher_reviewed"}).eq("id", attempt["id"]).execute()

    return {"review_id": review_id, "marked_attempt_id": marked_attempt_id}


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def _verify_teacher_review(client, review_id: str) -> dict | None:
    r = (
        client.table("teacher_reviews")
        .select("id, decision, feedback, created_at")
        .eq("id", review_id)
        .execute()
    )
    return r.data[0] if r.data else None


def _verify_marked_attempt(client, marked_attempt_id: str) -> dict | None:
    r = (
        client.table("marked_attempts")
        .select("id, result, marking_method")
        .eq("id", marked_attempt_id)
        .execute()
    )
    return r.data[0] if r.data else None


def _verify_attempt_status(client, attempt_id: str) -> str | None:
    r = (
        client.table("attempts")
        .select("marking_status")
        .eq("id", attempt_id)
        .execute()
    )
    return r.data[0]["marking_status"] if r.data else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso     = datetime.now(timezone.utc).isoformat()
    attempt_arg = sys.argv[1] if len(sys.argv) > 1 else None

    from supabase_client_v1 import get_supabase_service_client, mask_secret

    print("=" * 60)
    print("Quanta Aptus - Gate 58 Teacher Review Test v1")
    print("=" * 60)

    client, url = get_supabase_service_client()
    print(f"  connected     : {mask_secret(url)}")

    report: dict = {
        "report_id":  "quanta_aptus_gate58_teacher_review_test_v1",
        "gate":       "58",
        "created_at": now_iso,
        "status":     "failed",
    }

    # ── Find or create teacher_review_required attempt ──────────────────────
    created_test_attempt = False

    if attempt_arg:
        from_db = (
            client.table("attempts")
            .select("id, student_id, resource_id, subject_id, answer_text, marking_status, submitted_at")
            .eq("id", attempt_arg)
            .execute()
        )
        attempt = from_db.data[0] if from_db.data else None
        if not attempt:
            print(f"  [FAILED] Attempt not found: {attempt_arg}")
            report["error"] = f"Attempt not found: {attempt_arg}"
            _write_report(report)
            sys.exit(1)
        print(f"  attempt       : {attempt['id']} (specified)")
    else:
        attempt = _get_latest_teacher_review_required_attempt(client)
        if attempt:
            print(f"  attempt       : {attempt['id']} (existing teacher_review_required)")
        else:
            print("  no teacher_review_required attempt found — creating test attempt")
            # Find demo student
            student = _get_demo_student(client)
            if not student:
                student = {"id": DEMO_STUDENT_UUID_FALLBACK, "display_name": "Local Demo Student (fallback)"}
                print(f"  demo student  : fallback {DEMO_STUDENT_UUID_FALLBACK}")
            else:
                print(f"  demo student  : {student['display_name']}")

            # Find a teacher-review-type resource
            resource = _find_teacher_review_resource(client)
            if not resource:
                print("  [FAILED] No teacher-review-type resource found.")
                report["error"] = "No teacher-review-type resource found."
                _write_report(report)
                sys.exit(1)
            print(f"  resource      : {resource['resource_key']} ({resource['resource_type']})")

            attempt = _create_test_attempt(client, student["id"], resource)
            if not attempt:
                print("  [FAILED] Could not create test attempt.")
                report["error"] = "Test attempt creation failed."
                _write_report(report)
                sys.exit(1)
            created_test_attempt = True
            print(f"  attempt       : {attempt['id']} (created for test)")

    print(f"  marking_status: {attempt['marking_status']}")
    report["attempt_id"]                     = attempt["id"]
    report["created_test_attempt"]           = created_test_attempt
    report["attempt_marking_status_before"]  = attempt["marking_status"]

    # ── Submit teacher review ────────────────────────────────────────────────
    print(f"  decision      : {TEST_DECISION}")
    review_result = _submit_teacher_review(
        client,
        attempt,
        resource_id  = attempt["resource_id"],
        decision     = TEST_DECISION,
        feedback     = TEST_FEEDBACK,
        notes        = TEST_NOTES,
        score        = None,
    )
    if not review_result:
        print("  [FAILED] Teacher review submission failed.")
        report["error"] = "Teacher review submission failed."
        _write_report(report)
        sys.exit(1)

    review_id          = review_result["review_id"]
    marked_attempt_id  = review_result["marked_attempt_id"]
    print(f"  review_id     : {review_id}")
    print(f"  marked_attempt: {marked_attempt_id}")
    report["review_id"]          = review_id
    report["marked_attempt_id"]  = marked_attempt_id

    # ── Verify ──────────────────────────────────────────────────────────────
    tr_verify   = _verify_teacher_review(client, review_id)
    ma_verify   = _verify_marked_attempt(client, marked_attempt_id) if marked_attempt_id else None
    att_status  = _verify_attempt_status(client, attempt["id"])

    tr_ok  = tr_verify is not None and tr_verify.get("decision") == TEST_DECISION
    ma_ok  = ma_verify is not None and ma_verify.get("result") == TEST_DECISION
    att_ok = att_status == "teacher_reviewed"

    print(f"  verify review : {'OK' if tr_ok else 'FAIL'} — decision={tr_verify.get('decision') if tr_verify else 'not found'}")
    print(f"  verify marked : {'OK' if ma_ok else 'FAIL'} — result={ma_verify.get('result') if ma_verify else 'not found'}")
    print(f"  verify attempt: {'OK' if att_ok else 'FAIL'} — marking_status={att_status}")

    passed = tr_ok and ma_ok and att_ok
    print(f"\n  status        : {'PASSED' if passed else 'FAILED'}")

    report.update({
        "status":                     "passed" if passed else "failed",
        "teacher_review_row_created": tr_ok,
        "marked_attempt_updated":     ma_ok,
        "attempt_status_updated":     att_ok,
        "decision_used":              TEST_DECISION,
        "attempt_marking_status_after": att_status,
        "marked_attempt_result":       ma_verify.get("result") if ma_verify else None,
        "marked_attempt_method":       ma_verify.get("marking_method") if ma_verify else None,
    })

    _write_report(report)
    sys.exit(0 if passed else 1)


def _write_report(report: dict) -> None:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    path = DIAG_DIR / "gate58_teacher_review_test_report_v1.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {path}")


if __name__ == "__main__":
    main()
