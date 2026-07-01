"""
Gate 69F -- Build AI Local Published Package v1

Reads the approved package candidate and final publish approval, then
assembles the locally published package. Status is published_local_not_active.
No Supabase writes. No active registry switch. No AI API calls.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_local_published_package_v1.py

Inputs:
  data/ai/package_candidates/ai_resource_package_candidate_v1.json
  data/ai/package_candidates/ai_final_publish_approval_v1.json

Output:
  data/ai/published/ai_resource_package_v1/publish_package_v1.json
  data/ai/published/ai_resource_package_v1/student_resource_payload_v1.json
  data/ai/published/ai_resource_package_v1/teacher_resource_payload_v1.json
  data/ai/published/ai_resource_package_v1/ai_publish_manifest_v1.md
  data/ai/published/ai_resource_package_v1/ai_publish_report_v1.json
  data/diagnostics/ai_local_publish_build_report_v1.json
"""

import json
import sys
import datetime
from pathlib import Path

ROOT             = Path(__file__).resolve().parents[2]
PKG_CANDIDATE    = ROOT / "data" / "ai" / "package_candidates" / "ai_resource_package_candidate_v1.json"
APPROVAL_FILE    = ROOT / "data" / "ai" / "package_candidates" / "ai_final_publish_approval_v1.json"
PUBLISHED_DIR    = ROOT / "data" / "ai" / "published" / "ai_resource_package_v1"
REPORT_FILE      = ROOT / "data" / "diagnostics" / "ai_local_publish_build_report_v1.json"


def build_local_published_package() -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # ── Load approval ──────────────────────────────────────────────────────────
    if not APPROVAL_FILE.exists():
        return {
            "ok":    False,
            "error": (
                f"Approval file not found: {APPROVAL_FILE}\n"
                "Run: .venv-ingest\\Scripts\\python.exe "
                "tools\\ai\\approve_ai_package_candidate_v1.py --approve ..."
            ),
            "generated_at": now,
        }

    try:
        approval = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"Approval parse error: {exc}", "generated_at": now}

    if approval.get("approval_status") != "approved":
        return {
            "ok":    False,
            "error": (
                f"Package is not approved (status={approval.get('approval_status')!r}). "
                "Run approve_ai_package_candidate_v1.py --approve first."
            ),
            "generated_at": now,
        }

    if not approval.get("allow_local_publish"):
        return {
            "ok":    False,
            "error": "allow_local_publish is False — cannot build local published package.",
            "generated_at": now,
        }

    # ── Load package candidate ────────────────────────────────────────────────
    if not PKG_CANDIDATE.exists():
        return {
            "ok":    False,
            "error": f"Package candidate not found: {PKG_CANDIDATE}",
            "generated_at": now,
        }

    try:
        candidate = json.loads(PKG_CANDIDATE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"Candidate parse error: {exc}", "generated_at": now}

    resources = candidate.get("resources", [])

    # ── Build published package ───────────────────────────────────────────────
    published_resources = []
    for r in resources:
        published_resources.append({
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
            "student_instructions": r.get("student_instructions", "Show all working."),
            "answer_key":           r.get("answer_key", ""),
            "marking_rubric":       r.get("marking_rubric", []),
            "teacher_notes":        r.get("teacher_notes", ""),
            "safety_declaration":   r.get("safety_declaration", {}),
            "provenance":           r.get("provenance", {}),
        })

    published_package = {
        "package_id":               "quanta_aptus_ai_resource_package_v1",
        "version":                  "0.1.0",
        "status":                   "published_local_not_active",
        "published_at":             now,
        "source":                   "ai_final_approved_package_candidate",
        "package_candidate_id":     candidate.get("package_candidate_id"),
        "approved_by":              approval.get("approved_by"),
        "approval_notes":           approval.get("approval_notes"),
        "approved_at":              approval.get("approved_at"),
        "active_content":           False,
        "supabase_write_performed": False,
        "teacher_final_approval":   True,
        "allow_active_switch":      False,
        "allow_supabase_sync":      False,
        "resource_count":           len(published_resources),
        "resources":                published_resources,
    }

    # ── Student payload (prompts only, no answers) ────────────────────────────
    student_payload = {
        "payload_id":               "quanta_aptus_ai_published_student_payload_v1",
        "payload_type":             "student",
        "package_id":               "quanta_aptus_ai_resource_package_v1",
        "status":                   "published_local_not_active",
        "generated_at":             now,
        "active_content":           False,
        "supabase_write_performed": False,
        "resource_count":           len(published_resources),
        "resources": [
            {
                "resource_id":          r["resource_id"],
                "resource_type":        r.get("resource_type", "question"),
                "title":                r.get("title", ""),
                "topic":                r.get("topic", ""),
                "skill_name":           r.get("skill_name", ""),
                "difficulty":           r.get("difficulty", ""),
                "estimated_time_minutes": r.get("estimated_time_minutes", 0),
                "student_prompt":       r.get("student_prompt", ""),
                "student_instructions": r.get("student_instructions", ""),
            }
            for r in published_resources
        ],
    }

    # ── Teacher payload (full content) ────────────────────────────────────────
    teacher_payload = {
        "payload_id":               "quanta_aptus_ai_published_teacher_payload_v1",
        "payload_type":             "teacher",
        "package_id":               "quanta_aptus_ai_resource_package_v1",
        "status":                   "published_local_not_active",
        "generated_at":             now,
        "active_content":           False,
        "supabase_write_performed": False,
        "resource_count":           len(published_resources),
        "resources":                published_resources,
    }

    # ── Write outputs ──────────────────────────────────────────────────────────
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)

    pkg_path      = PUBLISHED_DIR / "publish_package_v1.json"
    student_path  = PUBLISHED_DIR / "student_resource_payload_v1.json"
    teacher_path  = PUBLISHED_DIR / "teacher_resource_payload_v1.json"
    report_path   = PUBLISHED_DIR / "ai_publish_report_v1.json"
    manifest_path = PUBLISHED_DIR / "ai_publish_manifest_v1.md"

    pkg_path.write_text(json.dumps(published_package, indent=2), encoding="utf-8")
    student_path.write_text(json.dumps(student_payload, indent=2), encoding="utf-8")
    teacher_path.write_text(json.dumps(teacher_payload, indent=2), encoding="utf-8")

    # ── Manifest ──────────────────────────────────────────────────────────────
    manifest = f"""# AI Resource Package v1 — Local Publish Manifest

Published: {now}
Status: published_local_not_active

## Package

- Package ID: quanta_aptus_ai_resource_package_v1
- Source: {candidate.get("package_candidate_id")}
- Approved by: {approval.get("approved_by")}
- Resource count: {len(published_resources)}

## Policy

- active_content: False
- supabase_write_performed: False
- teacher_final_approval: True
- allow_active_switch: False
- allow_supabase_sync: False

## Resources

{chr(10).join(f"- {r['resource_id']}: {r.get('title', '')} ({r.get('topic', '')} / {r.get('difficulty', '')})" for r in published_resources)}

## Next Step

Gate 69G: Supabase Sync and Active Content Switch (requires explicit flags).
"""
    manifest_path.write_text(manifest, encoding="utf-8")

    pkg_report = {
        "package_id":               "quanta_aptus_ai_resource_package_v1",
        "status":                   "published_local_not_active",
        "published_at":             now,
        "resource_count":           len(published_resources),
        "active_content":           False,
        "supabase_write_performed": False,
        "teacher_final_approval":   True,
    }
    report_path.write_text(json.dumps(pkg_report, indent=2), encoding="utf-8")

    return {
        "ok":                       True,
        "resource_count":           len(published_resources),
        "status":                   "published_local_not_active",
        "active_content":           False,
        "supabase_write_performed": False,
        "teacher_final_approval":   True,
        "generated_at":             now,
    }


def main():
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    print("Gate 69F -- Build AI Local Published Package v1")
    print("-" * 55)

    result = build_local_published_package()
    now    = result["generated_at"]

    if not result["ok"]:
        print(f"\n  ! FAILED: {result['error']}")
        REPORT_FILE.write_text(json.dumps(
            {"status": "failed", "error": result["error"], "generated_at": now}, indent=2),
            encoding="utf-8")
        print(f"\nReport: {REPORT_FILE}")
        sys.exit(1)

    sym = lambda ok: "+" if ok else "!"
    print(f"  [+] status:                   {result['status']}")
    print(f"  [+] resource_count:           {result['resource_count']}")
    print(f"  [+] active_content:           {result['active_content']}")
    print(f"  [+] supabase_write_performed: {result['supabase_write_performed']}")
    print(f"  [+] teacher_final_approval:   {result['teacher_final_approval']}")
    print(f"\n  Published dir: {PUBLISHED_DIR}")

    report = {
        "status":                   "passed",
        "resource_count":           result["resource_count"],
        "package_status":           result["status"],
        "active_content":           False,
        "supabase_write_performed": False,
        "teacher_final_approval":   True,
        "generated_at":             now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nStatus: passed")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
