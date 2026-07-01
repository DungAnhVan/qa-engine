"""
Gate 69E -- Build AI Approved Package Candidate v1

Reads the approved AI resource candidates (produced by Gate 69D teacher
review flow) and assembles them into a package candidate file.

Only approved items are included. Rejected and needs_revision items are
excluded automatically. No Supabase writes. No AI API calls.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_approved_package_candidate_v1.py

Input:
  data/ai/approved/ai_approved_resource_candidates_v1.json

Output:
  data/ai/package_candidates/ai_resource_package_candidate_v1.json
  data/diagnostics/ai_approved_package_candidate_build_report_v1.json
"""

import json
import sys
import datetime
from pathlib import Path

ROOT            = Path(__file__).resolve().parents[2]
APPROVED_FILE   = ROOT / "data" / "ai" / "approved" / "ai_approved_resource_candidates_v1.json"
PKG_DIR         = ROOT / "data" / "ai" / "package_candidates"
PKG_FILE        = PKG_DIR / "ai_resource_package_candidate_v1.json"
REPORT_FILE     = ROOT / "data" / "diagnostics" / "ai_approved_package_candidate_build_report_v1.json"

REQUIRED_RESOURCE_FIELDS = {
    "resource_id", "resource_type", "title", "topic",
    "skill_name", "skill_type", "difficulty",
    "student_prompt", "answer_key", "marking_rubric",
    "teacher_notes", "safety_declaration",
}


def build_package_candidate() -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # ── Load approved candidates ───────────────────────────────────────────────
    if not APPROVED_FILE.exists():
        return {
            "ok":    False,
            "error": (
                f"Approved candidates file not found: {APPROVED_FILE}\n"
                "Run Gate 69D test first:\n"
                "  .venv-ingest\\Scripts\\python.exe "
                "tools\\ai\\test_gate69d_ai_teacher_review_v1.py"
            ),
            "generated_at": now,
        }

    try:
        approved_data = json.loads(APPROVED_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"JSON parse error: {exc}", "generated_at": now}

    raw_resources = approved_data.get("resources", [])

    # ── Filter: only approved items ────────────────────────────────────────────
    resources = []
    skipped: list[str] = []
    issues: list[str] = []

    for r in raw_resources:
        decision = (r.get("review_decision") or r.get("review_status") or "").lower()
        if decision not in ("approve", "approved"):
            skipped.append(f"{r.get('resource_id')} — skipped (decision={decision!r})")
            continue

        # Validate required fields
        missing = REQUIRED_RESOURCE_FIELDS - set(r.keys())
        if missing:
            issues.append(f"{r.get('resource_id')} — missing fields: {sorted(missing)}")
            continue

        # Build provenance
        provenance = {
            "origin":                    "ai_generated",
            "approved_by_teacher_review": True,
            "reviewer_id":               r.get("reviewer_id", "local_demo_teacher"),
            "review_decision":           "approve",
            "decision_at":               r.get("decision_at", now),
            "source_queue":              approved_data.get("source_queue", ""),
            "no_raw_source_text_used":   True,
        }

        pkg_resource = {
            "resource_id":          r["resource_id"],
            "resource_type":        r.get("resource_type", "question"),
            "title":                r.get("title", ""),
            "topic":                r.get("topic", ""),
            "subtopic":             r.get("subtopic", ""),
            "skill_name":           r.get("skill_name", ""),
            "skill_type":           r.get("skill_type", ""),
            "difficulty":           r.get("difficulty", ""),
            "estimated_time_minutes": r.get("estimated_time_minutes", 0),
            "student_prompt":       r["student_prompt"],
            "student_instructions": r.get("student_instructions", "Show all working."),
            "answer_key":           r["answer_key"],
            "marking_rubric":       r.get("marking_rubric", []),
            "teacher_notes":        r.get("teacher_notes", ""),
            "safety_declaration":   r["safety_declaration"],
            "provenance":           provenance,
        }
        resources.append(pkg_resource)

    if issues:
        return {"ok": False, "error": "Resource validation failed", "issues": issues, "generated_at": now}

    package = {
        "package_candidate_id":          "quanta_aptus_ai_resource_package_candidate_v1",
        "version":                       "0.1.0",
        "status":                        "draft_package_candidate",
        "created_at":                    now,
        "source":                        "ai_approved_candidates",
        "auto_publish_enabled":          False,
        "supabase_write_performed":      False,
        "teacher_final_publish_required": True,
        "resource_count":                len(resources),
        "student_payload_count":         len(resources),
        "teacher_payload_count":         len(resources),
        "skipped_count":                 len(skipped),
        "skipped_resources":             skipped,
        "resources":                     resources,
    }

    return {"ok": True, "package": package, "generated_at": now}


def main():
    PKG_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    print("Gate 69E -- Build AI Approved Package Candidate v1")
    print("-" * 55)

    result = build_package_candidate()
    now    = result["generated_at"]

    if not result["ok"]:
        print(f"\n  ! FAILED: {result['error']}")
        for iss in result.get("issues", []):
            print(f"    ! {iss}")
        report = {
            "status":       "failed",
            "error":        result["error"],
            "issues":       result.get("issues", []),
            "generated_at": now,
        }
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport: {REPORT_FILE}")
        sys.exit(1)

    pkg = result["package"]
    print(f"  + package_candidate_id:          {pkg['package_candidate_id']}")
    print(f"  + status:                        {pkg['status']}")
    print(f"  + resource_count:                {pkg['resource_count']}")
    print(f"  + skipped_count:                 {pkg['skipped_count']}")
    print(f"  + auto_publish_enabled:          {pkg['auto_publish_enabled']}")
    print(f"  + supabase_write_performed:      {pkg['supabase_write_performed']}")
    print(f"  + teacher_final_publish_required:{pkg['teacher_final_publish_required']}")
    for sk in pkg.get("skipped_resources", []):
        print(f"    ~ skipped: {sk}")

    PKG_FILE.write_text(json.dumps(pkg, indent=2), encoding="utf-8")
    print(f"\nPackage: {PKG_FILE}")

    report = {
        "status":                        "passed",
        "package_candidate_id":          pkg["package_candidate_id"],
        "resource_count":                pkg["resource_count"],
        "skipped_count":                 pkg["skipped_count"],
        "auto_publish_enabled":          False,
        "supabase_write_performed":      False,
        "teacher_final_publish_required": True,
        "generated_at":                  now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report:  {REPORT_FILE}")


if __name__ == "__main__":
    main()
