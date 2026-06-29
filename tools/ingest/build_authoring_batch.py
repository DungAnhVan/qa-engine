"""
Build authoring batch spec and prompt from priority-1 generation targets.

Usage:
    python tools/ingest/build_authoring_batch.py <generation_targets_v0.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_authoring_batch.py \
        data/bank/cambridge_igcse/physics_0625/generation_targets_v0.json
"""

import sys
import json
from pathlib import Path

BATCH_NUMBER   = "001"
BATCH_ID       = f"cambridge_igcse_physics_0625_authoring_batch_{BATCH_NUMBER}"
COPYRIGHT_POLICY = (
    "Do not copy wording, numbers, contexts, diagrams, option order, or answer patterns "
    "from source materials. Generate original questions only."
)

GLOBAL_CONSTRAINTS = [
    "Do not copy Cambridge wording, phrasing, or sentence structure.",
    "Do not reuse source numbers, values, quantities, or contexts.",
    "Each question must have exactly 4 options labelled A, B, C, D.",
    "Exactly one option must be correct; all distractors must be plausible.",
    "Include a short explanation of why the correct answer is right.",
    "Include one common misconception students have about this skill.",
    "Use clear, concise student-facing language appropriate for IGCSE level.",
    "No diagrams for this batch — if the skill involves a diagram, express "
    "the scenario in plain text or a simple data table instead.",
    "Difficulty should be distributed across each skill's 5 questions: "
    "2 easy, 2 medium, 1 hard.",
]


SCHEMA_EXAMPLE = {
    "batch_id": BATCH_ID,
    "generated_items": [
        {
            "generated_item_id": f"{BATCH_ID}_atomic_structure_001",
            "target_id": "gen_cambridge_igcse_physics_0625_atomic_structure_calculate_neutron_number_from_nucleon_number_v0",
            "topic": "Nuclear physics",
            "subtopic": "Atomic structure",
            "skill": "Calculate neutron number from nucleon number",
            "question_type": "mcq",
            "stem": "An atom of carbon has a nucleon number of 12 and 6 protons. How many neutrons does it contain?",
            "options": {
                "A": "6",
                "B": "12",
                "C": "18",
                "D": "2",
            },
            "correct_answer": "A",
            "explanation": "Neutron number = nucleon number − proton number = 12 − 6 = 6.",
            "common_misconception": "Students often confuse nucleon number with neutron number and choose 12.",
            "difficulty": "easy",
            "quality_flags": {
                "uses_original_context": True,
                "no_diagram_required": True,
                "single_correct_answer": True,
            },
        }
    ],
}


# ---------------------------------------------------------------------------
# Batch JSON builder
# ---------------------------------------------------------------------------

def build_batch(targets):
    slim_targets = []
    for t in targets:
        slim_targets.append({
            "target_id":             t["target_id"],
            "board":                 t["board"],
            "level":                 t["level"],
            "subject":               t["subject"],
            "syllabus_code":         t["syllabus_code"],
            "topic":                 t["topic"],
            "subtopic":              t["subtopic"],
            "skill":                 t["skill"],
            "target_question_count": t["target_question_count"],
            "recommended_formats":   t["recommended_formats"],
            "copyright_rule":        t["copyright_rule"],
        })

    total_planned = sum(t["target_question_count"] for t in targets)

    return {
        "batch_id":                BATCH_ID,
        "purpose": (
            "Generate original exam-style MCQ questions from clean priority-1 skill targets."
        ),
        "copyright_policy":        COPYRIGHT_POLICY,
        "total_targets":           len(targets),
        "total_planned_questions": total_planned,
        "targets":                 slim_targets,
    }


# ---------------------------------------------------------------------------
# Prompt Markdown builder
# ---------------------------------------------------------------------------

def build_prompt(targets):
    lines = []

    lines.append(f"# Quanta Aptus Authoring Batch {BATCH_NUMBER} — Cambridge IGCSE Physics 0625")
    lines.append("")
    lines.append("## Task")
    lines.append("")
    lines.append(
        "Generate original exam-style multiple-choice questions (MCQs) for each skill listed below. "
        "These questions are for an internal question bank and must be entirely original — "
        "they must not reproduce, paraphrase, or adapt any Cambridge International past paper material."
    )
    lines.append("")

    lines.append("## Global Constraints")
    lines.append("")
    for c in GLOBAL_CONSTRAINTS:
        lines.append(f"- {c}")
    lines.append("")

    lines.append("## Copyright Policy")
    lines.append("")
    lines.append(f"> {COPYRIGHT_POLICY}")
    lines.append("")

    lines.append("## Target Skills")
    lines.append("")
    lines.append("Generate the specified number of questions for each skill:")
    lines.append("")
    lines.append("| # | Topic | Subtopic | Skill | Questions to generate |")
    lines.append("| -: | ----- | -------- | ----- | --------------------: |")
    for i, t in enumerate(targets, 1):
        lines.append(
            f"| {i} | {t['topic']} | {t['subtopic']} | {t['skill']} "
            f"| {t['target_question_count']} |"
        )
    lines.append("")

    total = sum(t["target_question_count"] for t in targets)
    lines.append(f"**Total: {total} questions across {len(targets)} skills.**")
    lines.append("")

    lines.append("## Expected Output JSON Schema")
    lines.append("")
    lines.append("Return your output as a single valid JSON object matching this schema exactly:")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(
        {
            "batch_id": BATCH_ID,
            "generated_items": [
                {
                    "generated_item_id": f"{BATCH_ID}_<subtopic_slug>_<NNN>",
                    "target_id": "<target_id from target list above>",
                    "topic": "<topic>",
                    "subtopic": "<subtopic>",
                    "skill": "<skill>",
                    "question_type": "mcq",
                    "stem": "<question stem — plain text only, no diagrams>",
                    "options": {
                        "A": "<option A text>",
                        "B": "<option B text>",
                        "C": "<option C text>",
                        "D": "<option D text>",
                    },
                    "correct_answer": "<A|B|C|D>",
                    "explanation": "<why the correct answer is right>",
                    "common_misconception": "<one common student error for this skill>",
                    "difficulty": "<easy|medium|hard>",
                    "quality_flags": {
                        "uses_original_context": True,
                        "no_diagram_required": True,
                        "single_correct_answer": True,
                    },
                }
            ],
        },
        indent=2, ensure_ascii=False,
    ))
    lines.append("```")
    lines.append("")

    lines.append("## Schema Notes")
    lines.append("")
    lines.append(
        "- `generated_item_id`: use format `{batch_id}_{subtopic_slug}_{NNN}` "
        "where NNN is a zero-padded 3-digit index within the skill (001, 002, ...)."
    )
    lines.append("- `stem`: must be a complete, self-contained question in plain text.")
    lines.append("- `options`: A, B, C, D must all be present; no option may be empty.")
    lines.append("- `correct_answer`: must be exactly one of A, B, C, or D.")
    lines.append("- `difficulty`: distribute across each skill as 2 easy, 2 medium, 1 hard.")
    lines.append(
        "- `quality_flags.uses_original_context`: set to `true` if you invented the scenario; "
        "`false` if you reused a known textbook example."
    )
    lines.append("")

    lines.append("## Final Instruction")
    lines.append("")
    lines.append(
        "Return **valid JSON only**. Do not include any markdown fences, commentary, "
        "preamble, or explanation outside the JSON object. "
        f"The root object must contain `\"batch_id\": \"{BATCH_ID}\"` "
        f"and `\"generated_items\"` with exactly {total} items."
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(targets_path):
    data = json.loads(targets_path.read_text(encoding="utf-8"))

    # Filter and sort priority-1 targets
    p1_targets = [
        t for t in data["targets"]
        if t["priority"] == 1
        and t["seed_quality"] == "ready_internal"
        and t["generation_mode"] == "original_variant"
    ]
    p1_targets.sort(key=lambda t: (t["topic"], t["subtopic"], t["skill"]))

    batch_targets = p1_targets[:6]
    total_planned = sum(t["target_question_count"] for t in batch_targets)

    batch = build_batch(batch_targets)
    prompt = build_prompt(batch_targets)

    out_dir = targets_path.parent
    batch_path  = out_dir / f"authoring_batch_{BATCH_NUMBER}.json"
    prompt_path = out_dir / f"authoring_prompt_{BATCH_NUMBER}.md"

    batch_path.write_text(
        json.dumps(batch, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    prompt_path.write_text(prompt, encoding="utf-8")

    print(f"batch_id               : {BATCH_ID}")
    print(f"total_targets          : {len(batch_targets)}")
    print(f"total_planned_questions: {total_planned}")
    print(f"authoring_batch        : {batch_path}")
    print(f"authoring_prompt       : {prompt_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <generation_targets_v0.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    run(p)
