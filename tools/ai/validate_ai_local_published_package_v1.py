"""
Gate 69F -- Validate AI Local Published Package v1

Validates a locally published AI package for policy compliance, safety,
and absence of raw Cambridge / API key / service role patterns.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\validate_ai_local_published_package_v1.py \\
      data\\ai\\published\\ai_resource_package_v1\\publish_package_v1.json

Output:
  data/diagnostics/ai_local_published_package_validation_report_v1.json
"""

import json
import re
import sys
import argparse
import datetime
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "ai_local_published_package_validation_report_v1.json"
STUDENT_FILE = ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "student_resource_payload_v1.json"
TEACHER_FILE = ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "teacher_resource_payload_v1.json"

REQUIRED_RESOURCE_FIELDS = {
    "resource_id", "resource_type", "title", "topic",
    "skill_name", "difficulty", "student_prompt",
    "answer_key", "marking_rubric", "safety_declaration", "provenance",
}

BANNED_CONTENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("raw_source_field",    re.compile(r'\boriginal_raw_block\b')),
    ("raw_source_field",    re.compile(r'\bnormalized_raw_block\b')),
    ("mark_scheme_field",   re.compile(r'\bmark_scheme_text\b')),
    ("raw_data_path",       re.compile(r'data[/\\]raw[/\\]')),
    ("cambridge_header",    re.compile(r'Question\s+Answer\s+Marks', re.IGNORECASE)),
    ("cambridge_entity",    re.compile(r'Cambridge\s+(International|Assessment)', re.IGNORECASE)),
    ("ucles",               re.compile(r'\bUCLES\b')),
    ("copyright_notice",    re.compile(r'©\s*Cambridge', re.IGNORECASE)),
]

SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("api_key_openai",   re.compile(r'sk-[A-Za-z0-9]{20,}')),
    ("api_key_anthropic",re.compile(r'sk-ant-[A-Za-z0-9\-_]{30,}')),
    ("jwt_token",        re.compile(r'eyJ[A-Za-z0-9+/=_-]{100,}')),
    ("service_role",     re.compile(r'NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY', re.IGNORECASE)),
    ("service_role_raw", re.compile(r'supabase_service_role', re.IGNORECASE)),
]


def validate_local_published_package(pkg_path: Path) -> dict:
    now    = datetime.datetime.now(datetime.timezone.utc).isoformat()
    issues: list[str] = []

    if not pkg_path.exists():
        return {"valid": False, "status": "failed",
                "issues": [f"Package not found: {pkg_path}"], "generated_at": now}

    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"valid": False, "status": "failed",
                "issues": [f"JSON parse error: {exc}"], "generated_at": now}

    # ── Package-level checks ──────────────────────────────────────────────────
    if pkg.get("status") != "published_local_not_active":
        issues.append(f"status must be 'published_local_not_active', got {pkg.get('status')!r}")

    if pkg.get("active_content") is not False:
        issues.append("CRITICAL: active_content must be False")

    if pkg.get("supabase_write_performed") is True:
        issues.append("CRITICAL: supabase_write_performed must be False")

    if pkg.get("teacher_final_approval") is not True:
        issues.append("teacher_final_approval must be True")

    resources = pkg.get("resources", [])
    if not isinstance(resources, list) or len(resources) == 0:
        issues.append("resources must be a non-empty list")

    # ── Student/teacher payload existence ─────────────────────────────────────
    student_exists = STUDENT_FILE.exists()
    teacher_exists = TEACHER_FILE.exists()
    if not student_exists:
        issues.append(f"Student payload not found: {STUDENT_FILE}")
    if not teacher_exists:
        issues.append(f"Teacher payload not found: {TEACHER_FILE}")

    # ── Per-resource checks ───────────────────────────────────────────────────
    resource_ids: set[str] = set()
    resources_valid = 0
    resource_issues: list[dict] = []

    for i, r in enumerate(resources):
        r_issues: list[str] = []
        rid = r.get("resource_id", f"<no id at {i}>")

        missing = REQUIRED_RESOURCE_FIELDS - set(r.keys())
        if missing:
            r_issues.append(f"Missing fields: {sorted(missing)}")

        if not r.get("student_prompt", "").strip():
            r_issues.append("student_prompt is empty")

        if not r.get("answer_key", "").strip():
            r_issues.append("answer_key is empty")

        rubric = r.get("marking_rubric", [])
        if not isinstance(rubric, list) or len(rubric) == 0:
            r_issues.append("marking_rubric must be a non-empty list")

        decl = r.get("safety_declaration", {})
        if isinstance(decl, dict):
            if decl.get("original_content") is not True:
                r_issues.append("safety_declaration.original_content must be True")
        else:
            r_issues.append("safety_declaration must be a dict")

        prov = r.get("provenance", {})
        if isinstance(prov, dict):
            if prov.get("origin") != "ai_generated":
                r_issues.append(f"provenance.origin must be 'ai_generated'")
            if prov.get("approved_by_teacher_review") is not True:
                r_issues.append("provenance.approved_by_teacher_review must be True")
        else:
            r_issues.append("provenance must be a dict")

        if rid in resource_ids:
            r_issues.append(f"Duplicate resource_id: {rid!r}")
        else:
            resource_ids.add(rid)

        r_str = json.dumps(r)
        for label, pat in BANNED_CONTENT_PATTERNS:
            if pat.search(r_str):
                r_issues.append(f"Banned content ({label}): {pat.pattern[:50]}")
        for label, pat in SECRET_PATTERNS:
            if pat.search(r_str):
                r_issues.append(f"Secret pattern ({label}) in resource")

        if r_issues:
            resource_issues.append({"resource_id": rid, "issues": r_issues})
            issues.extend([f"resource[{i}] ({rid}): {iss}" for iss in r_issues])
        else:
            resources_valid += 1

    # ── Scan full package string for secrets/cambridge ────────────────────────
    full_str = pkg_path.read_text(encoding="utf-8")
    for label, pat in SECRET_PATTERNS:
        if pat.search(full_str):
            issues.append(f"Secret pattern ({label}) in package file")

    valid  = len(issues) == 0
    status = "passed" if valid else "failed"

    return {
        "valid":                        valid,
        "status":                       status,
        "package_id":                   pkg.get("package_id", "unknown"),
        "package_status":               pkg.get("status"),
        "active_content":               pkg.get("active_content"),
        "supabase_write_performed":     pkg.get("supabase_write_performed"),
        "teacher_final_approval":       pkg.get("teacher_final_approval"),
        "resource_count":               len(resources),
        "resources_valid":              resources_valid,
        "resources_failed":             len(resources) - resources_valid,
        "student_payload_exists":       student_exists,
        "teacher_payload_exists":       teacher_exists,
        "resource_issues":              resource_issues,
        "issues":                       issues,
        "generated_at":                 now,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description="Gate 69F -- Validate AI Local Published Package")
    parser.add_argument("package_file", help="Path to publish_package_v1.json")
    args   = parser.parse_args()

    pkg_path = Path(args.package_file)
    if not pkg_path.is_absolute():
        pkg_path = ROOT / pkg_path

    print("Gate 69F -- Validate AI Local Published Package")
    print(f"Package: {pkg_path}")
    print("-" * 55)

    result = validate_local_published_package(pkg_path)

    sym = lambda ok: "+" if ok else "!"
    print(f"  [{sym(result['valid'])}] valid:                 {result['valid']}")
    print(f"  [{sym(result.get('resource_count', 0) > 0)}] resource_count:        {result.get('resource_count', 0)}")
    print(f"  [{sym(result.get('resources_valid', 0) == result.get('resource_count', 0))}] resources_valid:       {result.get('resources_valid')}/{result.get('resource_count')}")
    print(f"  [{sym(not result.get('active_content'))}] active_content:        {result.get('active_content')}")
    print(f"  [{sym(not result.get('supabase_write_performed'))}] supabase_write:        {result.get('supabase_write_performed')}")
    print(f"  [{sym(result.get('teacher_final_approval'))}] teacher_final_approval:{result.get('teacher_final_approval')}")
    print(f"  [{sym(result.get('student_payload_exists'))}] student_payload_exists:{result.get('student_payload_exists')}")
    print(f"  [{sym(result.get('teacher_payload_exists'))}] teacher_payload_exists:{result.get('teacher_payload_exists')}")

    if result.get("issues"):
        print("\n  Issues:")
        for iss in result["issues"][:10]:
            print(f"    ! {iss}")

    print(f"\nStatus: {result['status']}")
    OUTPUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Report: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
