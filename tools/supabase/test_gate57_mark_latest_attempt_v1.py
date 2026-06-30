"""
Gate 57 - Supabase Marking Test v1.

Finds the latest unmarked attempt, applies rule-based marking, writes a
marked_attempts row, and updates attempts.marking_status.

Mirrors the logic in liveSupabaseMarking.ts exactly.

What it does:
  1. Connect to Supabase using service role key.
  2. Find the latest attempt with marking_status = 'unmarked'.
  3. Load the associated resource (resource_type, worked_solution, marking_guidance).
  4. Apply rule-based marking:
       - calculation_drill, short_answer_calculation, algebra_drill → numeric overlap
       - teacher-review types → pending_teacher_review
       - other types → pending_teacher_review
  5. Check for existing marked_attempts row for the attempt (deduplication).
  6. Insert or update marked_attempts.
  7. Update attempts.marking_status.
  8. Write test report to data/diagnostics/gate57_marking_test_report_v1.json.

Does NOT:
  - Call OpenAI or any AI API.
  - Read or upload Cambridge source text.
  - Modify Supabase schema.
  - Expose service role key.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\test_gate57_mark_latest_attempt_v1.py [attempt_uuid]

Default: picks latest unmarked attempt.
Pass an explicit attempt UUID to mark a specific attempt.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
SUPABASE_TOOL = Path(__file__).parent
DIAG_DIR      = PROJECT_ROOT / "data" / "diagnostics"

if str(SUPABASE_TOOL) not in sys.path:
    sys.path.insert(0, str(SUPABASE_TOOL))

# ---------------------------------------------------------------------------
# Rule constants — mirror of liveSupabaseMarking.ts
# ---------------------------------------------------------------------------

TEACHER_REVIEW_TYPES = {
    "graphing_drill",
    "diagram_or_graph_drill",
    "experiment_planning_task",
    "planning_marking_checklist",
    "graph_marking_checklist",
    "marking_checklist",
    "data_interpretation_drill",
    "worked_example",
    "conceptual_explanation",
    "essay_planning",
}

NUMERIC_MARKING_TYPES = {
    "calculation_drill",
    "short_answer_calculation",
    "algebra_drill",
}


# ---------------------------------------------------------------------------
# Number extraction helpers — mirror of liveSupabaseMarking.ts
# ---------------------------------------------------------------------------

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def extract_numerics(text: str | None) -> set[str]:
    """Extract numbers from text and normalise to 2dp strings."""
    if not text:
        return set()
    result: set[str] = set()
    for m in _NUM_RE.findall(text):
        try:
            n = float(m)
            if not (n != n) and n != float("inf"):   # isfinite
                result.add(f"{n:.2f}")
        except ValueError:
            pass
    return result


def sets_overlap(a: set[str], b: set[str]) -> bool:
    return bool(a & b)


# ---------------------------------------------------------------------------
# Marking logic — pure, no DB
# ---------------------------------------------------------------------------

def apply_rule_based_marking(
    resource_type: str,
    worked_solution: str | None,
    marking_guidance: str | None,
    answer_text: str | None,
) -> dict:
    if resource_type in TEACHER_REVIEW_TYPES:
        return {
            "result":         "pending_teacher_review",
            "score":          None,
            "max_score":      None,
            "marking_status": "teacher_review_required",
            "feedback":       "This response requires teacher review.",
        }

    if resource_type in NUMERIC_MARKING_TYPES:
        expected = extract_numerics(worked_solution) | extract_numerics(marking_guidance)
        if not expected:
            return {
                "result":         "pending_teacher_review",
                "score":          None,
                "max_score":      None,
                "marking_status": "teacher_review_required",
                "feedback":       "No expected numerical answer found in solution guide. Teacher review required.",
            }
        student = extract_numerics(answer_text)
        if sets_overlap(student, expected):
            return {
                "result":         "correct",
                "score":          1,
                "max_score":      1,
                "marking_status": "auto_marked",
                "feedback":       "Your answer contains the correct numerical result.",
            }
        else:
            return {
                "result":         "incorrect",
                "score":          0,
                "max_score":      1,
                "marking_status": "auto_marked",
                "feedback":       "Your numerical answer does not match the expected result. Check your working.",
            }

    return {
        "result":         "pending_teacher_review",
        "score":          None,
        "max_score":      None,
        "marking_status": "teacher_review_required",
        "feedback":       "This resource type requires teacher review.",
    }


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_latest_unmarked_attempt(client) -> dict | None:
    r = (
        client.table("attempts")
        .select("id, student_id, resource_id, subject_id, answer_text, answer_json, attempt_type, marking_status")
        .eq("marking_status", "unmarked")
        .order("submitted_at", desc=True)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None


def _get_attempt_by_id(client, attempt_id: str) -> dict | None:
    r = (
        client.table("attempts")
        .select("id, student_id, resource_id, subject_id, answer_text, answer_json, attempt_type, marking_status")
        .eq("id", attempt_id)
        .execute()
    )
    return r.data[0] if r.data else None


def _get_resource(client, resource_id: str) -> dict | None:
    r = (
        client.table("resources")
        .select("id, resource_key, resource_type, skill_type, topic, worked_solution, marking_guidance")
        .eq("id", resource_id)
        .execute()
    )
    return r.data[0] if r.data else None


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


def _upsert_marked_attempt(
    client,
    attempt: dict,
    resource: dict,
    marking: dict,
    existing_id: str | None,
) -> dict | None:
    payload = {
        "attempt_id":     attempt["id"],
        "student_id":     attempt["student_id"],
        "resource_id":    attempt["resource_id"],
        "subject_id":     attempt.get("subject_id"),
        "marking_method": "rule_based",
        "score":          marking["score"],
        "max_score":      marking["max_score"],
        "result":         marking["result"],
        "feedback":       marking["feedback"],
        "skill_gap": {
            "topic":         resource.get("topic", ""),
            "skill_type":    resource.get("skill_type", ""),
            "resource_type": resource.get("resource_type", ""),
            "reason": (
                "Numerical answer does not match expected result."
                if marking["result"] == "incorrect"
                else "Requires teacher assessment for this resource type."
                if marking["result"] == "pending_teacher_review"
                else "Answer is correct."
            ),
        },
    }

    if existing_id:
        r = (
            client.table("marked_attempts")
            .update(payload)
            .eq("id", existing_id)
            .select("id, result, score, max_score")
            .execute()
        )
        return r.data[0] if r.data else None
    else:
        r = (
            client.table("marked_attempts")
            .insert(payload)
            .select("id, result, score, max_score")
            .execute()
        )
        return r.data[0] if r.data else None


def _update_attempt_marking_status(client, attempt_id: str, status: str) -> None:
    client.table("attempts").update({"marking_status": status}).eq("id", attempt_id).execute()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso     = datetime.now(timezone.utc).isoformat()
    attempt_arg = sys.argv[1] if len(sys.argv) > 1 else None

    from supabase_client_v1 import get_supabase_service_client, mask_secret

    print("=" * 60)
    print("Quanta Aptus - Gate 57 Marking Test v1")
    print("=" * 60)

    client, url = get_supabase_service_client()
    print(f"  connected     : {mask_secret(url)}")

    report: dict = {
        "report_id":  "quanta_aptus_gate57_marking_test_v1",
        "gate":       "57",
        "created_at": now_iso,
        "status":     "failed",
    }

    # ── Load attempt ────────────────────────────────────────────────────────
    if attempt_arg:
        attempt = _get_attempt_by_id(client, attempt_arg)
        if not attempt:
            print(f"  [FAILED] Attempt not found: {attempt_arg}")
            report["error"] = f"Attempt not found: {attempt_arg}"
            _write_report(report)
            sys.exit(1)
        print(f"  attempt       : {attempt['id']} (specified)")
    else:
        attempt = _get_latest_unmarked_attempt(client)
        if not attempt:
            print("  [FAILED] No unmarked attempts found.")
            print("  Hint: run test_gate56_attempt_write_v1.py first to create an unmarked attempt.")
            report["error"] = "No unmarked attempts found."
            _write_report(report)
            sys.exit(1)
        print(f"  attempt       : {attempt['id']} (latest unmarked)")

    print(f"  marking_status: {attempt['marking_status']}")
    report["attempt_id"]              = attempt["id"]
    report["attempt_marking_status_before"] = attempt["marking_status"]

    # ── Load resource ────────────────────────────────────────────────────────
    resource = _get_resource(client, attempt["resource_id"])
    if not resource:
        print(f"  [FAILED] Resource not found: {attempt['resource_id']}")
        report["error"] = f"Resource not found: {attempt['resource_id']}"
        _write_report(report)
        sys.exit(1)

    print(f"  resource      : {resource['resource_key']}")
    print(f"  resource_type : {resource['resource_type']}")
    report["resource_key"]  = resource["resource_key"]
    report["resource_type"] = resource["resource_type"]

    # ── Apply marking rules ──────────────────────────────────────────────────
    marking = apply_rule_based_marking(
        resource_type    = resource["resource_type"],
        worked_solution  = resource.get("worked_solution"),
        marking_guidance = resource.get("marking_guidance"),
        answer_text      = attempt.get("answer_text"),
    )

    print(f"  result        : {marking['result']}")
    print(f"  score         : {marking['score']}/{marking['max_score']}")
    print(f"  marking_method: rule_based")
    report["marking_result"]         = marking["result"]
    report["marking_score"]          = marking["score"]
    report["marking_max_score"]      = marking["max_score"]
    report["marking_status_target"]  = marking["marking_status"]
    report["feedback"]               = marking["feedback"]

    # ── Deduplication check ──────────────────────────────────────────────────
    existing = _find_existing_marked_attempt(client, attempt["id"])
    report["existing_marked_attempt_id"] = existing["id"] if existing else None
    if existing:
        print(f"  deduplication : existing row {existing['id'][:8]}… — will UPDATE")
    else:
        print("  deduplication : no existing row — will INSERT")

    # ── Upsert marked_attempts ───────────────────────────────────────────────
    marked_row = _upsert_marked_attempt(
        client, attempt, resource, marking, existing["id"] if existing else None
    )
    if not marked_row:
        print("  [FAILED] Could not write marked_attempts row.")
        report["error"] = "marked_attempts write failed"
        _write_report(report)
        sys.exit(1)

    print(f"  marked_attempt: {marked_row['id']}")
    report["marked_attempt_id"] = marked_row["id"]

    # ── Update attempts.marking_status ───────────────────────────────────────
    _update_attempt_marking_status(client, attempt["id"], marking["marking_status"])
    print(f"  attempts.marking_status → {marking['marking_status']}")
    report["attempt_marking_status_after"] = marking["marking_status"]

    # ── Verify ──────────────────────────────────────────────────────────────
    verify_r = (
        client.table("attempts")
        .select("marking_status")
        .eq("id", attempt["id"])
        .execute()
    )
    final_status = verify_r.data[0]["marking_status"] if verify_r.data else "unknown"
    print(f"  verified      : attempts.marking_status = {final_status}")
    report["verified_marking_status"] = final_status

    passed = final_status == marking["marking_status"]
    print(f"\n  status        : {'PASSED' if passed else 'FAILED (verify mismatch)'}")

    report.update({
        "status":  "passed" if passed else "failed",
        "marking_enabled": True,
        "marking_method":  "rule_based",
    })

    _write_report(report)
    sys.exit(0 if passed else 1)


def _write_report(report: dict) -> None:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    path = DIAG_DIR / "gate57_marking_test_report_v1.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {path}")


if __name__ == "__main__":
    main()
