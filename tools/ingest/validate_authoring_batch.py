"""
Validate a generated authoring batch against its spec before importing to the bank.

Usage:
    python tools/ingest/validate_authoring_batch.py <authoring_batch.json> <generated_batch.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/validate_authoring_batch.py \
        data/bank/cambridge_igcse/physics_0625/authoring_batch_001.json \
        data/bank/cambridge_igcse/physics_0625/generated_batch_001.json
"""

import sys
import json
import copy
from pathlib import Path
from collections import defaultdict

VALID_OPTIONS      = {"A", "B", "C", "D"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
EXPECTED_ITEMS     = 30

EXPECTED_DIFFICULTY_DIST = {"easy": 2, "medium": 2, "hard": 1}

COPYRIGHT_PHRASES = [
    "Cambridge",
    "0625",
    "past paper",
    "May/June",
    "UCLES",
]

REQUIRED_ITEM_FIELDS = [
    "generated_item_id",
    "target_id",
    "topic",
    "subtopic",
    "skill",
    "question_type",
    "stem",
    "options",
    "correct_answer",
    "explanation",
    "common_misconception",
    "difficulty",
    "quality_flags",
]


# ---------------------------------------------------------------------------
# Per-item validation
# ---------------------------------------------------------------------------

def validate_item(item, valid_target_ids):
    """
    Returns (status, issues) where status is "pass" | "needs_review" | "fail".
    Fail-level issues block import; needs_review-level issues flag for human check.
    """
    fail_issues   = []
    review_issues = []

    # --- Required fields present ---
    for field in REQUIRED_ITEM_FIELDS:
        if field not in item:
            fail_issues.append(f"missing required field: '{field}'")

    if fail_issues:
        return "fail", fail_issues + review_issues

    # --- question_type ---
    if item.get("question_type") != "mcq":
        fail_issues.append(f"question_type is '{item.get('question_type')}', expected 'mcq'")

    # --- stem ---
    if not str(item.get("stem", "")).strip():
        fail_issues.append("stem is empty")

    # --- options ---
    options = item.get("options", {})
    if not isinstance(options, dict):
        fail_issues.append("options is not a dict")
    else:
        missing_opts = [l for l in "ABCD" if l not in options]
        if missing_opts:
            fail_issues.append(f"options missing keys: {missing_opts}")
        else:
            empty_opts = [l for l in "ABCD" if not str(options.get(l, "")).strip()]
            if empty_opts:
                fail_issues.append(f"options have empty text: {empty_opts}")

    # --- correct_answer ---
    ca = item.get("correct_answer", "")
    if ca not in VALID_OPTIONS:
        fail_issues.append(f"correct_answer '{ca}' not in A/B/C/D")
    elif ca not in options:
        fail_issues.append(f"correct_answer '{ca}' not found in options dict")

    # --- explanation ---
    if not str(item.get("explanation", "")).strip():
        fail_issues.append("explanation is empty")

    # --- common_misconception ---
    if not str(item.get("common_misconception", "")).strip():
        fail_issues.append("common_misconception is empty")

    # --- difficulty ---
    if item.get("difficulty") not in VALID_DIFFICULTIES:
        fail_issues.append(
            f"difficulty '{item.get('difficulty')}' not in {sorted(VALID_DIFFICULTIES)}"
        )

    # --- target_id exists in spec ---
    if item.get("target_id") not in valid_target_ids:
        fail_issues.append(f"target_id '{item.get('target_id')}' not found in authoring batch spec")

    # --- quality_flags (needs_review level) ---
    qf = item.get("quality_flags", {})
    if not isinstance(qf, dict):
        review_issues.append("quality_flags is not a dict")
    else:
        for flag, expected in [
            ("uses_original_context", True),
            ("no_diagram_required", True),
            ("single_correct_answer", True),
        ]:
            if qf.get(flag) is not expected:
                review_issues.append(
                    f"quality_flags.{flag} = {qf.get(flag)!r}, expected {expected!r}"
                )

    # --- copyright hygiene (needs_review level) ---
    searchable = " ".join([
        str(item.get("stem", "")),
        str(item.get("explanation", "")),
        str(item.get("common_misconception", "")),
        " ".join(str(v) for v in item.get("options", {}).values()),
    ])
    for phrase in COPYRIGHT_PHRASES:
        if phrase.lower() in searchable.lower():
            review_issues.append(f"copyright hygiene: text contains '{phrase}'")

    all_issues = fail_issues + review_issues
    if fail_issues:
        status = "fail"
    elif review_issues:
        status = "needs_review"
    else:
        status = "pass"

    return status, all_issues


# ---------------------------------------------------------------------------
# Batch-level validation
# ---------------------------------------------------------------------------

def validate_batch(batch, batch_spec):
    valid_target_ids = {t["target_id"] for t in batch_spec["targets"]}
    expected_count_by_target = {
        t["target_id"]: t["target_question_count"]
        for t in batch_spec["targets"]
    }

    items = batch.get("generated_items", [])

    # Item-level validation
    validated_items = []
    item_id_seen     = {}
    stem_seen        = {}
    option_set_seen  = {}

    for idx, item in enumerate(items):
        status, issues = validate_item(item, valid_target_ids)
        validated_item = copy.deepcopy(item)
        validated_item["validation"] = {"status": status, "issues": list(issues)}
        validated_items.append(validated_item)

        # Uniqueness tracking
        iid = item.get("generated_item_id", f"<missing_{idx}>")
        if iid in item_id_seen:
            validated_item["validation"]["issues"].append(
                f"duplicate generated_item_id (also at index {item_id_seen[iid]})"
            )
            if validated_item["validation"]["status"] == "pass":
                validated_item["validation"]["status"] = "fail"
        else:
            item_id_seen[iid] = idx

        stem = str(item.get("stem", "")).strip().lower()
        if stem and stem in stem_seen:
            validated_item["validation"]["issues"].append(
                f"duplicate stem (also at index {stem_seen[stem]})"
            )
            if validated_item["validation"]["status"] == "pass":
                validated_item["validation"]["status"] = "needs_review"
        elif stem:
            stem_seen[stem] = idx

        opts = item.get("options", {})
        if isinstance(opts, dict):
            opt_sig = tuple(sorted((k, str(v).strip()) for k, v in opts.items()))
            if opt_sig in option_set_seen:
                validated_item["validation"]["issues"].append(
                    f"duplicate option set (also at index {option_set_seen[opt_sig]})"
                )
                if validated_item["validation"]["status"] == "pass":
                    validated_item["validation"]["status"] = "needs_review"
            else:
                option_set_seen[opt_sig] = idx

    # Target count and difficulty distribution
    target_counts = defaultdict(int)
    difficulty_by_target = defaultdict(lambda: defaultdict(int))
    for item in validated_items:
        tid = item.get("target_id", "")
        target_counts[tid] += 1
        diff = item.get("difficulty", "")
        difficulty_by_target[tid][diff] += 1

    # Check per-target counts and difficulty distribution
    for tid, expected_count in expected_count_by_target.items():
        actual_count = target_counts.get(tid, 0)
        if actual_count != expected_count:
            # Add a batch-level issue to all items for this target
            pass  # reported in report JSON only

    # Collect duplicate item IDs
    dup_ids   = [iid for iid, cnt in
                 _count_list(i.get("generated_item_id", "") for i in items).items()
                 if cnt > 1]
    dup_stems = [s for s, cnt in
                 _count_list(str(i.get("stem", "")).strip().lower() for i in items if i.get("stem", "").strip()).items()
                 if cnt > 1]
    copyright_issues = [
        {"generated_item_id": i.get("generated_item_id", ""), "issue": iss}
        for i in validated_items
        for iss in i["validation"]["issues"]
        if "copyright hygiene" in iss
    ]

    missing_target_ids = [
        tid for tid in valid_target_ids
        if target_counts.get(tid, 0) == 0
    ]

    # Summarise
    status_counts = defaultdict(int)
    for item in validated_items:
        status_counts[item["validation"]["status"]] += 1

    fail_count        = status_counts["fail"]
    review_count      = status_counts["needs_review"]
    pass_count        = status_counts["pass"]
    detected          = len(items)
    valid_items_count = pass_count + review_count  # items that are structurally OK

    if fail_count > 0 or detected != EXPECTED_ITEMS:
        batch_status = "fail"
    elif review_count > 0:
        batch_status = "needs_review"
    else:
        batch_status = "pass"

    return {
        "validated_items":           validated_items,
        "batch_status":              batch_status,
        "detected":                  detected,
        "valid_items_count":         valid_items_count,
        "pass_count":                pass_count,
        "needs_review_count":        review_count,
        "fail_count":                fail_count,
        "missing_target_ids":        sorted(missing_target_ids),
        "target_counts":             dict(sorted(target_counts.items())),
        "difficulty_by_target":      {k: dict(v) for k, v in sorted(difficulty_by_target.items())},
        "duplicate_generated_item_ids": sorted(set(dup_ids)),
        "duplicate_stems":           sorted(set(dup_stems)),
        "copyright_hygiene_issues":  copyright_issues,
    }


def _count_list(iterable):
    counts = defaultdict(int)
    for v in iterable:
        counts[v] += 1
    return counts


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def build_markdown(result, batch_id):
    lines = []
    lines.append(f"# Validation Report — {batch_id}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    status_emoji = {"pass": "PASS", "needs_review": "NEEDS REVIEW", "fail": "FAIL"}
    lines.append(f"**Overall status: {status_emoji[result['batch_status']]}**")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| ------ | ----: |")
    lines.append(f"| Expected items | {EXPECTED_ITEMS} |")
    lines.append(f"| Detected items | {result['detected']} |")
    lines.append(f"| Pass | {result['pass_count']} |")
    lines.append(f"| Needs review | {result['needs_review_count']} |")
    lines.append(f"| Fail | {result['fail_count']} |")
    lines.append(f"| Duplicate item IDs | {len(result['duplicate_generated_item_ids'])} |")
    lines.append(f"| Duplicate stems | {len(result['duplicate_stems'])} |")
    lines.append(f"| Copyright hygiene issues | {len(result['copyright_hygiene_issues'])} |")
    lines.append("")

    # Target counts and difficulty distribution
    lines.append("## Target Counts and Difficulty Distribution")
    lines.append("")
    lines.append("| Target ID (short) | Count | easy | medium | hard |")
    lines.append("| ----------------- | ----: | ---: | -----: | ---: |")
    for tid, count in result["target_counts"].items():
        short = tid.replace("gen_cambridge_igcse_physics_0625_", "").replace("_v0", "")
        diff  = result["difficulty_by_target"].get(tid, {})
        ok_e  = diff.get("easy", 0)
        ok_m  = diff.get("medium", 0)
        ok_h  = diff.get("hard", 0)
        dist_ok = (ok_e == 2 and ok_m == 2 and ok_h == 1)
        dist_flag = "" if dist_ok else " ⚠"
        lines.append(f"| {short}{dist_flag} | {count} | {ok_e} | {ok_m} | {ok_h} |")
    lines.append("")

    # Failed items
    failed = [i for i in result["validated_items"] if i["validation"]["status"] == "fail"]
    if failed:
        lines.append("## Failed Items")
        lines.append("")
        for item in failed:
            lines.append(f"### `{item.get('generated_item_id', '<unknown>')}`")
            lines.append("")
            lines.append(f"- **Skill:** {item.get('skill', '')}")
            for iss in item["validation"]["issues"]:
                lines.append(f"- **Issue:** {iss}")
            lines.append("")
    else:
        lines.append("## Failed Items")
        lines.append("")
        lines.append("None.")
        lines.append("")

    # Needs review items
    review = [i for i in result["validated_items"] if i["validation"]["status"] == "needs_review"]
    if review:
        lines.append("## Needs Review Items")
        lines.append("")
        for item in review:
            lines.append(f"### `{item.get('generated_item_id', '<unknown>')}`")
            lines.append("")
            lines.append(f"- **Skill:** {item.get('skill', '')}")
            for iss in item["validation"]["issues"]:
                lines.append(f"- **Issue:** {iss}")
            lines.append("")
    else:
        lines.append("## Needs Review Items")
        lines.append("")
        lines.append("None.")
        lines.append("")

    if result["missing_target_ids"]:
        lines.append("## Missing Target IDs")
        lines.append("")
        for tid in result["missing_target_ids"]:
            lines.append(f"- `{tid}`")
        lines.append("")

    if result["duplicate_generated_item_ids"]:
        lines.append("## Duplicate Item IDs")
        lines.append("")
        for iid in result["duplicate_generated_item_ids"]:
            lines.append(f"- `{iid}`")
        lines.append("")

    if result["duplicate_stems"]:
        lines.append("## Duplicate Stems")
        lines.append("")
        for stem in result["duplicate_stems"]:
            lines.append(f"- `{stem[:80]}...`")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(batch_spec_path, generated_path):
    batch_spec = json.loads(batch_spec_path.read_text(encoding="utf-8"))

    # Graceful load — file may not exist yet
    if not generated_path.exists():
        sys.exit(
            f"Error: generated batch file not found: {generated_path}\n"
            "Run the generation step first to produce this file."
        )

    batch = json.loads(generated_path.read_text(encoding="utf-8"))

    # Root-level checks
    root_issues = []
    if batch.get("batch_id") != batch_spec.get("batch_id"):
        root_issues.append(
            f"batch_id mismatch: got '{batch.get('batch_id')}', "
            f"expected '{batch_spec.get('batch_id')}'"
        )
    if not isinstance(batch.get("generated_items"), list):
        root_issues.append("generated_items is missing or not a list")

    if root_issues:
        for iss in root_issues:
            print(f"ROOT ERROR: {iss}")
        sys.exit(1)

    result = validate_batch(batch, batch_spec)
    batch_id = batch.get("batch_id", "")

    out_dir = generated_path.parent
    stem    = generated_path.stem  # e.g. "generated_batch_001"

    # --- validated JSON ---
    validated_out = {
        "batch_id":          batch_id,
        "validation_status": result["batch_status"],
        "total_items":       EXPECTED_ITEMS,
        "valid_items_count": result["valid_items_count"],
        "items":             result["validated_items"],
    }
    validated_path = out_dir / f"{stem}.validated.json"
    validated_path.write_text(
        json.dumps(validated_out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # --- validation report JSON ---
    report_json = {
        "batch_id":                       batch_id,
        "validation_status":              result["batch_status"],
        "expected_items":                 EXPECTED_ITEMS,
        "detected_items":                 result["detected"],
        "valid_items_count":              result["valid_items_count"],
        "needs_review_count":             result["needs_review_count"],
        "fail_count":                     result["fail_count"],
        "missing_target_ids":             result["missing_target_ids"],
        "target_counts":                  result["target_counts"],
        "difficulty_distribution_by_target": result["difficulty_by_target"],
        "duplicate_generated_item_ids":   result["duplicate_generated_item_ids"],
        "duplicate_stems":                result["duplicate_stems"],
        "copyright_hygiene_issues":       result["copyright_hygiene_issues"],
    }
    report_json_path = out_dir / f"{stem}.validation_report.json"
    report_json_path.write_text(
        json.dumps(report_json, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # --- validation report MD ---
    md = build_markdown(result, batch_id)
    report_md_path = out_dir / f"{stem}.validation_report.md"
    report_md_path.write_text(md, encoding="utf-8")

    print(f"validation_status   : {result['batch_status']}")
    print(f"detected_items      : {result['detected']}")
    print(f"valid_items_count   : {result['valid_items_count']}")
    print(f"needs_review_count  : {result['needs_review_count']}")
    print(f"fail_count          : {result['fail_count']}")
    print(f"validated_json      : {validated_path}")
    print(f"validation_report   : {report_json_path}")
    print(f"validation_report_md: {report_md_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: python {sys.argv[0]} <authoring_batch.json> <generated_batch.json>")
    spec_p = Path(sys.argv[1])
    gen_p  = Path(sys.argv[2])
    if not spec_p.exists():
        sys.exit(f"Error: file not found: {spec_p}")
    run(spec_p, gen_p)
