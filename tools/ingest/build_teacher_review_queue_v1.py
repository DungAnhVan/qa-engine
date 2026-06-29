"""
Build the Teacher Review Queue and Publish Candidate Bank from the Original Resource Bank.

Splits bank items into:
  - teacher_review_required  → teacher_review_queue_v1.json + teacher_review_queue_v1.md
  - publish_ready            → publish_candidate_resource_bank_v1.json

Usage:
    python tools/ingest/build_teacher_review_queue_v1.py \\
        data/bank/cambridge_igcse/physics_0625/original_resource_bank/\\
        original_resource_bank_v1.json

Output (data/bank/cambridge_igcse/physics_0625/teacher_review/):
    teacher_review_queue_v1.json
    teacher_review_queue_v1.md
    publish_candidate_resource_bank_v1.json
    teacher_review_queue_v1_report.json
    teacher_review_queue_v1_manifest.md
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Suggested action heuristic
# ---------------------------------------------------------------------------

def derive_suggested_action(warnings: list[str]) -> str:
    """Map validation warnings to a human-readable suggested action."""
    joined = " ".join(warnings).lower()
    if "very short" in joined and "unit" in joined:
        return "expand_worked_solution_and_add_unit_criteria"
    if "very short" in joined:
        return "expand_worked_solution"
    if "unit" in joined:
        return "add_unit_criteria_to_marking_guidance"
    if "checklist" in joined:
        return "review_checklist_structure"
    if "graphing" in joined:
        return "review_graphing_content"
    if "planning" in joined:
        return "review_planning_content"
    if "correct_answer" in joined or "worked_solution does not mention" in joined:
        return "verify_answer_explanation"
    return "review_content_quality"


# ---------------------------------------------------------------------------
# Review item builder
# ---------------------------------------------------------------------------

def make_review_id(bank_item_id: str) -> str:
    return f"rev_{bank_item_id}"


def build_review_item(bank_item: dict) -> dict:
    warnings = bank_item.get("validation_warnings") or []
    return {
        "review_id":         make_review_id(bank_item["bank_item_id"]),
        "bank_item_id":      bank_item["bank_item_id"],
        "resource_id":       bank_item.get("resource_id", ""),
        "resource_type":     bank_item.get("resource_type", ""),
        "component_type":    bank_item.get("component_type", ""),
        "topic":             bank_item.get("topic", ""),
        "skill_name":        bank_item.get("skill_name", ""),
        "skill_type":        bank_item.get("skill_type", ""),
        "difficulty":        bank_item.get("difficulty", ""),
        "student_prompt":    bank_item.get("student_prompt"),
        "options":           bank_item.get("options"),
        "correct_answer":    bank_item.get("correct_answer"),
        "worked_solution":   bank_item.get("worked_solution"),
        "marking_guidance":  bank_item.get("marking_guidance"),
        "common_misconception": bank_item.get("common_misconception"),
        "teacher_note":      bank_item.get("teacher_note"),
        "validation_warnings": warnings,
        "validation_errors": bank_item.get("validation_errors") or [],
        "review_status":     "pending",
        "teacher_decision":  None,
        "teacher_notes":     "",
        "suggested_action":  derive_suggested_action(warnings),
    }


# ---------------------------------------------------------------------------
# Markdown builder
# ---------------------------------------------------------------------------

def _md_field(label: str, value) -> str:
    if value is None:
        return f"**{label}:** *(none)*\n"
    text = str(value).strip()
    if not text:
        return f"**{label}:** *(empty)*\n"
    # Indent multi-line values
    lines = text.splitlines()
    if len(lines) == 1:
        return f"**{label}:** {text}\n"
    indented = "\n".join(f"  {ln}" for ln in lines)
    return f"**{label}:**\n{indented}\n"


def build_review_md(review_items: list[dict], queue_id: str, created_at: str) -> str:
    lines: list[str] = [
        "# Quanta Aptus Teacher Review Queue v1",
        "",
        f"- **Queue ID:** `{queue_id}`",
        f"- **Created:** {created_at}",
        f"- **Items requiring review:** {len(review_items)}",
        "",
        "---",
        "",
    ]

    for n, item in enumerate(review_items, start=1):
        warnings = item.get("validation_warnings") or []
        options  = item.get("options") or {}

        lines += [
            f"## Review Item {n}",
            "",
            f"- **Review ID:** `{item['review_id']}`",
            f"- **Bank Item ID:** `{item['bank_item_id']}`",
            f"- **Resource ID:** `{item['resource_id']}`",
            f"- **Resource type:** {item['resource_type']}",
            f"- **Component:** {item['component_type']}",
            f"- **Topic:** {item['topic']}",
            f"- **Skill:** {item['skill_name']}",
            f"- **Difficulty:** {item['difficulty']}",
            f"- **Suggested action:** {item['suggested_action']}",
            "",
        ]

        if warnings:
            lines.append("### Validation Warnings")
            lines.append("")
            for w in warnings:
                lines.append(f"- {w}")
            lines.append("")

        lines.append("### Content")
        lines.append("")

        sp = (item.get("student_prompt") or "").strip()
        if sp:
            lines.append("**Student Prompt:**")
            lines.append("")
            lines.append(sp)
            lines.append("")

        # Options for MCQ
        if options and any(v for v in options.values() if v):
            lines.append("**Options:**")
            lines.append("")
            for key in ("A", "B", "C", "D"):
                val = options.get(key) or ""
                if val:
                    lines.append(f"- {key}: {val}")
            ca = item.get("correct_answer")
            if ca:
                lines.append(f"\n**Correct answer:** {ca}")
            lines.append("")

        ws = (item.get("worked_solution") or "").strip()
        if ws:
            lines.append("**Worked Solution:**")
            lines.append("")
            lines.append(ws)
            lines.append("")

        mg = (item.get("marking_guidance") or "").strip()
        if mg:
            lines.append("**Marking Guidance:**")
            lines.append("")
            lines.append(mg)
            lines.append("")

        cm = (item.get("common_misconception") or "").strip()
        if cm:
            lines.append("**Common Misconception:**")
            lines.append("")
            lines.append(cm)
            lines.append("")

        tn = (item.get("teacher_note") or "").strip()
        if tn:
            lines.append("**Teacher Note:**")
            lines.append("")
            lines.append(tn)
            lines.append("")

        lines += [
            "### Teacher Checklist",
            "",
            "- [ ] Scientifically correct",
            "- [ ] Wording clear for IGCSE student",
            "- [ ] Marking guidance complete",
            "- [ ] Units / significant figures handled",
            "- [ ] No Cambridge wording or context copied",
            "- [ ] Approve",
            "- [ ] Revise",
            "- [ ] Reject",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Summary helper
# ---------------------------------------------------------------------------

def aggregate_summary(items: list[dict], key_fields: list[str]) -> dict:
    result: dict[str, dict[str, int]] = {f: {} for f in key_fields}
    for item in items:
        for field in key_fields:
            val = item.get(field) or ""
            if val:
                result[field][val] = result[field].get(val, 0) + 1
    return result


# ---------------------------------------------------------------------------
# JSON / output builders
# ---------------------------------------------------------------------------

def build_queue_json(
    review_items: list[dict],
    queue_id: str,
    source_bank_id: str,
    meta: dict,
    now_iso: str,
) -> dict:
    agg = aggregate_summary(
        review_items,
        ["resource_type", "component_type", "topic", "skill_type", "difficulty"],
    )
    return {
        "queue_id":          queue_id,
        "version":           "0.1.0",
        "status":            "ready_for_teacher_review",
        "created_at":        now_iso,
        "source_bank_id":    source_bank_id,
        "board":             meta["board"],
        "level":             meta["level"],
        "subject":           meta["subject"],
        "syllabus_code":     meta["syllabus_code"],
        "review_item_count": len(review_items),
        "items":             review_items,
        "summary": {
            "review_item_count": len(review_items),
            "resource_types":    agg["resource_type"],
            "component_types":   agg["component_type"],
            "topics":            agg["topic"],
            "skill_types":       agg["skill_type"],
            "difficulties":      agg["difficulty"],
        },
    }


def build_candidate_json(
    candidates: list[dict],
    candidate_id: str,
    source_bank_id: str,
    now_iso: str,
) -> dict:
    return {
        "candidate_bank_id": candidate_id,
        "version":           "0.1.0",
        "status":            "publish_candidates",
        "created_at":        now_iso,
        "source_bank_id":    source_bank_id,
        "candidate_count":   len(candidates),
        "items":             candidates,
    }


def build_report(
    bank_doc: dict,
    publish_candidates: list[dict],
    review_items: list[dict],
    out_files: dict,
) -> dict:
    total = bank_doc.get("item_count", 0)
    pub   = len(publish_candidates)
    rev   = len(review_items)
    excl  = total - pub - rev

    agg = aggregate_summary(
        bank_doc.get("items", []),
        ["resource_type", "component_type", "topic"],
    )

    if total == 0:
        status = "failed"
    elif pub == 0 and rev > 0:
        status = "needs_review"
    elif pub > 0 or rev > 0:
        status = "passed"
    else:
        status = "failed"

    return {
        "status":                        status,
        "source_bank_id":                bank_doc.get("bank_id", ""),
        "total_bank_items":              total,
        "publish_candidate_count":       pub,
        "teacher_review_required_count": rev,
        "excluded_count":                excl,
        "resource_types":                agg["resource_type"],
        "component_types":               agg["component_type"],
        "topics":                        agg["topic"],
        "output_files":                  out_files,
    }


def build_manifest_md(
    bank_doc: dict,
    report: dict,
    meta: dict,
    queue_id: str,
    now_iso: str,
) -> str:
    lines = [
        "# Quanta Aptus Teacher Review Queue v1",
        "",
        f"- **Board:** {meta['board'].title()}",
        f"- **Level:** {meta['level'].upper()}",
        f"- **Subject:** {meta['subject'].title()}",
        f"- **Syllabus:** {meta['syllabus_code']}",
        f"- **Queue ID:** `{queue_id}`",
        f"- **Status:** {report['status']}",
        f"- **Created:** {now_iso}",
        "",
        f"- **Source bank:** `{bank_doc.get('bank_id', '')}`",
        "",
        "## Item Counts",
        "",
        f"- **Total bank items:** {report['total_bank_items']}",
        f"- **Publish candidates:** {report['publish_candidate_count']}",
        f"- **Teacher review required:** {report['teacher_review_required_count']}",
        f"- **Excluded:** {report['excluded_count']}",
        "",
        "## Resource Types",
        "",
    ]
    for rt, count in sorted(report["resource_types"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{rt}:** {count}")

    lines += ["", "## Topics", ""]
    for topic, count in sorted(report["topics"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{topic}:** {count}")

    lines += ["", "## Output Paths", ""]
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")

    lines += [
        "",
        "---",
        "",
        "> Teacher review queue contains original Quanta Aptus resources that need",
        "> human approval before publishing.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON loader
# ---------------------------------------------------------------------------

def load_json(path: Path) -> tuple[dict | list | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build teacher review queue and publish candidate bank."
    )
    ap.add_argument("bank_json", help="Path to original_resource_bank_v1.json")
    args = ap.parse_args()

    bank_path = Path(args.bank_json)
    if not bank_path.exists():
        sys.exit(f"Error: file not found: {bank_path}")

    bank_doc, err = load_json(bank_path)
    if err:
        sys.exit(f"Error reading bank: {err}")
    if not isinstance(bank_doc, dict):
        sys.exit("Error: bank must be a JSON object.")

    now_iso      = datetime.now(timezone.utc).isoformat()
    source_bank_id = bank_doc.get("bank_id", "")
    all_items      = bank_doc.get("items", [])

    meta = {
        "board":         bank_doc.get("board",         "cambridge"),
        "level":         bank_doc.get("level",         "igcse"),
        "subject":       bank_doc.get("subject",       "physics"),
        "syllabus_code": bank_doc.get("syllabus_code", "0625"),
    }

    # ── Split items ──────────────────────────────────────────────────────────
    publish_candidates: list[dict] = []
    review_bank_items:  list[dict] = []

    for item in all_items:
        bs = item.get("bank_status", "")
        if bs == "publish_ready":
            publish_candidates.append(item)
        elif bs == "teacher_review_required":
            review_bank_items.append(item)
        # Items without recognised bank_status are silently excluded

    review_items = [build_review_item(bi) for bi in review_bank_items]

    # ── IDs ──────────────────────────────────────────────────────────────────
    board    = meta["board"]
    level    = meta["level"]
    subject  = meta["subject"]
    syllabus = meta["syllabus_code"]

    queue_id     = f"{board}_{level}_{subject}_{syllabus}_teacher_review_queue_v1"
    candidate_id = f"{board}_{level}_{subject}_{syllabus}_publish_candidate_resource_bank_v1"

    out_dir = bank_path.parent.parent / "teacher_review"
    out_dir.mkdir(parents=True, exist_ok=True)

    queue_json_path = out_dir / "teacher_review_queue_v1.json"
    queue_md_path   = out_dir / "teacher_review_queue_v1.md"
    cand_json_path  = out_dir / "publish_candidate_resource_bank_v1.json"
    report_path     = out_dir / "teacher_review_queue_v1_report.json"
    manifest_path   = out_dir / "teacher_review_queue_v1_manifest.md"

    out_files = {
        "teacher_review_queue_json":        str(queue_json_path),
        "teacher_review_queue_md":          str(queue_md_path),
        "publish_candidate_resource_bank":  str(cand_json_path),
        "report":                           str(report_path),
        "manifest":                         str(manifest_path),
    }

    # ── Build outputs ────────────────────────────────────────────────────────
    queue_doc  = build_queue_json(review_items, queue_id, source_bank_id, meta, now_iso)
    queue_md   = build_review_md(review_items, queue_id, now_iso)
    cand_doc   = build_candidate_json(publish_candidates, candidate_id, source_bank_id, now_iso)
    report     = build_report(bank_doc, publish_candidates, review_items, out_files)
    manifest   = build_manifest_md(bank_doc, report, meta, queue_id, now_iso)

    queue_json_path.write_text(
        json.dumps(queue_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    queue_md_path.write_text(queue_md, encoding="utf-8")
    cand_json_path.write_text(
        json.dumps(cand_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    manifest_path.write_text(manifest, encoding="utf-8")

    print(f"status                          : {report['status']}")
    print(f"total_bank_items                : {report['total_bank_items']}")
    print(f"publish_candidate_count         : {report['publish_candidate_count']}")
    print(f"teacher_review_required_count   : {report['teacher_review_required_count']}")
    print(f"resource_types                  : {report['resource_types']}")
    print(f"component_types                 : {report['component_types']}")
    print(f"topics                          : {report['topics']}")
    print(f"teacher review json             : {queue_json_path}")
    print(f"teacher review md               : {queue_md_path}")
    print(f"publish candidate bank          : {cand_json_path}")
    print(f"report                          : {report_path}")
    print(f"manifest                        : {manifest_path}")


if __name__ == "__main__":
    main()
