"""
Gate 42 - Student Result & Skill Gap Report v1
Reads marked_attempts_v1.json and builds a result report + skill gap analysis
for a single student. No OpenAI. No Supabase. Does not modify input files.
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

PLACEHOLDER_KEYWORDS = {"placeholder", "test", "redo", "placeholder"}

# Deterministic recommended action text
ACTIONS = {
    "calc_correct":      "Continue with medium or hard calculation drills to build fluency.",
    "graphing_review":   "Submit a graph image or have teacher check axes, scale and plotted points.",
    "placeholder_redo":  "Redo the task with full working to receive meaningful feedback.",
    "conf_appropriate":  "Maintain your confidence calibration — it matches your performance well.",
    "conf_high":         "Check your method carefully before submitting.",
    "conf_low_correct":  "Trust your working — you got it right with a low-confidence response.",
    "review_pending":    "Await teacher review for this item before progressing.",
    "incorrect_calc":    "Review the relevant formula and worked example, then reattempt.",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(num: int, denom: int) -> float | None:
    if denom == 0:
        return None
    return round(num / denom, 4)


def _is_placeholder(feedback: str) -> bool:
    fl = (feedback or "").lower()
    return "placeholder" in fl or "too short" in fl


def _gap_id(attempt_id: str, index: int) -> str:
    return f"gap_{attempt_id}_{index}"


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyse(items: list[dict]) -> dict:
    """Return full analysis dict from a list of marked attempt items."""

    attempt_count              = len(items)
    auto_marked_count          = sum(1 for i in items if i["marking_status"] == "auto_marked")
    teacher_review_req_count   = sum(1 for i in items if i["marking_status"] == "teacher_review_required")
    correct_count              = sum(1 for i in items if i["is_correct"] is True)
    incorrect_count            = sum(1 for i in items if i["is_correct"] is False)
    accuracy                   = _pct(correct_count, auto_marked_count)

    # ── Topic summary ────────────────────────────────────────────────────────
    topic_buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        topic_buckets[item.get("topic", "Unknown")].append(item)

    topics_summary: list[dict] = []
    for topic, t_items in sorted(topic_buckets.items()):
        t_auto    = sum(1 for i in t_items if i["marking_status"] == "auto_marked")
        t_correct = sum(1 for i in t_items if i["is_correct"] is True)
        t_wrong   = sum(1 for i in t_items if i["is_correct"] is False)
        t_review  = sum(1 for i in t_items if i["marking_status"] == "teacher_review_required")
        topics_summary.append({
            "topic":                     topic,
            "attempt_count":             len(t_items),
            "auto_marked_count":         t_auto,
            "correct_count":             t_correct,
            "incorrect_count":           t_wrong,
            "teacher_review_required_count": t_review,
            "accuracy":                  _pct(t_correct, t_auto),
        })

    # ── Skill type summary ───────────────────────────────────────────────────
    skill_buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        skill_buckets[item.get("skill_type", "unknown")].append(item)

    skill_types_summary: list[dict] = []
    for st, s_items in sorted(skill_buckets.items()):
        s_auto    = sum(1 for i in s_items if i["marking_status"] == "auto_marked")
        s_correct = sum(1 for i in s_items if i["is_correct"] is True)
        s_wrong   = sum(1 for i in s_items if i["is_correct"] is False)
        s_review  = sum(1 for i in s_items if i["marking_status"] == "teacher_review_required")
        skill_types_summary.append({
            "skill_type":                st,
            "attempt_count":             len(s_items),
            "auto_marked_count":         s_auto,
            "correct_count":             s_correct,
            "incorrect_count":           s_wrong,
            "teacher_review_required_count": s_review,
            "accuracy":                  _pct(s_correct, s_auto),
        })

    # ── Confidence signals ───────────────────────────────────────────────────
    conf_counts: dict[str, int] = defaultdict(int)
    for item in items:
        conf_counts[item.get("confidence_signal", "unknown")] += 1
    confidence_signals = dict(conf_counts)

    # ── Skill gaps & strengths ───────────────────────────────────────────────
    skill_gaps:  list[dict] = []
    strengths:   list[dict] = []
    gap_idx = 0

    # Low-accuracy topics (need >= 2 auto_marked to measure; threshold < 0.5)
    low_acc_topics: set[str] = set()
    for ts in topics_summary:
        if ts["auto_marked_count"] >= 2 and (ts["accuracy"] or 1.0) < 0.5:
            low_acc_topics.add(ts["topic"])

    for item in items:
        ms      = item["marking_status"]
        correct = item["is_correct"]
        csig    = item.get("confidence_signal", "unknown")
        topic   = item.get("topic", "Unknown")
        sname   = item.get("skill_name", "")
        stype   = item.get("skill_type", "")
        diff    = item.get("difficulty") or "unknown"
        rtype   = item.get("resource_type", "")
        feed    = item.get("feedback", "")
        aid     = item["attempt_id"]

        # ── Strengths ────────────────────────────────────────────────────────
        if correct is True:
            note = "Confidence well-calibrated." if csig == "appropriate" else (
                "Hidden strength — answered correctly despite low confidence."
                if csig == "underconfident_correct" else ""
            )
            strengths.append({
                "topic":      topic,
                "skill_name": sname,
                "skill_type": stype,
                "evidence":   f"Correctly answered {rtype.replace('_', ' ')} on {topic}.",
                "note":       note,
            })

        # ── Skill gaps ───────────────────────────────────────────────────────
        reasons: list[tuple[str, str, str]] = []  # (reason, severity, evidence)

        # Incorrect auto-marked
        if ms == "auto_marked" and correct is False:
            sev = "high" if diff == "hard" else "medium"
            reasons.append((
                "incorrect_answer",
                sev,
                f"Incorrect answer on a {diff} {rtype.replace('_', ' ')}. {feed}",
            ))

        # Teacher review required
        if ms == "teacher_review_required":
            sev = "high" if _is_placeholder(feed) else (
                "medium" if rtype in GRAPHING_PLANNING_TYPES else "medium"
            )
            reasons.append((
                "teacher_review_required",
                sev,
                feed or "Requires teacher review.",
            ))

        # Overconfident wrong
        if csig == "overconfident_wrong":
            reasons.append((
                "overconfident_wrong",
                "high",
                "High confidence submitted with an incorrect answer.",
            ))

        # Low topic accuracy (add gap only once per topic — check if not already added)
        if topic in low_acc_topics:
            already = any(
                g["topic"] == topic and g["reason"] == "low_topic_accuracy"
                for g in skill_gaps
            )
            if not already:
                reasons.append((
                    "low_topic_accuracy",
                    "medium",
                    f"Overall accuracy for {topic} is below 50% across auto-marked attempts.",
                ))

        for reason, sev, evidence in reasons:
            rec = _recommended_action(reason, rtype, diff, csig, feed)
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

    # ── Review queue ─────────────────────────────────────────────────────────
    review_queue = [
        {
            "attempt_id":   item["attempt_id"],
            "resource_id":  item["resource_id"],
            "topic":        item.get("topic", ""),
            "skill_name":   item.get("skill_name", ""),
            "resource_type": item.get("resource_type", ""),
            "student_answer": item.get("student_answer", ""),
            "feedback":     item.get("feedback", ""),
            "reason":       "teacher_review_required",
        }
        for item in items
        if item.get("needs_teacher_review") is True
    ]

    # ── Recommended next actions (deduplicated) ───────────────────────────────
    actions: list[str] = []
    seen_acts: set[str] = set()

    def _add_action(a: str) -> None:
        if a not in seen_acts:
            seen_acts.add(a)
            actions.append(a)

    for item in items:
        ms    = item["marking_status"]
        rtype = item.get("resource_type", "")
        csig  = item.get("confidence_signal", "unknown")
        feed  = item.get("feedback", "")
        corr  = item["is_correct"]

        if ms == "auto_marked" and corr is True and "calculation" in rtype:
            _add_action(ACTIONS["calc_correct"])
        if ms == "auto_marked" and corr is False:
            _add_action(ACTIONS["incorrect_calc"])
        if ms == "teacher_review_required" and rtype in GRAPHING_PLANNING_TYPES:
            _add_action(ACTIONS["graphing_review"])
        if ms == "teacher_review_required" and _is_placeholder(feed):
            _add_action(ACTIONS["placeholder_redo"])
        if csig == "appropriate":
            _add_action(ACTIONS["conf_appropriate"])
        if csig == "overconfident_wrong":
            _add_action(ACTIONS["conf_high"])
        if csig == "underconfident_correct":
            _add_action(ACTIONS["conf_low_correct"])
        if ms == "teacher_review_required":
            _add_action(ACTIONS["review_pending"])

    return {
        "attempt_count":                  attempt_count,
        "auto_marked_count":              auto_marked_count,
        "teacher_review_required_count":  teacher_review_req_count,
        "correct_count":                  correct_count,
        "incorrect_count":                incorrect_count,
        "accuracy":                       accuracy,
        "topics":                         topics_summary,
        "skill_types":                    skill_types_summary,
        "confidence_signals":             confidence_signals,
        "skill_gaps":                     skill_gaps,
        "review_queue":                   review_queue,
        "strengths":                      strengths,
        "recommended_next_actions":       actions,
    }


def _recommended_action(reason: str, rtype: str, diff: str,
                        csig: str, feed: str) -> str:
    if reason == "incorrect_answer":
        return ACTIONS["incorrect_calc"]
    if reason == "teacher_review_required":
        if rtype in GRAPHING_PLANNING_TYPES:
            return ACTIONS["graphing_review"]
        if _is_placeholder(feed):
            return ACTIONS["placeholder_redo"]
        return ACTIONS["review_pending"]
    if reason == "overconfident_wrong":
        return ACTIONS["conf_high"]
    if reason == "low_topic_accuracy":
        return ACTIONS["incorrect_calc"]
    return ACTIONS["review_pending"]


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def build_markdown(report: dict, student_id: str, now_iso: str) -> str:
    a = report
    pct = f"{a['accuracy'] * 100:.0f}%" if a["accuracy"] is not None else "N/A"

    lines = [
        "# Quanta Aptus Student Result Report",
        "",
        f"**Student ID:** `{student_id}`  ",
        f"**Generated:** {now_iso}  ",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Attempts | {a['attempt_count']} |",
        f"| Auto-marked | {a['auto_marked_count']} |",
        f"| Teacher review required | {a['teacher_review_required_count']} |",
        f"| Correct | {a['correct_count']} |",
        f"| Incorrect | {a['incorrect_count']} |",
        f"| Accuracy | {pct} |",
        "",
    ]

    # Strengths
    lines += ["## Strengths", ""]
    if a["strengths"]:
        for s in a["strengths"]:
            lines.append(f"- **{s['topic']}** — {s['evidence']}"
                         + (f" _{s['note']}_" if s.get("note") else ""))
    else:
        lines.append("_No auto-marked correct answers yet._")
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

    # Topic summary
    lines += ["## Topic Summary", ""]
    lines += [
        "| Topic | Attempts | Auto-marked | Correct | Incorrect | Review | Accuracy |",
        "|-------|----------|-------------|---------|-----------|--------|----------|",
    ]
    for t in a["topics"]:
        acc = f"{t['accuracy'] * 100:.0f}%" if t["accuracy"] is not None else "—"
        lines.append(
            f"| {t['topic']} | {t['attempt_count']} | {t['auto_marked_count']} | "
            f"{t['correct_count']} | {t['incorrect_count']} | "
            f"{t['teacher_review_required_count']} | {acc} |"
        )
    lines.append("")

    # Recommended next actions
    lines += ["## Recommended Next Actions", ""]
    for act in a["recommended_next_actions"]:
        lines.append(f"- {act}")
    lines.append("")

    # Teacher review queue
    lines += ["## Teacher Review Queue", ""]
    if a["review_queue"]:
        for q in a["review_queue"]:
            lines.append(f"- **{q['topic']}** | `{q['resource_type']}` | _{q['skill_name']}_")
            lines.append(f"  - Answer: {q['student_answer']}")
            lines.append(f"  - Feedback: {q['feedback']}")
    else:
        lines.append("_No items pending teacher review._")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

HTML_CSS = """
body{font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:0;background:#f0f4f8;color:#1a202c}
.topbar{background:#2b6cb0;color:#fff;padding:1rem 2rem;display:flex;align-items:center;gap:1rem}
.topbar h1{margin:0;font-size:1.4rem}
.badge{background:rgba(255,255,255,.2);border-radius:999px;padding:2px 10px;font-size:.78rem}
.container{max-width:960px;margin:2rem auto;padding:0 1rem}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px;margin-bottom:24px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:14px 16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.card .val{font-size:1.8rem;font-weight:700;color:#2b6cb0;line-height:1.1}
.card .lbl{font-size:.68rem;color:#718096;text-transform:uppercase;letter-spacing:.05em;margin-top:4px}
.sec{background:#fff;border:1px solid #e2e8f0;border-radius:6px;margin-bottom:20px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.sec-hdr{background:#1a1a2e;color:#fff;padding:9px 16px;font-size:.83rem;font-weight:600;letter-spacing:.03em}
.sec-body{padding:14px 16px}
table{width:100%;border-collapse:collapse;font-size:.82rem}
th{background:#f7fafc;padding:7px 10px;text-align:left;font-size:.7rem;font-weight:700;text-transform:uppercase;color:#718096;border-bottom:1px solid #e2e8f0}
td{padding:7px 10px;border-bottom:1px solid #e2e8f0;vertical-align:top}
tr:last-child td{border-bottom:none}
tr:hover td{background:#f7fafc}
.gap-card{border:1px solid #e2e8f0;border-radius:6px;padding:12px 14px;margin-bottom:10px;border-left:4px solid #e2e8f0}
.gap-card.high{border-left-color:#e53e3e}
.gap-card.medium{border-left-color:#d69e2e}
.gap-card.low{border-left-color:#38a169}
.gap-title{font-weight:600;font-size:.88rem;margin-bottom:4px}
.gap-meta{font-size:.74rem;color:#718096;margin-bottom:6px}
.gap-evidence{font-size:.82rem;color:#4a5568;margin-bottom:6px}
.gap-action{font-size:.78rem;color:#2b6cb0;font-style:italic}
.strength-card{border:1px solid #9ae6b4;border-radius:6px;padding:10px 14px;margin-bottom:8px;background:#f0fff4}
.strength-title{font-weight:600;font-size:.85rem;color:#276749}
.strength-note{font-size:.76rem;color:#276749;margin-top:3px;font-style:italic}
.badge-sev{display:inline-block;font-size:.66rem;font-weight:700;padding:1px 7px;border-radius:999px;text-transform:uppercase;margin-left:6px}
.sev-high{background:#fed7d7;color:#742a2a}
.sev-medium{background:#fefcbf;color:#744210}
.sev-low{background:#c6f6d5;color:#276749}
.q-card{border:1px solid #bee3f8;border-radius:6px;padding:10px 14px;margin-bottom:8px;background:#ebf8ff}
.q-title{font-weight:600;font-size:.83rem;color:#2b6cb0}
.q-answer{font-size:.8rem;color:#2d3748;margin-top:4px;white-space:pre-wrap;background:#fff;border:1px solid #bee3f8;border-radius:4px;padding:6px 8px}
.q-feedback{font-size:.75rem;color:#718096;margin-top:4px;font-style:italic}
.action-list{padding:0;margin:0;list-style:none}
.action-list li{padding:6px 0;border-bottom:1px solid #e2e8f0;font-size:.85rem;color:#2d3748}
.action-list li:last-child{border-bottom:none}
.action-list li::before{content:'-> ';color:#2b6cb0;font-weight:700}
.footer{text-align:center;color:#a0aec0;font-size:.76rem;margin:2rem 0 1rem}
.acc-good{color:#276749;font-weight:700}
.acc-bad{color:#e53e3e;font-weight:700}
"""


def _acc_span(accuracy: float | None) -> str:
    if accuracy is None:
        return "<span>N/A</span>"
    pct = accuracy * 100
    cls = "acc-good" if pct >= 70 else "acc-bad"
    return f'<span class="{cls}">{pct:.0f}%</span>'


def build_html(report: dict, student_id: str, source: str, now_iso: str) -> str:
    a = report
    pct_display = f"{a['accuracy'] * 100:.0f}%" if a["accuracy"] is not None else "N/A"

    cards_html = "\n".join([
        f'<div class="card"><div class="val">{a["attempt_count"]}</div><div class="lbl">Attempts</div></div>',
        f'<div class="card"><div class="val">{a["auto_marked_count"]}</div><div class="lbl">Auto-marked</div></div>',
        f'<div class="card"><div class="val">{a["teacher_review_required_count"]}</div><div class="lbl">Review Required</div></div>',
        f'<div class="card"><div class="val">{a["correct_count"]}</div><div class="lbl">Correct</div></div>',
        f'<div class="card"><div class="val">{a["incorrect_count"]}</div><div class="lbl">Incorrect</div></div>',
        f'<div class="card"><div class="val">{pct_display}</div><div class="lbl">Accuracy</div></div>',
    ])

    # Topic table
    topic_rows = ""
    for t in a["topics"]:
        topic_rows += (
            f"<tr><td>{t['topic']}</td>"
            f"<td style='text-align:center'>{t['attempt_count']}</td>"
            f"<td style='text-align:center'>{t['auto_marked_count']}</td>"
            f"<td style='text-align:center'>{t['correct_count']}</td>"
            f"<td style='text-align:center'>{t['incorrect_count']}</td>"
            f"<td style='text-align:center'>{t['teacher_review_required_count']}</td>"
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

    # Recommended actions
    actions_html = "<ul class='action-list'>" + "".join(
        f"<li>{act}</li>" for act in a["recommended_next_actions"]
    ) + "</ul>"

    # Review queue
    if a["review_queue"]:
        queue_html = ""
        for q in a["review_queue"]:
            queue_html += (
                f'<div class="q-card">'
                f'<div class="q-title">{q["topic"]} &mdash; {q["resource_type"].replace("_", " ")}</div>'
                f'<div style="font-size:.76rem;color:#718096;margin-top:2px">{q["skill_name"]}</div>'
                f'<div class="q-answer">{q["student_answer"]}</div>'
                f'<div class="q-feedback">{q["feedback"]}</div>'
                f'</div>'
            )
    else:
        queue_html = "<p style='color:#718096;font-size:.88rem'>No items pending teacher review.</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Student Result Report &mdash; {student_id}</title>
<style>{HTML_CSS}</style>
</head>
<body>
<div class="topbar">
  <h1>Quanta Aptus Student Result Report</h1>
  <span class="badge">{student_id}</span>
</div>
<div class="container">
  <p style="font-size:.8rem;color:#718096;margin-bottom:16px">
    Generated {now_iso} &middot; Source: {source}
  </p>

  <div class="cards">{cards_html}</div>

  <div class="sec">
    <div class="sec-hdr">Topic Summary</div>
    <div class="sec-body" style="padding:0">
      <table>
        <thead><tr>
          <th>Topic</th><th>Attempts</th><th>Auto-marked</th>
          <th>Correct</th><th>Incorrect</th><th>Review</th><th>Accuracy</th>
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
    <div class="sec-hdr">Recommended Next Actions</div>
    <div class="sec-body">{actions_html}</div>
  </div>

  <div class="sec">
    <div class="sec-hdr">Teacher Review Queue ({len(a['review_queue'])})</div>
    <div class="sec-body">{queue_html}</div>
  </div>

  <p class="footer">Quanta Aptus &mdash; Rule-based marking is provisional.
  Graphing, planning, and complex written answers require teacher review.</p>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Gate 42 - Student Result Report")
    parser.add_argument(
        "--marked-attempts",
        default="data/attempts/local/marked_attempts_v1.json",
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

    # Determine status
    if analysis["teacher_review_required_count"] > analysis["auto_marked_count"]:
        status = "needs_review"
    else:
        status = "passed"

    # Output folder
    out_dir = marked_path.parent / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path     = out_dir / "student_result_report_v1.json"
    md_path       = out_dir / "student_result_report_v1.md"
    preview_path  = out_dir / "student_result_report_preview_v1.html"
    report_path   = out_dir / "student_result_report_v1_report.json"

    output_paths = {
        "student_result_report_json":    str(json_path),
        "student_result_report_md":      str(md_path),
        "student_result_report_preview": str(preview_path),
        "report":                        str(report_path),
    }

    # Build + write student result report JSON
    result_doc = {
        "report_id":              "quanta_aptus_local_student_result_report_v1",
        "version":                "0.1.0",
        "created_at":             now_iso,
        "student_id":             student_id,
        "source_marked_attempts": str(marked_path),
        **analysis,
    }
    json_path.write_text(json.dumps(result_doc, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown
    md_path.write_text(
        build_markdown(analysis, student_id, now_iso), encoding="utf-8"
    )

    # HTML preview
    preview_path.write_text(
        build_html(analysis, student_id, str(marked_path), now_iso), encoding="utf-8"
    )

    # Script report
    script_report = {
        "status":                        status,
        "student_id":                    student_id,
        "attempt_count":                 analysis["attempt_count"],
        "auto_marked_count":             analysis["auto_marked_count"],
        "teacher_review_required_count": analysis["teacher_review_required_count"],
        "correct_count":                 analysis["correct_count"],
        "incorrect_count":               analysis["incorrect_count"],
        "accuracy":                      analysis["accuracy"],
        "skill_gap_count":               len(analysis["skill_gaps"]),
        "strength_count":                len(analysis["strengths"]),
        "review_queue_count":            len(analysis["review_queue"]),
        "output_files":                  output_paths,
    }
    report_path.write_text(
        json.dumps(script_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Terminal
    pct = f"{analysis['accuracy'] * 100:.0f}%" if analysis["accuracy"] is not None else "N/A"
    print(f"[{status.upper()}] Student result report built")
    print(f"  student_id                     : {student_id}")
    print(f"  attempt_count                  : {analysis['attempt_count']}")
    print(f"  auto_marked_count              : {analysis['auto_marked_count']}")
    print(f"  teacher_review_required_count  : {analysis['teacher_review_required_count']}")
    print(f"  correct_count                  : {analysis['correct_count']}")
    print(f"  incorrect_count                : {analysis['incorrect_count']}")
    print(f"  accuracy                       : {pct}")
    print(f"  skill_gap_count                : {len(analysis['skill_gaps'])}")
    print(f"  strength_count                 : {len(analysis['strengths'])}")
    print(f"  review_queue_count             : {len(analysis['review_queue'])}")
    print(f"  json    -> {json_path}")
    print(f"  md      -> {md_path}")
    print(f"  preview -> {preview_path}")
    print(f"  report  -> {report_path}")


if __name__ == "__main__":
    main()
