"""
Gate 69B -- AI Authoring Contract v1

Defines the safe input contract for AI-driven question authoring.

The contract ensures:
  - Only safe metadata is included in AI prompts.
  - No raw Cambridge source text, mark schemes, or PDF extracts are included.
  - Generated content must be original Quanta Aptus material.
  - Copyright strict mode is enforced by default.

This module has no external dependencies and makes no API calls.
"""

from __future__ import annotations
from typing import Any
from tools.ai.copyright_safety_guard_v1 import (
    DISALLOWED_PAYLOAD_FIELDS,
    assert_ai_input_is_safe,
)

# ---------------------------------------------------------------------------
# Contract field schema
# ---------------------------------------------------------------------------

# Required fields for a valid authoring request
REQUIRED_FIELDS = {"subject_slug", "topic"}

# All allowed top-level fields
ALLOWED_FIELDS = {
    "subject_slug",
    "syllabus_code",
    "topic",
    "subtopic",
    "skill_name",
    "skill_type",
    "difficulty",
    "resource_type",
    "learning_objective",
    "constraints",
    "source_metadata",
}

# Allowed keys inside the constraints sub-dict
ALLOWED_CONSTRAINT_KEYS = {
    "must_be_original",
    "no_source_copying",
    "cambridge_style_but_original",
    "student_level",
    "estimated_time_minutes",
}

# Allowed keys inside source_metadata
ALLOWED_SOURCE_METADATA_KEYS = {
    "source_ids",
    "paper_refs",
    "no_raw_text_included",
}

VALID_DIFFICULTIES   = {"easy", "medium", "hard", "very_hard"}
VALID_RESOURCE_TYPES = {"question", "worked_example", "explanation", "practice_set"}
VALID_SKILL_TYPES    = {"recall", "application", "analysis", "evaluation", "synthesis"}

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_safe_authoring_request(
    subject_slug: str,
    topic: str,
    *,
    syllabus_code: str = "",
    subtopic: str = "",
    skill_name: str = "",
    skill_type: str = "",
    difficulty: str = "medium",
    resource_type: str = "question",
    learning_objective: str = "",
    student_level: str = "A-Level",
    estimated_time_minutes: int = 10,
    source_ids: list[str] | None = None,
    paper_refs: list[str] | None = None,
) -> dict:
    """
    Build a safe authoring request payload.

    No raw source fields are allowed. The returned dict is safe to pass to
    an AI provider after running through validate_safe_authoring_request().
    """
    return {
        "subject_slug":      subject_slug,
        "syllabus_code":     syllabus_code,
        "topic":             topic,
        "subtopic":          subtopic,
        "skill_name":        skill_name,
        "skill_type":        skill_type,
        "difficulty":        difficulty,
        "resource_type":     resource_type,
        "learning_objective": learning_objective,
        "constraints": {
            "must_be_original":               True,
            "no_source_copying":              True,
            "cambridge_style_but_original":   True,
            "student_level":                  student_level,
            "estimated_time_minutes":         estimated_time_minutes,
        },
        "source_metadata": {
            "source_ids":           source_ids or [],
            "paper_refs":           paper_refs or [],
            "no_raw_text_included": True,
        },
    }

# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_safe_authoring_request(payload: dict) -> dict:
    """
    Validate an authoring request payload against the safe contract.

    Returns:
        {
          "valid": bool,
          "issues": list[str],
          "copyright_safe": bool,
          "missing_required": list[str],
          "disallowed_fields": list[str],
        }
    """
    issues: list[str] = []
    disallowed_found: list[str] = []

    # 1. Required fields
    missing = [f for f in REQUIRED_FIELDS if not payload.get(f)]
    if missing:
        issues.append(f"Missing required fields: {missing}")

    # 2. Disallowed fields at top level
    for k in payload:
        if k in DISALLOWED_PAYLOAD_FIELDS:
            disallowed_found.append(k)
            issues.append(f"Disallowed field at top level: '{k}'")

    # 3. Validate constraints sub-dict
    constraints = payload.get("constraints", {})
    if not isinstance(constraints, dict):
        issues.append("'constraints' must be a dict")
    else:
        for k in constraints:
            if k not in ALLOWED_CONSTRAINT_KEYS:
                issues.append(f"Unknown constraint key: '{k}'")
        if constraints.get("must_be_original") is not True:
            issues.append("constraints.must_be_original must be True")
        if constraints.get("no_source_copying") is not True:
            issues.append("constraints.no_source_copying must be True")

    # 4. Validate source_metadata sub-dict
    source_meta = payload.get("source_metadata", {})
    if not isinstance(source_meta, dict):
        issues.append("'source_metadata' must be a dict")
    else:
        for k in source_meta:
            if k not in ALLOWED_SOURCE_METADATA_KEYS:
                issues.append(f"Unknown source_metadata key: '{k}'")
        if source_meta.get("no_raw_text_included") is not True:
            issues.append("source_metadata.no_raw_text_included must be True")

    # 5. Copyright safety guard (deep scan)
    safety = assert_ai_input_is_safe(payload)
    if not safety["safe"]:
        for issue in safety["issues"]:
            issues.append(f"Copyright safety: {issue}")

    # 6. Enum validation (non-blocking warnings)
    difficulty = payload.get("difficulty", "")
    if difficulty and difficulty not in VALID_DIFFICULTIES:
        issues.append(f"difficulty={difficulty!r} not in {sorted(VALID_DIFFICULTIES)}")

    resource_type = payload.get("resource_type", "")
    if resource_type and resource_type not in VALID_RESOURCE_TYPES:
        issues.append(f"resource_type={resource_type!r} not in {sorted(VALID_RESOURCE_TYPES)}")

    valid = len(missing) == 0 and len(disallowed_found) == 0 and safety["safe"]

    return {
        "valid":             valid,
        "issues":            issues,
        "copyright_safe":    safety["safe"],
        "missing_required":  missing,
        "disallowed_fields": disallowed_found,
    }

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def summarize_authoring_request(payload: dict) -> str:
    """
    Return a human-readable one-line summary of an authoring request.
    Safe to print — contains no source material.
    """
    parts = []
    if payload.get("subject_slug"):
        parts.append(payload["subject_slug"])
    if payload.get("topic"):
        parts.append(f"topic={payload['topic']!r}")
    if payload.get("subtopic"):
        parts.append(f"subtopic={payload['subtopic']!r}")
    if payload.get("difficulty"):
        parts.append(f"difficulty={payload['difficulty']}")
    if payload.get("resource_type"):
        parts.append(f"type={payload['resource_type']}")
    if payload.get("skill_name"):
        parts.append(f"skill={payload['skill_name']!r}")
    return "AuthoringRequest(" + ", ".join(parts) + ")"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("AI Authoring Contract — self-test")
    print("-" * 40)

    # Valid request
    req = make_safe_authoring_request(
        subject_slug="physics",
        topic="Waves and Superposition",
        subtopic="Diffraction",
        difficulty="medium",
        resource_type="question",
        learning_objective="Describe the conditions for constructive interference",
    )
    result = validate_safe_authoring_request(req)
    print(f"Valid request:  valid={result['valid']}  issues={result['issues']}")
    print(f"  Summary: {summarize_authoring_request(req)}")

    # Invalid: raw source field injected
    bad_req = {**req, "original_raw_block": "Some copied text here"}
    bad_result = validate_safe_authoring_request(bad_req)
    print(f"Invalid (raw):  valid={bad_result['valid']}  disallowed={bad_result['disallowed_fields']}")

    # Missing required
    incomplete = {"topic": "Waves"}
    incomplete_result = validate_safe_authoring_request(incomplete)
    print(f"Incomplete:     valid={incomplete_result['valid']}  missing={incomplete_result['missing_required']}")
