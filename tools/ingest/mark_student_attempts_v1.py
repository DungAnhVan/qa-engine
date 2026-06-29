"""
Gate 41 - Basic Local Marking Engine v1
Reads student_attempts_v1.json + teacher_resource_payload_v2.json,
applies rule-based marking, writes marked_attempts_v1 outputs.
No OpenAI. No Supabase. Does not modify input files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CALC_TYPES = {
    "calculation_drill",
    "short_answer_calculation",
    "worked_example",
    "data_interpretation_drill",
}

GRAPHING_TYPES = {
    "graphing_drill",
    "diagram_or_graph_drill",
    "experiment_planning_task",
    "planning_marking_checklist",
    "graph_marking_checklist",
    "marking_checklist",
}

MCQ_OPTIONS = {"A", "B", "C", "D"}

UNIT_PATTERN = re.compile(
    r"\b("
    r"m/s|m s\b|ms\b|"
    r"km/h|kmh\b|"
    r"m/s.?2|"
    r"[Nn]\b|"
    r"[Jj]\b|"
    r"[Ww]\b|"
    r"[Vv]\b|"
    r"[Aa]\b|"
    r"ohm|Ohm|[Oo]hms|"
    r"Ω|"
    r"kg\b|g\b|mg\b|"
    r"km\b|cm\b|mm\b|"
    r"[Ss]\b|"
    r"min\b|minutes?\b|"
    r"°C|°K|\bK\b|"
    r"Hz\b|kHz\b|MHz\b|"
    r"Pa\b|kPa\b|"
    r"kJ\b|MJ\b|kW\b|MW\b"
    r")"
)

PLACEHOLDER_ANSWERS = {"test", "abc", "placeholder", "none", "n/a", "na", "null", ""}

FINAL_CONTEXT_PATTERN = re.compile(
    r"(?:answer|therefore|=|final|so|total|result)[^=]{0,30}=\s*"
    r"([-+]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?)",
    re.IGNORECASE,
)

NUMBER_PATTERN = re.compile(r"[-+]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?")


# ---------------------------------------------------------------------------
# Number helpers
# ---------------------------------------------------------------------------

def _parse_float(s: str) -> float | None:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def extract_numbers(text: str) -> list[float]:
    nums = []
    for m in NUMBER_PATTERN.finditer(text):
        v = _parse_float(m.group())
        if v is not None:
            nums.append(v)
    return nums


def extract_final_numbers(text: str) -> list[float]:
    """Extract numbers that appear as likely final answers (after = signs)."""
    seen: set[float] = set()
    result: list[float] = []

    def _add(v: float | None) -> None:
        if v is not None and v not in seen:
            seen.add(v)
            result.append(v)

    # Strategy 1: contextual — "= NUMBER" near answer-signalling phrases
    for m in FINAL_CONTEXT_PATTERN.finditer(text):
        _add(_parse_float(m.group(1)))

    # Strategy 2: ALL "= NUMBER" in the text (always run so final answers
    # like "= 135 m" are never missed even when Strategy 1 fired)
    for m in re.finditer(r"=\s*([-+]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?)", text):
        _add(_parse_float(m.group(1)))

    return result


def numbers_match(student: list[float], expected: list[float]) -> bool:
    for s in student:
        for e in expected:
            if e == 0:
                if abs(s) <= 0.01:
                    return True
            elif abs(e) < 1:
                if abs(s - e) <= 0.01:
                    return True
            else:
                if abs(s - e) / abs(e) <= 0.02:
                    return True
    return False


# ---------------------------------------------------------------------------
# Unit check
# ---------------------------------------------------------------------------

def check_units(resource_type: str, student_answer: str) -> str:
    if "calculation" in resource_type or resource_type in CALC_TYPES:
        return "present" if UNIT_PATTERN.search(student_answer) else "missing"
    return "not_applicable"


# ---------------------------------------------------------------------------
# Confidence signal
# ---------------------------------------------------------------------------

def confidence_signal(self_confidence: str | None, is_correct: bool | None) -> str:
    if is_correct is None:
        return "unknown"
    if self_confidence == "high" and is_correct is False:
        return "overconfident_wrong"
    if self_confidence == "low" and is_correct is True:
        return "underconfident_correct"
    return "appropriate"


# ---------------------------------------------------------------------------
# Core marking
# ---------------------------------------------------------------------------

def mark_attempt(attempt: dict, teacher_resource: dict | None) -> dict:
    resource_id   = attempt["resource_id"]
    resource_type = attempt.get("resource_type", "")
    student_answer = attempt.get("student_answer", "")
    selected_option = attempt.get("selected_option")
    self_confidence = attempt.get("self_confidence")

    # Teacher reference fields (safe defaults)
    teacher_ref: dict = {
        "correct_answer": None,
        "worked_solution": None,
        "marking_guidance": None,
        "common_misconception": None,
    }
    if teacher_resource:
        teacher_ref = {
            "correct_answer":       teacher_resource.get("correct_answer"),
            "worked_solution":      teacher_resource.get("worked_solution"),
            "marking_guidance":     teacher_resource.get("marking_guidance"),
            "common_misconception": teacher_resource.get("common_misconception"),
        }

    # Defaults
    marking_status  = "teacher_review_required"
    marking_method  = "rule_based_v1"
    score: float | None  = None
    max_score       = 1
    is_correct: bool | None = None
    feedback        = ""
    detected_nums: list[float] = []
    expected_nums: list[float] = []
    unit_check      = check_units(resource_type, student_answer)
    needs_review    = True

    # ── 1. Placeholder / too-short guard ────────────────────────────────────
    if len(student_answer.strip()) < 3:
        marking_status = "teacher_review_required"
        needs_review   = True
        feedback       = "Answer is too short to mark reliably."
        return _build_output(
            attempt, teacher_ref, marking_status, marking_method, score, max_score,
            is_correct, feedback, detected_nums, expected_nums,
            unit_check, needs_review, self_confidence
        )

    if student_answer.strip().lower() in PLACEHOLDER_ANSWERS:
        marking_status = "teacher_review_required"
        needs_review   = True
        is_correct     = None
        score          = None
        feedback       = "Answer appears to be a placeholder and needs teacher review."
        return _build_output(
            attempt, teacher_ref, marking_status, marking_method, score, max_score,
            is_correct, feedback, detected_nums, expected_nums,
            unit_check, needs_review, self_confidence
        )

    # ── 2. No matched resource ───────────────────────────────────────────────
    if teacher_resource is None:
        marking_status = "cannot_mark"
        needs_review   = True
        feedback       = "No matching teacher resource found for this attempt."
        return _build_output(
            attempt, teacher_ref, marking_status, marking_method, score, max_score,
            is_correct, feedback, detected_nums, expected_nums,
            unit_check, needs_review, self_confidence
        )

    # ── 3. Graphing / diagram / planning ────────────────────────────────────
    if resource_type in GRAPHING_TYPES:
        marking_status = "teacher_review_required"
        needs_review   = True
        score          = None
        is_correct     = None
        feedback       = "This resource type requires teacher review or richer marking."
        unit_check     = "not_applicable"
        return _build_output(
            attempt, teacher_ref, marking_status, marking_method, score, max_score,
            is_correct, feedback, detected_nums, expected_nums,
            unit_check, needs_review, self_confidence
        )

    # ── 4. MCQ marking ───────────────────────────────────────────────────────
    correct_answer = teacher_resource.get("correct_answer")
    if correct_answer and str(correct_answer).strip().upper() in MCQ_OPTIONS:
        expected_opt = str(correct_answer).strip().upper()
        if selected_option and str(selected_option).strip().upper() in MCQ_OPTIONS:
            chosen = str(selected_option).strip().upper()
            if chosen == expected_opt:
                is_correct     = True
                score          = 1.0
                marking_status = "auto_marked"
                needs_review   = False
                feedback       = "Correct option selected."
            else:
                is_correct     = False
                score          = 0.0
                marking_status = "auto_marked"
                needs_review   = False
                feedback       = f"Incorrect option selected. Expected {expected_opt}."
        else:
            marking_status = "cannot_mark"
            is_correct     = None
            needs_review   = True
            feedback       = "No option selected for this MCQ item."
        return _build_output(
            attempt, teacher_ref, marking_status, marking_method, score, max_score,
            is_correct, feedback, detected_nums, expected_nums,
            unit_check, needs_review, self_confidence
        )

    # ── 5. Calculation marking ───────────────────────────────────────────────
    if resource_type in CALC_TYPES:
        # Build expected number pool from teacher fields
        ref_text = " ".join(filter(None, [
            teacher_resource.get("worked_solution", ""),
            teacher_resource.get("correct_answer", "") if isinstance(teacher_resource.get("correct_answer"), str) else "",
            teacher_resource.get("marking_guidance", ""),
        ]))
        expected_nums = extract_final_numbers(ref_text)
        detected_nums = extract_numbers(student_answer)

        if not expected_nums:
            marking_status = "teacher_review_required"
            needs_review   = True
            feedback       = "Cannot extract expected answer from teacher resources; teacher review required."
        elif not detected_nums:
            marking_status = "teacher_review_required"
            needs_review   = True
            feedback       = "No numerical values found in student answer; teacher review required."
        elif numbers_match(detected_nums, expected_nums):
            is_correct     = True
            score          = 1.0
            marking_status = "auto_marked"
            needs_review   = False
            feedback       = "Numerical answer appears correct. Check working and units if needed."
        else:
            is_correct     = False
            score          = 0.0
            marking_status = "auto_marked"
            needs_review   = False
            feedback       = "Numerical answer does not match the expected result."

        return _build_output(
            attempt, teacher_ref, marking_status, marking_method, score, max_score,
            is_correct, feedback, detected_nums, expected_nums,
            unit_check, needs_review, self_confidence
        )

    # ── 6. Fallback ──────────────────────────────────────────────────────────
    marking_status = "teacher_review_required"
    needs_review   = True
    feedback       = "Resource type not handled by rule-based engine; teacher review required."
    return _build_output(
        attempt, teacher_ref, marking_status, marking_method, score, max_score,
        is_correct, feedback, detected_nums, expected_nums,
        unit_check, needs_review, self_confidence
    )


def _build_output(
    attempt: dict,
    teacher_ref: dict,
    marking_status: str,
    marking_method: str,
    score: float | None,
    max_score: int,
    is_correct: bool | None,
    feedback: str,
    detected_nums: list[float],
    expected_nums: list[float],
    unit_check: str,
    needs_review: bool,
    self_confidence: str | None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "marked_attempt_id":  f"marked_{attempt['attempt_id']}",
        "attempt_id":         attempt["attempt_id"],
        "student_id":         attempt.get("student_id", "local_demo_student"),
        "package_id":         attempt.get("package_id", ""),
        "resource_id":        attempt.get("resource_id", ""),
        "resource_type":      attempt.get("resource_type", ""),
        "topic":              attempt.get("topic", ""),
        "skill_name":         attempt.get("skill_name", ""),
        "skill_type":         attempt.get("skill_type", ""),
        "difficulty":         attempt.get("difficulty"),
        "student_answer":     attempt.get("student_answer", ""),
        "selected_option":    attempt.get("selected_option"),
        "self_confidence":    self_confidence,
        "marking_status":     marking_status,
        "marking_method":     marking_method,
        "score":              score,
        "max_score":          max_score,
        "is_correct":         is_correct,
        "feedback":           feedback,
        "detected_numbers":   detected_nums,
        "expected_numbers":   expected_nums,
        "unit_check":         unit_check,
        "needs_teacher_review": needs_review,
        "teacher_reference":  teacher_ref,
        "confidence_signal":  confidence_signal(self_confidence, is_correct),
        "created_at":         now,
    }


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def build_manifest(report: dict, output_paths: dict, now_iso: str) -> str:
    lines = [
        "# Quanta Aptus Basic Local Marking v1",
        "",
        f"**Generated:** {now_iso}  ",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Attempt count | {report['attempt_count']} |",
        f"| Matched resources | {report['matched_resource_count']} |",
        f"| Unmatched resources | {report['unmatched_resource_count']} |",
        f"| Auto-marked | {report['auto_marked_count']} |",
        f"| Teacher review required | {report['teacher_review_required_count']} |",
        f"| Cannot mark | {report['cannot_mark_count']} |",
        f"| Correct | {report['correct_count']} |",
        f"| Incorrect | {report['incorrect_count']} |",
        "",
        "## Confidence Signals",
        "",
        "| Signal | Count |",
        "|--------|-------|",
    ]
    for k, v in report.get("confidence_signals", {}).items():
        lines.append(f"| {k} | {v} |")

    lines += [
        "",
        "## Output Files",
        "",
        f"- **Marked Attempts:** `{output_paths['marked_attempts']}`",
        f"- **Report:** `{output_paths['report']}`",
        f"- **Manifest:** `{output_paths['manifest']}`",
        "",
        "> **Note:** Rule-based marking is provisional. Graphing, planning, and",
        "> complex written answers require teacher review.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Gate 41 - Basic Local Marking Engine")
    parser.add_argument(
        "--attempts",
        default="data/attempts/local/student_attempts_v1.json",
        help="Path to student_attempts_v1.json",
    )
    parser.add_argument(
        "--teacher-payload",
        default=(
            "data/publish/cambridge_igcse/physics_0625/"
            "resource_package_v2/teacher_resource_payload_v2.json"
        ),
        help="Path to teacher_resource_payload_v2.json",
    )
    args = parser.parse_args()

    attempts_path = Path(args.attempts)
    teacher_path  = Path(args.teacher_payload)

    # Load attempts
    if not attempts_path.exists():
        print(f"[FAILED] Attempts file not found: {attempts_path}")
        sys.exit(1)
    try:
        attempts_doc = json.loads(attempts_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAILED] Cannot load attempts: {exc}")
        sys.exit(1)

    # Load teacher payload
    if not teacher_path.exists():
        print(f"[FAILED] Teacher payload not found: {teacher_path}")
        sys.exit(1)
    try:
        teacher_doc = json.loads(teacher_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAILED] Cannot load teacher payload: {exc}")
        sys.exit(1)

    attempts: list[dict] = attempts_doc.get("attempts", [])
    if not attempts:
        print("[FAILED] No attempts found in file.")
        sys.exit(1)

    # Build teacher resource lookup
    teacher_by_id: dict[str, dict] = {
        r["resource_id"]: r for r in teacher_doc.get("resources", [])
    }

    # Mark each attempt
    now_iso = datetime.now(timezone.utc).isoformat()
    marked_items: list[dict] = []
    unmatched = 0

    for attempt in attempts:
        rid = attempt.get("resource_id", "")
        teacher_res = teacher_by_id.get(rid)
        if teacher_res is None:
            unmatched += 1
        marked_items.append(mark_attempt(attempt, teacher_res))

    # Aggregate counts
    auto_marked_count  = sum(1 for m in marked_items if m["marking_status"] == "auto_marked")
    review_required    = sum(1 for m in marked_items if m["marking_status"] == "teacher_review_required")
    cannot_mark_count  = sum(1 for m in marked_items if m["marking_status"] == "cannot_mark")
    correct_count      = sum(1 for m in marked_items if m["is_correct"] is True)
    incorrect_count    = sum(1 for m in marked_items if m["is_correct"] is False)

    # Breakdowns
    topics: dict[str, int] = {}
    skill_types: dict[str, int] = {}
    conf_signals: dict[str, int] = {}
    for m in marked_items:
        t = m.get("topic", "unknown")
        topics[t] = topics.get(t, 0) + 1
        st = m.get("skill_type", "unknown")
        skill_types[st] = skill_types.get(st, 0) + 1
        cs = m.get("confidence_signal", "unknown")
        conf_signals[cs] = conf_signals.get(cs, 0) + 1

    # Output paths
    out_dir = attempts_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    marked_path   = out_dir / "marked_attempts_v1.json"
    report_path   = out_dir / "marked_attempts_v1_report.json"
    manifest_path = out_dir / "marked_attempts_v1_manifest.md"

    output_paths = {
        "marked_attempts": str(marked_path),
        "report":          str(report_path),
        "manifest":        str(manifest_path),
    }

    # Write marked attempts
    marked_doc = {
        "marked_attempt_file_id":     "quanta_aptus_local_marked_attempts_v1",
        "version":                    "0.1.0",
        "created_at":                 now_iso,
        "updated_at":                 now_iso,
        "source_attempt_file_id":     attempts_doc.get("attempt_file_id", ""),
        "source_teacher_payload":     str(teacher_path),
        "attempt_count":              len(marked_items),
        "auto_marked_count":          auto_marked_count,
        "teacher_review_required_count": review_required,
        "cannot_mark_count":          cannot_mark_count,
        "correct_count":              correct_count,
        "incorrect_count":            incorrect_count,
        "items":                      marked_items,
    }
    marked_path.write_text(
        json.dumps(marked_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write report
    status = "passed"
    if unmatched > 0:
        status = "needs_review"

    report = {
        "status":                     status,
        "attempt_count":              len(marked_items),
        "matched_resource_count":     len(marked_items) - unmatched,
        "unmatched_resource_count":   unmatched,
        "auto_marked_count":          auto_marked_count,
        "teacher_review_required_count": review_required,
        "cannot_mark_count":          cannot_mark_count,
        "correct_count":              correct_count,
        "incorrect_count":            incorrect_count,
        "topics":                     topics,
        "skill_types":                skill_types,
        "confidence_signals":         conf_signals,
        "output_files":               output_paths,
    }
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write manifest
    manifest_path.write_text(
        build_manifest(report, output_paths, now_iso), encoding="utf-8"
    )

    # Terminal summary
    print(f"[{status.upper()}] Basic local marking complete")
    print(f"  attempt_count              : {len(marked_items)}")
    print(f"  matched_resource_count     : {len(marked_items) - unmatched}")
    print(f"  unmatched_resource_count   : {unmatched}")
    print(f"  auto_marked_count          : {auto_marked_count}")
    print(f"  teacher_review_required    : {review_required}")
    print(f"  cannot_mark_count          : {cannot_mark_count}")
    print(f"  correct_count              : {correct_count}")
    print(f"  incorrect_count            : {incorrect_count}")
    print(f"  marked_attempts -> {marked_path}")
    print(f"  report          -> {report_path}")
    print(f"  manifest        -> {manifest_path}")


if __name__ == "__main__":
    main()
