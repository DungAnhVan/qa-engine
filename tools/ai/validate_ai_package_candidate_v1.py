"""
Gate 69E -- Validate AI Package Candidate v1

Validates a package candidate JSON file for correctness, policy compliance,
and absence of raw Cambridge source / API key patterns.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\validate_ai_package_candidate_v1.py \\
      data\\ai\\package_candidates\\ai_resource_package_candidate_v1.json

Output:
  data/diagnostics/ai_package_candidate_validation_report_v1.json
"""

import json
import re
import sys
import datetime
import argparse
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "ai_package_candidate_validation_report_v1.json"

REQUIRED_RESOURCE_FIELDS = {
    "resource_id", "resource_type", "title", "topic",
    "skill_name", "skill_type", "difficulty",
    "student_prompt", "answer_key", "marking_rubric",
    "safety_declaration", "provenance",
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
    ("blank_page",          re.compile(r'BLANK PAGE', re.IGNORECASE)),
]

API_KEY_PATTERNS: list[re.Pattern] = [
    re.compile(r'sk-[A-Za-z0-9]{20,}'),
    re.compile(r'sk-ant-[A-Za-z0-9\-_]{30,}'),
    re.compile(r'eyJ[A-Za-z0-9+/=_-]{100,}'),
]


def validate_package_candidate(pkg_path: Path) -> dict:
    now    = datetime.datetime.now(datetime.timezone.utc).isoformat()
    issues: list[str] = []

    if not pkg_path.exists():
        return {
            "valid":  False,
            "status": "failed",
            "issues": [f"Package candidate not found: {pkg_path}"],
            "generated_at": now,
        }

    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "valid":  False,
            "status": "failed",
            "issues": [f"JSON parse error: {exc}"],
            "generated_at": now,
        }

    # ── Package-level policy checks ───────────────────────────────────────────
    if pkg.get("status") != "draft_package_candidate":
        issues.append(f"status must be 'draft_package_candidate', got {pkg.get('status')!r}")

    if pkg.get("auto_publish_enabled") is True:
        issues.append("CRITICAL: auto_publish_enabled is True — must be False")

    if pkg.get("teacher_final_publish_required") is not True:
        issues.append("teacher_final_publish_required must be True")

    if pkg.get("supabase_write_performed") is True:
        issues.append("supabase_write_performed must be False")

    resources = pkg.get("resources", [])
    if not isinstance(resources, list) or len(resources) == 0:
        issues.append("resources must be a non-empty list")

    # ── Per-resource checks ────────────────────────────────────────────────────
    resource_ids: set[str] = set()
    resources_valid = 0
    resource_issues: list[dict] = []

    for i, r in enumerate(resources):
        r_issues: list[str] = []
        rid = r.get("resource_id", f"<no id at index {i}>")

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

        # Safety declaration
        decl = r.get("safety_declaration", {})
        if not isinstance(decl, dict):
            r_issues.append("safety_declaration must be a dict")
        else:
            if decl.get("original_content") is not True:
                r_issues.append("safety_declaration.original_content must be True")

        # Provenance
        prov = r.get("provenance", {})
        if not isinstance(prov, dict):
            r_issues.append("provenance must be a dict")
        else:
            if prov.get("origin") != "ai_generated":
                r_issues.append(f"provenance.origin must be 'ai_generated', got {prov.get('origin')!r}")
            if prov.get("approved_by_teacher_review") is not True:
                r_issues.append("provenance.approved_by_teacher_review must be True")
            if prov.get("no_raw_source_text_used") is not True:
                r_issues.append("provenance.no_raw_source_text_used must be True")

        # Unique resource_id
        if rid in resource_ids:
            r_issues.append(f"Duplicate resource_id: {rid!r}")
        else:
            resource_ids.add(rid)

        # Copyright / source scan on resource JSON
        r_str = json.dumps(r)
        for label, pat in BANNED_CONTENT_PATTERNS:
            if pat.search(r_str):
                r_issues.append(f"Banned content pattern ({label}): {pat.pattern[:50]}")

        for pat in API_KEY_PATTERNS:
            if pat.search(r_str):
                r_issues.append("API key pattern detected in resource content")

        if r_issues:
            resource_issues.append({"resource_id": rid, "issues": r_issues})
            issues.extend([f"resource[{i}] ({rid}): {iss}" for iss in r_issues])
        else:
            resources_valid += 1

    # ── Student/teacher payload derivability check ────────────────────────────
    for r in resources:
        if not r.get("student_prompt"):
            issues.append(f"Cannot derive student payload: {r.get('resource_id')} has no student_prompt")
        if not r.get("answer_key") and not r.get("marking_rubric"):
            issues.append(f"Cannot derive teacher payload: {r.get('resource_id')} has no answer_key or rubric")

    valid  = len(issues) == 0
    status = "passed" if valid else "failed"

    return {
        "valid":                        valid,
        "status":                       status,
        "package_candidate_id":         pkg.get("package_candidate_id", "unknown"),
        "package_status":               pkg.get("status"),
        "auto_publish_enabled":         pkg.get("auto_publish_enabled"),
        "teacher_final_publish_required": pkg.get("teacher_final_publish_required"),
        "supabase_write_performed":     pkg.get("supabase_write_performed"),
        "resource_count":               len(resources),
        "resources_valid":              resources_valid,
        "resources_failed":             len(resources) - resources_valid,
        "resource_issues":              resource_issues,
        "issues":                       issues,
        "generated_at":                 now,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description="Gate 69E -- Validate AI Package Candidate")
    parser.add_argument("package_file", help="Path to the package candidate JSON")
    args   = parser.parse_args()

    pkg_path = Path(args.package_file)
    if not pkg_path.is_absolute():
        pkg_path = ROOT / pkg_path

    print("Gate 69E -- Validate AI Package Candidate")
    print(f"Package: {pkg_path}")
    print("-" * 55)

    result = validate_package_candidate(pkg_path)

    sym = lambda ok: "+" if ok else "!"
    print(f"  [{sym(result['valid'])}] valid:                 {result['valid']}")
    print(f"  [{sym(result.get('resource_count', 0) > 0)}] resource_count:        {result.get('resource_count', 0)}")
    print(f"  [{sym(result.get('resources_valid', 0) == result.get('resource_count', 0))}] resources_valid:       {result.get('resources_valid', 0)}/{result.get('resource_count', 0)}")
    print(f"  [{sym(not result.get('auto_publish_enabled'))}] auto_publish_enabled:  {result.get('auto_publish_enabled')}")
    print(f"  [{sym(result.get('teacher_final_publish_required'))}] teacher_final_pub_req: {result.get('teacher_final_publish_required')}")
    print(f"  [{sym(not result.get('supabase_write_performed'))}] supabase_write:        {result.get('supabase_write_performed')}")

    if result.get("issues"):
        print("\n  Issues:")
        for iss in result["issues"][:10]:
            print(f"    ! {iss}")
        if len(result["issues"]) > 10:
            print(f"    ... and {len(result['issues']) - 10} more")

    print(f"\nStatus: {result['status']}")
    OUTPUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Report: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
