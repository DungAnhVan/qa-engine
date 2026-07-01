"""
Gate 69G -- Build AI Supabase Sync Plan v1

Reads the Gate 69F locally published AI package and produces a dry-run
sync plan describing every Supabase upsert operation that would be needed.
Does NOT connect to Supabase and does NOT write any data.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_supabase_sync_plan_v1.py

Output:
  data/ai/supabase_sync/ai_supabase_sync_plan_v1.json
  data/diagnostics/ai_supabase_sync_plan_report_v1.json
"""

import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PUBLISHED_DIR  = ROOT / "data" / "ai" / "published" / "ai_resource_package_v1"
PUBLISH_PKG    = PUBLISHED_DIR / "publish_package_v1.json"
STUDENT_PAY    = PUBLISHED_DIR / "student_resource_payload_v1.json"
TEACHER_PAY    = PUBLISHED_DIR / "teacher_resource_payload_v1.json"

SYNC_DIR       = ROOT / "data" / "ai" / "supabase_sync"
PLAN_FILE      = SYNC_DIR / "ai_supabase_sync_plan_v1.json"
REPORT_FILE    = ROOT / "data" / "diagnostics" / "ai_supabase_sync_plan_report_v1.json"

COPYRIGHT_PATTERNS = ["UCLES", "Cambridge International", "Cambridge Assessment",
                      "Question Answer Marks", "original_raw_block", "data/raw/"]

SECRET_PATTERNS = ["sk-", "sk-ant-", "SUPABASE_SERVICE_ROLE_KEY",
                   "supabase_service_role", "NEXT_PUBLIC_SUPABASE_SERVICE_ROLE"]


def _has_copyright(text: str) -> bool:
    return any(p in text for p in COPYRIGHT_PATTERNS)


def _has_secret(text: str) -> bool:
    return any(p in text for p in SECRET_PATTERNS)


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def validate_local_package() -> tuple[bool, list[str]]:
    issues: list[str] = []
    if not PUBLISH_PKG.exists():
        issues.append("publish_package_v1.json missing — run Gate 69F first")
        return False, issues
    pkg = load_json(PUBLISH_PKG)
    if not pkg:
        issues.append("publish_package_v1.json unreadable")
        return False, issues
    if pkg.get("status") != "published_local_not_active":
        issues.append(f"status must be 'published_local_not_active', got '{pkg.get('status')}'")
    if pkg.get("active_content") is not False:
        issues.append("active_content must be false")
    if pkg.get("teacher_final_approval") is not True:
        issues.append("teacher_final_approval must be true")
    raw = json.dumps(pkg)
    if _has_copyright(raw):
        issues.append("copyright pattern detected in package")
    if _has_secret(raw):
        issues.append("secret pattern detected in package")
    if not STUDENT_PAY.exists():
        issues.append("student_resource_payload_v1.json missing")
    if not TEACHER_PAY.exists():
        issues.append("teacher_resource_payload_v1.json missing")
    return len(issues) == 0, issues


def build_sync_plan(pkg: dict) -> dict:
    now       = datetime.datetime.now(datetime.timezone.utc).isoformat()
    resources = pkg.get("resources", [])
    package_id = pkg.get("package_id", "quanta_aptus_ai_resource_package_v1")

    # Determine subject slug from first resource or fallback
    first = resources[0] if resources else {}
    topic = first.get("topic", "")
    # AI resources for physics → use physics_0625 subject if it exists
    # If not, upsert as ai_generated subject
    subject_slug = "physics_0625"

    operations: list[dict] = []

    # Op 1: upsert subject (if needed — only if physics_0625 doesn't exist)
    operations.append({
        "op":          "upsert_subject_if_needed",
        "table":       "subjects",
        "subject_slug": subject_slug,
        "fields": {
            "board":         "cambridge",
            "level":         "igcse",
            "subject_slug":  subject_slug,
            "subject_name":  "Physics",
            "syllabus_code": "0625",
            "adapter_name":  "physics_0625_adapter_v1",
            "adapter_status": "full_adapter",
            "is_active":     True,
        },
        "note": "Upsert physics_0625 subject if not present; skip if exists",
    })

    # Op 2+: upsert each resource
    for r in resources:
        rid   = r.get("resource_id", "")
        rubric_json = json.dumps(r.get("marking_rubric", []))
        operations.append({
            "op":          "upsert_resource",
            "table":       "resources",
            "resource_key": rid,
            "fields": {
                "resource_key":          rid,
                "title":                 r.get("title", ""),
                "topic":                 r.get("topic", ""),
                "subtopic":              r.get("subtopic", ""),
                "skill_type":            r.get("skill_name", ""),
                "resource_type":         r.get("resource_type", ""),
                "difficulty":            r.get("difficulty", "unknown"),
                "estimated_time_minutes": r.get("estimated_time_minutes", 0),
                "student_prompt":        r.get("student_prompt", ""),
                "worked_solution":       r.get("answer_key", ""),
                "marking_guidance":      rubric_json,
                "teacher_notes":         r.get("teacher_notes", ""),
                "originality_statement": "AI generated original content — no Cambridge source text",
                "copyright_status":      "original_generated",
                "publish_status":        "approved",
                "needs_human_review":    False,
            },
            "note": "Upsert resource by resource_key — no delete, no overwrite of other resources",
        })

    # Package upsert
    operations.append({
        "op":           "upsert_resource_package",
        "table":        "resource_packages",
        "package_key":  package_id,
        "fields": {
            "package_key":    package_id,
            "version":        1,
            "title":          "Quanta Aptus AI Resource Package v1",
            "status":         "draft",
            "resource_count": len(resources),
        },
        "note": "status=draft — NOT active. Do not set active without explicit --activate flag.",
    })

    # Package items
    for i, r in enumerate(resources):
        rid = r.get("resource_id", "")
        operations.append({
            "op":          "upsert_resource_package_item",
            "table":       "resource_package_items",
            "resource_key": rid,
            "package_key":  package_id,
            "fields": {
                "sort_order": i,
                "visibility": "student",
            },
            "note": "Link resource to package — unique(package_id, resource_id)",
        })

    return {
        "sync_plan_id":           "quanta_aptus_ai_supabase_sync_plan_v1",
        "version":                "0.1.0",
        "created_at":             now,
        "package_id":             package_id,
        "source_package_path":    str(PUBLISH_PKG.relative_to(ROOT)),
        "subject_slug":           subject_slug,
        "dry_run_default":        True,
        "active_switch_default":  False,
        "supabase_write_required": True,
        "resource_count":         len(resources),
        "operation_count":        len(operations),
        "operations":             operations,
        "safety": {
            "no_delete":          True,
            "no_active_switch":   True,
            "no_raw_source_text": True,
            "no_api_keys":        True,
            "no_schema_change":   True,
        },
    }


def main():
    print("Gate 69G -- Build AI Supabase Sync Plan v1")
    print("-" * 55)

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    # Validate
    valid, issues = validate_local_package()
    if not valid:
        print("VALIDATION FAILED:")
        for i in issues:
            print(f"  ! {i}")
        report = {
            "status": "failed", "valid": False, "issues": issues,
            "sync_plan_created": False,
        }
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise SystemExit(1)

    pkg = json.loads(PUBLISH_PKG.read_text(encoding="utf-8"))

    # Build plan
    plan = build_sync_plan(pkg)
    PLAN_FILE.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    now = plan["created_at"]
    print(f"  + package_id:      {plan['package_id']}")
    print(f"  + resource_count:  {plan['resource_count']}")
    print(f"  + operations:      {plan['operation_count']}")
    print(f"  + dry_run_default: {plan['dry_run_default']}")
    print(f"  + active_switch:   {plan['active_switch_default']}")
    print(f"  + plan:            {PLAN_FILE}")

    for op in plan["operations"]:
        print(f"    [{op['op']}] {op.get('resource_key') or op.get('package_key') or op.get('subject_slug', '')}")

    report = {
        "gate":              "69G",
        "status":            "passed",
        "sync_plan_created": True,
        "valid":             True,
        "package_id":        plan["package_id"],
        "resource_count":    plan["resource_count"],
        "operation_count":   plan["operation_count"],
        "dry_run_default":   plan["dry_run_default"],
        "active_switch_default": plan["active_switch_default"],
        "plan_file":         str(PLAN_FILE.relative_to(ROOT)),
        "generated_at":      now,
        "issues":            [],
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nStatus: passed")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
