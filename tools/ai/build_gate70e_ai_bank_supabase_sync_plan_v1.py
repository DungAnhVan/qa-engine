"""
Gate 70E -- Build AI Bank Supabase Sync Plan v1

Validates Gate 70D local package and builds a Supabase sync plan.
Does NOT connect to Supabase. Does NOT write any data.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate70e_ai_bank_supabase_sync_plan_v1.py

Output:
  data/ai/supabase_sync/gate70e_ai_bank_supabase_sync_plan_v1.json
  data/diagnostics/gate70e_ai_bank_supabase_sync_plan_report_v1.json
"""

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PUB_DIR     = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1"
PUBLISH_PKG = PUB_DIR / "publish_package_v1.json"
STUDENT_PAY = PUB_DIR / "student_resource_payload_v1.json"
TEACHER_PAY = PUB_DIR / "teacher_resource_payload_v1.json"

SYNC_DIR    = ROOT / "data" / "ai" / "supabase_sync"
PLAN_FILE   = SYNC_DIR / "gate70e_ai_bank_supabase_sync_plan_v1.json"
REPORT_FILE = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_sync_plan_report_v1.json"

TARGET_PACKAGE_KEY = "quanta_aptus_gate70e_ai_bank_package_v1"
SUBJECT_SLUG       = "physics_0625"

COPYRIGHT_PATTERNS = ["UCLES", "Cambridge International", "Cambridge Assessment",
                      "Question Answer Marks", "original_raw_block", "data/raw/"]
SECRET_PATTERNS    = ["sk-", "sk-ant-", "SUPABASE_SERVICE_ROLE_KEY",
                      "supabase_service_role", "NEXT_PUBLIC_SUPABASE_SERVICE"]

print("Gate 70E -- Build AI Bank Supabase Sync Plan v1")
print("=" * 60)

issues: list[str] = []

# ── Validate Gate 70D local package ────────────────────────────────────────
if not PUBLISH_PKG.exists():
    print("ERROR: Gate 70D publish_package_v1.json not found. Run Gate 70D first.")
    sys.exit(1)

pkg = json.loads(PUBLISH_PKG.read_text(encoding="utf-8"))

if pkg.get("status") != "published_local_not_active":
    issues.append(f"status must be published_local_not_active, got {pkg.get('status')}")
if pkg.get("active_content") is not False:
    issues.append("active_content must be false")
if pkg.get("teacher_final_approval") is not True:
    issues.append("teacher_final_approval must be true")
if pkg.get("supabase_write_performed") is not False:
    issues.append("supabase_write_performed must be false (Gate 70D does not write Supabase)")
if not STUDENT_PAY.exists():
    issues.append("student_resource_payload_v1.json missing")
if not TEACHER_PAY.exists():
    issues.append("teacher_resource_payload_v1.json missing")

pkg_raw = json.dumps(pkg)
if any(p in pkg_raw for p in COPYRIGHT_PATTERNS):
    issues.append("copyright pattern detected in Gate 70D package")
if any(p in pkg_raw for p in SECRET_PATTERNS):
    issues.append("secret pattern detected in Gate 70D package")

if issues:
    print("Gate 70D validation failed:")
    for iss in issues:
        print(f"  ! {iss}")
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps({"status": "failed", "issues": issues, "sync_plan_created": False}, indent=2), encoding="utf-8")
    sys.exit(1)

resources: list[dict] = pkg.get("resources", [])
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(f"Gate 70D package validated: {len(resources)} resource(s)")

# ── Build operations ────────────────────────────────────────────────────────
operations: list[dict] = []

operations.append({
    "op":           "upsert_subject_if_needed",
    "table":        "subjects",
    "subject_slug": SUBJECT_SLUG,
    "fields": {
        "board":          "cambridge",
        "level":          "igcse",
        "subject_slug":   SUBJECT_SLUG,
        "subject_name":   "Physics",
        "syllabus_code":  "0625",
        "adapter_name":   "physics_0625_adapter_v1",
        "adapter_status": "full_adapter",
        "is_active":      True,
    },
    "note": "Upsert physics_0625 subject if not present; skip if exists",
})

for r in resources:
    rid = r.get("resource_id", "")
    operations.append({
        "op":           "upsert_resource",
        "table":        "resources",
        "resource_key": rid,
        "fields": {
            "resource_key":           rid,
            "title":                  r.get("title", ""),
            "topic":                  r.get("topic", ""),
            "subtopic":               r.get("subtopic", ""),
            "skill_type":             r.get("skill_name", ""),
            "resource_type":          r.get("resource_type", ""),
            "difficulty":             r.get("difficulty", "unknown"),
            "estimated_time_minutes": r.get("estimated_time_minutes", 0),
            "student_prompt":         r.get("student_prompt", ""),
            "worked_solution":        r.get("answer_key", ""),
            "marking_guidance":       json.dumps(r.get("marking_rubric", [])),
            "teacher_notes":          r.get("teacher_notes", ""),
            "originality_statement":  "AI generated original content — no Cambridge source text",
            "copyright_status":       "original_generated",
            "publish_status":         "approved",
            "needs_human_review":     False,
        },
        "note": "Upsert resource by resource_key — no delete, no overwrite of other resources",
    })

operations.append({
    "op":          "upsert_resource_package",
    "table":       "resource_packages",
    "package_key": TARGET_PACKAGE_KEY,
    "active":      False,
    "fields": {
        "package_key":    TARGET_PACKAGE_KEY,
        "version":        1,
        "title":          "Quanta Aptus Gate 70E AI Bank Package v1",
        "status":         "draft",
        "resource_count": len(resources),
    },
    "note": "status=draft — NOT active. active_switch_allowed=false in Gate 70E.",
})

for i, r in enumerate(resources):
    rid = r.get("resource_id", "")
    operations.append({
        "op":           "upsert_resource_package_item",
        "table":        "resource_package_items",
        "resource_key": rid,
        "package_key":  TARGET_PACKAGE_KEY,
        "fields":       {"sort_order": i, "visibility": "student"},
        "note":         "Link resource to package",
    })

plan = {
    "sync_plan_id":          "quanta_aptus_gate70e_ai_bank_supabase_sync_plan_v1",
    "version":               "0.1.0",
    "created_at":            now,
    "source_package_id":     pkg.get("package_id"),
    "target_package_key":    TARGET_PACKAGE_KEY,
    "source_package_path":   str(PUBLISH_PKG.relative_to(ROOT)),
    "dry_run_default":       True,
    "active_switch_allowed": False,
    "target_active":         False,
    "supabase_write_required_for_execute": True,
    "existing_active_package_preserve_required": True,
    "resource_count":        len(resources),
    "operation_count":       len(operations),
    "operations":            operations,
    "safety": {
        "no_delete":                True,
        "no_active_switch":         True,
        "no_raw_source_text":       True,
        "no_api_keys":              True,
        "no_service_role_in_outputs": True,
        "no_schema_change":         True,
    },
}

SYNC_DIR.mkdir(parents=True, exist_ok=True)
PLAN_FILE.write_text(json.dumps(plan, indent=2), encoding="utf-8")

print(f"Target package key: {TARGET_PACKAGE_KEY}")
print(f"Operations:         {len(operations)}")
for op in operations:
    marker = op.get("resource_key") or op.get("package_key") or op.get("subject_slug", "")
    print(f"  [{op['op']}] {marker}")

report = {
    "gate":               "70E",
    "status":             "passed",
    "sync_plan_created":  True,
    "valid":              True,
    "source_package_id":  pkg.get("package_id"),
    "target_package_key": TARGET_PACKAGE_KEY,
    "resource_count":     len(resources),
    "operation_count":    len(operations),
    "dry_run_default":    True,
    "active_switch_allowed": False,
    "plan_file":          str(PLAN_FILE.relative_to(ROOT)),
    "issues":             [],
}
REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nPlan:   {PLAN_FILE.relative_to(ROOT)}")
print(f"Report: {REPORT_FILE.relative_to(ROOT)}")
print("Status: PASSED")
sys.exit(0)
