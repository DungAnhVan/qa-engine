# Quanta Aptus Authoring Batch v1 001

## Role

You are creating original Quanta Aptus learning resources for Cambridge IGCSE Mathematics 0580.

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
  "batch_id": "cambridge_igcse_mathematics_0580_authoring_batch_v1_001",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q01_calculation_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q01"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Mensuration",
    "skill_name": "| Area, A, of triangle, base b, height h",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q01_short_answer_calculation",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q01"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Mensuration",
    "skill_name": "| Area, A, of triangle, base b, height h",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q01_worked_example",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q01"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Mensuration",
    "skill_name": "| Area, A, of triangle, base b, height h",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q03_calculation_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q03"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Algebra",
    "skill_name": "| Volume, V, of cylinder of radius r, height h",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q03_short_answer_calculation",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q03"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Algebra",
    "skill_name": "| Volume, V, of cylinder of radius r, height h",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q03_worked_example",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q03"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Algebra",
    "skill_name": "| Volume, V, of cylinder of radius r, height h",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q05_calculation_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q05"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Probability",
    "skill_name": "Scott changes $300 into pounds (£)",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q05_short_answer_calculation",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q05"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Probability",
    "skill_name": "Scott changes $300 into pounds (£)",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q05_worked_example",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q05"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Probability",
    "skill_name": "Scott changes $300 into pounds (£)",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q06_calculation_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q06"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Mensuration",
    "skill_name": "A solid wooden cone has base radius 4 cm and height 12 cm",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q06_short_answer_calculation",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q06"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Mensuration",
    "skill_name": "A solid wooden cone has base radius 4 cm and height 12 cm",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q06_worked_example",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q06"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Mensuration",
    "skill_name": "A solid wooden cone has base radius 4 cm and height 12 cm",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q07_calculation_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q07"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Number",
    "skill_name": "y = mx+c Rearrange the formula to make m the subject",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q07_short_answer_calculation",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q07"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Number",
    "skill_name": "y = mx+c Rearrange the formula to make m the subject",
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
    "target_id": "cambridge_igcse_mathematics_0580_2025_s_p42_q07_worked_example",
    "source_skill_unit_ids": [
      "cambridge_igcse_mathematics_0580_2025_s_p42_q07"
    ],
    "component_type": "theory_structured",
    "paper_code": "42",
    "topic": "Number",
    "skill_name": "y = mx+c Rearrange the formula to make m the subject",
    "skill_type": "equation_manipulation",
    "assessment_mode": "theory_written",
    "resource_type": "worked_example",
    "generation_goal": "Create a fully worked example with annotated solution steps for this skill.",
    "planned_item_count": 2,
    "priority": 1,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  }
]
```
