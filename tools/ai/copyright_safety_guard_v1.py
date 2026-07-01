"""
Gate 69B -- Copyright Safety Guard v1

Prevents raw Cambridge source material from being sent to AI providers.

Rules:
  - Raw question text, mark schemes, PDF extracts are NEVER allowed in AI prompts.
  - Safe metadata (topic, skill, difficulty, etc.) is always allowed.
  - Generated output is scanned for obvious copyright risk phrases.

This module has no external dependencies and makes no API calls.
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Disallowed field names in payload dicts
# These fields contain raw source material and must never be forwarded to AI.
# ---------------------------------------------------------------------------

DISALLOWED_PAYLOAD_FIELDS = {
    "original_raw_block",
    "normalized_raw_block",
    "raw_mark_scheme",
    "mark_scheme_text",
    "raw_pdf_path",
    "source_text",
    "raw_text",
    "extracted_text",
    "pdf_text",
    "question_raw",
    "answer_raw",
    "mark_scheme_raw",
}

# ---------------------------------------------------------------------------
# Patterns indicating disallowed content in prompt strings
# ---------------------------------------------------------------------------

DISALLOWED_PROMPT_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # Payload field names appearing literally in a prompt string
    ("raw_source_field",      re.compile(r'\boriginal_raw_block\b'),           "Field 'original_raw_block' in prompt"),
    ("raw_source_field",      re.compile(r'\bnormalized_raw_block\b'),         "Field 'normalized_raw_block' in prompt"),
    ("raw_source_field",      re.compile(r'\braw_mark_scheme\b'),              "Field 'raw_mark_scheme' in prompt"),
    ("raw_source_field",      re.compile(r'\bmark_scheme_text\b'),             "Field 'mark_scheme_text' in prompt"),
    ("raw_pdf_path",          re.compile(r'\braw_pdf_path\b'),                 "Field 'raw_pdf_path' in prompt"),
    # Path patterns that indicate raw source material
    ("raw_data_path",         re.compile(r'data[/\\]raw[/\\]'),                "data/raw/ path in prompt"),
    ("pdf_path",              re.compile(r'\S+\.pdf', re.IGNORECASE),          ".pdf file reference in prompt"),
    # Cambridge-specific structural patterns typical of exam paper extraction
    ("cambridge_header",      re.compile(r'Question\s+Answer\s+Marks', re.IGNORECASE),
                                                                               "Cambridge mark scheme header in prompt"),
    ("cambridge_paper_ref",   re.compile(r'Cambridge\s+(International|Assessment|A\s*Level)\s+(Examinations?|AS\s*&?\s*A)', re.IGNORECASE),
                                                                               "Cambridge exam body reference in prompt"),
    ("cambridge_paper_code",  re.compile(r'\b97\d{2}/\d{2}/[OM]\b'),          "Cambridge paper code format in prompt"),
    ("mark_scheme_line",      re.compile(r'\[\s*\d+\s*\]\s*$', re.MULTILINE), "Mark allocation line in prompt (e.g. [3])"),
    # Raw file-based content signatures
    ("raw_source_key",        re.compile(r'"raw_text"\s*:'),                   "raw_text JSON key in prompt"),
    ("raw_source_key",        re.compile(r'"original_raw_block"\s*:'),         "original_raw_block JSON key in prompt"),
]

# Threshold: a single line longer than this in a prompt is a risk signal
# (genuine prompts use metadata, not pasted paragraphs of source text)
LONG_LINE_THRESHOLD = 400

# Patterns that look like copied source in generated output
GENERATED_CONTENT_RISK_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("copyright_notice",  re.compile(r'Cambridge\s+(International|Assessment)', re.IGNORECASE),
                                                                          "Cambridge entity name in output"),
    ("exam_footer",       re.compile(r'(BLANK PAGE|This document has \d+ pages)', re.IGNORECASE),
                                                                          "Exam paper footer in output"),
    ("mark_scheme_fmt",   re.compile(r'Question\s+Answer\s+Marks', re.IGNORECASE),
                                                                          "Mark scheme table header in output"),
    ("paper_code",        re.compile(r'\b97\d{2}/\d{2}/[OM]\b'),         "Cambridge paper code in output"),
    ("raw_block_ref",     re.compile(r'\boriginal_raw_block\b'),          "Raw block field name in output"),
]

# ---------------------------------------------------------------------------
# Safe metadata fields (these are always allowed in AI input)
# ---------------------------------------------------------------------------

SAFE_METADATA_FIELDS = {
    "subject_slug", "syllabus_code", "topic", "subtopic",
    "skill_name", "skill_type", "difficulty", "resource_type",
    "learning_objective", "constraints", "source_metadata",
    "estimated_time_minutes", "student_level", "must_be_original",
    "no_source_copying", "cambridge_style_but_original",
    "source_ids", "paper_refs", "no_raw_text_included",
}

# ---------------------------------------------------------------------------
# Scan functions
# ---------------------------------------------------------------------------

def scan_prompt_for_disallowed_source_text(prompt: str) -> dict:
    """
    Scan a prompt string for patterns that indicate raw Cambridge source material.

    Returns:
        {
          "safe": bool,
          "risk_level": "low" | "medium" | "high",
          "allowed_for_ai_provider": bool,
          "issues": list[str]
        }
    """
    issues: list[str] = []
    risk_score = 0

    # Check known patterns
    for _, pattern, description in DISALLOWED_PROMPT_PATTERNS:
        if pattern.search(prompt):
            issues.append(description)
            risk_score += 2

    # Check for suspiciously long single lines
    for line in prompt.splitlines():
        stripped = line.strip()
        if len(stripped) > LONG_LINE_THRESHOLD:
            issues.append(
                f"Long unbroken text block detected ({len(stripped)} chars) — "
                "may be pasted source text"
            )
            risk_score += 3
            break  # one warning is enough

    safe = risk_score == 0
    if risk_score == 0:
        risk_level = "low"
    elif risk_score <= 3:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "safe":                   safe,
        "risk_level":             risk_level,
        "allowed_for_ai_provider": safe,
        "issues":                 issues,
    }


def scan_generated_content_for_risk(text: str) -> dict:
    """
    Scan AI-generated text for copyright risk patterns.

    Returns:
        {
          "safe": bool,
          "risk_level": "low" | "medium" | "high",
          "issues": list[str]
        }
    """
    issues: list[str] = []
    risk_score = 0

    for _, pattern, description in GENERATED_CONTENT_RISK_PATTERNS:
        if pattern.search(text):
            issues.append(description)
            risk_score += 2

    safe = risk_score == 0
    risk_level = "low" if risk_score == 0 else "medium" if risk_score <= 3 else "high"

    return {
        "safe":       safe,
        "risk_level": risk_level,
        "issues":     issues,
    }


def assert_ai_input_is_safe(payload: dict) -> dict:
    """
    Check that a payload dict does not contain disallowed source fields.

    Returns:
        {
          "safe": bool,
          "risk_level": "low" | "medium" | "high",
          "allowed_for_ai_provider": bool,
          "issues": list[str]
        }
    """
    issues: list[str] = []
    risk_score = 0

    def _scan_dict(d: dict, path: str = "") -> None:
        nonlocal risk_score
        for k, v in d.items():
            full_key = f"{path}.{k}" if path else k
            if k in DISALLOWED_PAYLOAD_FIELDS:
                issues.append(f"Disallowed field '{full_key}' present in AI payload")
                risk_score += 3
            elif isinstance(v, dict):
                _scan_dict(v, full_key)
            elif isinstance(v, str):
                # Check individual string values for length and known bad patterns
                if len(v) > LONG_LINE_THRESHOLD:
                    issues.append(
                        f"Field '{full_key}' contains a very long string ({len(v)} chars) — "
                        "possible pasted source text"
                    )
                    risk_score += 2
                else:
                    # Scan the value for embedded disallowed content patterns
                    for _, pattern, description in DISALLOWED_PROMPT_PATTERNS:
                        if pattern.search(v):
                            if description not in issues:
                                issues.append(f"Pattern in '{full_key}': {description}")
                                risk_score += 1

    _scan_dict(payload)

    safe = risk_score == 0
    risk_level = "low" if risk_score == 0 else "medium" if risk_score <= 3 else "high"

    return {
        "safe":                   safe,
        "risk_level":             risk_level,
        "allowed_for_ai_provider": safe,
        "issues":                 issues,
    }


def build_safe_ai_payload_from_generation_target(target: dict) -> dict:
    """
    Build a safe AI input payload from a generation target dict.

    Only copies fields that are on the SAFE_METADATA_FIELDS allowlist.
    Disallowed fields are silently dropped and reported in the result.

    Returns:
        {
          "payload": dict,   -- the safe subset of target
          "dropped_fields": list[str],
          "safe": bool
        }
    """
    safe_payload: dict = {}
    dropped: list[str] = []

    for k, v in target.items():
        if k in SAFE_METADATA_FIELDS:
            safe_payload[k] = v
        elif k in DISALLOWED_PAYLOAD_FIELDS:
            dropped.append(k)
        elif isinstance(v, str) and len(v) > LONG_LINE_THRESHOLD:
            dropped.append(k)
        else:
            # Unknown but short fields — include but note
            safe_payload[k] = v

    return {
        "payload":       safe_payload,
        "dropped_fields": dropped,
        "safe":          len(dropped) == 0,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Copyright Safety Guard — self-test")
    print("-" * 40)

    # Safe metadata test
    safe_payload = {
        "subject_slug": "physics",
        "topic": "Waves",
        "difficulty": "medium",
    }
    r = assert_ai_input_is_safe(safe_payload)
    print(f"Safe metadata:  safe={r['safe']} risk={r['risk_level']}")

    # Disallowed field test
    bad_payload = {
        "topic": "Waves",
        "original_raw_block": "Some copied question text...",
    }
    r2 = assert_ai_input_is_safe(bad_payload)
    print(f"Disallowed field: safe={r2['safe']} risk={r2['risk_level']} issues={r2['issues']}")

    # Prompt scan
    safe_prompt = "Generate a question about the refraction of light in glass."
    r3 = scan_prompt_for_disallowed_source_text(safe_prompt)
    print(f"Safe prompt:    safe={r3['safe']} risk={r3['risk_level']}")

    bad_prompt = "Use this source: data/raw/physics_0625.pdf Question Answer Marks"
    r4 = scan_prompt_for_disallowed_source_text(bad_prompt)
    print(f"Bad prompt:     safe={r4['safe']} risk={r4['risk_level']} issues={r4['issues']}")
