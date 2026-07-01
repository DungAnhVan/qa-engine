"""
Gate 69E -- Export AI Package Candidate Payloads v1

Reads the package candidate and exports separate student and teacher payloads.

Student payload: prompt and instructions only — no answer key, no rubric
  detailed answers, no teacher notes.
Teacher payload: full content including answer key, rubric, teacher notes,
  safety declaration, and provenance.

No Supabase writes. No AI API calls.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\export_ai_package_candidate_payloads_v1.py

Output:
  data/ai/package_candidates/student_ai_package_payload_v1.json
  data/ai/package_candidates/teacher_ai_package_payload_v1.json
  data/diagnostics/ai_package_candidate_payload_export_report_v1.json
"""

import json
import sys
import datetime
from pathlib import Path

ROOT         = Path(__file__).resolve().parents[2]
PKG_DIR      = ROOT / "data" / "ai" / "package_candidates"
PKG_FILE     = PKG_DIR / "ai_resource_package_candidate_v1.json"
STUDENT_FILE = PKG_DIR / "student_ai_package_payload_v1.json"
TEACHER_FILE = PKG_DIR / "teacher_ai_package_payload_v1.json"
REPORT_FILE  = ROOT / "data" / "diagnostics" / "ai_package_candidate_payload_export_report_v1.json"


def export_payloads() -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if not PKG_FILE.exists():
        return {
            "ok":    False,
            "error": (
                f"Package candidate not found: {PKG_FILE}\n"
                "Run build_ai_approved_package_candidate_v1.py first."
            ),
            "generated_at": now,
        }

    try:
        pkg = json.loads(PKG_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"JSON parse error: {exc}", "generated_at": now}

    resources = pkg.get("resources", [])

    student_resources = []
    teacher_resources = []

    for r in resources:
        # Student payload: questions only, no answers
        student_resources.append({
            "resource_id":          r["resource_id"],
            "resource_type":        r.get("resource_type", "question"),
            "title":                r.get("title", ""),
            "topic":                r.get("topic", ""),
            "skill_name":           r.get("skill_name", ""),
            "difficulty":           r.get("difficulty", ""),
            "estimated_time_minutes": r.get("estimated_time_minutes", 0),
            "student_prompt":       r.get("student_prompt", ""),
            "student_instructions": r.get("student_instructions", "Show all working."),
        })

        # Teacher payload: full content
        teacher_resources.append({
            "resource_id":          r["resource_id"],
            "resource_type":        r.get("resource_type", "question"),
            "title":                r.get("title", ""),
            "topic":                r.get("topic", ""),
            "subtopic":             r.get("subtopic", ""),
            "skill_name":           r.get("skill_name", ""),
            "skill_type":           r.get("skill_type", ""),
            "difficulty":           r.get("difficulty", ""),
            "estimated_time_minutes": r.get("estimated_time_minutes", 0),
            "student_prompt":       r.get("student_prompt", ""),
            "student_instructions": r.get("student_instructions", ""),
            "answer_key":           r.get("answer_key", ""),
            "marking_rubric":       r.get("marking_rubric", []),
            "teacher_notes":        r.get("teacher_notes", ""),
            "safety_declaration":   r.get("safety_declaration", {}),
            "provenance":           r.get("provenance", {}),
        })

    student_payload = {
        "payload_id":             "quanta_aptus_student_ai_package_payload_v1",
        "version":                "0.1.0",
        "payload_type":           "student",
        "generated_at":           now,
        "source_package":         pkg.get("package_candidate_id"),
        "package_status":         pkg.get("status"),
        "auto_publish_enabled":   False,
        "supabase_write_performed": False,
        "teacher_final_publish_required": True,
        "resource_count":         len(student_resources),
        "resources":              student_resources,
    }

    teacher_payload = {
        "payload_id":             "quanta_aptus_teacher_ai_package_payload_v1",
        "version":                "0.1.0",
        "payload_type":           "teacher",
        "generated_at":           now,
        "source_package":         pkg.get("package_candidate_id"),
        "package_status":         pkg.get("status"),
        "auto_publish_enabled":   False,
        "supabase_write_performed": False,
        "teacher_final_publish_required": True,
        "resource_count":         len(teacher_resources),
        "resources":              teacher_resources,
    }

    PKG_DIR.mkdir(parents=True, exist_ok=True)
    STUDENT_FILE.write_text(json.dumps(student_payload, indent=2), encoding="utf-8")
    TEACHER_FILE.write_text(json.dumps(teacher_payload, indent=2), encoding="utf-8")

    return {
        "ok":                     True,
        "student_resource_count": len(student_resources),
        "teacher_resource_count": len(teacher_resources),
        "generated_at":           now,
    }


def main():
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    print("Gate 69E -- Export AI Package Candidate Payloads v1")
    print("-" * 55)

    result = export_payloads()
    now    = result["generated_at"]

    if not result["ok"]:
        print(f"\n  ! FAILED: {result['error']}")
        report = {
            "status": "failed",
            "error":  result["error"],
            "generated_at": now,
        }
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport: {REPORT_FILE}")
        sys.exit(1)

    print(f"  + student_resource_count: {result['student_resource_count']}")
    print(f"  + teacher_resource_count: {result['teacher_resource_count']}")
    print(f"  + student payload:        {STUDENT_FILE}")
    print(f"  + teacher payload:        {TEACHER_FILE}")

    report = {
        "status":                 "passed",
        "student_resource_count": result["student_resource_count"],
        "teacher_resource_count": result["teacher_resource_count"],
        "student_payload_file":   str(STUDENT_FILE.relative_to(ROOT)),
        "teacher_payload_file":   str(TEACHER_FILE.relative_to(ROOT)),
        "auto_publish_enabled":   False,
        "supabase_write_performed": False,
        "teacher_final_publish_required": True,
        "generated_at":           now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nStatus: passed")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
