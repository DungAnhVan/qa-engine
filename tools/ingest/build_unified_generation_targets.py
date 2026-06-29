"""
Build the Quanta Aptus Unified Generation Targets from the Unified Skill Map.

Reads unified_skill_map_v0.json and produces a structured authoring plan that
specifies which original resources to generate per skill unit.  No Cambridge
source content is included — this is a generation plan only.

Usage:
    python tools/ingest/build_unified_generation_targets.py \\
        data/bank/cambridge_igcse/physics_0625/skill_map/unified_skill_map_v0.json

Output (data/bank/cambridge_igcse/physics_0625/generation_targets/):
    unified_generation_targets_v0.json
    unified_generation_targets_report.json
    unified_generation_targets_manifest.md
"""

import sys
import re
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Resource type mapping
# ---------------------------------------------------------------------------

def get_resource_types(comp: str, skill_type: str) -> list[str]:
    if comp == "mcq":
        types = ["original_mcq", "worked_explanation"]
        if skill_type in ("calculation", "equation_manipulation"):
            types.append("calculation_drill")
        return types

    if comp == "theory_structured":
        mapping: dict[str, list[str]] = {
            "recall_definition":      ["short_answer_recall", "definition_flashcard"],
            "conceptual_explanation": ["short_answer_explanation", "misconception_drill"],
            "calculation":            ["worked_example", "calculation_drill", "short_answer_calculation"],
            "equation_manipulation":  ["worked_example", "calculation_drill", "short_answer_calculation"],
            "diagram_drawing":        ["diagram_or_graph_drill", "marking_checklist"],
            "graphing":               ["diagram_or_graph_drill", "marking_checklist"],
            "data_interpretation":    ["data_interpretation_drill", "worked_example"],
        }
        return mapping.get(skill_type, ["review_before_generation"])

    if comp == "practical_structured":
        mapping = {
            "measurement":           ["measurement_drill", "practical_accuracy_checklist"],
            "graphing":              ["graphing_drill", "graph_marking_checklist"],
            "table_design":          ["table_design_drill"],
            "variable_control":      ["fair_test_variable_drill"],
            "experimental_design":   ["experiment_planning_task", "planning_marking_checklist"],
            "extended_planning":     ["experiment_planning_task", "planning_marking_checklist"],
            "evaluation_accuracy":   ["evaluation_improvement_drill"],
            "practical_calculation": ["practical_calculation_drill", "worked_example"],
        }
        return mapping.get(skill_type, ["review_before_generation"])

    return ["review_before_generation"]


# ---------------------------------------------------------------------------
# Planned item count per resource_type
# ---------------------------------------------------------------------------

PLANNED_ITEMS: dict[str, int] = {
    "original_mcq":                  3,
    "worked_explanation":            2,
    "calculation_drill":             5,
    "short_answer_explanation":      3,
    "short_answer_recall":           3,
    "definition_flashcard":          3,
    "misconception_drill":           3,
    "worked_example":                2,
    "short_answer_calculation":      3,
    "diagram_or_graph_drill":        3,
    "marking_checklist":             1,
    "data_interpretation_drill":     3,
    "graphing_drill":                3,
    "graph_marking_checklist":       1,
    "table_design_drill":            3,
    "measurement_drill":             3,
    "practical_accuracy_checklist":  1,
    "experiment_planning_task":      2,
    "planning_marking_checklist":    1,
    "evaluation_improvement_drill":  3,
    "practical_calculation_drill":   3,
    "fair_test_variable_drill":      3,
    "review_before_generation":      0,
}

# ---------------------------------------------------------------------------
# Priority per skill_type
# ---------------------------------------------------------------------------

PRIORITY_MAP: dict[str, int] = {
    "calculation":           1,
    "equation_manipulation": 1,
    "graphing":              1,
    "experimental_design":   1,
    "extended_planning":     1,
    "measurement":           1,
    "conceptual_explanation":2,
    "data_interpretation":   2,
    "table_design":          2,
    "evaluation_accuracy":   2,
    "variable_control":      2,
    "recall_definition":     3,
    "multiple_choice_concept":3,
}


def get_priority(skill_type: str, resource_type: str) -> int:
    if resource_type == "review_before_generation" or skill_type == "unknown":
        return 9
    return PRIORITY_MAP.get(skill_type, 3)


# ---------------------------------------------------------------------------
# Generation goals per resource_type
# ---------------------------------------------------------------------------

GENERATION_GOALS: dict[str, str] = {
    "original_mcq":
        "Create an original MCQ question testing this skill with 4 options (A-D) and a correct answer key.",
    "worked_explanation":
        "Create a step-by-step worked explanation of the reasoning needed to answer an MCQ on this skill.",
    "calculation_drill":
        "Create a set of original calculation practice problems with full step-by-step solutions.",
    "short_answer_recall":
        "Create short-answer recall questions testing key definitions, units, or facts for this skill.",
    "definition_flashcard":
        "Create a definition flashcard: front = term or concept; back = definition plus a brief original example.",
    "short_answer_explanation":
        "Create short-answer explanation questions requiring students to explain a concept or phenomenon.",
    "misconception_drill":
        "Create questions that identify and correct common student misconceptions about this topic and skill.",
    "worked_example":
        "Create a fully worked example with annotated solution steps for this skill.",
    "short_answer_calculation":
        "Create short-answer calculation questions including expected working and a final answer.",
    "diagram_or_graph_drill":
        "Create a diagram or graph drawing exercise with original data and a marking guide.",
    "marking_checklist":
        "Create a marking checklist covering key features for diagram or graph drawing tasks.",
    "data_interpretation_drill":
        "Create a data interpretation exercise using original (non-Cambridge) data sets.",
    "graphing_drill":
        "Create a graphing exercise: plot points from original data, draw a best-fit line, and extract values.",
    "graph_marking_checklist":
        "Create a marking checklist for graphing tasks covering axes, scale, plots, and best-fit line.",
    "table_design_drill":
        "Create a table design exercise: choose appropriate column headers, quantities, and units.",
    "measurement_drill":
        "Create a practical measurement exercise requiring students to read instruments and record values precisely.",
    "practical_accuracy_checklist":
        "Create a checklist of accuracy and precision requirements for this practical skill.",
    "experiment_planning_task":
        "Create an original experiment planning task covering setup, method, variables, results table, and graph.",
    "planning_marking_checklist":
        "Create a marking checklist for experiment planning tasks aligned to mark-point criteria (MP1-MP7 style).",
    "evaluation_improvement_drill":
        "Create evaluation questions: identify sources of error, suggest improvements, and assess reliability.",
    "practical_calculation_drill":
        "Create practical calculation exercises using typical original measurement data.",
    "fair_test_variable_drill":
        "Create variable identification exercises: state independent, dependent, and controlled variables.",
    "review_before_generation":
        "Skill type is unknown or unclear. Review this skill unit before creating any generation targets.",
}

# ---------------------------------------------------------------------------
# Audience flags per resource_type
# ---------------------------------------------------------------------------

TEACHER_ONLY_TYPES: frozenset[str] = frozenset({
    "marking_checklist",
    "graph_marking_checklist",
    "planning_marking_checklist",
    "practical_accuracy_checklist",
    "review_before_generation",
})


def get_facing(resource_type: str) -> tuple[bool, bool]:
    """Returns (student_facing, teacher_facing)."""
    if resource_type in TEACHER_ONLY_TYPES:
        return False, True
    return True, False


# ---------------------------------------------------------------------------
# Paper code extraction
# ---------------------------------------------------------------------------

def extract_paper_code(source_id: str) -> str:
    m = re.search(r'_p(\d+)$', source_id)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Deduplication key
# ---------------------------------------------------------------------------

def dedup_key(unit: dict, resource_type: str) -> str:
    return (
        f"{unit.get('topic', '')}|"
        f"{unit.get('skill_type', '')}|"
        f"{(unit.get('skill') or '')}|"
        f"{resource_type}"
    )


# ---------------------------------------------------------------------------
# Core target builder
# ---------------------------------------------------------------------------

def build_targets(skill_units: list[dict]) -> list[dict]:
    """
    Build one raw target per (skill_unit × resource_type), then deduplicate
    on (topic, skill_type, skill_name, resource_type).  Returns the final
    deduplicated list preserving insertion order.
    """
    # ordered dict: dedup_key → target
    seen_targets: dict[str, dict] = {}

    for unit in skill_units:
        comp       = unit["component_type"]
        skill_type = unit["skill_type"]
        unit_id    = unit["skill_unit_id"]
        source_id  = unit.get("source_id", "")
        paper_code = extract_paper_code(source_id)

        for rtype in get_resource_types(comp, skill_type):
            key = dedup_key(unit, rtype)

            if key not in seen_targets:
                student_f, teacher_f = get_facing(rtype)
                status = (
                    "needs_review"
                    if rtype == "review_before_generation"
                    else "ready_for_authoring"
                )
                seen_targets[key] = {
                    "target_id":              f"{unit_id}_{rtype}",
                    "source_skill_unit_id":   unit_id,
                    "source_skill_unit_ids":  [unit_id],
                    "component_type":         comp,
                    "paper_code":             paper_code,
                    "topic":                  unit.get("topic", ""),
                    "skill_name":             unit.get("skill", "") or "",
                    "skill_type":             skill_type,
                    "assessment_mode":        unit.get("assessment_mode", ""),
                    "resource_type":          rtype,
                    "generation_goal":        GENERATION_GOALS.get(rtype, ""),
                    "student_facing":         student_f,
                    "teacher_facing":         teacher_f,
                    "priority":               get_priority(skill_type, rtype),
                    "planned_item_count":     PLANNED_ITEMS.get(rtype, 0),
                    "copyright_rule":         "create_original_content_only_do_not_copy_source_wording",
                    "status":                 status,
                }
            else:
                # Merge: append source unit to existing target
                existing = seen_targets[key]
                if unit_id not in existing["source_skill_unit_ids"]:
                    existing["source_skill_unit_ids"].append(unit_id)
                    # Keep source_skill_unit_id as the first one (primary)
                    # and promote paper_code to a list if it differs
                    if existing["paper_code"] != paper_code:
                        existing["paper_code"] = ""  # mixed — clear singular field

    return list(seen_targets.values())


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

def build_summary(targets: list[dict]) -> dict:
    component_types: dict[str, int] = {}
    topics:          dict[str, int] = {}
    skill_types:     dict[str, int] = {}
    resource_types:  dict[str, int] = {}
    priorities:      dict[str, int] = {}
    planned_total = 0

    for t in targets:
        def inc(d: dict, k: str) -> None:
            d[k] = d.get(k, 0) + 1

        inc(component_types, t["component_type"])
        inc(topics,          t["topic"])
        inc(skill_types,     t["skill_type"])
        inc(resource_types,  t["resource_type"])
        inc(priorities,      str(t["priority"]))
        planned_total += t["planned_item_count"]

    return {
        "component_types":   component_types,
        "topics":            topics,
        "skill_types":       skill_types,
        "resource_types":    resource_types,
        "priorities":        priorities,
        "planned_total_items": planned_total,
    }


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------

def build_warnings(skill_map: dict, sm_path: Path) -> list[str]:
    warnings: list[str] = []

    sm_total = skill_map.get("summary", {}).get("total_marks_indexed", None)

    # Try loading the sibling source corpus to compare marks
    corpus_path = sm_path.parent.parent / "source_corpus" / "unified_source_corpus_v0.json"
    if corpus_path.exists():
        try:
            corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
            corpus_total = corpus.get("summary", {}).get("total_marks", None)
            if sm_total is not None and corpus_total is not None and sm_total != corpus_total:
                warnings.append(
                    f"total_marks_indexed ({sm_total}) differs from source corpus "
                    f"total_marks ({corpus_total}); review mark aggregation later."
                )
        except Exception:
            pass

    return warnings


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(
    target_doc: dict,
    n_skill_units: int,
    out_files: dict,
) -> dict:
    targets   = target_doc["targets"]
    total     = len(targets)
    ready     = sum(1 for t in targets if t["status"] == "ready_for_authoring")
    rbg       = sum(1 for t in targets if t["status"] == "needs_review")
    planned   = target_doc["summary"]["planned_total_items"]
    warnings  = target_doc.get("warnings", [])

    if total == 0:
        status = "failed"
    elif rbg >= total * 0.20:
        status = "needs_review"
    else:
        status = "passed"

    return {
        "status":                       status,
        "target_set_id":                target_doc["target_set_id"],
        "source_skill_units":           n_skill_units,
        "target_count":                 total,
        "ready_for_authoring_count":    ready,
        "review_before_generation_count": rbg,
        "planned_total_items":          planned,
        "component_types":              target_doc["summary"]["component_types"],
        "resource_types":               target_doc["summary"]["resource_types"],
        "priorities":                   target_doc["summary"]["priorities"],
        "warnings":                     warnings,
        "output_files":                 out_files,
    }


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------

def build_manifest_md(target_doc: dict, report: dict) -> str:
    sm  = target_doc["summary"]
    lines = [
        "# Quanta Aptus Unified Generation Targets v0",
        "",
        f"- **Board:** {target_doc['board'].title()}",
        f"- **Level:** {target_doc['level'].upper()}",
        f"- **Subject:** {target_doc['subject'].title()}",
        f"- **Syllabus:** {target_doc['syllabus_code']}",
        f"- **Target Set ID:** `{target_doc['target_set_id']}`",
        f"- **Source Skill Map:** `{target_doc['source_skill_map_id']}`",
        f"- **Status:** {report['status']}",
        f"- **Created:** {target_doc['created_at']}",
        "",
        f"- **Source skill units:** {report['source_skill_units']}",
        f"- **Target count:** {report['target_count']}",
        f"- **Ready for authoring:** {report['ready_for_authoring_count']}",
        f"- **Review before generation:** {report['review_before_generation_count']}",
        f"- **Planned total items:** {sm['planned_total_items']}",
        "",
        "## Component Types",
        "",
    ]
    for ct, count in sm["component_types"].items():
        lines.append(f"- **{ct}:** {count} targets")

    lines += ["", "## Resource Types", ""]
    for rt, count in sorted(sm["resource_types"].items(), key=lambda x: -x[1]):
        pic = PLANNED_ITEMS.get(rt, 0)
        lines.append(f"- **{rt}:** {count} targets ({count * pic} planned items)")

    lines += ["", "## Priority Distribution", ""]
    for p, count in sorted(sm["priorities"].items()):
        label = {
            "1": "Priority 1 (core skills)",
            "2": "Priority 2 (applied skills)",
            "3": "Priority 3 (knowledge recall)",
            "9": "Priority 9 (review required)",
        }.get(p, f"Priority {p}")
        lines.append(f"- **{label}:** {count} targets")

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
        "> Targets are generation instructions only.",
        "> All generated content must be original Quanta Aptus content and must not",
        "> copy Cambridge source wording, numbers, diagrams, or contexts.",
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
        return None, f"Not found: {path}"
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build Quanta Aptus Unified Generation Targets."
    )
    ap.add_argument("skill_map_json", help="Path to unified_skill_map_v0.json")
    args = ap.parse_args()

    sm_path = Path(args.skill_map_json)
    if not sm_path.exists():
        sys.exit(f"Error: file not found: {sm_path}")

    skill_map, err = load_json(sm_path)
    if err:
        sys.exit(f"Error reading skill map: {err}")

    out_dir = sm_path.parent.parent / "generation_targets"
    out_dir.mkdir(parents=True, exist_ok=True)

    skill_units    = skill_map.get("skill_units", [])
    n_skill_units  = len(skill_units)
    targets        = build_targets(skill_units)
    summary        = build_summary(targets)
    warnings       = build_warnings(skill_map, sm_path)

    board    = skill_map.get("board",         "cambridge")
    level    = skill_map.get("level",         "igcse")
    subject  = skill_map.get("subject",       "physics")
    syllabus = skill_map.get("syllabus_code", "0625")

    target_set_id = (
        f"{board}_{level}_{subject}_{syllabus}_unified_generation_targets_v0"
    )

    target_doc = {
        "target_set_id":       target_set_id,
        "version":             "0.1.0",
        "status":              "internal_authoring_plan",
        "created_at":          datetime.now(timezone.utc).isoformat(),
        "source_skill_map_id": skill_map.get("skill_map_id", ""),
        "copyright_status":    "generation_plan_only_no_source_content",
        "board":               board,
        "level":               level,
        "subject":             subject,
        "syllabus_code":       syllabus,
        "target_count":        len(targets),
        "targets":             targets,
        "summary":             summary,
        "warnings":            warnings,
    }

    tgt_path = out_dir / "unified_generation_targets_v0.json"
    rep_path = out_dir / "unified_generation_targets_report.json"
    man_path = out_dir / "unified_generation_targets_manifest.md"

    out_files = {
        "targets":  str(tgt_path),
        "report":   str(rep_path),
        "manifest": str(man_path),
    }

    report   = build_report(target_doc, n_skill_units, out_files)
    manifest = build_manifest_md(target_doc, report)

    tgt_path.write_text(json.dumps(target_doc, indent=2, ensure_ascii=False), encoding="utf-8")
    rep_path.write_text(json.dumps(report,     indent=2, ensure_ascii=False), encoding="utf-8")
    man_path.write_text(manifest, encoding="utf-8")

    # Terminal output
    print(f"status                        : {report['status']}")
    print(f"target_set_id                 : {target_set_id}")
    print(f"source_skill_units            : {n_skill_units}")
    print(f"target_count                  : {report['target_count']}")
    print(f"ready_for_authoring_count     : {report['ready_for_authoring_count']}")
    print(f"review_before_generation_count: {report['review_before_generation_count']}")
    print(f"planned_total_items           : {report['planned_total_items']}")
    print(f"resource_types                : {summary['resource_types']}")
    print(f"priorities                    : {summary['priorities']}")
    if warnings:
        for w in warnings:
            print(f"WARNING: {w}")
    else:
        print("warnings                      : none")
    print(f"targets                       : {tgt_path}")
    print(f"report                        : {rep_path}")
    print(f"manifest                      : {man_path}")


if __name__ == "__main__":
    main()
