"""
Build a Quanta Aptus Authoring Batch and Prompt from Generation Targets.

Reads unified_generation_targets_v0.json, selects a priority-ordered batch
of ready targets up to a planned-item cap, and writes:
  - authoring_batch_v1_{batch_id}.json     (machine-readable batch spec)
  - authoring_prompt_v1_{batch_id}.md      (AI authoring prompt — no content generated here)
  - authoring_batch_v1_{batch_id}_report.json

Usage:
    python tools/ingest/build_authoring_batch_v1.py \\
        data/bank/cambridge_igcse/physics_0625/generation_targets/unified_generation_targets_v0.json \\
        [--batch-id 001] [--max-planned-items 50] \\
        [--priority 1,2] [--include-components mcq,theory_structured,practical_structured]
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Fields to carry from each generation-target into the batch
BATCH_TARGET_FIELDS = [
    "target_id",
    "source_skill_unit_ids",
    "component_type",
    "paper_code",
    "topic",
    "skill_name",
    "skill_type",
    "assessment_mode",
    "resource_type",
    "generation_goal",
    "planned_item_count",
    "priority",
    "student_facing",
    "teacher_facing",
    "copyright_rule",
]


# ---------------------------------------------------------------------------
# Target selection
# ---------------------------------------------------------------------------

def select_targets(
    all_targets: list[dict],
    max_planned: int,
    priorities: set[int],
    components: set[str],
) -> list[dict]:
    """
    Filter → sort by priority → greedily accumulate until max_planned reached.
    Targets with planned_item_count = 0 are always excluded (review_before_generation).
    """
    eligible = [
        t for t in all_targets
        if t.get("status") == "ready_for_authoring"
        and t.get("priority", 9) in priorities
        and t.get("component_type") in components
        and (t.get("planned_item_count") or 0) > 0
    ]
    eligible.sort(key=lambda t: (t.get("priority", 9), t.get("target_id", "")))

    selected: list[dict] = []
    running = 0
    for t in eligible:
        pic = t.get("planned_item_count", 0)
        if running + pic <= max_planned:
            selected.append(t)
            running += pic
        # Don't break — smaller targets later might still fit

    return selected


def trim_target(t: dict) -> dict:
    """Return only the fields required in the authoring batch."""
    out: dict = {}
    for field in BATCH_TARGET_FIELDS:
        if field in t:
            out[field] = t[field]
    return out


# ---------------------------------------------------------------------------
# Authoring batch JSON
# ---------------------------------------------------------------------------

def build_batch(
    targets: list[dict],
    batch_id_full: str,
    source_target_set_id: str,
    board: str,
    level: str,
    subject: str,
    syllabus: str,
) -> dict:
    trimmed = [trim_target(t) for t in targets]
    planned = sum(t.get("planned_item_count", 0) for t in trimmed)

    return {
        "batch_id":               batch_id_full,
        "version":                "0.1.0",
        "status":                 "ready_for_ai_authoring",
        "created_at":             datetime.now(timezone.utc).isoformat(),
        "source_target_set_id":   source_target_set_id,
        "board":                  board,
        "level":                  level,
        "subject":                subject,
        "syllabus_code":          syllabus,
        "copyright_policy": {
            "source_use":   "internal_reference_only",
            "public_output":"original_quanta_aptus_content_only",
            "rules": [
                "Do not copy Cambridge wording.",
                "Do not copy Cambridge numbers.",
                "Do not copy Cambridge diagrams.",
                "Do not copy Cambridge contexts.",
                "Do not reproduce mark scheme wording.",
                "Generate new original learning resources based only on the derived skill metadata.",
            ],
        },
        "generation_schema_version": "resource_batch_v1",
        "target_count":           len(trimmed),
        "planned_item_count":     planned,
        "targets":                trimmed,
    }


# ---------------------------------------------------------------------------
# Authoring prompt markdown
# ---------------------------------------------------------------------------

def build_prompt_md(batch: dict) -> str:
    batch_label = batch["batch_id"].split("_")[-1]   # e.g. "001"
    lines: list[str] = [
        f"# Quanta Aptus Authoring Batch v1 {batch_label}",
        "",
        "## Role",
        "",
        "You are creating original Quanta Aptus learning resources for "
        f"Cambridge IGCSE {batch['subject'].title()} {batch['syllabus_code']}.",
        "",
        "## Non-Negotiable Copyright Rules",
        "",
        "- Use the source metadata only as skill guidance.",
        "- Do not copy Cambridge question wording.",
        "- Do not copy Cambridge numbers.",
        "- Do not copy Cambridge diagrams.",
        "- Do not copy Cambridge experimental contexts.",
        "- Do not copy Cambridge mark scheme wording.",
        "- Create original student-facing and teacher-facing resources.",
        "",
        "## Output Format",
        "",
        "Return **valid JSON only**.",
        "No markdown. No commentary outside JSON.",
        "",
        "## Required JSON Output Schema",
        "",
        "```json",
        json.dumps(
            {
                "batch_id": batch["batch_id"],
                "schema_version": "generated_resource_batch_v1",
                "generated_resources": [
                    {
                        "resource_id": "<batch_id>_<target_id>_<item_index e.g. 01>",
                        "target_id": "<target_id from batch>",
                        "resource_type": "<resource_type>",
                        "component_type": "<component_type>",
                        "topic": "<topic>",
                        "skill_name": "<skill_name>",
                        "skill_type": "<skill_type>",
                        "difficulty": "easy | medium | hard",
                        "student_prompt": "<the question or task text>",
                        "options": {
                            "A": "<option text or null>",
                            "B": "<option text or null>",
                            "C": "<option text or null>",
                            "D": "<option text or null>",
                        },
                        "correct_answer": "A | B | C | D | null",
                        "worked_solution": "<step-by-step solution or explanation>",
                        "marking_guidance": "<how to mark or checklist items>",
                        "common_misconception": "<common student error and correction>",
                        "teacher_note": "<pedagogical note for teacher>",
                        "estimated_time_minutes": 1,
                        "originality_statement": (
                            "Original Quanta Aptus content generated "
                            "from derived skill metadata only."
                        ),
                    }
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        "```",
        "",
        "## Schema Rules by Resource Type",
        "",
        "### original_mcq",
        "- `student_prompt`: required.",
        "- `options`: exactly 4 options A–D, all required.",
        "- `correct_answer`: exactly one of A, B, C, D.",
        "- `worked_solution`: required — explain why the correct answer is right.",
        "- `common_misconception`: required.",
        "- Do not require diagrams unless the target skill_type is graphing or diagram_drawing.",
        "",
        "### worked_explanation",
        "- `options`: null for all four options.",
        "- `correct_answer`: null.",
        "- `student_prompt`: brief framing of the concept.",
        "- `worked_solution`: step-by-step conceptual explanation.",
        "- `common_misconception`: required.",
        "",
        "### worked_example",
        "- Create a new original numerical scenario.",
        "- `worked_solution`: full annotated step-by-step working.",
        "- Do not reuse Cambridge numbers or experimental contexts.",
        "",
        "### calculation_drill / short_answer_calculation",
        "- `student_prompt`: a concise original calculation task.",
        "- `worked_solution`: include each calculation step and final answer with units.",
        "- Use IGCSE-appropriate numbers.",
        "",
        "### graphing_drill",
        "- `student_prompt`: include an original data table and graphing instructions.",
        "- `marking_guidance`: axis labels, scale, point plotting, best-fit line.",
        "- Do not require image generation; describe data and axes textually.",
        "",
        "### graph_marking_checklist / marking_checklist / planning_marking_checklist",
        "- `student_prompt`: null (teacher-facing resource).",
        "- `correct_answer`: null.",
        "- `options`: null.",
        "- `marking_guidance`: list all mark-point criteria.",
        "",
        "### experiment_planning_task",
        "- `student_prompt`: original practical planning task (not Cambridge context).",
        "- `worked_solution`: cover setup, method, variables, table structure, graph.",
        "- `marking_guidance`: MP-style checklist.",
        "",
        "### definition_flashcard / short_answer_recall",
        "- `student_prompt`: one clear, concise question.",
        "- `worked_solution`: model answer with units if applicable.",
        "",
        "### data_interpretation_drill",
        "- `student_prompt`: present a small original data set or trend.",
        "- `worked_solution`: step-by-step interpretation.",
        "",
        "## Difficulty Distribution",
        "",
        "For each target with `planned_item_count >= 3`:",
        "- At least 1 `easy`.",
        "- At least 1 `medium`.",
        "- At least 1 `hard` where appropriate for the skill type.",
        "",
        "## Quality Requirements",
        "",
        "- Language must be appropriate for Cambridge IGCSE students (age 14–16).",
        "- Clear, direct, exam-style phrasing, but entirely original.",
        "- Avoid ambiguous answer choices.",
        "- Include correct SI units where needed.",
        "- Avoid unsafe practical instructions.",
        "- Do not mention Cambridge source papers or exam series in generated resources.",
        "",
        "## Targets to Author",
        "",
        "```json",
        json.dumps(batch["targets"], indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(
    batch: dict,
    source_target_set_id: str,
    excluded_rbg: int,
    out_files: dict,
) -> dict:
    targets = batch["targets"]
    total   = len(targets)
    planned = batch["planned_item_count"]

    priority_dist: dict[str, int] = {}
    resource_types: dict[str, int] = {}
    component_types: dict[str, int] = {}

    for t in targets:
        p  = str(t.get("priority", "?"))
        rt = t.get("resource_type", "unknown")
        ct = t.get("component_type", "unknown")
        priority_dist[p]   = priority_dist.get(p, 0) + 1
        resource_types[rt] = resource_types.get(rt, 0) + 1
        component_types[ct]= component_types.get(ct, 0) + 1

    status = "passed" if total > 0 and planned > 0 else "failed"

    return {
        "status":                               status,
        "batch_id":                             batch["batch_id"],
        "source_target_set_id":                 source_target_set_id,
        "selected_target_count":                total,
        "planned_item_count":                   planned,
        "priority_distribution":                priority_dist,
        "resource_types":                       resource_types,
        "component_types":                      component_types,
        "excluded_review_before_generation_count": excluded_rbg,
        "output_files":                         out_files,
    }


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
        description="Build a Quanta Aptus Authoring Batch and Prompt."
    )
    ap.add_argument("targets_json", help="Path to unified_generation_targets_v0.json")
    ap.add_argument("--batch-id",         default="001", dest="batch_id",
                    help="Batch suffix (default: 001)")
    ap.add_argument("--max-planned-items", default=50, type=int, dest="max_planned",
                    help="Max total planned items (default: 50)")
    ap.add_argument("--priority",          default="1,2,3", dest="priority",
                    help="Comma-separated priority levels to include (default: 1,2,3)")
    ap.add_argument("--include-components", default="mcq,theory_structured,practical_structured",
                    dest="components",
                    help="Comma-separated component types to include")
    args = ap.parse_args()

    tgt_path = Path(args.targets_json)
    if not tgt_path.exists():
        sys.exit(f"Error: file not found: {tgt_path}")

    tgt_doc, err = load_json(tgt_path)
    if err:
        sys.exit(f"Error reading targets: {err}")

    # Parse filter arguments
    try:
        priorities = {int(p.strip()) for p in args.priority.split(",") if p.strip()}
    except ValueError:
        sys.exit("Error: --priority must be comma-separated integers, e.g. 1,2")
    components = {c.strip() for c in args.components.split(",") if c.strip()}

    all_targets: list[dict] = tgt_doc.get("targets", [])
    excluded_rbg = sum(
        1 for t in all_targets
        if t.get("resource_type") == "review_before_generation"
        or t.get("priority", 0) == 9
    )

    selected = select_targets(all_targets, args.max_planned, priorities, components)
    if not selected:
        sys.exit("Error: no targets matched the selection criteria.")

    board    = tgt_doc.get("board",         "cambridge")
    level    = tgt_doc.get("level",         "igcse")
    subject  = tgt_doc.get("subject",       "physics")
    syllabus = tgt_doc.get("syllabus_code", "0625")
    source_target_set_id = tgt_doc.get("target_set_id", "")

    batch_id_full = (
        f"{board}_{level}_{subject}_{syllabus}_authoring_batch_v1_{args.batch_id}"
    )

    out_dir = tgt_path.parent.parent / "authoring_batches"
    out_dir.mkdir(parents=True, exist_ok=True)

    batch_fname  = f"authoring_batch_v1_{args.batch_id}.json"
    prompt_fname = f"authoring_prompt_v1_{args.batch_id}.md"
    report_fname = f"authoring_batch_v1_{args.batch_id}_report.json"

    batch_path  = out_dir / batch_fname
    prompt_path = out_dir / prompt_fname
    report_path = out_dir / report_fname

    out_files = {
        "authoring_batch":   str(batch_path),
        "authoring_prompt":  str(prompt_path),
        "report":            str(report_path),
    }

    batch   = build_batch(selected, batch_id_full, source_target_set_id,
                          board, level, subject, syllabus)
    prompt  = build_prompt_md(batch)
    report  = build_report(batch, source_target_set_id, excluded_rbg, out_files)

    batch_path.write_text(
        json.dumps(batch, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    prompt_path.write_text(prompt, encoding="utf-8")
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Terminal output
    print(f"status                  : {report['status']}")
    print(f"batch_id                : {batch_id_full}")
    print(f"selected_target_count   : {report['selected_target_count']}")
    print(f"planned_item_count      : {report['planned_item_count']}")
    print(f"resource_types          : {report['resource_types']}")
    print(f"component_types         : {report['component_types']}")
    print(f"priority_distribution   : {report['priority_distribution']}")
    print(f"authoring_batch         : {batch_path}")
    print(f"authoring_prompt        : {prompt_path}")
    print(f"report                  : {report_path}")


if __name__ == "__main__":
    main()
