"""
Gate 69C -- AI Prompt Builder v1

Builds safe prompts for AI resource authoring.

Rules:
  - Prompt uses only safe metadata fields.
  - No raw Cambridge source text, mark schemes, or PDF content.
  - Safety guard runs before returning any prompt.
  - Generated output must be original Quanta Aptus content.

This module has no external dependencies and makes no API calls.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.ai.copyright_safety_guard_v1 import (
    assert_ai_input_is_safe,
    scan_prompt_for_disallowed_source_text,
)

# ---------------------------------------------------------------------------
# System-level safety instructions (prepended to all prompts)
# ---------------------------------------------------------------------------

def build_system_safety_instructions() -> str:
    return """You are a content creation assistant for Quanta Aptus, an educational platform.

STRICT CONTENT RULES — you must follow these without exception:
1. Generate ENTIRELY ORIGINAL content. Do not reproduce any text from Cambridge exam papers,
   past papers, mark schemes, textbooks, or any copyrighted source material.
2. Do not copy question wording, numbers, diagrams, contexts, answer options, or marking
   criteria from any existing source.
3. Your content is Cambridge-style in FORMAT and DIFFICULTY only — not in specific content.
4. Never include raw text from source files, PDFs, or any extracted documents.
5. Content must be new, created by you, suitable for the topic and difficulty specified.
6. Always respond with ONLY a valid JSON object. No preamble, no explanation, no markdown fences.

OUTPUT FORMAT — respond with exactly this JSON structure:
{
  "resource_id": "<unique-id-you-generate>",
  "resource_type": "<type>",
  "title": "<short descriptive title>",
  "topic": "<topic>",
  "skill_name": "<skill>",
  "skill_type": "<skill_type>",
  "difficulty": "<difficulty>",
  "estimated_time_minutes": <number>,
  "student_prompt": "<the main question or task text>",
  "student_instructions": "<instructions for the student>",
  "answer_key": "<model answer>",
  "marking_rubric": [
    {"criterion": "<criterion>", "marks": <number>, "guidance": "<guidance>"}
  ],
  "teacher_notes": "<notes for teacher>",
  "safety_declaration": {
    "original_content": true,
    "no_raw_source_text_used": true,
    "no_mark_scheme_copied": true
  }
}"""


def build_output_schema_instruction() -> str:
    return """Respond with ONLY valid JSON matching this structure. No markdown, no explanation.
All fields are required. safety_declaration values must all be true."""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_resource_authoring_prompt(request: dict) -> dict:
    """
    Build a safe prompt dict from a validated authoring request.

    Returns:
        {
          "safe": bool,
          "system_prompt": str,
          "user_prompt": str,
          "full_prompt": str,  -- system + user combined for single-turn APIs
          "safety_check": dict,
          "payload_safety": dict,
          "issues": list[str],
        }

    Raises nothing — errors are returned in issues[].
    """
    issues: list[str] = []

    # 1. Safety check on the input payload
    payload_safety = assert_ai_input_is_safe(request)
    if not payload_safety["safe"]:
        return {
            "safe":           False,
            "system_prompt":  "",
            "user_prompt":    "",
            "full_prompt":    "",
            "safety_check":   payload_safety,
            "payload_safety": payload_safety,
            "issues":         payload_safety["issues"],
        }

    # 2. Extract safe metadata fields only
    subject_slug       = str(request.get("subject_slug", ""))
    syllabus_code      = str(request.get("syllabus_code", ""))
    topic              = str(request.get("topic", ""))
    subtopic           = str(request.get("subtopic", ""))
    skill_name         = str(request.get("skill_name", ""))
    skill_type         = str(request.get("skill_type", ""))
    difficulty         = str(request.get("difficulty", "medium"))
    resource_type      = str(request.get("resource_type", "question"))
    learning_objective = str(request.get("learning_objective", ""))
    constraints        = request.get("constraints", {})
    source_metadata    = request.get("source_metadata", {})

    student_level      = str(constraints.get("student_level", "A-Level")) if isinstance(constraints, dict) else "A-Level"
    est_time           = int(constraints.get("estimated_time_minutes", 10)) if isinstance(constraints, dict) else 10
    source_ids         = source_metadata.get("source_ids", []) if isinstance(source_metadata, dict) else []

    # 3. Build the user-facing portion of the prompt
    lines = [
        f"Create an original Quanta Aptus learning resource with the following specifications:",
        f"",
        f"Subject: {subject_slug}" + (f" ({syllabus_code})" if syllabus_code else ""),
        f"Topic: {topic}" + (f" — {subtopic}" if subtopic else ""),
        f"Resource type: {resource_type}",
        f"Difficulty: {difficulty}",
        f"Student level: {student_level}",
        f"Estimated time: {est_time} minutes",
    ]
    if skill_name:
        lines.append(f"Skill: {skill_name}" + (f" ({skill_type})" if skill_type else ""))
    if learning_objective:
        lines.append(f"Learning objective: {learning_objective}")
    if source_ids:
        # Only pass metadata IDs, not any content
        lines.append(f"Related source metadata IDs: {', '.join(str(i) for i in source_ids[:5])}")

    lines += [
        f"",
        f"IMPORTANT: Generate completely original content. Do not use any text from:",
        f"- Cambridge exam papers or mark schemes",
        f"- PDF extracts or source documents",
        f"- Any existing question banks",
        f"",
        build_output_schema_instruction(),
    ]

    user_prompt = "\n".join(lines)

    # 4. Safety check on the assembled user prompt
    prompt_safety = scan_prompt_for_disallowed_source_text(user_prompt)
    if not prompt_safety["safe"]:
        issues.extend(prompt_safety["issues"])
        return {
            "safe":           False,
            "system_prompt":  "",
            "user_prompt":    user_prompt,
            "full_prompt":    "",
            "safety_check":   prompt_safety,
            "payload_safety": payload_safety,
            "issues":         issues,
        }

    system_prompt = build_system_safety_instructions()
    full_prompt   = system_prompt + "\n\n" + user_prompt

    return {
        "safe":           True,
        "system_prompt":  system_prompt,
        "user_prompt":    user_prompt,
        "full_prompt":    full_prompt,
        "safety_check":   prompt_safety,
        "payload_safety": payload_safety,
        "issues":         issues,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from tools.ai.ai_authoring_contract_v1 import make_safe_authoring_request

    req = make_safe_authoring_request(
        subject_slug="physics",
        topic="Wave Superposition",
        subtopic="Double-slit interference",
        difficulty="hard",
        resource_type="question",
        learning_objective="Calculate fringe spacing using the double-slit formula.",
        student_level="A-Level Year 2",
    )
    result = build_resource_authoring_prompt(req)
    print(f"safe:   {result['safe']}")
    print(f"issues: {result['issues']}")
    if result["safe"]:
        print("\n--- User prompt preview (first 400 chars) ---")
        print(result["user_prompt"][:400])
