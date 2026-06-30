"""
Gate 53F — Read Active Package from Supabase v1.

Queries the live Supabase project for:
  - The active resource_package for a given subject
  - All resources in that package (via resource_package_items)

Exports three JSON files to data/supabase_exports/ that the app layer
can consume in Gate 54+ without touching local files.

COPYRIGHT SAFETY:
  - Reads only Quanta Aptus original_generated content.
  - raw_text (source_items) and source_documents are never queried here.
  - No Cambridge source text is read or exported.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\read_active_package_from_supabase_v1.py [subject_slug]

Default subject_slug: physics_0625
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT    = Path(__file__).resolve().parents[2]
SUPABASE_TOOL   = Path(__file__).parent
EXPORT_DIR      = PROJECT_ROOT / "data" / "supabase_exports"
DIAG_DIR        = PROJECT_ROOT / "data" / "diagnostics"

EXPECTED_PACKAGE_KEY = "cambridge_igcse_physics_0625_resource_package_v2"

if str(SUPABASE_TOOL) not in sys.path:
    sys.path.insert(0, str(SUPABASE_TOOL))


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _query_subject(client, subject_slug: str) -> Optional[dict]:
    r = (
        client.table("subjects")
        .select("id, board, level, subject_slug, subject_name, syllabus_code, adapter_status")
        .eq("subject_slug", subject_slug)
        .execute()
    )
    return r.data[0] if r.data else None


def _query_active_package(client, subject_id: str) -> Optional[dict]:
    r = (
        client.table("resource_packages")
        .select(
            "id, subject_id, package_key, version, title, status, "
            "resource_count, student_resource_count, teacher_resource_count, "
            "created_at, published_at"
        )
        .eq("subject_id", subject_id)
        .eq("status", "active")
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None


def _query_package_items(client, package_id: str) -> list[dict]:
    r = (
        client.table("resource_package_items")
        .select("id, resource_id, sort_order, visibility")
        .eq("package_id", package_id)
        .order("sort_order")
        .execute()
    )
    return r.data or []


def _query_resources_by_ids(client, resource_ids: list[str]) -> dict[str, dict]:
    """Batch fetch resources by id. Returns id -> resource dict."""
    if not resource_ids:
        return {}
    r = (
        client.table("resources")
        .select(
            "id, resource_key, title, topic, subtopic, skill_type, resource_type, "
            "difficulty, estimated_time_minutes, student_prompt, worked_solution, "
            "marking_guidance, common_misconceptions, teacher_notes, "
            "originality_statement, copyright_status, adapter_status, confidence, "
            "needs_human_review, publish_status"
        )
        .in_("id", resource_ids)
        .execute()
    )
    return {row["id"]: row for row in (r.data or [])}


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def _build_full_resource(res: dict, item: dict) -> dict:
    """Full resource row as stored in Supabase, enriched with visibility."""
    return {
        "resource_key":           res.get("resource_key"),
        "title":                  res.get("title"),
        "topic":                  res.get("topic"),
        "subtopic":               res.get("subtopic"),
        "skill_type":             res.get("skill_type"),
        "resource_type":          res.get("resource_type"),
        "difficulty":             res.get("difficulty"),
        "estimated_time_minutes": res.get("estimated_time_minutes"),
        "student_prompt":         res.get("student_prompt"),
        "worked_solution":        res.get("worked_solution"),
        "marking_guidance":       res.get("marking_guidance"),
        "common_misconceptions":  res.get("common_misconceptions"),
        "teacher_notes":          res.get("teacher_notes"),
        "originality_statement":  res.get("originality_statement"),
        "copyright_status":       res.get("copyright_status"),
        "adapter_status":         res.get("adapter_status"),
        "confidence":             res.get("confidence"),
        "needs_human_review":     res.get("needs_human_review"),
        "publish_status":         res.get("publish_status"),
        "visibility":             item.get("visibility"),
        "sort_order":             item.get("sort_order"),
    }


def _build_student_resource(res: dict, item: dict) -> dict:
    """Student-safe view — no teacher_notes or marking_guidance."""
    return {
        "resource_key":           res.get("resource_key"),
        "title":                  res.get("title"),
        "topic":                  res.get("topic"),
        "skill_type":             res.get("skill_type"),
        "resource_type":          res.get("resource_type"),
        "difficulty":             res.get("difficulty"),
        "estimated_time_minutes": res.get("estimated_time_minutes"),
        "student_prompt":         res.get("student_prompt"),
        "worked_solution":        res.get("worked_solution"),
        "sort_order":             item.get("sort_order"),
    }


def _build_teacher_resource(res: dict, item: dict) -> dict:
    """Teacher view — all fields including marking guidance and teacher notes."""
    return {
        "resource_key":           res.get("resource_key"),
        "title":                  res.get("title"),
        "topic":                  res.get("topic"),
        "subtopic":               res.get("subtopic"),
        "skill_type":             res.get("skill_type"),
        "resource_type":          res.get("resource_type"),
        "difficulty":             res.get("difficulty"),
        "estimated_time_minutes": res.get("estimated_time_minutes"),
        "student_prompt":         res.get("student_prompt"),
        "worked_solution":        res.get("worked_solution"),
        "marking_guidance":       res.get("marking_guidance"),
        "common_misconceptions":  res.get("common_misconceptions"),
        "teacher_notes":          res.get("teacher_notes"),
        "needs_human_review":     res.get("needs_human_review"),
        "publish_status":         res.get("publish_status"),
        "visibility":             item.get("visibility"),
        "sort_order":             item.get("sort_order"),
    }


# ---------------------------------------------------------------------------
# Main read + export
# ---------------------------------------------------------------------------

def read_and_export(client, subject_slug: str, now_iso: str) -> dict:
    """Core logic. Returns the report dict."""

    # ── 1. Subject lookup ──────────────────────────────────────────────────
    subject = _query_subject(client, subject_slug)
    if not subject:
        return {
            "gate":                      "53F",
            "status":                    "failed",
            "subject_slug":              subject_slug,
            "active_package_found":      False,
            "error":                     f"Subject '{subject_slug}' not found in Supabase.",
        }

    subject_id = subject["id"]

    # ── 2. Active package ──────────────────────────────────────────────────
    pkg = _query_active_package(client, subject_id)
    if not pkg:
        return {
            "gate":                 "53F",
            "status":               "failed",
            "subject_slug":         subject_slug,
            "active_package_found": False,
            "error":                f"No active resource_package found for '{subject_slug}'.",
        }

    package_id  = pkg["id"]
    package_key = pkg["package_key"]
    version     = pkg["version"]

    # ── 3. Package items ───────────────────────────────────────────────────
    items = _query_package_items(client, package_id)
    if not items:
        return {
            "gate":                 "53F",
            "status":               "needs_review",
            "subject_slug":         subject_slug,
            "active_package_found": True,
            "package_key":          package_key,
            "error":                "Package found but no resource_package_items.",
        }

    # ── 4. Resources batch fetch ───────────────────────────────────────────
    resource_ids = [item["resource_id"] for item in items]
    resources_by_id = _query_resources_by_ids(client, resource_ids)

    # ── 5. Build payload lists ─────────────────────────────────────────────
    all_resources:     list[dict] = []
    student_resources: list[dict] = []
    teacher_resources: list[dict] = []
    teacher_only_count = 0
    nhr_count = 0

    for item in items:
        res = resources_by_id.get(item["resource_id"])
        if not res:
            continue

        visibility = item.get("visibility", "student")
        full       = _build_full_resource(res, item)
        all_resources.append(full)
        teacher_resources.append(_build_teacher_resource(res, item))

        if visibility == "teacher_only":
            teacher_only_count += 1
        else:
            student_resources.append(_build_student_resource(res, item))

        if res.get("needs_human_review"):
            nhr_count += 1

    # ── 6. Build export docs ───────────────────────────────────────────────
    active_pkg_export = {
        "source":                  "supabase",
        "exported_at":             now_iso,
        "subject_slug":            subject_slug,
        "subject_name":            subject.get("subject_name"),
        "board":                   subject.get("board"),
        "level":                   subject.get("level"),
        "syllabus_code":           subject.get("syllabus_code"),
        "package_key":             package_key,
        "version":                 version,
        "status":                  pkg["status"],
        "resource_count":          pkg["resource_count"],
        "student_resource_count":  pkg["student_resource_count"],
        "teacher_resource_count":  pkg["teacher_resource_count"],
        "published_at":            pkg.get("published_at"),
        "copyright_note":          "All resources are original Quanta Aptus content. No Cambridge source text included.",
        "resources":               all_resources,
    }

    student_payload_export = {
        "source":         "supabase",
        "exported_at":    now_iso,
        "payload_type":   "student",
        "subject_slug":   subject_slug,
        "package_key":    package_key,
        "resource_count": len(student_resources),
        "copyright_note": "Original Quanta Aptus content. No Cambridge source text included.",
        "resources":      student_resources,
    }

    teacher_payload_export = {
        "source":                    "supabase",
        "exported_at":               now_iso,
        "payload_type":              "teacher",
        "subject_slug":              subject_slug,
        "package_key":               package_key,
        "resource_count":            len(teacher_resources),
        "teacher_only_count":        teacher_only_count,
        "needs_human_review_count":  nhr_count,
        "copyright_note":            "Original Quanta Aptus content. Teacher use only.",
        "resources":                 teacher_resources,
    }

    # ── 7. Write export files ──────────────────────────────────────────────
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    active_path  = EXPORT_DIR / "active_package_from_supabase_v1.json"
    student_path = EXPORT_DIR / "student_resource_payload_from_supabase_v1.json"
    teacher_path = EXPORT_DIR / "teacher_resource_payload_from_supabase_v1.json"

    active_path.write_text(
        json.dumps(active_pkg_export, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    student_path.write_text(
        json.dumps(student_payload_export, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    teacher_path.write_text(
        json.dumps(teacher_payload_export, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ── 8. Build report ────────────────────────────────────────────────────
    matches_expected = (package_key == EXPECTED_PACKAGE_KEY)
    status = "passed" if (matches_expected and len(all_resources) > 0) else "needs_review"

    report = {
        "report_id":                   "quanta_aptus_supabase_active_package_read_v1",
        "gate":                        "53F",
        "created_at":                  now_iso,
        "status":                      status,
        "subject_slug":                subject_slug,
        "active_package_found":        True,
        "package_key":                 package_key,
        "version":                     version,
        "resources_read":              len(all_resources),
        "student_resources_exported":  len(student_resources),
        "teacher_resources_exported":  len(teacher_resources),
        "teacher_only_count":          teacher_only_count,
        "needs_human_review_count":    nhr_count,
        "matches_expected_active_package": matches_expected,
        "expected_package_key":        EXPECTED_PACKAGE_KEY,
        "export_files": {
            "active_package":  str(active_path),
            "student_payload": str(student_path),
            "teacher_payload": str(teacher_path),
        },
        "copyright_safety": {
            "raw_cambridge_pdf_read":     False,
            "extracted_source_text_read": False,
            "generated_resources_only":   True,
        },
        "next_gate": "Gate 54 - App Supabase Read Mode",
    }

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    subject_slug = sys.argv[1] if len(sys.argv) > 1 else "physics_0625"

    from supabase_client_v1 import get_supabase_service_client, mask_secret

    print("=" * 60)
    print("Quanta Aptus - Read Active Package from Supabase v1")
    print("=" * 60)

    client, url = get_supabase_service_client()
    print(f"  connected     : {mask_secret(url)}")
    print(f"  subject_slug  : {subject_slug}")

    report = read_and_export(client, subject_slug, now_iso)

    if report.get("status") == "failed":
        print(f"\n[FAILED] {report.get('error', 'Unknown error')}")
    else:
        print(f"  package_key   : {report.get('package_key')}")
        print(f"  resources_read: {report.get('resources_read')}")
        print(f"  student_exp   : {report.get('student_resources_exported')}")
        print(f"  teacher_exp   : {report.get('teacher_resources_exported')}")
        if report.get("needs_human_review_count"):
            print(f"  needs_review  : {report.get('needs_human_review_count')}")
        if not report.get("matches_expected_active_package"):
            print(f"  WARN: package_key does not match expected '{report.get('expected_package_key')}'")
        print(f"  status        : {report.get('status', '').upper()}")
        for k, v in (report.get("export_files") or {}).items():
            print(f"  {k:<14}: {v}")

    # ── Write report ───────────────────────────────────────────────────────
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "supabase_active_package_read_report_v1.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  report        -> {report_path}")

    sys.exit(0 if report.get("status") in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
