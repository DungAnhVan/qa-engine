"""
Gate 45 - Apply Teacher Attempt Review Decisions v1
Reads marked_attempts_v1.json + teacher_attempt_review_decisions_v1.json,
applies decisions, writes marked_attempts_v2.json + report + manifest.
Does NOT modify marked_attempts_v1.json.
"""
from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (relative to cwd = project root)
# ---------------------------------------------------------------------------

MARKED_V1_PATH    = Path("data/attempts/local/marked_attempts_v1.json")
DECISIONS_PATH    = Path("data/attempts/local/teacher_attempt_review_decisions_v1.json")
OUT_DIR           = Path("data/attempts/local")
MARKED_V2_PATH    = OUT_DIR / "marked_attempts_v2.json"
REPORT_PATH       = OUT_DIR / "teacher_attempt_review_application_report_v1.json"
MANIFEST_PATH     = OUT_DIR / "teacher_attempt_review_application_manifest_v1.md"


# ---------------------------------------------------------------------------
# Decision application logic
# ---------------------------------------------------------------------------

def _final_status_for_auto(item: dict) -> str:
    is_correct = item.get("is_correct")
    if is_correct is True:
        return "correct"
    if is_correct is False:
        return "incorrect"
    return "indeterminate"


def apply_decision(item: dict, decision: dict | None) -> dict:
    """Return a new item dict (never mutates input) with v2 fields applied."""
    out = copy.deepcopy(item)

    if decision is not None:
        d = decision["decision"]

        out["marking_status"]      = "teacher_reviewed"
        out["teacher_decision"]    = d
        out["teacher_review_status"] = "reviewed"
        out["needs_teacher_review"]  = False
        out["teacher_review"] = {
            "teacher_feedback": decision.get("teacher_feedback", ""),
            "teacher_notes":    decision.get("teacher_notes",    ""),
            "score":            decision.get("score"),
            "max_score":        decision.get("max_score", 1),
            "decided_at":       decision.get("decided_at", ""),
            "decided_by":       decision.get("decided_by", ""),
        }

        if d == "needs_resubmission":
            out["final_status"]       = "needs_resubmission"
            out["needs_resubmission"] = True
            out["is_correct"]         = None
            out["score"]              = None

        elif d == "correct":
            out["final_status"]       = "correct"
            out["needs_resubmission"] = False
            out["is_correct"]         = True
            out["score"]              = decision.get("score") if decision.get("score") is not None else 1

        elif d == "partially_correct":
            out["final_status"]       = "partially_correct"
            out["needs_resubmission"] = False
            out["is_correct"]         = True
            out["score"]              = decision.get("score") if decision.get("score") is not None else 0.5

        elif d == "incorrect":
            out["final_status"]       = "incorrect"
            out["needs_resubmission"] = False
            out["is_correct"]         = False
            out["score"]              = decision.get("score") if decision.get("score") is not None else 0

        else:
            out["final_status"]       = "unknown"
            out["needs_resubmission"] = False

    else:
        # No decision available for this item
        orig_status = item.get("marking_status", "")
        out["teacher_decision"]     = None
        out["teacher_review"]       = None
        out["needs_resubmission"]   = False

        if orig_status == "auto_marked":
            out["final_status"]          = _final_status_for_auto(item)
            out["teacher_review_status"] = "not_required"

        elif orig_status == "teacher_review_required":
            out["final_status"]          = "pending_teacher_review"
            out["teacher_review_status"] = "pending"

        else:
            out["final_status"]          = "unknown"
            out["teacher_review_status"] = "unknown"

    return out


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _count_if(items: list[dict], **kwargs: object) -> int:
    count = 0
    for item in items:
        if all(item.get(k) == v for k, v in kwargs.items()):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def build_manifest(report: dict, now_iso: str) -> str:
    lines = [
        "# Quanta Aptus Teacher Attempt Review Application v1",
        "",
        f"**Generated:** {now_iso}  ",
        f"**Source marked attempts:** `{report['source_marked_attempts']}`  ",
        f"**Source decisions:** `{report['source_decisions']}`  ",
        "",
        "## Counts",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Attempt count | {report['attempt_count']} |",
        f"| Decision count | {report['decision_count']} |",
        f"| Matched decisions | {report['matched_decision_count']} |",
        f"| Unmatched decisions | {report['unmatched_decision_count']} |",
        f"| Auto-marked | {report['auto_marked_count']} |",
        f"| Teacher reviewed | {report['teacher_reviewed_count']} |",
        f"| Pending teacher review | {report['pending_teacher_review_count']} |",
        "",
        "## Final Status Breakdown",
        "",
        "| Final Status | Count |",
        "|-------------|-------|",
        f"| correct | {report['correct_count']} |",
        f"| incorrect | {report['incorrect_count']} |",
        f"| partially_correct | {report['partially_correct_count']} |",
        f"| needs_resubmission | {report['needs_resubmission_count']} |",
        f"| pending_teacher_review | {report['pending_teacher_review_count']} |",
        "",
        "## Output Files",
        "",
        f"- **marked_attempts_v2:** `{report['output_files']['marked_attempts_v2']}`",
        f"- **report:** `{report['output_files']['report']}`",
        f"- **manifest:** `{report['output_files']['manifest']}`",
        "",
        "> Source file `marked_attempts_v1.json` was not modified.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Load marked attempts v1
    if not MARKED_V1_PATH.exists():
        print(f"[FAILED] File not found: {MARKED_V1_PATH}")
        sys.exit(1)
    try:
        marked_doc = json.loads(MARKED_V1_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAILED] Cannot load marked attempts: {exc}")
        sys.exit(1)

    # Load decisions (may not exist yet)
    decisions_by_id: dict[str, dict] = {}
    decision_count = 0
    if DECISIONS_PATH.exists():
        try:
            decisions_doc = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
            for d in decisions_doc.get("decisions", []):
                decisions_by_id[d["marked_attempt_id"]] = d
            decision_count = len(decisions_by_id)
        except Exception as exc:
            print(f"[WARNING] Cannot load decisions file: {exc}")
    else:
        print("[WARNING] No decisions file found — all items will be inherited unchanged.")

    items_v1: list[dict] = marked_doc.get("items", [])
    if not items_v1:
        print("[FAILED] No items found in marked_attempts_v1.json")
        sys.exit(1)

    now_iso = datetime.now(timezone.utc).isoformat()

    # Apply decisions
    items_v2: list[dict] = []
    matched_count = 0

    for item in items_v1:
        mid = item.get("marked_attempt_id", "")
        decision = decisions_by_id.get(mid)
        if decision is not None:
            matched_count += 1
        out_item = apply_decision(item, decision)
        items_v2.append(out_item)

    unmatched_decision_count = decision_count - matched_count

    # Aggregate counts
    auto_marked_count    = _count_if(items_v2, marking_status="auto_marked")
    teacher_rev_count    = _count_if(items_v2, marking_status="teacher_reviewed")
    pending_review_count = sum(
        1 for i in items_v2
        if i.get("final_status") == "pending_teacher_review"
    )
    correct_count     = _count_if(items_v2, final_status="correct")
    incorrect_count   = _count_if(items_v2, final_status="incorrect")
    partial_count     = _count_if(items_v2, final_status="partially_correct")
    resubmit_count    = _count_if(items_v2, final_status="needs_resubmission")

    # Build output files
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "marked_attempts_v2": str(MARKED_V2_PATH),
        "report":             str(REPORT_PATH),
        "manifest":           str(MANIFEST_PATH),
    }

    # marked_attempts_v2.json
    v2_doc = {
        "marked_attempt_file_id":         "quanta_aptus_local_marked_attempts_v2",
        "version":                        "0.2.0",
        "created_at":                     now_iso,
        "updated_at":                     now_iso,
        "source_marked_attempts_v1":      str(MARKED_V1_PATH),
        "source_decisions":               str(DECISIONS_PATH) if DECISIONS_PATH.exists() else None,
        "attempt_count":                  len(items_v2),
        "auto_marked_count":              auto_marked_count,
        "teacher_reviewed_count":         teacher_rev_count,
        "pending_teacher_review_count":   pending_review_count,
        "correct_count":                  correct_count,
        "incorrect_count":                incorrect_count,
        "partially_correct_count":        partial_count,
        "needs_resubmission_count":       resubmit_count,
        "items":                          items_v2,
    }
    MARKED_V2_PATH.write_text(
        json.dumps(v2_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Report JSON
    status = "passed"
    if pending_review_count > 0:
        status = "has_pending_review"

    report = {
        "status":                       status,
        "source_marked_attempts":       str(MARKED_V1_PATH),
        "source_decisions":             str(DECISIONS_PATH),
        "attempt_count":                len(items_v2),
        "decision_count":               decision_count,
        "matched_decision_count":       matched_count,
        "unmatched_decision_count":     unmatched_decision_count,
        "auto_marked_count":            auto_marked_count,
        "teacher_reviewed_count":       teacher_rev_count,
        "pending_teacher_review_count": pending_review_count,
        "correct_count":                correct_count,
        "incorrect_count":              incorrect_count,
        "partially_correct_count":      partial_count,
        "needs_resubmission_count":     resubmit_count,
        "output_files":                 output_paths,
    }
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Manifest
    MANIFEST_PATH.write_text(
        build_manifest(report, now_iso), encoding="utf-8"
    )

    # Terminal summary
    print(f"[{status.upper()}] Teacher attempt review decisions applied")
    print(f"  attempt_count              : {len(items_v2)}")
    print(f"  decision_count             : {decision_count}")
    print(f"  matched_decision_count     : {matched_count}")
    print(f"  unmatched_decision_count   : {unmatched_decision_count}")
    print(f"  auto_marked_count          : {auto_marked_count}")
    print(f"  teacher_reviewed_count     : {teacher_rev_count}")
    print(f"  pending_teacher_review_count: {pending_review_count}")
    print(f"  correct_count              : {correct_count}")
    print(f"  incorrect_count            : {incorrect_count}")
    print(f"  partially_correct_count    : {partial_count}")
    print(f"  needs_resubmission_count   : {resubmit_count}")
    print(f"  marked_attempts_v2 -> {MARKED_V2_PATH}")
    print(f"  report             -> {REPORT_PATH}")
    print(f"  manifest           -> {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
