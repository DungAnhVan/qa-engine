"""
Gate 49 - Rebuild Latest Learning State v1
Builds attempt chains, supersedes old attempts, marks current ones,
applies teacher decisions (only for current attempts), and generates
the latest result report.
Does NOT modify student_attempts_v1.json or any prior marked_attempt files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Import marking helpers from Gate 41 script
# ---------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).parent
sys.path.insert(0, str(_TOOLS_DIR))

from mark_student_attempts_v1 import (  # noqa: E402
    mark_attempt,
    CALC_TYPES,
    GRAPHING_TYPES,
    PLACEHOLDER_ANSWERS,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLACEHOLDER_KEYWORDS = {"placeholder", "test", "redo"}

ACTIONS = {
    "calc_correct":       "Continue with medium or hard calculation drills.",
    "resub_pending":      "Wait for teacher review of the resubmitted task.",
    "no_resub":           "No current item is awaiting resubmission.",
    "history_note":       "Older attempts with resubmissions are archived as history.",
    "incorrect_calc":     "Review the relevant formula and worked example, then reattempt.",
    "partial_improve":    "Review the areas where you lost marks and reattempt to reach full marks.",
    "conf_appropriate":   "Maintain confidence calibration.",
    "conf_high":          "Check your method carefully before submitting.",
    "conf_low_correct":   "Trust your working — you got it right with a low-confidence response.",
    "no_pending":         "All current teacher reviews are resolved.",
}

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _pct(num: float, denom: int) -> float | None:
    return round(num / denom, 4) if denom else None


def _is_placeholder(text: str) -> bool:
    tl = (text or "").lower().strip()
    return any(kw in tl for kw in PLACEHOLDER_KEYWORDS)


def _gap_id(attempt_id: str, index: int) -> str:
    return f"gap_{attempt_id}_{index}"


def _get_final_status(item: dict) -> str:
    fs = item.get("final_status")
    if fs:
        return fs
    if item.get("is_correct") is True:
        return "correct"
    if item.get("is_correct") is False:
        return "incorrect"
    if item.get("needs_teacher_review") is True:
        return "pending_teacher_review"
    return "unknown"


def _acc_span(accuracy: float | None) -> str:
    if accuracy is None:
        return "<span>N/A</span>"
    pct = accuracy * 100
    cls = "acc-good" if pct >= 70 else "acc-bad"
    return f'<span class="{cls}">{pct:.0f}%</span>'


# ---------------------------------------------------------------------------
# Chain building
# ---------------------------------------------------------------------------

def build_chains(attempts: list[dict]) -> list[list[dict]]:
    """
    Return a list of chains, each chain is a list of attempts ordered
    oldest→newest. chain[-1] is the current (leaf) attempt; all others
    are superseded.
    """
    by_id: dict[str, dict] = {a["attempt_id"]: a for a in attempts}

    # Build parent->children map
    children: dict[str, list[dict]] = defaultdict(list)
    roots: list[dict] = []

    for attempt in attempts:
        pid = attempt.get("parent_attempt_id") or None
        if pid:
            children[pid].append(attempt)
        else:
            roots.append(attempt)

    def walk(root: dict) -> list[dict]:
        chain = [root]
        current = root
        while True:
            kids = sorted(
                children.get(current["attempt_id"], []),
                key=lambda a: a["created_at"],
            )
            if not kids:
                break
            current = kids[-1]
            chain.append(current)
        return chain

    chains = []
    for root in sorted(roots, key=lambda a: a["created_at"]):
        chains.append(walk(root))

    return chains


# ---------------------------------------------------------------------------
# Teacher decision lookup
# ---------------------------------------------------------------------------

def build_decisions_map(decisions_doc: dict | None) -> dict[str, dict]:
    """
    Build a lookup keyed by attempt_id (stripped from marked_attempt_id or
    from decision["attempt_id"] field directly).
    """
    if not decisions_doc:
        return {}
    result: dict[str, dict] = {}
    for d in decisions_doc.get("decisions", []):
        # Primary key: attempt_id field
        if d.get("attempt_id"):
            result[d["attempt_id"]] = d
        # Secondary key: strip "marked_" prefix from marked_attempt_id
        mid = d.get("marked_attempt_id", "")
        if mid.startswith("marked_"):
            aid = mid[len("marked_"):]
            result.setdefault(aid, d)
    return result


# ---------------------------------------------------------------------------
# Marking + final status assignment
# ---------------------------------------------------------------------------

def build_marked_item(
    attempt: dict,
    teacher_res_map: dict[str, dict],
    decisions_map: dict[str, dict],
    lifecycle_status: str,
    superseded_by: str | None,
) -> dict:
    """Mark an attempt with rule-based logic; apply teacher decision if current."""
    resource_id = attempt.get("resource_id", "")
    teacher_res = teacher_res_map.get(resource_id)

    # Rule-based marking (Gate 41 logic)
    marked = mark_attempt(attempt, teacher_res)

    # Add chain / lifecycle fields
    marked["attempt_type"]       = attempt.get("attempt_type", "first_attempt")
    marked["parent_attempt_id"]  = attempt.get("parent_attempt_id")
    marked["resubmission_of"]    = attempt.get("resubmission_of")
    marked["lifecycle_status"]   = lifecycle_status
    marked["superseded_by_attempt_id"] = superseded_by

    # Apply teacher decision only for current attempts
    if lifecycle_status == "current":
        decision = decisions_map.get(attempt["attempt_id"])
        if decision:
            d_val = decision.get("decision", "")
            marked["marking_status"]       = "teacher_reviewed"
            marked["teacher_decision"]     = d_val
            marked["teacher_review_status"] = "reviewed"
            marked["needs_teacher_review"] = False
            marked["teacher_review"] = {
                "teacher_feedback": decision.get("teacher_feedback", ""),
                "teacher_notes":    decision.get("teacher_notes", ""),
                "score":            decision.get("score"),
                "decided_at":       decision.get("decided_at", ""),
                "decided_by":       decision.get("decided_by", ""),
            }
            if d_val == "correct":
                marked["is_correct"] = True
                marked["score"]      = decision.get("score") or 1.0
                marked["final_status"] = "correct"
            elif d_val == "incorrect":
                marked["is_correct"] = False
                marked["score"]      = decision.get("score") or 0.0
                marked["final_status"] = "incorrect"
            elif d_val == "partially_correct":
                marked["is_correct"] = True
                marked["score"]      = decision.get("score") or 0.5
                marked["final_status"] = "partially_correct"
            elif d_val == "needs_resubmission":
                marked["is_correct"]         = None
                marked["score"]              = None
                marked["needs_resubmission"] = True
                marked["final_status"]       = "needs_resubmission"
            else:
                marked["final_status"] = "unknown"
        else:
            marked["teacher_decision"]     = None
            marked["teacher_review"]       = None
            marked["teacher_review_status"] = (
                "pending" if marked.get("needs_teacher_review") else "not_required"
            )
            marked["needs_resubmission"] = False
            marked["final_status"]       = _get_final_status(marked)
    else:
        # Superseded — set final_status but don't apply new decisions
        marked["teacher_decision"]     = None
        marked["teacher_review"]       = None
        marked["teacher_review_status"] = "superseded"
        marked["needs_resubmission"]   = False
        marked["final_status"]         = "superseded"

    return marked


# ---------------------------------------------------------------------------
# Analysis (current items only)
# ---------------------------------------------------------------------------

def analyse(current_items: list[dict], superseded_count: int, resub_count: int) -> dict:
    attempt_count = len(current_items)

    auto_marked_count          = 0
    teacher_reviewed_count     = 0
    pending_teacher_review_count = 0
    correct_count              = 0
    incorrect_count            = 0
    partially_correct_count    = 0
    needs_resubmission_count   = 0
    acc_correct: float         = 0
    acc_denom                  = 0

    for item in current_items:
        ms = item.get("marking_status", "")
        fs = _get_final_status(item)

        if ms == "auto_marked":
            auto_marked_count += 1
        elif ms == "teacher_reviewed":
            teacher_reviewed_count += 1

        if fs == "correct":
            correct_count += 1
            acc_correct   += 1
            acc_denom     += 1
        elif fs == "incorrect":
            incorrect_count += 1
            acc_denom       += 1
        elif fs == "partially_correct":
            partially_correct_count += 1
            if item.get("score") is not None:
                acc_correct += float(item.get("score", 0))
                acc_denom   += 1
        elif fs == "needs_resubmission":
            needs_resubmission_count += 1
        elif fs == "pending_teacher_review":
            pending_teacher_review_count += 1

    accuracy = _pct(acc_correct, acc_denom)

    # ── Topic summary ─────────────────────────────────────────────────────────
    topic_buckets: dict[str, list[dict]] = defaultdict(list)
    for item in current_items:
        topic_buckets[item.get("topic", "Unknown")].append(item)

    topics_summary: list[dict] = []
    for topic, t_items in sorted(topic_buckets.items()):
        t_auto     = sum(1 for i in t_items if i.get("marking_status") == "auto_marked")
        t_reviewed = sum(1 for i in t_items if i.get("marking_status") == "teacher_reviewed")
        t_pending  = sum(1 for i in t_items if _get_final_status(i) == "pending_teacher_review")
        t_correct  = sum(1 for i in t_items if _get_final_status(i) == "correct")
        t_wrong    = sum(1 for i in t_items if _get_final_status(i) == "incorrect")
        t_partial  = sum(1 for i in t_items if _get_final_status(i) == "partially_correct")
        t_resub    = sum(1 for i in t_items if _get_final_status(i) == "needs_resubmission")
        t_denom    = t_correct + t_wrong
        topics_summary.append({
            "topic":                        topic,
            "attempt_count":                len(t_items),
            "auto_marked_count":            t_auto,
            "teacher_reviewed_count":       t_reviewed,
            "pending_teacher_review_count": t_pending,
            "correct_count":                t_correct,
            "incorrect_count":              t_wrong,
            "partially_correct_count":      t_partial,
            "needs_resubmission_count":     t_resub,
            "accuracy":                     _pct(t_correct, t_denom),
        })

    # ── Skill type summary ────────────────────────────────────────────────────
    skill_buckets: dict[str, list[dict]] = defaultdict(list)
    for item in current_items:
        skill_buckets[item.get("skill_type", "unknown")].append(item)

    skill_types_summary: list[dict] = []
    for st, s_items in sorted(skill_buckets.items()):
        s_correct = sum(1 for i in s_items if _get_final_status(i) == "correct")
        s_wrong   = sum(1 for i in s_items if _get_final_status(i) == "incorrect")
        skill_types_summary.append({
            "skill_type":     st,
            "attempt_count":  len(s_items),
            "correct_count":  s_correct,
            "incorrect_count": s_wrong,
            "accuracy":       _pct(s_correct, s_correct + s_wrong),
        })

    # ── Confidence signals ────────────────────────────────────────────────────
    conf_counts: dict[str, int] = defaultdict(int)
    for item in current_items:
        conf_counts[item.get("confidence_signal", "unknown")] += 1

    # ── Skill gaps ────────────────────────────────────────────────────────────
    skill_gaps:  list[dict] = []
    strengths:   list[dict] = []
    gap_idx = 0

    for item in current_items:
        fs      = _get_final_status(item)
        csig    = item.get("confidence_signal", "unknown")
        topic   = item.get("topic", "Unknown")
        sname   = item.get("skill_name", "")
        stype   = item.get("skill_type", "")
        diff    = item.get("difficulty") or "unknown"
        rtype   = item.get("resource_type", "")
        feed    = item.get("feedback", "")
        aid     = item.get("attempt_id", "")
        tr      = item.get("teacher_review") or {}
        is_resub = item.get("attempt_type") == "resubmission"

        # Strengths
        if fs == "correct":
            note = ""
            if csig == "appropriate":
                note = "Confidence well-calibrated."
            elif csig == "underconfident_correct":
                note = "Hidden strength — answered correctly despite low confidence."
            strengths.append({
                "topic":      topic,
                "skill_name": sname,
                "skill_type": stype,
                "evidence":   f"Correctly answered {rtype.replace('_', ' ')} on {topic}.",
                "note":       note,
            })

        # Skill gaps
        reasons: list[tuple[str, str, str]] = []

        if fs == "incorrect":
            sev = "high" if diff == "hard" else "medium"
            reasons.append((
                "incorrect_answer", sev,
                f"Incorrect answer on a {diff} {rtype.replace('_', ' ')}. {feed}",
            ))

        elif fs == "partially_correct":
            reasons.append((
                "partially_correct", "medium",
                f"Partially correct on {rtype.replace('_', ' ')} — {feed}",
            ))

        elif fs == "needs_resubmission":
            tf = tr.get("teacher_feedback", "") or feed
            sev = "high" if _is_placeholder(item.get("student_answer", "")) else "medium"
            reasons.append(("needs_resubmission", sev, tf or "Marked as needs resubmission."))

        elif fs == "pending_teacher_review":
            if is_resub:
                reasons.append((
                    "pending_teacher_review", "medium",
                    "Wait for teacher review of the resubmitted task.",
                ))
            else:
                sev = "high" if _is_placeholder(feed) else "medium"
                reasons.append(("pending_teacher_review", sev, feed or "Requires teacher review."))

        if csig == "overconfident_wrong" and fs != "correct":
            reasons.append((
                "overconfident_wrong", "high",
                "High confidence submitted with an incorrect answer.",
            ))

        for reason, sev, evidence in reasons:
            rec = _recommended_action(reason, rtype, diff, csig, is_resub)
            skill_gaps.append({
                "gap_id":             _gap_id(aid, gap_idx),
                "topic":              topic,
                "skill_name":         sname,
                "skill_type":         stype,
                "difficulty":         diff,
                "reason":             reason,
                "severity":           sev,
                "evidence":           evidence,
                "recommended_action": rec,
            })
            gap_idx += 1

    # ── Teacher review queue (pending review, not awaiting resubmission) ──────
    teacher_review_queue = [
        {
            "attempt_id":    item.get("attempt_id", ""),
            "resource_id":   item.get("resource_id", ""),
            "topic":         item.get("topic", ""),
            "skill_name":    item.get("skill_name", ""),
            "resource_type": item.get("resource_type", ""),
            "student_answer": item.get("student_answer", ""),
            "feedback":       item.get("feedback", ""),
            "attempt_type":   item.get("attempt_type", "first_attempt"),
            "is_resubmission": item.get("attempt_type") == "resubmission",
        }
        for item in current_items
        if _get_final_status(item) == "pending_teacher_review"
    ]

    # ── Resubmission queue (teacher explicitly said needs_resubmission) ───────
    resubmission_queue = [
        {
            "attempt_id":       item.get("attempt_id", ""),
            "resource_id":      item.get("resource_id", ""),
            "topic":            item.get("topic", ""),
            "skill_name":       item.get("skill_name", ""),
            "resource_type":    item.get("resource_type", ""),
            "student_answer":   item.get("student_answer", ""),
            "teacher_feedback": (item.get("teacher_review") or {}).get("teacher_feedback", ""),
            "teacher_notes":    (item.get("teacher_review") or {}).get("teacher_notes", ""),
            "recommended_action": "Redo and resubmit.",
        }
        for item in current_items
        if _get_final_status(item) == "needs_resubmission"
    ]

    # ── Recommended next actions ──────────────────────────────────────────────
    actions: list[str] = []
    seen: set[str] = set()

    def _add(a: str) -> None:
        if a not in seen:
            seen.add(a)
            actions.append(a)

    for item in current_items:
        fs    = _get_final_status(item)
        rtype = item.get("resource_type", "")
        csig  = item.get("confidence_signal", "unknown")
        is_resub = item.get("attempt_type") == "resubmission"

        if fs == "correct" and "calculation" in rtype:
            _add(ACTIONS["calc_correct"])
        if fs == "pending_teacher_review" and is_resub:
            _add(ACTIONS["resub_pending"])
        if fs in ("incorrect",):
            _add(ACTIONS["incorrect_calc"])
        if fs == "partially_correct":
            _add(ACTIONS["partial_improve"])
        if csig == "appropriate":
            _add(ACTIONS["conf_appropriate"])
        if csig == "overconfident_wrong":
            _add(ACTIONS["conf_high"])
        if csig == "underconfident_correct":
            _add(ACTIONS["conf_low_correct"])

    if needs_resubmission_count == 0:
        _add(ACTIONS["no_resub"])
    if pending_teacher_review_count == 0 and needs_resubmission_count == 0:
        _add(ACTIONS["no_pending"])
    if superseded_count > 0:
        _add(ACTIONS["history_note"])

    return {
        "attempt_count":                  attempt_count,
        "auto_marked_count":              auto_marked_count,
        "teacher_reviewed_count":         teacher_reviewed_count,
        "pending_teacher_review_count":   pending_teacher_review_count,
        "correct_count":                  correct_count,
        "incorrect_count":                incorrect_count,
        "partially_correct_count":        partially_correct_count,
        "needs_resubmission_count":       needs_resubmission_count,
        "accuracy":                       accuracy,
        "topics":                         topics_summary,
        "skill_types":                    skill_types_summary,
        "confidence_signals":             dict(conf_counts),
        "skill_gaps":                     skill_gaps,
        "teacher_review_queue":           teacher_review_queue,
        "resubmission_queue":             resubmission_queue,
        "strengths":                      strengths,
        "recommended_next_actions":       actions,
    }


def _recommended_action(reason: str, rtype: str, diff: str, csig: str, is_resub: bool) -> str:
    if reason == "pending_teacher_review":
        return ACTIONS["resub_pending"] if is_resub else "Await teacher review before progressing."
    if reason == "needs_resubmission":
        return "Redo and resubmit this task with full working or the required graph."
    if reason in ("incorrect_answer",):
        return ACTIONS["incorrect_calc"]
    if reason == "partially_correct":
        return ACTIONS["partial_improve"]
    if reason == "overconfident_wrong":
        return ACTIONS["conf_high"]
    return "Review this item with your teacher."


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def build_markdown(a: dict, student_id: str, source: str, now_iso: str,
                   raw_count: int, superseded_count: int, resub_count: int) -> str:
    pct = f"{a['accuracy'] * 100:.0f}%" if a["accuracy"] is not None else "N/A"

    lines = [
        "# Quanta Aptus Latest Learning Report v1",
        "",
        f"**Student ID:** `{student_id}`  ",
        f"**Generated:** {now_iso}  ",
        f"**Source:** `{source}`  ",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Raw attempts | {raw_count} |",
        f"| Current attempts | {a['attempt_count']} |",
        f"| Superseded attempts | {superseded_count} |",
        f"| Resubmission attempts | {resub_count} |",
        f"| Auto-marked | {a['auto_marked_count']} |",
        f"| Teacher reviewed | {a['teacher_reviewed_count']} |",
        f"| Pending teacher review | {a['pending_teacher_review_count']} |",
        f"| Correct | {a['correct_count']} |",
        f"| Incorrect | {a['incorrect_count']} |",
        f"| Needs resubmission | {a['needs_resubmission_count']} |",
        f"| Accuracy | {pct} |",
        "",
        "> Only **current** attempts are used for statistics.",
        "> Superseded attempts (replaced by resubmission) are archived as history.",
        "",
    ]

    lines += ["## Strengths", ""]
    if a["strengths"]:
        for s in a["strengths"]:
            note_part = f" _{s['note']}_" if s.get("note") else ""
            lines.append(f"- **{s['topic']}** — {s['evidence']}{note_part}")
    else:
        lines.append("_No confirmed strengths yet._")
    lines.append("")

    lines += ["## Skill Gaps", ""]
    if a["skill_gaps"]:
        for g in a["skill_gaps"]:
            icon = {"high": "!", "medium": "~", "low": "-"}.get(g["severity"], "-")
            lines.append(
                f"- [{icon}] **{g['topic']}** ({g['skill_type']}, {g['difficulty']}) — "
                f"_{g['reason'].replace('_', ' ')}_: {g['evidence']}"
            )
            lines.append(f"  - Recommended: {g['recommended_action']}")
    else:
        lines.append("_No skill gaps identified._")
    lines.append("")

    lines += ["## Teacher Review Queue", ""]
    if a["teacher_review_queue"]:
        for q in a["teacher_review_queue"]:
            tag = " [RESUBMISSION]" if q.get("is_resubmission") else ""
            lines.append(f"- **{q['topic']}**{tag} | `{q['resource_type']}` | _{q['skill_name']}_")
            lines.append(f"  - Answer: {q['student_answer']}")
    else:
        lines.append("_No items pending teacher review._")
    lines.append("")

    lines += ["## Resubmission Queue", ""]
    if a["resubmission_queue"]:
        for q in a["resubmission_queue"]:
            lines.append(f"- **{q['topic']}** | `{q['resource_type']}` | _{q['skill_name']}_")
    else:
        lines.append("_No items awaiting resubmission._")
    lines.append("")

    lines += ["## Topic Summary", ""]
    lines += [
        "| Topic | Attempts | Auto | Reviewed | Pending | Correct | Incorrect | Accuracy |",
        "|-------|----------|------|----------|---------|---------|-----------|----------|",
    ]
    for t in a["topics"]:
        acc = f"{t['accuracy'] * 100:.0f}%" if t["accuracy"] is not None else "—"
        lines.append(
            f"| {t['topic']} | {t['attempt_count']} | {t['auto_marked_count']} | "
            f"{t['teacher_reviewed_count']} | {t['pending_teacher_review_count']} | "
            f"{t['correct_count']} | {t['incorrect_count']} | {acc} |"
        )
    lines.append("")

    lines += ["## Recommended Next Actions", ""]
    for act in a["recommended_next_actions"]:
        lines.append(f"- {act}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML preview
# ---------------------------------------------------------------------------

HTML_CSS = """
body{font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:0;background:#f0f4f8;color:#1a202c}
.topbar{background:#2b6cb0;color:#fff;padding:1rem 2rem;display:flex;align-items:center;gap:1rem}
.topbar h1{margin:0;font-size:1.35rem}
.topbar .v-badge{background:#276749;border-radius:999px;padding:2px 10px;font-size:.72rem;font-weight:700}
.container{max-width:980px;margin:2rem auto;padding:0 1rem}
.note-box{background:#fffbeb;border:1px solid #f6e05e;border-radius:5px;padding:8px 12px;font-size:.78rem;color:#744210;margin-bottom:16px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;margin-bottom:20px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:14px 16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.card .val{font-size:1.7rem;font-weight:700;color:#2b6cb0;line-height:1.1}
.card .lbl{font-size:.63rem;color:#718096;text-transform:uppercase;letter-spacing:.05em;margin-top:4px}
.sec{background:#fff;border:1px solid #e2e8f0;border-radius:6px;margin-bottom:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.sec-hdr{background:#1a1a2e;color:#fff;padding:9px 16px;font-size:.83rem;font-weight:600;letter-spacing:.03em}
.sec-body{padding:14px 16px}
table{width:100%;border-collapse:collapse;font-size:.8rem}
th{background:#f7fafc;padding:7px 8px;text-align:left;font-size:.67rem;font-weight:700;text-transform:uppercase;color:#718096;border-bottom:1px solid #e2e8f0}
td{padding:7px 8px;border-bottom:1px solid #e2e8f0;vertical-align:top}
tr:last-child td{border-bottom:none}
tr:hover td{background:#f7fafc}
.gap-card{border:1px solid #e2e8f0;border-radius:6px;padding:12px 14px;margin-bottom:10px;border-left:4px solid #e2e8f0}
.gap-card.high{border-left-color:#e53e3e}
.gap-card.medium{border-left-color:#d69e2e}
.gap-card.low{border-left-color:#38a169}
.gap-title{font-weight:600;font-size:.88rem;margin-bottom:4px}
.gap-meta{font-size:.72rem;color:#718096;margin-bottom:6px}
.gap-evidence{font-size:.82rem;color:#4a5568;margin-bottom:6px}
.gap-action{font-size:.78rem;color:#2b6cb0;font-style:italic}
.badge-sev{display:inline-block;font-size:.65rem;font-weight:700;padding:1px 7px;border-radius:999px;text-transform:uppercase;margin-left:6px}
.sev-high{background:#fed7d7;color:#742a2a}
.sev-medium{background:#fefcbf;color:#744210}
.sev-low{background:#c6f6d5;color:#276749}
.strength-card{border:1px solid #9ae6b4;border-radius:6px;padding:10px 14px;margin-bottom:8px;background:#f0fff4}
.strength-title{font-weight:600;font-size:.85rem;color:#276749}
.strength-note{font-size:.75rem;color:#276749;margin-top:3px;font-style:italic}
.review-card{border:1px solid #bee3f8;border-radius:6px;padding:10px 14px;margin-bottom:8px;background:#ebf8ff;border-left:4px solid #2b6cb0}
.review-card.resubmission{border-left-color:#d97706;background:#fffaf0;border-color:#fbd38d}
.review-title{font-weight:600;font-size:.83rem;color:#2b6cb0}
.review-card.resubmission .review-title{color:#744210}
.review-answer{font-size:.8rem;color:#2d3748;margin-top:4px;white-space:pre-wrap;background:#fff;border:1px solid #bee3f8;border-radius:4px;padding:6px 8px}
.review-card.resubmission .review-answer{border-color:#fbd38d}
.resub-tag{display:inline-block;font-size:.62rem;font-weight:700;padding:1px 6px;border-radius:999px;background:#fbd38d;color:#744210;text-transform:uppercase;margin-left:6px;vertical-align:middle}
.action-list{padding:0;margin:0;list-style:none}
.action-list li{padding:6px 0;border-bottom:1px solid #e2e8f0;font-size:.85rem;color:#2d3748}
.action-list li:last-child{border-bottom:none}
.action-list li::before{content:'-> ';color:#2b6cb0;font-weight:700}
.resolved{background:#f0fff4;color:#276749;border:1px solid #9ae6b4;border-radius:5px;padding:10px 14px;font-size:.87rem;font-weight:600}
.footer{text-align:center;color:#a0aec0;font-size:.76rem;margin:2rem 0 1rem}
.acc-good{color:#276749;font-weight:700}
.acc-bad{color:#e53e3e;font-weight:700}
"""


def build_html(a: dict, student_id: str, source: str, now_iso: str,
               raw_count: int, superseded_count: int, resub_count: int) -> str:
    pct_display = f"{a['accuracy'] * 100:.0f}%" if a["accuracy"] is not None else "N/A"

    cards_html = "\n".join([
        f'<div class="card"><div class="val">{raw_count}</div><div class="lbl">Raw Attempts</div></div>',
        f'<div class="card"><div class="val">{a["attempt_count"]}</div><div class="lbl">Current</div></div>',
        f'<div class="card"><div class="val">{superseded_count}</div><div class="lbl">Superseded</div></div>',
        f'<div class="card"><div class="val">{a["correct_count"]}</div><div class="lbl">Correct</div></div>',
        f'<div class="card"><div class="val">{a["pending_teacher_review_count"]}</div><div class="lbl">Pending Review</div></div>',
        f'<div class="card"><div class="val">{pct_display}</div><div class="lbl">Accuracy</div></div>',
    ])

    # Topic table
    topic_rows = ""
    for t in a["topics"]:
        topic_rows += (
            f"<tr><td>{t['topic']}</td>"
            f"<td style='text-align:center'>{t['attempt_count']}</td>"
            f"<td style='text-align:center'>{t['auto_marked_count']}</td>"
            f"<td style='text-align:center'>{t['teacher_reviewed_count']}</td>"
            f"<td style='text-align:center'>{t['pending_teacher_review_count']}</td>"
            f"<td style='text-align:center'>{t['correct_count']}</td>"
            f"<td style='text-align:center'>{t['incorrect_count']}</td>"
            f"<td style='text-align:center'>{_acc_span(t['accuracy'])}</td></tr>"
        )

    # Strengths
    strengths_html = ""
    if a["strengths"]:
        for s in a["strengths"]:
            strengths_html += (
                f'<div class="strength-card">'
                f'<div class="strength-title">{s["topic"]} &mdash; {s["evidence"]}</div>'
                + (f'<div class="strength-note">{s["note"]}</div>' if s.get("note") else "")
                + "</div>"
            )
    else:
        strengths_html = "<p style='color:#718096;font-size:.88rem'>No confirmed strengths yet.</p>"

    # Skill gaps
    gaps_html = ""
    if a["skill_gaps"]:
        for g in a["skill_gaps"]:
            sev_badge = f'<span class="badge-sev sev-{g["severity"]}">{g["severity"]}</span>'
            gaps_html += (
                f'<div class="gap-card {g["severity"]}">'
                f'<div class="gap-title">{g["topic"]}{sev_badge}</div>'
                f'<div class="gap-meta">{g["skill_type"]} &middot; {g["difficulty"]} &middot; '
                f'{g["reason"].replace("_", " ")}</div>'
                f'<div class="gap-evidence">{g["evidence"]}</div>'
                f'<div class="gap-action">Recommendation: {g["recommended_action"]}</div>'
                f'</div>'
            )
    else:
        gaps_html = "<p style='color:#718096;font-size:.88rem'>No skill gaps identified.</p>"

    # Teacher review queue
    tq_html = ""
    if a["teacher_review_queue"]:
        for q in a["teacher_review_queue"]:
            is_resub = q.get("is_resubmission", False)
            card_cls = "review-card resubmission" if is_resub else "review-card"
            resub_tag = '<span class="resub-tag">resubmission</span>' if is_resub else ""
            tq_html += (
                f'<div class="{card_cls}">'
                f'<div class="review-title">{q["topic"]}{resub_tag}</div>'
                f'<div style="font-size:.72rem;color:#718096;margin:3px 0">'
                f'{q["resource_type"].replace("_"," ")} &middot; {q["skill_name"]}</div>'
                f'<div class="review-answer">{q["student_answer"]}</div>'
                f'</div>'
            )
    else:
        tq_html = '<div class="resolved">No items pending teacher review.</div>'

    # Resubmission queue
    resub_html = ""
    if a["resubmission_queue"]:
        for q in a["resubmission_queue"]:
            resub_html += (
                f'<div class="gap-card medium">'
                f'<div class="gap-title">{q["topic"]}</div>'
                f'<div class="gap-meta">{q["resource_type"].replace("_"," ")} &middot; {q["skill_name"]}</div>'
                f'<div class="gap-evidence">{q["student_answer"]}</div>'
                f'<div class="gap-action">Recommendation: {q["recommended_action"]}</div>'
                f'</div>'
            )
    else:
        resub_html = '<div class="resolved">No items awaiting resubmission.</div>'

    # Actions
    actions_html = "<ul class='action-list'>" + "".join(
        f"<li>{act}</li>" for act in a["recommended_next_actions"]
    ) + "</ul>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quanta Aptus Latest Learning Report &mdash; {student_id}</title>
<style>{HTML_CSS}</style>
</head>
<body>
<div class="topbar">
  <h1>Quanta Aptus Latest Learning Report</h1>
  <span class="topbar-badge" style="background:rgba(255,255,255,.2);border-radius:999px;padding:2px 10px;font-size:.78rem">{student_id}</span>
  <span class="v-badge">latest</span>
</div>
<div class="container">
  <p style="font-size:.8rem;color:#718096;margin-bottom:10px">
    Generated {now_iso} &middot; Source: {source}
  </p>
  <div class="note-box">
    Only <strong>current</strong> attempts are counted in statistics.
    Superseded attempts (replaced by resubmission) are archived as history only.
    Accuracy denominator excludes pending review and needs-resubmission items.
  </div>

  <div class="cards">{cards_html}</div>

  <div class="sec">
    <div class="sec-hdr">Topic Summary (current attempts)</div>
    <div class="sec-body" style="padding:0">
      <table>
        <thead><tr>
          <th>Topic</th><th>Attempts</th><th>Auto</th><th>Reviewed</th>
          <th>Pending</th><th>Correct</th><th>Incorrect</th><th>Accuracy</th>
        </tr></thead>
        <tbody>{topic_rows}</tbody>
      </table>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hdr">Strengths ({len(a['strengths'])})</div>
    <div class="sec-body">{strengths_html}</div>
  </div>

  <div class="sec">
    <div class="sec-hdr">Skill Gaps ({len(a['skill_gaps'])})</div>
    <div class="sec-body">{gaps_html}</div>
  </div>

  <div class="sec">
    <div class="sec-hdr">Teacher Review Queue ({len(a['teacher_review_queue'])})</div>
    <div class="sec-body">{tq_html}</div>
  </div>

  <div class="sec">
    <div class="sec-hdr">Resubmission Queue ({len(a['resubmission_queue'])})</div>
    <div class="sec-body">{resub_html}</div>
  </div>

  <div class="sec">
    <div class="sec-hdr">Recommended Next Actions</div>
    <div class="sec-body">{actions_html}</div>
  </div>

  <p class="footer">Quanta Aptus &mdash; Latest Learning State &mdash;
  Superseded: {superseded_count} &middot; Resubmissions: {resub_count} of {raw_count} total.</p>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def build_manifest(report: dict, now_iso: str) -> str:
    lines = [
        "# Quanta Aptus Latest Learning State v1",
        "",
        f"**Generated:** {now_iso}  ",
        "",
        "## Counts",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Raw attempt count | {report['raw_attempt_count']} |",
        f"| Current attempt count | {report['current_attempt_count']} |",
        f"| Superseded attempt count | {report['superseded_attempt_count']} |",
        f"| Resubmission attempt count | {report['resubmission_attempt_count']} |",
        f"| Auto-marked | {report['auto_marked_count']} |",
        f"| Teacher reviewed | {report['teacher_reviewed_count']} |",
        f"| Pending teacher review | {report['pending_teacher_review_count']} |",
        f"| Correct | {report['correct_count']} |",
        f"| Incorrect | {report['incorrect_count']} |",
        f"| Needs resubmission | {report['needs_resubmission_count']} |",
        "",
        "## Output Files",
        "",
    ]
    for k, v in report.get("output_files", {}).items():
        lines.append(f"- **{k}:** `{v}`")
    lines.append("")
    lines.append("> Superseded attempts are kept in history and not counted in statistics.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Gate 49 - Rebuild Latest Learning State v1")
    parser.add_argument("--attempts",          default="data/attempts/local/student_attempts_v1.json")
    parser.add_argument("--teacher-payload",   default="data/publish/cambridge_igcse/physics_0625/resource_package_v2/teacher_resource_payload_v2.json")
    parser.add_argument("--teacher-decisions", default="data/attempts/local/teacher_attempt_review_decisions_v1.json")
    parser.add_argument("--student-id",        default="local_demo_student")
    args = parser.parse_args()

    attempts_path   = Path(args.attempts)
    payload_path    = Path(args.teacher_payload)
    decisions_path  = Path(args.teacher_decisions)
    student_id      = args.student_id

    # ── Load attempts ─────────────────────────────────────────────────────────
    if not attempts_path.exists():
        print(f"[FAILED] Attempts file not found: {attempts_path}")
        sys.exit(1)
    try:
        attempts_doc = json.loads(attempts_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAILED] Cannot load attempts: {exc}")
        sys.exit(1)

    all_attempts: list[dict] = attempts_doc.get("attempts", [])
    student_attempts = [a for a in all_attempts if a.get("student_id") == student_id]

    if not student_attempts:
        print(f"[FAILED] No attempts found for student_id={student_id!r}")
        sys.exit(1)

    raw_attempt_count = len(student_attempts)

    # ── Load teacher payload ──────────────────────────────────────────────────
    teacher_res_map: dict[str, dict] = {}
    if payload_path.exists():
        try:
            payload_doc = json.loads(payload_path.read_text(encoding="utf-8"))
            resources = payload_doc.get("resources") or payload_doc.get("items") or []
            for r in resources:
                rid = r.get("resource_id", "")
                if rid:
                    teacher_res_map[rid] = r
        except Exception as exc:
            print(f"[WARNING] Cannot load teacher payload: {exc}")

    # ── Load teacher decisions ────────────────────────────────────────────────
    decisions_doc: dict | None = None
    if decisions_path.exists():
        try:
            decisions_doc = json.loads(decisions_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[WARNING] Cannot load decisions: {exc}")
    decisions_map = build_decisions_map(decisions_doc)

    now_iso = datetime.now(timezone.utc).isoformat()

    # ── Build chains ──────────────────────────────────────────────────────────
    chains = build_chains(student_attempts)

    current_raw: list[dict] = []
    superseded_raw: list[dict] = []
    resubmission_attempt_count = 0

    chain_summaries: list[dict] = []
    for chain in chains:
        current_attempt  = chain[-1]
        superseded_chain = chain[:-1]
        current_raw.append(current_attempt)
        superseded_raw.extend(superseded_chain)
        if current_attempt.get("attempt_type") == "resubmission":
            resubmission_attempt_count += 1

        chain_summaries.append({
            "root_attempt_id":    chain[0]["attempt_id"],
            "resource_id":        chain[0].get("resource_id", ""),
            "length":             len(chain),
            "current_attempt_id": current_attempt["attempt_id"],
            "history":            [a["attempt_id"] for a in chain],
        })

    superseded_count = len(superseded_raw)
    current_count    = len(current_raw)

    # ── Mark current attempts ─────────────────────────────────────────────────
    current_items: list[dict] = []
    for attempt in current_raw:
        marked = build_marked_item(
            attempt, teacher_res_map, decisions_map,
            lifecycle_status="current",
            superseded_by=None,
        )
        current_items.append(marked)

    # ── Mark history items (superseded, no decisions applied) ─────────────────
    history_items: list[dict] = []
    # Map: superseded attempt_id -> id of the attempt that supersedes it
    supersedes_map: dict[str, str] = {}
    for chain in chains:
        leaf_id = chain[-1]["attempt_id"]
        for sup in chain[:-1]:
            supersedes_map[sup["attempt_id"]] = leaf_id

    for attempt in superseded_raw:
        marked = build_marked_item(
            attempt, teacher_res_map, decisions_map,
            lifecycle_status="superseded_by_resubmission",
            superseded_by=supersedes_map.get(attempt["attempt_id"]),
        )
        history_items.append(marked)

    # ── Analysis ──────────────────────────────────────────────────────────────
    a = analyse(current_items, superseded_count, resubmission_attempt_count)

    # ── Status ────────────────────────────────────────────────────────────────
    if a["pending_teacher_review_count"] > 0:
        status = "needs_review"
    else:
        status = "passed"

    # ── Output paths ─────────────────────────────────────────────────────────
    LOCAL_DIR  = Path("data/attempts/local")
    REPORTS_DIR = LOCAL_DIR / "reports"
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    state_path       = LOCAL_DIR  / "latest_learning_state_v1.json"
    marked_path      = LOCAL_DIR  / "marked_attempts_latest_v1.json"
    report_path      = LOCAL_DIR  / "latest_learning_state_report_v1.json"
    manifest_path    = LOCAL_DIR  / "latest_learning_state_manifest_v1.md"

    result_json_path = REPORTS_DIR / "student_result_report_latest_v1.json"
    result_md_path   = REPORTS_DIR / "student_result_report_latest_v1.md"
    result_html_path = REPORTS_DIR / "student_result_report_latest_preview_v1.html"
    result_rep_path  = REPORTS_DIR / "student_result_report_latest_report_v1.json"

    output_paths = {
        "latest_learning_state":          str(state_path),
        "marked_attempts_latest":         str(marked_path),
        "student_result_report_latest_json":    str(result_json_path),
        "student_result_report_latest_md":      str(result_md_path),
        "student_result_report_latest_preview": str(result_html_path),
        "student_result_report_latest_report":  str(result_rep_path),
        "report":                         str(report_path),
        "manifest":                       str(manifest_path),
    }

    # ── Write latest_learning_state_v1.json ───────────────────────────────────
    state_doc = {
        "state_id":                    "quanta_aptus_latest_learning_state_v1",
        "version":                     "0.1.0",
        "created_at":                  now_iso,
        "student_id":                  student_id,
        "raw_attempt_count":           raw_attempt_count,
        "current_attempt_count":       current_count,
        "superseded_attempt_count":    superseded_count,
        "resubmission_attempt_count":  resubmission_attempt_count,
        "auto_marked_count":           a["auto_marked_count"],
        "teacher_reviewed_count":      a["teacher_reviewed_count"],
        "pending_teacher_review_count": a["pending_teacher_review_count"],
        "correct_count":               a["correct_count"],
        "incorrect_count":             a["incorrect_count"],
        "partially_correct_count":     a["partially_correct_count"],
        "needs_resubmission_count":    a["needs_resubmission_count"],
        "accuracy":                    a["accuracy"],
        "current_items":               current_items,
        "superseded_items":            history_items,
        "chains":                      chain_summaries,
    }
    state_path.write_text(json.dumps(state_doc, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Write marked_attempts_latest_v1.json ──────────────────────────────────
    marked_doc = {
        "marked_attempt_file_id":  "quanta_aptus_local_marked_attempts_latest_v1",
        "version":                 "0.1.0",
        "created_at":              now_iso,
        "updated_at":              now_iso,
        "source_attempt_file":     str(attempts_path),
        "source_teacher_payload":  str(payload_path),
        "source_teacher_decisions": str(decisions_path),
        "raw_attempt_count":       raw_attempt_count,
        "current_attempt_count":   current_count,
        "superseded_attempt_count": superseded_count,
        "history_items":           history_items,
        "current_items":           current_items,
    }
    marked_path.write_text(json.dumps(marked_doc, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Write student_result_report_latest_v1.json ────────────────────────────
    result_doc = {
        "report_id":                    "quanta_aptus_local_student_result_report_latest_v1",
        "version":                      "latest.0.1",
        "created_at":                   now_iso,
        "student_id":                   student_id,
        "source_latest_learning_state": str(state_path),
        "attempt_count":                a["attempt_count"],
        "raw_attempt_count":            raw_attempt_count,
        "superseded_attempt_count":     superseded_count,
        "resubmission_attempt_count":   resubmission_attempt_count,
        **a,
    }
    result_json_path.write_text(json.dumps(result_doc, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Markdown ──────────────────────────────────────────────────────────────
    result_md_path.write_text(
        build_markdown(a, student_id, str(attempts_path), now_iso,
                       raw_attempt_count, superseded_count, resubmission_attempt_count),
        encoding="utf-8",
    )

    # ── HTML preview ──────────────────────────────────────────────────────────
    result_html_path.write_text(
        build_html(a, student_id, str(attempts_path), now_iso,
                   raw_attempt_count, superseded_count, resubmission_attempt_count),
        encoding="utf-8",
    )

    # ── Script report ─────────────────────────────────────────────────────────
    report_doc = {
        "status":                       status,
        "student_id":                   student_id,
        "raw_attempt_count":            raw_attempt_count,
        "current_attempt_count":        current_count,
        "superseded_attempt_count":     superseded_count,
        "resubmission_attempt_count":   resubmission_attempt_count,
        "auto_marked_count":            a["auto_marked_count"],
        "teacher_reviewed_count":       a["teacher_reviewed_count"],
        "pending_teacher_review_count": a["pending_teacher_review_count"],
        "correct_count":                a["correct_count"],
        "incorrect_count":              a["incorrect_count"],
        "partially_correct_count":      a["partially_correct_count"],
        "needs_resubmission_count":     a["needs_resubmission_count"],
        "accuracy":                     a["accuracy"],
        "output_files":                 output_paths,
    }
    report_path.write_text(json.dumps(report_doc, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Manifest ──────────────────────────────────────────────────────────────
    manifest_path.write_text(
        build_manifest(report_doc, now_iso), encoding="utf-8"
    )

    # ── Write result report JSON ──────────────────────────────────────────────
    result_rep_doc = {
        "status":                       status,
        "student_id":                   student_id,
        "attempt_count":                a["attempt_count"],
        "raw_attempt_count":            raw_attempt_count,
        "superseded_attempt_count":     superseded_count,
        "resubmission_attempt_count":   resubmission_attempt_count,
        "auto_marked_count":            a["auto_marked_count"],
        "teacher_reviewed_count":       a["teacher_reviewed_count"],
        "pending_teacher_review_count": a["pending_teacher_review_count"],
        "correct_count":                a["correct_count"],
        "incorrect_count":              a["incorrect_count"],
        "partially_correct_count":      a["partially_correct_count"],
        "needs_resubmission_count":     a["needs_resubmission_count"],
        "accuracy":                     a["accuracy"],
        "skill_gap_count":              len(a["skill_gaps"]),
        "strength_count":               len(a["strengths"]),
        "teacher_review_queue_count":   len(a["teacher_review_queue"]),
        "resubmission_queue_count":     len(a["resubmission_queue"]),
        "output_files": {
            "student_result_report_latest_json":    str(result_json_path),
            "student_result_report_latest_md":      str(result_md_path),
            "student_result_report_latest_preview": str(result_html_path),
            "report":                               str(result_rep_path),
        },
    }
    result_rep_path.write_text(json.dumps(result_rep_doc, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Terminal summary ───────────────────────────────────────────────────────
    pct = f"{a['accuracy'] * 100:.0f}%" if a["accuracy"] is not None else "N/A"
    print(f"[{status.upper()}] Latest learning state rebuilt")
    print(f"  student_id                    : {student_id}")
    print(f"  raw_attempt_count             : {raw_attempt_count}")
    print(f"  current_attempt_count         : {current_count}")
    print(f"  superseded_attempt_count      : {superseded_count}")
    print(f"  resubmission_attempt_count    : {resubmission_attempt_count}")
    print(f"  auto_marked_count             : {a['auto_marked_count']}")
    print(f"  teacher_reviewed_count        : {a['teacher_reviewed_count']}")
    print(f"  pending_teacher_review_count  : {a['pending_teacher_review_count']}")
    print(f"  correct_count                 : {a['correct_count']}")
    print(f"  needs_resubmission_count      : {a['needs_resubmission_count']}")
    print(f"  accuracy                      : {pct}")
    print(f"  latest_learning_state  -> {state_path}")
    print(f"  marked_attempts_latest -> {marked_path}")
    print(f"  result_report_json     -> {result_json_path}")
    print(f"  result_report_md       -> {result_md_path}")
    print(f"  result_report_preview  -> {result_html_path}")
    print(f"  report                 -> {report_path}")
    print(f"  manifest               -> {manifest_path}")


if __name__ == "__main__":
    main()
