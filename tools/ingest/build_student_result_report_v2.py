"""
Gate 46 - Student Result & Skill Gap Report v2
Reads marked_attempts_v2.json (which includes teacher-reviewed decisions)
and builds an updated result report for a single student.
Does NOT modify marked_attempts_v2.json or any v1 outputs.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRAPHING_PLANNING_TYPES = {
    "graphing_drill",
    "diagram_or_graph_drill",
    "experiment_planning_task",
    "planning_marking_checklist",
    "graph_marking_checklist",
    "marking_checklist",
}

PLACEHOLDER_KEYWORDS = {"placeholder", "test", "redo"}

ACTIONS = {
    "calc_correct":     "Continue with medium or hard calculation drills.",
    "needs_resubmit":   "Redo the graphing task and submit a real graph with labelled axes, scale and plotted points.",
    "no_pending":       "All current teacher reviews are resolved.",
    "conf_appropriate": "Maintain confidence calibration.",
    "conf_high":        "Check your method carefully before submitting.",
    "conf_low_correct": "Trust your working — you got it right with a low-confidence response.",
    "incorrect_calc":   "Review the relevant formula and worked example, then reattempt.",
    "placeholder_redo": "Redo the task with full working to receive meaningful feedback.",
    "partial_improve":  "Review the areas where you lost marks and reattempt to reach full marks.",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(num: int, denom: int) -> float | None:
    if denom == 0:
        return None
    return round(num / denom, 4)


def _is_placeholder(text: str) -> bool:
    tl = (text or "").lower().strip()
    return any(kw in tl for kw in PLACEHOLDER_KEYWORDS)


def _gap_id(attempt_id: str, index: int) -> str:
    return f"gap_{attempt_id}_{index}"


def _get_final_status(item: dict) -> str:
    """Derive final_status using the Gate 45 priority rule."""
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
# Core analysis
# ---------------------------------------------------------------------------

def analyse(items: list[dict]) -> dict:
    attempt_count = len(items)

    # ── Top-level counts ─────────────────────────────────────────────────────
    auto_marked_count          = 0
    teacher_reviewed_count     = 0
    pending_teacher_review_count = 0
    correct_count              = 0
    incorrect_count            = 0
    partially_correct_count    = 0
    needs_resubmission_count   = 0

    # Accuracy denominator: only resolved scored attempts
    acc_correct = 0
    acc_denom   = 0

    for item in items:
        ms = item.get("marking_status", "")
        fs = _get_final_status(item)

        if ms == "auto_marked":
            auto_marked_count += 1
        elif ms == "teacher_reviewed":
            teacher_reviewed_count += 1

        if fs == "correct":
            correct_count += 1
            acc_correct += 1
            acc_denom   += 1
        elif fs == "incorrect":
            incorrect_count += 1
            acc_denom += 1
        elif fs == "partially_correct":
            partially_correct_count += 1
            if item.get("score") is not None:
                acc_denom   += 1
                # partial credit — counted as fraction toward correct
                acc_correct += item.get("score", 0)
        elif fs == "needs_resubmission":
            needs_resubmission_count += 1
        elif fs == "pending_teacher_review":
            pending_teacher_review_count += 1

    accuracy = _pct(acc_correct, acc_denom) if acc_denom else None

    # ── Topic summary ─────────────────────────────────────────────────────────
    topic_buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
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

        t_acc_corr  = t_correct
        t_acc_denom = t_correct + t_wrong + t_partial
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
            "accuracy":                     _pct(t_acc_corr, t_acc_denom),
        })

    # ── Skill type summary ────────────────────────────────────────────────────
    skill_buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        skill_buckets[item.get("skill_type", "unknown")].append(item)

    skill_types_summary: list[dict] = []
    for st, s_items in sorted(skill_buckets.items()):
        s_auto     = sum(1 for i in s_items if i.get("marking_status") == "auto_marked")
        s_reviewed = sum(1 for i in s_items if i.get("marking_status") == "teacher_reviewed")
        s_correct  = sum(1 for i in s_items if _get_final_status(i) == "correct")
        s_wrong    = sum(1 for i in s_items if _get_final_status(i) == "incorrect")
        s_resub    = sum(1 for i in s_items if _get_final_status(i) == "needs_resubmission")
        s_denom    = s_correct + s_wrong
        skill_types_summary.append({
            "skill_type":              st,
            "attempt_count":           len(s_items),
            "auto_marked_count":       s_auto,
            "teacher_reviewed_count":  s_reviewed,
            "correct_count":           s_correct,
            "incorrect_count":         s_wrong,
            "needs_resubmission_count": s_resub,
            "accuracy":                _pct(s_correct, s_denom),
        })

    # ── Confidence signals ────────────────────────────────────────────────────
    conf_counts: dict[str, int] = defaultdict(int)
    for item in items:
        conf_counts[item.get("confidence_signal", "unknown")] += 1

    # ── Skill gaps, strengths ─────────────────────────────────────────────────
    skill_gaps:  list[dict] = []
    strengths:   list[dict] = []
    gap_idx = 0

    low_acc_topics: set[str] = set()
    for ts in topics_summary:
        scored = ts["correct_count"] + ts["incorrect_count"]
        if scored >= 2 and (ts["accuracy"] or 1.0) < 0.5:
            low_acc_topics.add(ts["topic"])

    for item in items:
        ms      = item.get("marking_status", "")
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

        # ── Strengths ────────────────────────────────────────────────────────
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

        # ── Skill gaps ───────────────────────────────────────────────────────
        reasons: list[tuple[str, str, str]] = []

        if fs == "incorrect":
            sev = "high" if diff == "hard" else "medium"
            reasons.append((
                "incorrect_answer",
                sev,
                f"Incorrect answer on a {diff} {rtype.replace('_', ' ')}. {feed}",
            ))

        elif fs == "partially_correct":
            reasons.append((
                "partially_correct",
                "medium",
                f"Partially correct on {rtype.replace('_', ' ')} — {feed}",
            ))

        elif fs == "needs_resubmission":
            teacher_feedback = tr.get("teacher_feedback", "") or feed
            ans_is_placeholder = _is_placeholder(item.get("student_answer", ""))
            sev = "high" if (ans_is_placeholder or _is_placeholder(feed)) else "medium"
            reasons.append((
                "needs_resubmission",
                sev,
                teacher_feedback or feed or "Teacher marked this attempt as needs resubmission.",
            ))

        elif fs == "pending_teacher_review":
            sev = "high" if _is_placeholder(feed) else "medium"
            reasons.append((
                "teacher_review_required",
                sev,
                feed or "Requires teacher review.",
            ))

        if csig == "overconfident_wrong" and fs != "correct":
            reasons.append((
                "overconfident_wrong",
                "high",
                "High confidence submitted with an incorrect answer.",
            ))

        if topic in low_acc_topics:
            already = any(
                g["topic"] == topic and g["reason"] == "low_topic_accuracy"
                for g in skill_gaps
            )
            if not already:
                reasons.append((
                    "low_topic_accuracy",
                    "medium",
                    f"Overall accuracy for {topic} is below 50% across resolved attempts.",
                ))

        for reason, sev, evidence in reasons:
            rec = _recommended_action(reason, rtype, diff, csig, feed, tr)
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

    # ── Resubmission queue ────────────────────────────────────────────────────
    resubmission_queue = []
    for item in items:
        if _get_final_status(item) == "needs_resubmission":
            tr = item.get("teacher_review") or {}
            resubmission_queue.append({
                "attempt_id":       item.get("attempt_id", ""),
                "resource_id":      item.get("resource_id", ""),
                "topic":            item.get("topic", ""),
                "skill_name":       item.get("skill_name", ""),
                "resource_type":    item.get("resource_type", ""),
                "student_answer":   item.get("student_answer", ""),
                "teacher_feedback": tr.get("teacher_feedback", "") or item.get("feedback", ""),
                "teacher_notes":    tr.get("teacher_notes", ""),
                "recommended_action": "Redo and resubmit.",
            })

    # ── Recommended next actions ──────────────────────────────────────────────
    actions: list[str] = []
    seen: set[str] = set()

    def _add(a: str) -> None:
        if a not in seen:
            seen.add(a)
            actions.append(a)

    for item in items:
        ms    = item.get("marking_status", "")
        fs    = _get_final_status(item)
        rtype = item.get("resource_type", "")
        csig  = item.get("confidence_signal", "unknown")

        if fs == "correct" and "calculation" in rtype:
            _add(ACTIONS["calc_correct"])
        if fs == "needs_resubmission":
            _add(ACTIONS["needs_resubmit"])
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

    if pending_teacher_review_count == 0:
        _add(ACTIONS["no_pending"])

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
        "resubmission_queue":             resubmission_queue,
        "strengths":                      strengths,
        "recommended_next_actions":       actions,
    }


def _recommended_action(reason: str, rtype: str, diff: str,
                        csig: str, feed: str, tr: dict) -> str:
    if reason == "needs_resubmission":
        return ACTIONS["needs_resubmit"]
    if reason == "incorrect_answer":
        return ACTIONS["incorrect_calc"]
    if reason == "partially_correct":
        return ACTIONS["partial_improve"]
    if reason == "teacher_review_required":
        if _is_placeholder(feed):
            return ACTIONS["placeholder_redo"]
        return ACTIONS["no_pending"]
    if reason == "overconfident_wrong":
        return ACTIONS["conf_high"]
    if reason == "low_topic_accuracy":
        return ACTIONS["incorrect_calc"]
    return ACTIONS["incorrect_calc"]


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def build_markdown(a: dict, student_id: str, source: str, now_iso: str) -> str:
    pct = f"{a['accuracy'] * 100:.0f}%" if a["accuracy"] is not None else "N/A"

    lines = [
        "# Quanta Aptus Student Result Report v2",
        "",
        f"**Student ID:** `{student_id}`  ",
        f"**Generated:** {now_iso}  ",
        f"**Source:** `{source}`  ",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Attempts | {a['attempt_count']} |",
        f"| Auto-marked | {a['auto_marked_count']} |",
        f"| Teacher Reviewed | {a['teacher_reviewed_count']} |",
        f"| Pending Teacher Review | {a['pending_teacher_review_count']} |",
        f"| Correct | {a['correct_count']} |",
        f"| Incorrect | {a['incorrect_count']} |",
        f"| Partially Correct | {a['partially_correct_count']} |",
        f"| Needs Resubmission | {a['needs_resubmission_count']} |",
        f"| Accuracy | {pct} |",
        "",
    ]

    # Accuracy note
    lines += [
        "> **Accuracy** is calculated from resolved scored attempts only",
        "> (correct + incorrect + partially_correct). Needs-resubmission",
        "> and pending review attempts are excluded from the denominator.",
        "",
    ]

    # Strengths
    lines += ["## Strengths", ""]
    if a["strengths"]:
        for s in a["strengths"]:
            note_part = f" _{s['note']}_" if s.get("note") else ""
            lines.append(f"- **{s['topic']}** — {s['evidence']}{note_part}")
    else:
        lines.append("_No confirmed strengths yet._")
    lines.append("")

    # Skill gaps
    lines += ["## Skill Gaps", ""]
    if a["skill_gaps"]:
        for g in a["skill_gaps"]:
            sev_icon = {"high": "!", "medium": "~", "low": "-"}.get(g["severity"], "-")
            lines.append(
                f"- [{sev_icon}] **{g['topic']}** ({g['skill_type']}, {g['difficulty']}) — "
                f"_{g['reason'].replace('_', ' ')}_: {g['evidence']}"
            )
            lines.append(f"  - Recommended: {g['recommended_action']}")
    else:
        lines.append("_No skill gaps identified._")
    lines.append("")

    # Resubmission queue
    lines += ["## Resubmission Queue", ""]
    if a["resubmission_queue"]:
        for q in a["resubmission_queue"]:
            lines.append(f"- **{q['topic']}** | `{q['resource_type']}` | _{q['skill_name']}_")
            lines.append(f"  - Answer: {q['student_answer']}")
            lines.append(f"  - Teacher feedback: {q['teacher_feedback']}")
            if q.get("teacher_notes"):
                lines.append(f"  - Teacher notes: {q['teacher_notes']}")
    else:
        lines.append("_No items in resubmission queue._")
    lines.append("")

    # Topic summary
    lines += ["## Topic Summary", ""]
    lines += [
        "| Topic | Attempts | Auto | Reviewed | Pending | Correct | Incorrect | Partial | Resub | Accuracy |",
        "|-------|----------|------|----------|---------|---------|-----------|---------|-------|----------|",
    ]
    for t in a["topics"]:
        acc = f"{t['accuracy'] * 100:.0f}%" if t["accuracy"] is not None else "—"
        lines.append(
            f"| {t['topic']} | {t['attempt_count']} | {t['auto_marked_count']} | "
            f"{t['teacher_reviewed_count']} | {t['pending_teacher_review_count']} | "
            f"{t['correct_count']} | {t['incorrect_count']} | "
            f"{t['partially_correct_count']} | {t['needs_resubmission_count']} | {acc} |"
        )
    lines.append("")

    # Recommended next actions
    lines += ["## Recommended Next Actions", ""]
    for act in a["recommended_next_actions"]:
        lines.append(f"- {act}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

HTML_CSS = """
body{font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:0;background:#f0f4f8;color:#1a202c}
.topbar{background:#2b6cb0;color:#fff;padding:1rem 2rem;display:flex;align-items:center;gap:1rem}
.topbar h1{margin:0;font-size:1.4rem}
.topbar-badge{background:rgba(255,255,255,.2);border-radius:999px;padding:2px 10px;font-size:.78rem}
.topbar-v{background:#276749;color:#fff;border-radius:999px;padding:2px 10px;font-size:.74rem;font-weight:700}
.container{max-width:980px;margin:2rem auto;padding:0 1rem}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;margin-bottom:22px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:14px 16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.card .val{font-size:1.7rem;font-weight:700;color:#2b6cb0;line-height:1.1}
.card .lbl{font-size:.65rem;color:#718096;text-transform:uppercase;letter-spacing:.05em;margin-top:4px}
.sec{background:#fff;border:1px solid #e2e8f0;border-radius:6px;margin-bottom:18px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.sec-hdr{background:#1a1a2e;color:#fff;padding:9px 16px;font-size:.83rem;font-weight:600;letter-spacing:.03em}
.sec-body{padding:14px 16px}
.note-box{background:#fffbeb;border:1px solid #f6e05e;border-radius:5px;padding:8px 12px;font-size:.78rem;color:#744210;margin-bottom:16px}
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
.resub-card{border:1px solid #fbd38d;border-radius:6px;padding:12px 14px;margin-bottom:10px;background:#fffaf0;border-left:4px solid #d69e2e}
.resub-title{font-weight:600;font-size:.85rem;color:#744210;margin-bottom:4px}
.resub-meta{font-size:.72rem;color:#975a16;margin-bottom:6px}
.resub-answer{font-size:.8rem;color:#2d3748;background:#fff;border:1px solid #fbd38d;border-radius:4px;padding:6px 8px;white-space:pre-wrap;margin-bottom:6px}
.resub-feedback{font-size:.78rem;color:#744210;font-style:italic}
.resub-notes{font-size:.74rem;color:#975a16;margin-top:4px}
.action-list{padding:0;margin:0;list-style:none}
.action-list li{padding:6px 0;border-bottom:1px solid #e2e8f0;font-size:.85rem;color:#2d3748}
.action-list li:last-child{border-bottom:none}
.action-list li::before{content:'-> ';color:#2b6cb0;font-weight:700}
.footer{text-align:center;color:#a0aec0;font-size:.76rem;margin:2rem 0 1rem}
.acc-good{color:#276749;font-weight:700}
.acc-bad{color:#e53e3e;font-weight:700}
"""


def build_html(a: dict, student_id: str, source: str, now_iso: str) -> str:
    pct_display = f"{a['accuracy'] * 100:.0f}%" if a["accuracy"] is not None else "N/A"

    cards_html = "\n".join([
        f'<div class="card"><div class="val">{a["attempt_count"]}</div><div class="lbl">Attempts</div></div>',
        f'<div class="card"><div class="val">{a["auto_marked_count"]}</div><div class="lbl">Auto-marked</div></div>',
        f'<div class="card"><div class="val">{a["teacher_reviewed_count"]}</div><div class="lbl">Teacher Reviewed</div></div>',
        f'<div class="card"><div class="val">{a["correct_count"]}</div><div class="lbl">Correct</div></div>',
        f'<div class="card"><div class="val">{a["needs_resubmission_count"]}</div><div class="lbl">Needs Resubmission</div></div>',
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
            f"<td style='text-align:center'>{t['correct_count']}</td>"
            f"<td style='text-align:center'>{t['incorrect_count']}</td>"
            f"<td style='text-align:center'>{t['needs_resubmission_count']}</td>"
            f"<td style='text-align:center'>{_acc_span(t['accuracy'])}</td></tr>"
        )

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

    # Resubmission queue
    resub_html = ""
    if a["resubmission_queue"]:
        for q in a["resubmission_queue"]:
            resub_html += (
                f'<div class="resub-card">'
                f'<div class="resub-title">{q["topic"]}</div>'
                f'<div class="resub-meta">{q["resource_type"].replace("_", " ")} &middot; {q["skill_name"]}</div>'
                f'<div class="resub-answer">{q["student_answer"]}</div>'
                f'<div class="resub-feedback">Teacher feedback: {q["teacher_feedback"]}</div>'
                + (f'<div class="resub-notes">Notes: {q["teacher_notes"]}</div>' if q.get("teacher_notes") else "")
                + '</div>'
            )
    else:
        resub_html = "<p style='color:#718096;font-size:.88rem'>No items require resubmission.</p>"

    # Actions
    actions_html = "<ul class='action-list'>" + "".join(
        f"<li>{act}</li>" for act in a["recommended_next_actions"]
    ) + "</ul>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quanta Aptus Student Result Report v2 &mdash; {student_id}</title>
<style>{HTML_CSS}</style>
</head>
<body>
<div class="topbar">
  <h1>Quanta Aptus Student Result Report v2</h1>
  <span class="topbar-badge">{student_id}</span>
  <span class="topbar-v">v2</span>
</div>
<div class="container">
  <p style="font-size:.8rem;color:#718096;margin-bottom:10px">
    Generated {now_iso} &middot; Source: {source}
  </p>
  <div class="note-box">
    Accuracy is calculated from resolved scored attempts only (correct + incorrect + partially correct).
    Needs-resubmission and pending-review attempts are excluded from the denominator.
  </div>

  <div class="cards">{cards_html}</div>

  <div class="sec">
    <div class="sec-hdr">Topic Summary</div>
    <div class="sec-body" style="padding:0">
      <table>
        <thead><tr>
          <th>Topic</th><th>Attempts</th><th>Auto</th><th>Reviewed</th>
          <th>Correct</th><th>Incorrect</th><th>Needs Resubmission</th><th>Accuracy</th>
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
    <div class="sec-hdr">Resubmission Queue ({len(a['resubmission_queue'])})</div>
    <div class="sec-body">{resub_html}</div>
  </div>

  <div class="sec">
    <div class="sec-hdr">Recommended Next Actions</div>
    <div class="sec-body">{actions_html}</div>
  </div>

  <p class="footer">Quanta Aptus &mdash; Rule-based marking is provisional.
  Teacher-reviewed decisions are reflected in this v2 report.</p>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Gate 46 - Student Result Report v2")
    parser.add_argument(
        "--marked-attempts",
        default="data/attempts/local/marked_attempts_v2.json",
    )
    parser.add_argument(
        "--student-id",
        default="local_demo_student",
    )
    args = parser.parse_args()

    marked_path = Path(args.marked_attempts)
    student_id  = args.student_id

    if not marked_path.exists():
        print(f"[FAILED] Marked attempts file not found: {marked_path}")
        sys.exit(1)

    try:
        marked_doc = json.loads(marked_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAILED] Cannot load marked attempts: {exc}")
        sys.exit(1)

    all_items: list[dict] = marked_doc.get("items", [])
    items = [i for i in all_items if i.get("student_id") == student_id]

    if not items:
        print(f"[FAILED] No attempts found for student_id={student_id!r}")
        sys.exit(1)

    now_iso = datetime.now(timezone.utc).isoformat()
    analysis = analyse(items)

    # Status
    if analysis["pending_teacher_review_count"] > 0:
        status = "needs_review"
    else:
        status = "passed"

    # Output paths
    out_dir = Path("data/attempts/local/reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path    = out_dir / "student_result_report_v2.json"
    md_path      = out_dir / "student_result_report_v2.md"
    preview_path = out_dir / "student_result_report_preview_v2.html"
    report_path  = out_dir / "student_result_report_v2_report.json"

    output_paths = {
        "student_result_report_json":    str(json_path),
        "student_result_report_md":      str(md_path),
        "student_result_report_preview": str(preview_path),
        "report":                        str(report_path),
    }

    # Build + write result report JSON
    result_doc = {
        "report_id":              "quanta_aptus_local_student_result_report_v2",
        "version":                "0.2.0",
        "created_at":             now_iso,
        "student_id":             student_id,
        "source_marked_attempts": str(marked_path),
        **analysis,
    }
    json_path.write_text(json.dumps(result_doc, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown
    md_path.write_text(
        build_markdown(analysis, student_id, str(marked_path), now_iso), encoding="utf-8"
    )

    # HTML preview
    preview_path.write_text(
        build_html(analysis, student_id, str(marked_path), now_iso), encoding="utf-8"
    )

    # Script report
    script_report = {
        "status":                       status,
        "student_id":                   student_id,
        "attempt_count":                analysis["attempt_count"],
        "auto_marked_count":            analysis["auto_marked_count"],
        "teacher_reviewed_count":       analysis["teacher_reviewed_count"],
        "pending_teacher_review_count": analysis["pending_teacher_review_count"],
        "correct_count":                analysis["correct_count"],
        "incorrect_count":              analysis["incorrect_count"],
        "partially_correct_count":      analysis["partially_correct_count"],
        "needs_resubmission_count":     analysis["needs_resubmission_count"],
        "accuracy":                     analysis["accuracy"],
        "skill_gap_count":              len(analysis["skill_gaps"]),
        "strength_count":               len(analysis["strengths"]),
        "resubmission_queue_count":     len(analysis["resubmission_queue"]),
        "output_files":                 output_paths,
    }
    report_path.write_text(
        json.dumps(script_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Terminal output
    pct = f"{analysis['accuracy'] * 100:.0f}%" if analysis["accuracy"] is not None else "N/A"
    print(f"[{status.upper()}] Student result report v2 built")
    print(f"  student_id                    : {student_id}")
    print(f"  attempt_count                 : {analysis['attempt_count']}")
    print(f"  auto_marked_count             : {analysis['auto_marked_count']}")
    print(f"  teacher_reviewed_count        : {analysis['teacher_reviewed_count']}")
    print(f"  pending_teacher_review_count  : {analysis['pending_teacher_review_count']}")
    print(f"  correct_count                 : {analysis['correct_count']}")
    print(f"  incorrect_count               : {analysis['incorrect_count']}")
    print(f"  partially_correct_count       : {analysis['partially_correct_count']}")
    print(f"  needs_resubmission_count      : {analysis['needs_resubmission_count']}")
    print(f"  accuracy                      : {pct}")
    print(f"  skill_gap_count               : {len(analysis['skill_gaps'])}")
    print(f"  strength_count                : {len(analysis['strengths'])}")
    print(f"  resubmission_queue_count      : {len(analysis['resubmission_queue'])}")
    print(f"  json    -> {json_path}")
    print(f"  md      -> {md_path}")
    print(f"  preview -> {preview_path}")
    print(f"  report  -> {report_path}")


if __name__ == "__main__":
    main()
