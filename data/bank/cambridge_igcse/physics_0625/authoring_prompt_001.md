# Quanta Aptus Authoring Batch 001 — Cambridge IGCSE Physics 0625

## Task

Generate original exam-style multiple-choice questions (MCQs) for each skill listed below. These questions are for an internal question bank and must be entirely original — they must not reproduce, paraphrase, or adapt any Cambridge International past paper material.

## Global Constraints

- Do not copy Cambridge wording, phrasing, or sentence structure.
- Do not reuse source numbers, values, quantities, or contexts.
- Each question must have exactly 4 options labelled A, B, C, D.
- Exactly one option must be correct; all distractors must be plausible.
- Include a short explanation of why the correct answer is right.
- Include one common misconception students have about this skill.
- Use clear, concise student-facing language appropriate for IGCSE level.
- No diagrams for this batch — if the skill involves a diagram, express the scenario in plain text or a simple data table instead.
- Difficulty should be distributed across each skill's 5 questions: 2 easy, 2 medium, 1 hard.

## Copyright Policy

> Do not copy wording, numbers, contexts, diagrams, option order, or answer patterns from source materials. Generate original questions only.

## Target Skills

Generate the specified number of questions for each skill:

| # | Topic | Subtopic | Skill | Questions to generate |
| -: | ----- | -------- | ----- | --------------------: |
| 1 | Nuclear physics | Atomic structure | Calculate neutron number from nucleon number | 5 |
| 2 | Nuclear physics | Radiation safety | Recall gamma radiation safety precautions | 5 |
| 3 | Space physics | Universe and redshift | Recall properties of the Universe and redshift | 5 |
| 4 | Thermal physics | Evaporation | Recall what escapes during evaporation | 5 |
| 5 | Thermal physics | Specific heat capacity | Interpret specific heat capacity definition | 5 |
| 6 | Waves | Refraction | Calculate refractive index | 5 |

**Total: 30 questions across 6 skills.**

## Expected Output JSON Schema

Return your output as a single valid JSON object matching this schema exactly:

```json
{
  "batch_id": "cambridge_igcse_physics_0625_authoring_batch_001",
  "generated_items": [
    {
      "generated_item_id": "cambridge_igcse_physics_0625_authoring_batch_001_<subtopic_slug>_<NNN>",
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
        "D": "<option D text>"
      },
      "correct_answer": "<A|B|C|D>",
      "explanation": "<why the correct answer is right>",
      "common_misconception": "<one common student error for this skill>",
      "difficulty": "<easy|medium|hard>",
      "quality_flags": {
        "uses_original_context": true,
        "no_diagram_required": true,
        "single_correct_answer": true
      }
    }
  ]
}
```

## Schema Notes

- `generated_item_id`: use format `{batch_id}_{subtopic_slug}_{NNN}` where NNN is a zero-padded 3-digit index within the skill (001, 002, ...).
- `stem`: must be a complete, self-contained question in plain text.
- `options`: A, B, C, D must all be present; no option may be empty.
- `correct_answer`: must be exactly one of A, B, C, or D.
- `difficulty`: distribute across each skill as 2 easy, 2 medium, 1 hard.
- `quality_flags.uses_original_context`: set to `true` if you invented the scenario; `false` if you reused a known textbook example.

## Final Instruction

Return **valid JSON only**. Do not include any markdown fences, commentary, preamble, or explanation outside the JSON object. The root object must contain `"batch_id": "cambridge_igcse_physics_0625_authoring_batch_001"` and `"generated_items"` with exactly 30 items.
