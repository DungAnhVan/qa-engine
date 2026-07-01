"""
Gate 69C -- Validate AI Generated Batch v1

Validates a generated batch JSON file for required fields, unique IDs,
safety declarations, and absence of raw Cambridge source patterns.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\validate_ai_generated_batch_v1.py \\
      data\\ai\\generated_batches\\gate69c_sample_generated_batch_v1.json

Output:
  data/diagnostics/ai_generated_batch_validation_report_v1.json
"""

import json
import re
import sys
import datetime
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "ai_generated_batch_validation_report_v1.json"

# ---------------------------------------------------------------------------
# Copyright / safety patterns that must NOT appear in generated content
# ---------------------------------------------------------------------------

BANNED_CONTENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("raw_source_field",     re.compile(r'\boriginal_raw_block\b')),
    ("raw_source_field",     re.compile(r'\bnormalized_raw_block\b')),
    ("mark_scheme_field",    re.compile(r'\bmark_scheme_text\b')),
    ("raw_data_path",        re.compile(r'data[/\\]raw[/\\]')),
    ("cambridge_header",     re.compile(r'Question\s+Answer\s+Marks', re.IGNORECASE)),
    ("cambridge_entity",     re.compile(r'Cambridge\s+(International|Assessment)', re.IGNORECASE)),
    ("ucles",                re.compile(r'\bUCLES\b')),
    ("copyright_notice",     re.compile(r'©\s*Cambridge', re.IGNORECASE)),
    ("exam_footer",          re.compile(r'BLANK PAGE', re.IGNORECASE)),
]

# API key patterns must not appear in generated content
API_KEY_PATTERNS: list[re.Pattern] = [
    re.compile(r'sk-[A-Za-z0-9]{20,}'),
    re.compile(r'sk-ant-[A-Za-z0-9\-_]{30,}'),
    re.compile(r'eyJ[A-Za-z0-9+/=_-]{100,}'),
]

# Required top-level fields for each resource
REQUIRED_RESOURCE_FIELDS = {
    "resource_id",
    "resource_type",
    "student_prompt",
    "answer_key",
    "marking_rubric",
    "safety_declaration",
}

REQUIRED_BATCH_FIELDS = {
    "batch_id",
    "generated_at",
    "provider",
    "dry_run",
    "resources",
}

# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_batch(batch_path: Path) -> dict:
    """
    Validate a generated batch file.

    Returns a validation result dict.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    issues: list[str] = []

    # ── File existence ────────────────────────────────────────────────────────
    if not batch_path.exists():
        return {
            "valid":           False,
            "batch_file":      str(batch_path),
            "issues":          [f"Batch file not found: {batch_path}"],
            "resource_count":  0,
            "resources_valid": 0,
            "generated_at":    now,
        }

    # ── Load JSON ─────────────────────────────────────────────────────────────
    try:
        batch = json.loads(batch_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "valid":           False,
            "batch_file":      str(batch_path),
            "issues":          [f"JSON parse error: {exc}"],
            "resource_count":  0,
            "resources_valid": 0,
            "generated_at":    now,
        }

    # ── Batch-level fields ────────────────────────────────────────────────────
    missing_batch = REQUIRED_BATCH_FIELDS - set(batch.keys())
    if missing_batch:
        issues.append(f"Batch missing required fields: {sorted(missing_batch)}")

    resources = batch.get("resources", [])
    if not isinstance(resources, list):
        issues.append("'resources' is not a list")
        resources = []

    if len(resources) == 0:
        issues.append("Batch contains no resources")

    # ── Teacher approval / no auto-publish ───────────────────────────────────
    if batch.get("auto_publish_enabled") is True:
        issues.append("CRITICAL: auto_publish_enabled is True — must be False")
    if batch.get("teacher_approval_required") is not True:
        issues.append("teacher_approval_required must be True")

    # ── Per-resource validation ───────────────────────────────────────────────
    resource_ids: set[str] = set()
    resources_valid = 0
    resource_issues: list[dict] = []

    for i, resource in enumerate(resources):
        r_issues: list[str] = []
        resource_id = resource.get("resource_id", f"<no id at index {i}>")

        # Required fields
        missing_fields = REQUIRED_RESOURCE_FIELDS - set(resource.keys())
        if missing_fields:
            r_issues.append(f"Missing fields: {sorted(missing_fields)}")

        # Non-empty student_prompt
        student_prompt = resource.get("student_prompt", "")
        if not student_prompt or not str(student_prompt).strip():
            r_issues.append("student_prompt is empty")

        # Non-empty answer_key
        answer_key = resource.get("answer_key", "")
        if not answer_key or not str(answer_key).strip():
            r_issues.append("answer_key is empty")

        # marking_rubric is a non-empty list
        rubric = resource.get("marking_rubric", [])
        if not isinstance(rubric, list) or len(rubric) == 0:
            r_issues.append("marking_rubric must be a non-empty list")

        # safety_declaration all True
        decl = resource.get("safety_declaration", {})
        if not isinstance(decl, dict):
            r_issues.append("safety_declaration must be a dict")
        else:
            for key in ("original_content", "no_raw_source_text_used", "no_mark_scheme_copied"):
                if decl.get(key) is not True:
                    r_issues.append(f"safety_declaration.{key} is not True")

        # Unique resource_id
        if resource_id in resource_ids:
            r_issues.append(f"Duplicate resource_id: {resource_id!r}")
        else:
            resource_ids.add(resource_id)

        # Copyright / source text scan
        resource_str = json.dumps(resource)
        for label, pattern in BANNED_CONTENT_PATTERNS:
            if pattern.search(resource_str):
                r_issues.append(f"Banned content pattern ({label}): {pattern.pattern[:50]}")

        # API key scan
        for pattern in API_KEY_PATTERNS:
            if pattern.search(resource_str):
                r_issues.append(f"API key pattern detected in resource content")

        if r_issues:
            resource_issues.append({"resource_id": resource_id, "issues": r_issues})
            issues.extend([f"resource[{i}] ({resource_id}): {iss}" for iss in r_issues])
        else:
            resources_valid += 1

    valid = len(issues) == 0
    status = "passed" if valid else "failed" if issues else "passed"

    return {
        "valid":                valid,
        "status":               status,
        "batch_file":           str(batch_path.relative_to(ROOT) if batch_path.is_absolute() else batch_path),
        "batch_id":             batch.get("batch_id", "unknown"),
        "provider":             batch.get("provider", "unknown"),
        "dry_run":              batch.get("dry_run"),
        "resource_count":       len(resources),
        "resources_valid":      resources_valid,
        "resources_failed":     len(resources) - resources_valid,
        "resource_issues":      resource_issues,
        "teacher_approval_required": batch.get("teacher_approval_required"),
        "auto_publish_enabled": batch.get("auto_publish_enabled"),
        "issues":               issues,
        "generated_at":         now,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description="Gate 69C -- Validate AI Generated Batch")
    parser.add_argument("batch_file", help="Path to the batch JSON file to validate")
    args = parser.parse_args()

    batch_path = Path(args.batch_file)
    if not batch_path.is_absolute():
        batch_path = ROOT / batch_path

    print("Gate 69C -- AI Generated Batch Validator")
    print(f"Batch file: {batch_path}")
    print("-" * 55)

    result = validate_batch(batch_path)

    status_sym = "+" if result["valid"] else "!"
    print(f"  [{status_sym}] valid:            {result['valid']}")
    print(f"  [{'+'  if result.get('resource_count', 0) > 0 else '!'}] resource_count:   {result.get('resource_count', 0)}")
    print(f"  [{'+'  if result.get('resources_valid', 0) == result.get('resource_count', 0) else '!'}] resources_valid:  {result.get('resources_valid', 0)}/{result.get('resource_count', 0)}")
    print(f"  [{'+'  if result.get('teacher_approval_required') else '!'}] teacher_approval_required: {result.get('teacher_approval_required')}")
    print(f"  [{'+'  if not result.get('auto_publish_enabled') else '!'}] auto_publish_enabled: {result.get('auto_publish_enabled')}")

    if result.get("issues"):
        print("\n  Issues:")
        for i in result["issues"][:10]:
            print(f"    ! {i}")
        if len(result["issues"]) > 10:
            print(f"    ... and {len(result['issues']) - 10} more")

    print(f"\nStatus: {result.get('status', 'unknown')}")

    OUTPUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Report: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
