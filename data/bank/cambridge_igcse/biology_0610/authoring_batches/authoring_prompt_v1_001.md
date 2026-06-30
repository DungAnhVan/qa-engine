# Quanta Aptus Authoring Batch v1 001

## Role

You are creating original Quanta Aptus learning resources for Cambridge IGCSE Biology 0610.

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
  "batch_id": "cambridge_igcse_biology_0610_authoring_batch_v1_001",
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
    "target_id": "cambridge_igcse_biology_0610_2025_s_p61_q01_graph_marking_checklist",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p61_q01"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Cells",
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
    "target_id": "cambridge_igcse_biology_0610_2025_s_p61_q01_graphing_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p61_q01"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Cells",
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
    "target_id": "cambridge_igcse_biology_0610_2025_s_p61_q02_graph_marking_checklist",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p61_q02"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Cells",
    "skill_name": "2 ..............................................................................",
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
    "target_id": "cambridge_igcse_biology_0610_2025_s_p61_q02_graphing_drill",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p61_q02"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Cells",
    "skill_name": "2 ..............................................................................",
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
    "target_id": "cambridge_igcse_biology_0610_2025_s_p61_q03_experiment_planning_task",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p61_q03"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Transport in plants",
    "skill_name": "Step 5 Place all the test-tubes into a warm water-bath",
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
    "target_id": "cambridge_igcse_biology_0610_2025_s_p61_q03_planning_marking_checklist",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p61_q03"
    ],
    "component_type": "practical_structured",
    "paper_code": "61",
    "topic": "Transport in plants",
    "skill_name": "Step 5 Place all the test-tubes into a warm water-bath",
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
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q33_original_mcq",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q33",
      "cambridge_igcse_biology_0610_2025_s_p21_q38"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Needs manual classification",
    "skill_name": "Unknown",
    "skill_type": "conceptual_explanation",
    "assessment_mode": "mcq",
    "resource_type": "original_mcq",
    "generation_goal": "Create an original MCQ question testing this skill with 4 options (A-D) and a correct answer key.",
    "planned_item_count": 3,
    "priority": 2,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q33_worked_explanation",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q33",
      "cambridge_igcse_biology_0610_2025_s_p21_q38"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Needs manual classification",
    "skill_name": "Unknown",
    "skill_type": "conceptual_explanation",
    "assessment_mode": "mcq",
    "resource_type": "worked_explanation",
    "generation_goal": "Create a step-by-step worked explanation of the reasoning needed to answer an MCQ on this skill.",
    "planned_item_count": 2,
    "priority": 2,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q01_original_mcq",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q01",
      "cambridge_igcse_biology_0610_2025_s_p21_q03",
      "cambridge_igcse_biology_0610_2025_s_p21_q04",
      "cambridge_igcse_biology_0610_2025_s_p21_q05",
      "cambridge_igcse_biology_0610_2025_s_p21_q06",
      "cambridge_igcse_biology_0610_2025_s_p21_q08",
      "cambridge_igcse_biology_0610_2025_s_p21_q10",
      "cambridge_igcse_biology_0610_2025_s_p21_q11",
      "cambridge_igcse_biology_0610_2025_s_p21_q12",
      "cambridge_igcse_biology_0610_2025_s_p21_q13",
      "cambridge_igcse_biology_0610_2025_s_p21_q15",
      "cambridge_igcse_biology_0610_2025_s_p21_q16",
      "cambridge_igcse_biology_0610_2025_s_p21_q19",
      "cambridge_igcse_biology_0610_2025_s_p21_q20",
      "cambridge_igcse_biology_0610_2025_s_p21_q22",
      "cambridge_igcse_biology_0610_2025_s_p21_q23",
      "cambridge_igcse_biology_0610_2025_s_p21_q24",
      "cambridge_igcse_biology_0610_2025_s_p21_q25",
      "cambridge_igcse_biology_0610_2025_s_p21_q29",
      "cambridge_igcse_biology_0610_2025_s_p21_q32",
      "cambridge_igcse_biology_0610_2025_s_p21_q35",
      "cambridge_igcse_biology_0610_2025_s_p21_q37",
      "cambridge_igcse_biology_0610_2025_s_p21_q39",
      "cambridge_igcse_biology_0610_2025_s_p21_q40"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Needs manual classification",
    "skill_name": "Unknown",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "original_mcq",
    "generation_goal": "Create an original MCQ question testing this skill with 4 options (A-D) and a correct answer key.",
    "planned_item_count": 3,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q01_worked_explanation",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q01",
      "cambridge_igcse_biology_0610_2025_s_p21_q03",
      "cambridge_igcse_biology_0610_2025_s_p21_q04",
      "cambridge_igcse_biology_0610_2025_s_p21_q05",
      "cambridge_igcse_biology_0610_2025_s_p21_q06",
      "cambridge_igcse_biology_0610_2025_s_p21_q08",
      "cambridge_igcse_biology_0610_2025_s_p21_q10",
      "cambridge_igcse_biology_0610_2025_s_p21_q11",
      "cambridge_igcse_biology_0610_2025_s_p21_q12",
      "cambridge_igcse_biology_0610_2025_s_p21_q13",
      "cambridge_igcse_biology_0610_2025_s_p21_q15",
      "cambridge_igcse_biology_0610_2025_s_p21_q16",
      "cambridge_igcse_biology_0610_2025_s_p21_q19",
      "cambridge_igcse_biology_0610_2025_s_p21_q20",
      "cambridge_igcse_biology_0610_2025_s_p21_q22",
      "cambridge_igcse_biology_0610_2025_s_p21_q23",
      "cambridge_igcse_biology_0610_2025_s_p21_q24",
      "cambridge_igcse_biology_0610_2025_s_p21_q25",
      "cambridge_igcse_biology_0610_2025_s_p21_q29",
      "cambridge_igcse_biology_0610_2025_s_p21_q32",
      "cambridge_igcse_biology_0610_2025_s_p21_q35",
      "cambridge_igcse_biology_0610_2025_s_p21_q37",
      "cambridge_igcse_biology_0610_2025_s_p21_q39",
      "cambridge_igcse_biology_0610_2025_s_p21_q40"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Needs manual classification",
    "skill_name": "Unknown",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "worked_explanation",
    "generation_goal": "Create a step-by-step worked explanation of the reasoning needed to answer an MCQ on this skill.",
    "planned_item_count": 2,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q02_original_mcq",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q02",
      "cambridge_igcse_biology_0610_2025_s_p21_q07",
      "cambridge_igcse_biology_0610_2025_s_p21_q17",
      "cambridge_igcse_biology_0610_2025_s_p21_q21",
      "cambridge_igcse_biology_0610_2025_s_p21_q36"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Electricity and magnetism",
    "skill_name": "Identify circuit in which LEDs conduct",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "original_mcq",
    "generation_goal": "Create an original MCQ question testing this skill with 4 options (A-D) and a correct answer key.",
    "planned_item_count": 3,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q02_worked_explanation",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q02",
      "cambridge_igcse_biology_0610_2025_s_p21_q07",
      "cambridge_igcse_biology_0610_2025_s_p21_q17",
      "cambridge_igcse_biology_0610_2025_s_p21_q21",
      "cambridge_igcse_biology_0610_2025_s_p21_q36"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Electricity and magnetism",
    "skill_name": "Identify circuit in which LEDs conduct",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "worked_explanation",
    "generation_goal": "Create a step-by-step worked explanation of the reasoning needed to answer an MCQ on this skill.",
    "planned_item_count": 2,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q09_original_mcq",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q09"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Space physics",
    "skill_name": "Order orbital and rotational periods of Earth and Moon",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "original_mcq",
    "generation_goal": "Create an original MCQ question testing this skill with 4 options (A-D) and a correct answer key.",
    "planned_item_count": 3,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q09_worked_explanation",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q09"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Space physics",
    "skill_name": "Order orbital and rotational periods of Earth and Moon",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "worked_explanation",
    "generation_goal": "Create a step-by-step worked explanation of the reasoning needed to answer an MCQ on this skill.",
    "planned_item_count": 2,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q14_original_mcq",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q14",
      "cambridge_igcse_biology_0610_2025_s_p21_q27",
      "cambridge_igcse_biology_0610_2025_s_p21_q30"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Motion, forces and energy",
    "skill_name": "Calculate spring constant",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "original_mcq",
    "generation_goal": "Create an original MCQ question testing this skill with 4 options (A-D) and a correct answer key.",
    "planned_item_count": 3,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q14_worked_explanation",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q14",
      "cambridge_igcse_biology_0610_2025_s_p21_q27",
      "cambridge_igcse_biology_0610_2025_s_p21_q30"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Motion, forces and energy",
    "skill_name": "Calculate spring constant",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "worked_explanation",
    "generation_goal": "Create a step-by-step worked explanation of the reasoning needed to answer an MCQ on this skill.",
    "planned_item_count": 2,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q18_original_mcq",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q18"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Space physics",
    "skill_name": "Recall properties of the Universe and redshift",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "original_mcq",
    "generation_goal": "Create an original MCQ question testing this skill with 4 options (A-D) and a correct answer key.",
    "planned_item_count": 3,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q18_worked_explanation",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q18"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Space physics",
    "skill_name": "Recall properties of the Universe and redshift",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "worked_explanation",
    "generation_goal": "Create a step-by-step worked explanation of the reasoning needed to answer an MCQ on this skill.",
    "planned_item_count": 2,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q26_original_mcq",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q26",
      "cambridge_igcse_biology_0610_2025_s_p21_q34"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Needs manual classification",
    "skill_name": "Unknown",
    "skill_type": "recall_definition",
    "assessment_mode": "mcq",
    "resource_type": "original_mcq",
    "generation_goal": "Create an original MCQ question testing this skill with 4 options (A-D) and a correct answer key.",
    "planned_item_count": 3,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q26_worked_explanation",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q26",
      "cambridge_igcse_biology_0610_2025_s_p21_q34"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Needs manual classification",
    "skill_name": "Unknown",
    "skill_type": "recall_definition",
    "assessment_mode": "mcq",
    "resource_type": "worked_explanation",
    "generation_goal": "Create a step-by-step worked explanation of the reasoning needed to answer an MCQ on this skill.",
    "planned_item_count": 2,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  },
  {
    "target_id": "cambridge_igcse_biology_0610_2025_s_p21_q28_original_mcq",
    "source_skill_unit_ids": [
      "cambridge_igcse_biology_0610_2025_s_p21_q28"
    ],
    "component_type": "mcq",
    "paper_code": "21",
    "topic": "Motion, forces and energy",
    "skill_name": "Analyse speed–time graph",
    "skill_type": "multiple_choice_concept",
    "assessment_mode": "mcq",
    "resource_type": "original_mcq",
    "generation_goal": "Create an original MCQ question testing this skill with 4 options (A-D) and a correct answer key.",
    "planned_item_count": 3,
    "priority": 3,
    "student_facing": true,
    "teacher_facing": false,
    "copyright_rule": "create_original_content_only_do_not_copy_source_wording"
  }
]
```
