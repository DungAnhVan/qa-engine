"""
Build internal question bank v0 from reconciled questions.

Usage:
    python tools/ingest/build_internal_bank.py <questions.reconciled.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_internal_bank.py \
        data/ingested/markitdown/cambridge_igcse_physics_0625_2025_s_p21_qp/questions.reconciled.json
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

EXPECTED = 40

SOURCE_META = {
    "board":          "cambridge",
    "level":          "igcse",
    "subject":        "physics",
    "syllabus_code":  "0625",
    "year":           2025,
    "series":         "summer",
    "paper":          "p21",
    "document_type":  "question_paper",
}

ITEM_ID_PREFIX = "cambridge_igcse_physics_0625_2025_s_p21"


# ---------------------------------------------------------------------------
# Quality status
# ---------------------------------------------------------------------------

def get_quality_status(q):
    """
    Priority: not_publishable > needs_human_review > ready_internal

    not_publishable when:
      - options are diagram-label placeholders (content not usable as-is)
      - stem is empty (question cannot be understood without PDF)
      - table parsing broke and options weren't recovered (has_table AND
        options_complete=False AND no reconciliation applied)

    needs_human_review: any remaining needs_review=True question

    ready_internal: needs_review=False, all four options present
    """
    flags = q.get("flags", {})
    recon = q.get("option_reconciliation")

    if recon == "diagram_label_placeholder":
        return "not_publishable"

    if flags.get("stem_empty", False):
        return "not_publishable"

    # Table completely broke parsing and was not manually reconciled
    if (flags.get("has_table") and not flags.get("options_complete") and not recon):
        return "not_publishable"

    if q.get("needs_review", False):
        return "needs_human_review"

    return "ready_internal"


# ---------------------------------------------------------------------------
# Item builder
# ---------------------------------------------------------------------------

def build_item(q):
    qnum  = q["question_number"]
    flags = q.get("flags", {})
    qs    = get_quality_status(q)

    return {
        "item_id":        f"{ITEM_ID_PREFIX}_q{qnum:02d}",
        "source":         dict(SOURCE_META),
        "question_number": qnum,
        "question_type":  "mcq",
        "stem":           q.get("stem", ""),
        "options":        q.get("options", {}),
        "correct_answer": q.get("correct_answer"),
        "topic":          q.get("topic", ""),
        "subtopic":       q.get("subtopic", ""),
        "skill":          q.get("skill", ""),
        "confidence":     q.get("confidence", ""),
        "quality": {
            "needs_review":         q.get("needs_review", False),
            "issues":               q.get("issues", []),
            "has_diagram":          flags.get("has_diagram_hint", False),
            "has_table":            flags.get("has_table", False),
            "option_reconciliation": recon_value(q),
        },
        "quality_status":   qs,
        "raw": {
            "normalized_raw_block": q.get("normalized_raw_block", ""),
            "original_raw_block":   q.get("original_raw_block", ""),
        },
        "copyright_status": "internal_reference_only",
    }


def recon_value(q):
    return q.get("option_reconciliation", None)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_bank(reconciled_path):
    data      = json.loads(reconciled_path.read_text(encoding="utf-8"))
    questions = data["questions"]

    items = sorted(
        [build_item(q) for q in questions],
        key=lambda x: x["question_number"],
    )

    # Aggregate counts
    status_counts = defaultdict(int)
    topic_counts  = defaultdict(int)
    for item in items:
        status_counts[item["quality_status"]] += 1
        topic_counts[item["topic"]] += 1

    diagram_ph_nums = sorted(
        item["question_number"] for item in items
        if item["quality"]["option_reconciliation"] == "diagram_label_placeholder"
    )
    empty_stem_nums = sorted(
        item["question_number"] for item in items
        if any("stem is empty" in iss for iss in item["quality"]["issues"])
    )
    table_nums = sorted(
        item["question_number"] for item in items
        if item["quality"]["has_table"]
    )

    # Output directory: data/bank/cambridge_igcse/physics_0625/
    out_dir = Path("data/bank/cambridge_igcse/physics_0625")
    out_dir.mkdir(parents=True, exist_ok=True)

    bank_out = {
        "document_id": data["document_id"],
        "total_items": EXPECTED,
        "items":       items,
    }
    bank_path = out_dir / "internal_bank_v0.json"
    bank_path.write_text(
        json.dumps(bank_out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report_out = {
        "total_items":                     EXPECTED,
        "ready_internal_count":            status_counts["ready_internal"],
        "needs_human_review_count":        status_counts["needs_human_review"],
        "not_publishable_count":           status_counts["not_publishable"],
        "topic_counts":                    dict(sorted(topic_counts.items())),
        "items_with_diagram_placeholders": diagram_ph_nums,
        "items_with_empty_stem":           empty_stem_nums,
        "items_with_tables":               table_nums,
    }
    report_path = out_dir / "internal_bank_report.json"
    report_path.write_text(
        json.dumps(report_out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"total_items               : {EXPECTED}")
    print(f"ready_internal_count      : {status_counts['ready_internal']}")
    print(f"needs_human_review_count  : {status_counts['needs_human_review']}")
    print(f"not_publishable_count     : {status_counts['not_publishable']}")
    print(f"internal_bank_v0          : {bank_path}")
    print(f"internal_bank_report      : {report_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <questions.reconciled.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    build_bank(p)
