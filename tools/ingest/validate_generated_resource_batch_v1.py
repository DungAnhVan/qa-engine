"""
Validate a Quanta Aptus generated resource batch against its authoring batch.

Checks: schema structure, copyright leakage, dummy placeholders, MCQ rules,
resource-type-specific rules, duplicate detection, and planned-count coverage.

Usage:
    python tools/ingest/validate_generated_resource_batch_v1.py \\
        data/bank/.../authoring_batches/authoring_batch_v1_001.json \\
        data/bank/.../generated_batches/generated_resource_batch_v1_001.json

Output (same folder as generated batch):
    generated_resource_batch_v1_001.validated.json
    generated_resource_batch_v1_001.validation_report.json
    generated_resource_batch_v1_001.validation_manifest.md
"""

import sys
import re
import json
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "resource_id", "target_id", "resource_type", "component_type",
    "topic", "skill_name", "skill_type", "difficulty",
    "student_prompt", "worked_solution", "marking_guidance",
    "common_misconception", "teacher_note", "estimated_time_minutes",
    "originality_statement",
]

VALID_DIFFICULTIES = {"easy", "medium", "hard"}

VALID_RESOURCE_TYPES = {
    "original_mcq", "worked_explanation", "calculation_drill",
    "short_answer_explanation", "short_answer_recall", "definition_flashcard",
    "misconception_drill", "worked_example", "short_answer_calculation",
    "diagram_or_graph_drill", "marking_checklist", "data_interpretation_drill",
    "graphing_drill", "graph_marking_checklist", "table_design_drill",
    "measurement_drill", "practical_accuracy_checklist",
    "experiment_planning_task", "planning_marking_checklist",
    "evaluation_improvement_drill", "practical_calculation_drill",
    "fair_test_variable_drill", "review_before_generation",
}

CALCULATION_RESOURCE_TYPES = {
    "calculation_drill", "short_answer_calculation",
    "worked_example", "practical_calculation_drill",
}

CHECKLIST_RESOURCE_TYPES = {
    "marking_checklist", "graph_marking_checklist",
    "planning_marking_checklist", "practical_accuracy_checklist",
}

# (pattern, case_sensitive)
COPYRIGHT_PATTERNS: list[tuple[str, bool]] = [
    ("Cambridge",        True),
    ("UCLES",            True),
    ("0625/",            True),
    ("Paper 4",          True),
    ("Paper 6",          True),
    ("May/June 2025",    True),
    ("question paper",   False),
    ("mark scheme",      False),
    ("as in the source", False),
    ("from the exam",    False),
    ("Cambridge source", False),
]

PLACEHOLDER_PATTERNS: list[tuple[str, bool]] = [
    ("placeholder",                         False),
    ("TODO",                                True),
    ("lorem ipsum",                         False),
    ("option alpha",                        False),
    ("option beta",                         False),
    ("Original question",                   True),
    ("core principle",                      False),
    ("Students often confuse the key terms",False),
    ("sample text",                         False),
]

# Fields to scan for copyright and placeholder leakage
CONTENT_FIELDS = [
    "student_prompt", "worked_solution", "marking_guidance",
    "teacher_note", "common_misconception",
]

GRAPHING_KEYWORDS = {"axes", "scale", "plot", "best-fit", "graph", "data"}

PLANNING_KEYWORDS = {
    "variable", "apparatus", "method", "table",
    "repeat", "conclusion", "control", "measure",
}

DIGIT_RE = re.compile(r'\d')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> tuple[dict | list | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"JSON decode error: {exc}"
    except Exception as exc:
        return None, str(exc)


def get_str(obj: dict, key: str) -> str:
    """Return string value or empty string."""
    v = obj.get(key)
    return str(v) if v is not None else ""


def contains_pattern(text: str, pattern: str, case_sensitive: bool) -> bool:
    if case_sensitive:
        return pattern in text
    return pattern.lower() in text.lower()


def check_copyright_leakage(resource: dict) -> list[str]:
    hits: list[str] = []
    for field in CONTENT_FIELDS:
        text = get_str(resource, field)
        if not text:
            continue
        for pattern, cs in COPYRIGHT_PATTERNS:
            if contains_pattern(text, pattern, cs):
                hits.append(f"Field '{field}' contains copyright marker: \"{pattern}\"")
    return hits


def check_placeholder(resource: dict) -> list[str]:
    hits: list[str] = []
    for field in CONTENT_FIELDS:
        text = get_str(resource, field)
        if not text:
            continue
        for pattern, cs in PLACEHOLDER_PATTERNS:
            if contains_pattern(text, pattern, cs):
                hits.append(f"Field '{field}' contains placeholder text: \"{pattern}\"")
    return hits


# ---------------------------------------------------------------------------
# Item-level validator
# ---------------------------------------------------------------------------

class ItemResult:
    __slots__ = ("errors", "warnings")

    def __init__(self) -> None:
        self.errors:   list[str] = []
        self.warnings: list[str] = []

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def status(self) -> str:
        if self.errors:
            return "failed"
        if self.warnings:
            return "needs_review"
        return "passed"


def validate_resource(
    res: dict,
    target_map: dict,
    seen_resource_ids: dict,   # mutated in place
    seen_prompts: dict,        # mutated in place
) -> ItemResult:
    r = ItemResult()

    # ── 1. Required fields ──────────────────────────────────────────────────
    for field in REQUIRED_FIELDS:
        if field not in res:
            r.fail(f"Missing required field: '{field}'")

    if r.errors:
        # Can't safely continue without basic structure
        return r

    resource_id   = get_str(res, "resource_id")
    target_id     = get_str(res, "target_id")
    resource_type = get_str(res, "resource_type")
    difficulty    = get_str(res, "difficulty")
    orig_stmt     = get_str(res, "originality_statement")
    student_prompt = get_str(res, "student_prompt")
    worked_sol     = get_str(res, "worked_solution")
    marking_guid   = get_str(res, "marking_guidance")

    # ── 2. Duplicate resource_id ────────────────────────────────────────────
    if resource_id in seen_resource_ids:
        r.fail(f"Duplicate resource_id: '{resource_id}' (first seen at index {seen_resource_ids[resource_id]})")
    else:
        seen_resource_ids[resource_id] = res.get("_index", -1)

    # ── 3. target_id must exist in authoring batch ──────────────────────────
    if not target_id:
        r.fail("target_id is empty")
    elif target_id not in target_map:
        r.fail(f"Unknown target_id: '{target_id}' (not in authoring batch)")

    # ── 4. resource_type must match authoring batch target ──────────────────
    if not resource_type:
        r.fail("resource_type is empty")
    elif target_id in target_map:
        expected_rt = target_map[target_id].get("resource_type", "")
        if resource_type != expected_rt:
            r.fail(
                f"resource_type mismatch: generated='{resource_type}', "
                f"expected='{expected_rt}' for target '{target_id}'"
            )

    # ── 5. Difficulty ───────────────────────────────────────────────────────
    if difficulty not in VALID_DIFFICULTIES:
        r.fail(f"Invalid difficulty: '{difficulty}' (must be easy/medium/hard)")

    # ── 6. Originality statement ────────────────────────────────────────────
    if "Original Quanta Aptus content" not in orig_stmt:
        r.fail(
            "originality_statement must contain 'Original Quanta Aptus content' "
            f"(got: '{orig_stmt[:80]}')"
        )

    # ── 7. Copyright leakage ────────────────────────────────────────────────
    for hit in check_copyright_leakage(res):
        r.fail(f"COPYRIGHT LEAK — {hit}")

    # ── 8. Placeholder / dummy content ─────────────────────────────────────
    for hit in check_placeholder(res):
        r.fail(f"PLACEHOLDER — {hit}")

    # ── 9. Duplicate student_prompt ─────────────────────────────────────────
    prompt_key = student_prompt.strip()
    if prompt_key:
        if prompt_key in seen_prompts:
            r.warn(
                f"Duplicate student_prompt (exact match with resource "
                f"'{seen_prompts[prompt_key]}')"
            )
        else:
            seen_prompts[prompt_key] = resource_id

    # ── 10. MCQ-specific rules ──────────────────────────────────────────────
    if resource_type == "original_mcq":
        _validate_mcq(res, r)
    else:
        _validate_non_mcq(res, r)

    # ── 11. Checklist rules ─────────────────────────────────────────────────
    if resource_type in CHECKLIST_RESOURCE_TYPES:
        _validate_checklist(res, r)

    # ── 12. Graphing drill ──────────────────────────────────────────────────
    if resource_type == "graphing_drill":
        _validate_graphing_drill(student_prompt, worked_sol, marking_guid, r)

    # ── 13. Experiment planning ─────────────────────────────────────────────
    if resource_type == "experiment_planning_task":
        _validate_experiment_planning(student_prompt, marking_guid, r)

    # ── 14. Calculation resources ───────────────────────────────────────────
    if resource_type in CALCULATION_RESOURCE_TYPES:
        _validate_calculation(student_prompt, worked_sol, marking_guid, r)

    return r


# ---------------------------------------------------------------------------
# Resource-type sub-validators
# ---------------------------------------------------------------------------

def _validate_mcq(res: dict, r: ItemResult) -> None:
    options       = res.get("options")
    correct_answer = get_str(res, "correct_answer")
    student_prompt = get_str(res, "student_prompt")
    worked_sol     = get_str(res, "worked_solution")
    misconception  = get_str(res, "common_misconception")

    # options must be a dict with A, B, C, D
    if not isinstance(options, dict):
        r.fail("original_mcq: options must be an object with keys A, B, C, D")
    else:
        for key in ("A", "B", "C", "D"):
            if key not in options:
                r.fail(f"original_mcq: options missing key '{key}'")
            elif not isinstance(options[key], str) or not options[key].strip():
                r.fail(f"original_mcq: option '{key}' must be a non-empty string")
        extra = set(options.keys()) - {"A", "B", "C", "D"}
        if extra:
            r.fail(f"original_mcq: options has unexpected keys: {sorted(extra)}")

    if correct_answer not in ("A", "B", "C", "D"):
        r.fail(
            f"original_mcq: correct_answer must be A, B, C, or D "
            f"(got '{correct_answer}')"
        )

    if not student_prompt.strip():
        r.fail("original_mcq: student_prompt must be non-empty")

    if not worked_sol.strip():
        r.fail("original_mcq: worked_solution must be non-empty")
    elif correct_answer in ("A", "B", "C", "D"):
        # Worked solution should reference the correct option
        if correct_answer not in worked_sol:
            r.warn(
                "original_mcq: worked_solution does not mention the correct "
                f"answer letter '{correct_answer}'"
            )

    if not misconception.strip():
        r.fail("original_mcq: common_misconception must be non-empty")


def _validate_non_mcq(res: dict, r: ItemResult) -> None:
    student_prompt = get_str(res, "student_prompt")
    worked_sol     = get_str(res, "worked_solution")
    marking_guid   = get_str(res, "marking_guidance")
    options        = res.get("options")
    resource_type  = get_str(res, "resource_type")

    # For teacher-facing checklists, student_prompt may legitimately be empty/null
    is_checklist = resource_type in CHECKLIST_RESOURCE_TYPES
    if not is_checklist and not student_prompt.strip():
        r.fail("non-MCQ: student_prompt must be non-empty")

    if not worked_sol.strip() and not marking_guid.strip():
        r.fail("non-MCQ: at least one of worked_solution or marking_guidance must be non-empty")

    # If options are present they must be a valid A-D dict or all-null
    if options is not None and isinstance(options, dict):
        all_null = all(v is None for v in options.values())
        if not all_null:
            for key in ("A", "B", "C", "D"):
                if key in options and options[key] is not None:
                    if not isinstance(options[key], str) or not options[key].strip():
                        r.warn(
                            f"non-MCQ: option '{key}' is present and non-null "
                            "but not a valid string"
                        )


def _validate_checklist(res: dict, r: ItemResult) -> None:
    marking_guid  = get_str(res, "marking_guidance")
    correct_answer = res.get("correct_answer")

    if correct_answer is not None and correct_answer != "null":
        # correct_answer should be null for checklists
        r.warn("checklist: correct_answer should be null")

    if not marking_guid.strip():
        r.fail("checklist: marking_guidance must be non-empty")
        return

    # Detect checklist-like structure: bullets or numbered points
    has_bullets  = bool(re.search(r'^\s*[-*•]', marking_guid, re.MULTILINE))
    has_numbered = bool(re.search(r'^\s*\d+[.)]\s', marking_guid, re.MULTILINE))
    has_mp       = bool(re.search(r'\bMP\d\b', marking_guid))

    if not (has_bullets or has_numbered or has_mp):
        r.warn(
            "checklist: marking_guidance does not appear to contain a "
            "checklist structure (bullets, numbered points, or MP marks)"
        )


def _validate_graphing_drill(
    student_prompt: str, worked_sol: str, marking_guid: str, r: ItemResult
) -> None:
    combined = (student_prompt + " " + worked_sol).lower()
    matched = {kw for kw in GRAPHING_KEYWORDS if kw in combined}
    if len(matched) < 2:
        r.warn(
            f"graphing_drill: student_prompt or worked_solution mentions only "
            f"{len(matched)} graphing keyword(s) (need at least 2 of: "
            f"{sorted(GRAPHING_KEYWORDS)}). Found: {sorted(matched) or 'none'}"
        )
    if not marking_guid.strip():
        r.fail("graphing_drill: marking_guidance must be non-empty")


def _validate_experiment_planning(
    student_prompt: str, marking_guid: str, r: ItemResult
) -> None:
    combined = (student_prompt + " " + marking_guid).lower()
    matched = {kw for kw in PLANNING_KEYWORDS if kw in combined}
    if len(matched) < 3:
        r.warn(
            f"experiment_planning_task: student_prompt or marking_guidance mentions "
            f"only {len(matched)} planning keyword(s) (need at least 3 of: "
            f"{sorted(PLANNING_KEYWORDS)}). Found: {sorted(matched) or 'none'}"
        )


def _validate_calculation(
    student_prompt: str, worked_sol: str, marking_guid: str, r: ItemResult
) -> None:
    combined = student_prompt + " " + worked_sol
    if not DIGIT_RE.search(combined):
        r.fail(
            "calculation resource: at least one number must appear in "
            "student_prompt or worked_solution"
        )

    if worked_sol.strip() and len(worked_sol.strip()) < 50:
        r.warn(
            "calculation resource: worked_solution is very short "
            f"({len(worked_sol.strip())} chars) — may be missing step-by-step working"
        )

    marking_lower = marking_guid.lower()
    if "unit" not in marking_lower and "units" not in marking_lower:
        r.warn(
            "calculation resource: marking_guidance does not mention 'unit' "
            "or 'units' — consider adding unit award criteria"
        )


# ---------------------------------------------------------------------------
# Batch-level aggregation
# ---------------------------------------------------------------------------

def check_planned_counts(
    resources: list[dict], target_map: dict
) -> list[str]:
    """Compare actual generated counts vs planned_item_count per target."""
    actual: dict[str, int] = {}
    for res in resources:
        tid = get_str(res, "target_id")
        if tid:
            actual[tid] = actual.get(tid, 0) + 1

    warnings: list[str] = []
    for tid, tgt in target_map.items():
        planned = tgt.get("planned_item_count", 0)
        gen     = actual.get(tid, 0)
        if gen == 0:
            warnings.append(
                f"Target '{tid}': planned {planned} item(s) but 0 generated"
            )
        elif gen < planned:
            warnings.append(
                f"Target '{tid}': planned {planned} item(s) but only {gen} generated"
            )
        elif gen > planned + 2:
            warnings.append(
                f"Target '{tid}': planned {planned} item(s) but {gen} generated "
                "(more than expected + 2)"
            )
    return warnings


# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------

def build_validated_json(
    generated_batch: dict,
    auth_path: str,
    validated_resources: list[dict],
) -> dict:
    n = len(validated_resources)
    passed = sum(1 for r in validated_resources if r["validation_status"] == "passed")
    needs  = sum(1 for r in validated_resources if r["validation_status"] == "needs_review")
    failed = sum(1 for r in validated_resources if r["validation_status"] == "failed")

    if n == 0 or failed > 0:
        status = "failed"
    elif needs > 0:
        status = "needs_review"
    else:
        status = "passed"

    return {
        "batch_id":                generated_batch.get("batch_id", ""),
        "schema_version":          "validated_generated_resource_batch_v1",
        "source_authoring_batch":  auth_path,
        "status":                  status,
        "generated_count":         n,
        "passed_count":            passed,
        "needs_review_count":      needs,
        "failed_count":            failed,
        "resources":               validated_resources,
    }


def build_report(
    validated: dict,
    auth_path: str,
    gen_path: str,
    target_map: dict,
    copyright_leak_count: int,
    dummy_placeholder_count: int,
    dup_resource_id_count: int,
    dup_prompt_count: int,
    unknown_target_count: int,
    batch_warnings: list[str],
    out_files: dict,
) -> dict:
    resources = validated["resources"]
    generated_tids = {get_str(r, "target_id") for r in resources if get_str(r, "target_id")}
    missing_tids   = [tid for tid in target_map if tid not in generated_tids]

    resource_types:  dict[str, int] = {}
    component_types: dict[str, int] = {}
    for res in resources:
        rt = get_str(res, "resource_type")
        ct = get_str(res, "component_type")
        resource_types[rt]  = resource_types.get(rt, 0) + 1
        component_types[ct] = component_types.get(ct, 0) + 1

    return {
        "status":                         validated["status"],
        "batch_id":                        validated["batch_id"],
        "authoring_batch_file":            auth_path,
        "generated_batch_file":            gen_path,
        "generated_count":                 validated["generated_count"],
        "passed_count":                    validated["passed_count"],
        "needs_review_count":              validated["needs_review_count"],
        "failed_count":                    validated["failed_count"],
        "unknown_target_count":            unknown_target_count,
        "copyright_leak_count":            copyright_leak_count,
        "dummy_placeholder_count":         dummy_placeholder_count,
        "duplicate_resource_id_count":     dup_resource_id_count,
        "duplicate_prompt_count":          dup_prompt_count,
        "target_coverage": {
            "target_count":                     len(target_map),
            "targets_with_generated_resources": len(generated_tids & set(target_map)),
            "targets_missing_generated_resources": len(missing_tids),
        },
        "resource_types":   resource_types,
        "component_types":  component_types,
        "warnings":         batch_warnings,
        "output_files":     out_files,
    }


def build_manifest_md(report: dict) -> str:
    cov = report["target_coverage"]
    lines = [
        "# Quanta Aptus Generated Resource Validation v1",
        "",
        f"- **Batch ID:** `{report['batch_id']}`",
        f"- **Authoring batch:** `{report['authoring_batch_file']}`",
        f"- **Generated batch:** `{report['generated_batch_file']}`",
        f"- **Validation status:** {report['status']}",
        "",
        "## Counts",
        "",
        f"- **Generated resources:** {report['generated_count']}",
        f"- **Passed:** {report['passed_count']}",
        f"- **Needs review:** {report['needs_review_count']}",
        f"- **Failed:** {report['failed_count']}",
        "",
        "## Quality Issues",
        "",
        f"- **Copyright leakage detections:** {report['copyright_leak_count']}",
        f"- **Dummy/placeholder detections:** {report['dummy_placeholder_count']}",
        f"- **Duplicate resource IDs:** {report['duplicate_resource_id_count']}",
        f"- **Duplicate student prompts:** {report['duplicate_prompt_count']}",
        f"- **Unknown target IDs:** {report['unknown_target_count']}",
        "",
        "## Target Coverage",
        "",
        f"- **Total targets in authoring batch:** {cov['target_count']}",
        f"- **Targets with generated resources:** {cov['targets_with_generated_resources']}",
        f"- **Targets missing generated resources:** {cov['targets_missing_generated_resources']}",
        "",
        "## Resource Types",
        "",
    ]
    for rt, count in sorted(report["resource_types"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{rt}:** {count}")

    lines += ["", "## Component Types", ""]
    for ct, count in sorted(report["component_types"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{ct}:** {count}")

    if report["warnings"]:
        lines += ["", "## Warnings", ""]
        for w in report["warnings"]:
            lines.append(f"- {w}")

    lines += ["", "## Output Paths", ""]
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")

    lines += [
        "",
        "---",
        "",
        "> Only resources that pass validation should move into the original resource bank.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Validate a Quanta Aptus generated resource batch."
    )
    ap.add_argument("authoring_batch",  help="Path to authoring_batch_v1_NNN.json")
    ap.add_argument("generated_batch",  help="Path to generated_resource_batch_v1_NNN.json")
    args = ap.parse_args()

    auth_path = Path(args.authoring_batch)
    gen_path  = Path(args.generated_batch)

    for p in (auth_path, gen_path):
        if not p.exists():
            sys.exit(f"Error: file not found: {p}")

    auth_doc, err = load_json(auth_path)
    if err:
        sys.exit(f"Error reading authoring batch: {err}")

    gen_doc, err = load_json(gen_path)
    if err:
        sys.exit(f"Error reading generated batch: {err}")

    # ── Structural checks on generated batch ──────────────────────────────
    if not isinstance(gen_doc, dict):
        sys.exit("Error: generated batch must be a JSON object.")

    if gen_doc.get("schema_version") != "generated_resource_batch_v1":
        print(
            f"WARNING: schema_version is '{gen_doc.get('schema_version')}', "
            "expected 'generated_resource_batch_v1'"
        )

    raw_resources = gen_doc.get("generated_resources")
    if not isinstance(raw_resources, list) or len(raw_resources) == 0:
        sys.exit("Error: generated_resources must be a non-empty list.")

    # ── Build target lookup from authoring batch ──────────────────────────
    target_map: dict[str, dict] = {
        t["target_id"]: t
        for t in (auth_doc.get("targets") or [])
        if "target_id" in t
    }

    # ── Validate each resource ────────────────────────────────────────────
    seen_resource_ids: dict[str, int] = {}
    seen_prompts: dict[str, str] = {}
    validated_resources: list[dict] = []

    copyright_leak_count    = 0
    dummy_placeholder_count = 0
    dup_resource_id_count   = 0
    dup_prompt_count        = 0
    unknown_target_count    = 0

    for idx, res in enumerate(raw_resources):
        if not isinstance(res, dict):
            validated_resources.append({
                "_index":            idx,
                "validation_status": "failed",
                "validation_errors": [f"Item at index {idx} is not a JSON object"],
                "validation_warnings": [],
            })
            continue

        res["_index"] = idx
        result = validate_resource(res, target_map, seen_resource_ids, seen_prompts)

        # Track specific issue types for report counters
        for err in result.errors:
            if "COPYRIGHT LEAK" in err:
                copyright_leak_count += 1
            elif "PLACEHOLDER" in err:
                dummy_placeholder_count += 1
            elif "Duplicate resource_id" in err:
                dup_resource_id_count += 1
            elif "Unknown target_id" in err:
                unknown_target_count += 1

        for w in result.warnings:
            if "Duplicate student_prompt" in w:
                dup_prompt_count += 1

        # Build validated resource (merge original + validation fields)
        vres: dict = {k: v for k, v in res.items() if k != "_index"}
        vres["validation_status"]   = result.status
        vres["validation_errors"]   = result.errors
        vres["validation_warnings"] = result.warnings
        validated_resources.append(vres)

    # ── Planned-count warnings ────────────────────────────────────────────
    batch_warnings = check_planned_counts(raw_resources, target_map)

    # ── Output paths ──────────────────────────────────────────────────────
    out_dir    = gen_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem       = gen_path.stem            # e.g. "generated_resource_batch_v1_001"

    val_path  = out_dir / f"{stem}.validated.json"
    rep_path  = out_dir / f"{stem}.validation_report.json"
    man_path  = out_dir / f"{stem}.validation_manifest.md"

    out_files = {
        "validated": str(val_path),
        "report":    str(rep_path),
        "manifest":  str(man_path),
    }

    validated = build_validated_json(gen_doc, str(auth_path), validated_resources)
    report    = build_report(
        validated, str(auth_path), str(gen_path),
        target_map,
        copyright_leak_count, dummy_placeholder_count,
        dup_resource_id_count, dup_prompt_count,
        unknown_target_count, batch_warnings, out_files,
    )
    manifest  = build_manifest_md(report)

    val_path.write_text(
        json.dumps(validated, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    rep_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    man_path.write_text(manifest, encoding="utf-8")

    cov = report["target_coverage"]
    print(f"status                          : {report['status']}")
    print(f"batch_id                        : {report['batch_id']}")
    print(f"generated_count                 : {report['generated_count']}")
    print(f"passed_count                    : {report['passed_count']}")
    print(f"needs_review_count              : {report['needs_review_count']}")
    print(f"failed_count                    : {report['failed_count']}")
    print(f"copyright_leak_count            : {report['copyright_leak_count']}")
    print(f"dummy_placeholder_count         : {report['dummy_placeholder_count']}")
    print(f"duplicate_resource_id_count     : {report['duplicate_resource_id_count']}")
    print(f"duplicate_prompt_count          : {report['duplicate_prompt_count']}")
    print(f"targets_with_generated_resources: {cov['targets_with_generated_resources']}")
    print(f"targets_missing_generated_resources: {cov['targets_missing_generated_resources']}")
    print(f"validated                       : {val_path}")
    print(f"report                          : {rep_path}")
    print(f"manifest                        : {man_path}")


if __name__ == "__main__":
    main()
