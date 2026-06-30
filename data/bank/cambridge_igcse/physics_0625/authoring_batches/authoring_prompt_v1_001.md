# Quanta Aptus Authoring Batch v1 001

## Role

You are creating original Quanta Aptus learning resources for Cambridge IGCSE Physics 0625.

## Non-Negotiable Copyright Rules

- Use the source metadata only as skill guidance.
- Do not copy Cambridge question wording.
- Do not copy Cambridge numbers.
- Do not copy Cambridge diagrams.
- Do not copy Cambridge experimental contexts.
- Do not copy Cambridge mark scheme wording.
- Create original student-facing and teacher-facing resources.

## Output Format

Return **valid JSON only**.
No markdown. No commentary outside JSON.

## Required JSON Output Schema

```json
{
  "batch_id": "cambridge_igcse_physics_0625_authoring_batch_v1_001",
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
        "D": "<option text or null>"
      },
      "correct_answer": "A | B | C | D | null",
      "worked_solution": "<step-by-step solution or explanation>",
      "marking_guidance": "<how to mark or checklist items>",
      "common_misconception": "<common student error and correction>",
      "teacher_note": "<pedagogical note for teacher>",
      "estimated_time_minutes": 1,
      "originality_statement": "Original Quanta Aptus content generated from derived skill metadata only."
    }
  ]
}
```

## Schema Rules by Resource Type

### original_mcq
- `student_prompt`: required.
- `options`: exactly 4 options A–D, all required.
- `correct_answer`: exactly one of A, B, C, D.
- `worked_solution`: required — explain why the correct answer is right.
- `common_misconception`: required.
- Do not require diagrams unless the target skill_type is graphing or diagram_drawing.

### worked_explanation
- `options`: null for all four options.
- `correct_answer`: null.
- `student_prompt`: brief framing of the concept.
- `worked_solution`: step-by-step conceptual explanation.
- `common_misconception`: required.

### worked_example
- Create a new original numerical scenario.
- `worked_solution`: full annotated step-by-step working.
- Do not reuse Cambridge numbers or experimental contexts.

### calculation_drill / short_answer_calculation
- `student_prompt`: a concise original calculation task.
- `worked_solution`: include each calculation step and final answer with units.
- Use IGCSE-appropriate numbers.

### graphing_drill
- `student_prompt`: include an original data table and graphing instructions.
- `marking_guidance`: axis labels, scale, point plotting, best-fit line.
- Do not require image generation; describe data and axes textually.

### graph_marking_checklist / marking_checklist / planning_marking_checklist
- `student_prompt`: null (teacher-facing resource).
- `correct_answer`: null.
- `options`: null.
- `marking_guidance`: list all mark-point criteria.

### experiment_planning_task
- `student_prompt`: original practical planning task (not Cambridge context).
- `worked_solution`: cover setup, method, variables, table structure, graph.
- `marking_guidance`: MP-style checklist.

### definition_flashcard / short_answer_recall
- `student_prompt`: one clear, concise question.
- `worked_solution`: model answer with units if applicable.

### data_interpretation_drill
- `student_prompt`: present a small original data set or trend.
- `worked_solution`: step-by-step interpretation.

## Difficulty Distribution

For each target with `planned_item_count >= 3`:
- At least 1 `easy`.
- At least 1 `medium`.
- At least 1 `hard` where appropriate for the skill type.

## Quality Requirements

- Language must be appropriate for Cambridge IGCSE students (age 14–16).
- Clear, direct, exam-style phrasing, but entirely original.
- Avoid ambiguous answer choices.
- Include correct SI units where needed.
- Avoid unsafe practical instructions.
- Do not mention Cambridge source papers or exam series in generated resources.

## Targets to Author

```json
[
  {
    "target_id": "cambridge_igcse_physics_0625_2024_w_p61_q01_graph_marking_checklist",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2024_w_p61_q01"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Motion, forces and energy",
    "skill_name": "hour You must answer on the question paper",
    "skill_type": "graphing",
    "assessment_mode": "practical",
    "resource_type": "graph_marking_checklist",
    "generation_goal": "Create a marking checklist for graphing tasks covering axes, scale, plots, and best-fit line.",
    "planned_item_count": 1,
    "priority": 1,
    "student_facing": false,
    "teacher_facing": true,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2024_w_p61_q01_graphing_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2024_w_p61_q01"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Motion, forces and energy",
    "skill_name": "hour You must answer on the question paper",
    "skill_type": "graphing",
    "assessment_mode": "practical",
    "resource_type": "graphing_drill",
    "generation_goal": "Create a graphing exercise: plot points from original data, draw a best-fit line, and extract values.",
    "planned_item_count": 3,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2024_w_p61_q02_graph_marking_checklist",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2024_w_p61_q02"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Thermal physics",
    "skill_name": "2 A student investigates the cooling of water in a metal container",
    "skill_type": "graphing",
    "assessment_mode": "practical",
    "resource_type": "graph_marking_checklist",
    "generation_goal": "Create a marking checklist for graphing tasks covering axes, scale, plots, and best-fit line.",
    "planned_item_count": 1,
    "priority": 1,
    "student_facing": false,
    "teacher_facing": true,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2024_w_p61_q02_graphing_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2024_w_p61_q02"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Thermal physics",
    "skill_name": "2 A student investigates the cooling of water in a metal container",
    "skill_type": "graphing",
    "assessment_mode": "practical",
    "resource_type": "graphing_drill",
    "generation_goal": "Create a graphing exercise: plot points from original data, draw a best-fit line, and extract values.",
    "planned_item_count": 3,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2024_w_p61_q04_experiment_planning_task",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2024_w_p61_q04"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Electricity and magnetism",
    "skill_name": "4 A student investigates the current required to melt different fuse wires",
    "skill_type": "extended_planning",
    "assessment_mode": "practical",
    "resource_type": "experiment_planning_task",
    "generation_goal": "Create an original experiment planning task covering setup, method, variables, results table, and graph.",
    "planned_item_count": 2,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2024_w_p61_q04_planning_marking_checklist",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2024_w_p61_q04"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Electricity and magnetism",
    "skill_name": "4 A student investigates the current required to melt different fuse wires",
    "skill_type": "extended_planning",
    "assessment_mode": "practical",
    "resource_type": "planning_marking_checklist",
    "generation_goal": "Create a marking checklist for experiment planning tasks aligned to mark-point criteria (MP1-MP7 style).",
    "planned_item_count": 1,
    "priority": 1,
    "student_facing": false,
    "teacher_facing": true,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q03_calculation_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q03"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Motion, forces and energy",
    "skill_name": "(iii) Calculate the distance between station A and station B",
    "skill_type": "calculation",
    "assessment_mode": "theory_written",
    "resource_type": "calculation_drill",
    "generation_goal": "Create a set of original calculation practice problems with full step-by-step solutions.",
    "planned_item_count": 5,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q03_short_answer_calculation",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q03"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Motion, forces and energy",
    "skill_name": "(iii) Calculate the distance between station A and station B",
    "skill_type": "calculation",
    "assessment_mode": "theory_written",
    "resource_type": "short_answer_calculation",
    "generation_goal": "Create short-answer calculation questions including expected working and a final answer.",
    "planned_item_count": 3,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q03_worked_example",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q03"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Motion, forces and energy",
    "skill_name": "(iii) Calculate the distance between station A and station B",
    "skill_type": "calculation",
    "assessment_mode": "theory_written",
    "resource_type": "worked_example",
    "generation_goal": "Create a fully worked example with annotated solution steps for this skill.",
    "planned_item_count": 2,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q04_calculation_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q04"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Motion, forces and energy",
    "skill_name": "4 Fig. 4.1 shows a heater used to warm the air in a room. Fig. 4.1",
    "skill_type": "equation_manipulation",
    "assessment_mode": "theory_written",
    "resource_type": "calculation_drill",
    "generation_goal": "Create a set of original calculation practice problems with full step-by-step solutions.",
    "planned_item_count": 5,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q04_short_answer_calculation",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q04"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Motion, forces and energy",
    "skill_name": "4 Fig. 4.1 shows a heater used to warm the air in a room. Fig. 4.1",
    "skill_type": "equation_manipulation",
    "assessment_mode": "theory_written",
    "resource_type": "short_answer_calculation",
    "generation_goal": "Create short-answer calculation questions including expected working and a final answer.",
    "planned_item_count": 3,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q04_worked_example",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q04"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Motion, forces and energy",
    "skill_name": "4 Fig. 4.1 shows a heater used to warm the air in a room. Fig. 4.1",
    "skill_type": "equation_manipulation",
    "assessment_mode": "theory_written",
    "resource_type": "worked_example",
    "generation_goal": "Create a fully worked example with annotated solution steps for this skill.",
    "planned_item_count": 2,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q05_calculation_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q05"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Waves",
    "skill_name": "5 A ray of light is incident on a soap film",
    "skill_type": "equation_manipulation",
    "assessment_mode": "theory_written",
    "resource_type": "calculation_drill",
    "generation_goal": "Create a set of original calculation practice problems with full step-by-step solutions.",
    "planned_item_count": 5,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q05_short_answer_calculation",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q05"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Waves",
    "skill_name": "5 A ray of light is incident on a soap film",
    "skill_type": "equation_manipulation",
    "assessment_mode": "theory_written",
    "resource_type": "short_answer_calculation",
    "generation_goal": "Create short-answer calculation questions including expected working and a final answer.",
    "planned_item_count": 3,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q05_worked_example",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q05"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Waves",
    "skill_name": "5 A ray of light is incident on a soap film",
    "skill_type": "equation_manipulation",
    "assessment_mode": "theory_written",
    "resource_type": "worked_example",
    "generation_goal": "Create a fully worked example with annotated solution steps for this skill.",
    "planned_item_count": 2,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q08_diagram_or_graph_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q08"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Electricity and magnetism",
    "skill_name": "8 Fig. 8.1 shows a diagram of part of a simple a.c. generator. external circuit",
    "skill_type": "graphing",
    "assessment_mode": "theory_written",
    "resource_type": "diagram_or_graph_drill",
    "generation_goal": "Create a diagram or graph drawing exercise with original data and a marking guide.",
    "planned_item_count": 3,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p41_q08_marking_checklist",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p41_q08"
    ],
    "component_type": "theory_structured",
    "paper_code": "41",
    "topic": "Electricity and magnetism",
    "skill_name": "8 Fig. 8.1 shows a diagram of part of a simple a.c. generator. external circuit",
    "skill_type": "graphing",
    "assessment_mode": "theory_written",
    "resource_type": "marking_checklist",
    "generation_goal": "Create a marking checklist covering key features for diagram or graph drawing tasks.",
    "planned_item_count": 1,
    "priority": 1,
    "student_facing": false,
    "teacher_facing": true,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p61_q02_graph_marking_checklist",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p61_q02"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Thermal physics",
    "skill_name": "2 Fig. 1.1 (i) On Fig. 1.1",
    "skill_type": "graphing",
    "assessment_mode": "practical",
    "resource_type": "graph_marking_checklist",
    "generation_goal": "Create a marking checklist for graphing tasks covering axes, scale, plots, and best-fit line.",
    "planned_item_count": 1,
    "priority": 1,
    "student_facing": false,
    "teacher_facing": true,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p61_q02_graphing_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p61_q02"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Thermal physics",
    "skill_name": "2 Fig. 1.1 (i) On Fig. 1.1",
    "skill_type": "graphing",
    "assessment_mode": "practical",
    "resource_type": "graphing_drill",
    "generation_goal": "Create a graphing exercise: plot points from original data, draw a best-fit line, and extract values.",
    "planned_item_count": 3,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_physics_0625_2025_s_p61_q03_graph_marking_checklist",
    "source_skill_unit_ids": [
      "cambridge_igcse_physics_0625_2025_s_p61_q03"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Waves",
    "skill_name": "(c) The student measures the mass m of a dish",
    "skill_type": "graphing",
    "assessment_mode": "practical",
    "resource_type": "graph_marking_checklist",
    "generation_goal": "Create a marking checklist for graphing tasks covering axes, scale, plots, and best-fit line.",
    "planned_item_count": 1,
    "priority": 1,
    "student_facing": false,
    "teacher_facing": true,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  }
]
```
