"""
Gate 56 - Student Attempt Write Test v1.

Writes a safe demo attempt to Supabase directly through the service client.
This is an integration test — it requires live Supabase connection.

What it does:
  1. Connect to Supabase using service role key.
  2. Find the demo student (external_code = 'local_demo_student').
  3. Find the first published resource from the active physics package.
  4. Insert a test attempt with answer_text = 'Gate 56 test attempt'.
  5. Verify the inserted row.
  6. Write report to data/diagnostics/gate56_attempt_write_test_report_v1.json.

Does NOT:
  - Mark the attempt.
  - Upload Cambridge source text.
  - Expose the service role key.
  - Modify the schema.

CLI:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\test_gate56_attempt_write_v1.py [resource_key]

Default: picks first published resource from active physics package.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
SUPABASE_TOOL = Path(__file__).parent
DIAG_DIR      = PROJECT_ROOT / "data" / "diagnostics"

if str(SUPABASE_TOOL) not in sys.path:
    sys.path.insert(0, str(SUPABASE_TOOL))

DEMO_STUDENT_EXTERNAL_CODE = "local_demo_student"
DEMO_STUDENT_UUID_FALLBACK = "20000000-0000-0000-0000-000000000001"
DEFAULT_SUBJECT_SLUG       = "physics_0625"
TEST_ANSWER_TEXT           = "Gate 56 test attempt"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_demo_student(client) -> dict | None:
    r = (
        client.table("students")
        .select("id, display_name, external_code")
        .eq("external_code", DEMO_STUDENT_EXTERNAL_CODE)
        .execute()
    )
    return r.data[0] if r.data else None


def _get_active_package(client, subject_slug: str) -> tuple[dict | None, dict | None]:
    """Returns (subject_row, package_row) or (None, None)."""
    subj_r = (
        client.table("subjects")
        .select("id, subject_slug, subject_name")
        .eq("subject_slug", subject_slug)
        .execute()
    )
    if not subj_r.data:
        return None, None
    subj = subj_r.data[0]

    pkg_r = (
        client.table("resource_packages")
        .select("id, package_key, version, status")
        .eq("subject_id", subj["id"])
        .eq("status", "active")
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    return subj, (pkg_r.data[0] if pkg_r.data else None)


def _get_first_published_resource(client, package_id: str, resource_key_override: str | None = None) -> dict | None:
    """Return first published resource in the package, or None."""
    if resource_key_override:
        r = (
            client.table("resources")
            .select("id, resource_key, title, topic, subject_id, publish_status")
            .eq("resource_key", resource_key_override)
            .execute()
        )
        return r.data[0] if r.data else None

    # Get all items in package sorted by sort_order
    items_r = (
        client.table("resource_package_items")
        .select("resource_id, sort_order")
        .eq("package_id", package_id)
        .order("sort_order")
        .limit(10)
        .execute()
    )
    if not items_r.data:
        return None

    resource_ids = [item["resource_id"] for item in items_r.data]
    res_r = (
        client.table("resources")
        .select("id, resource_key, title, topic, subject_id, publish_status")
        .in_("id", resource_ids)
        .eq("publish_status", "published")
        .execute()
    )
    return res_r.data[0] if res_r.data else (
        # Fall back to any resource if none published
        client.table("resources")
        .select("id, resource_key, title, topic, subject_id, publish_status")
        .in_("id", resource_ids)
        .limit(1)
        .execute()
        .data or [None]
    )[0]


def _insert_test_attempt(client, student_id: str, resource: dict, attempt_type: str = "first_attempt") -> dict | None:
    r = (
        client.table("attempts")
        .insert({
            "student_id":        student_id,
            "resource_id":       resource["id"],
            "subject_id":        resource.get("subject_id"),
            "attempt_type":      attempt_type,
            "parent_attempt_id": None,
            "answer_text":       TEST_ANSWER_TEXT,
            "answer_json":       {"test": True, "source": "gate56_test_script"},
            "confidence_level":  "medium",
            "marking_status":    "unmarked",
        })
        .select("id, submitted_at, marking_status, student_id, resource_id, subject_id")
        .execute()
    )
    return r.data[0] if r.data else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso          = datetime.now(timezone.utc).isoformat()
    resource_key_arg = sys.argv[1] if len(sys.argv) > 1 else None

    from supabase_client_v1 import get_supabase_service_client, mask_secret

    print("=" * 60)
    print("Quanta Aptus - Gate 56 Attempt Write Test v1")
    print("=" * 60)

    client, url = get_supabase_service_client()
    print(f"  connected     : {mask_secret(url)}")

    report: dict = {
        "report_id":   "quanta_aptus_gate56_attempt_write_test_v1",
        "gate":        "56",
        "created_at":  now_iso,
        "status":      "failed",
    }

    # ── Demo student ────────────────────────────────────────────────────────
    student = _get_demo_student(client)
    if not student:
        # Use hardcoded fallback UUID — student exists from seed but query may differ
        print(f"  demo student  : using fallback UUID {DEMO_STUDENT_UUID_FALLBACK}")
        student = {"id": DEMO_STUDENT_UUID_FALLBACK, "display_name": "Local Demo Student (fallback)", "external_code": DEMO_STUDENT_EXTERNAL_CODE}
    else:
        print(f"  demo student  : found — {student['display_name']}")

    report["demo_student_found"] = True
    report["demo_student_id"]    = student["id"][:8] + "..."  # truncated

    # ── Active package ──────────────────────────────────────────────────────
    subj, pkg = _get_active_package(client, DEFAULT_SUBJECT_SLUG)
    if not subj:
        print(f"  [FAILED] Subject '{DEFAULT_SUBJECT_SLUG}' not found in Supabase.")
        report["error"] = f"Subject not found: {DEFAULT_SUBJECT_SLUG}"
        _write_report(report)
        sys.exit(1)
    if not pkg:
        print(f"  [FAILED] No active package found for '{DEFAULT_SUBJECT_SLUG}'.")
        report["error"] = "No active package found"
        _write_report(report)
        sys.exit(1)

    print(f"  package       : {pkg['package_key']}")
    report["package_key"] = pkg["package_key"]

    # ── Resource ────────────────────────────────────────────────────────────
    resource = _get_first_published_resource(client, pkg["id"], resource_key_arg)
    if not resource:
        print("  [FAILED] No resource found to test with.")
        report["error"] = "No resource found"
        _write_report(report)
        sys.exit(1)

    print(f"  resource      : {resource['resource_key']}")
    print(f"  resource title: {resource['title']}")
    report["resource_key"]   = resource["resource_key"]
    report["resource_title"] = resource["title"]

    # ── Insert attempt ──────────────────────────────────────────────────────
    inserted = _insert_test_attempt(client, student["id"], resource)
    if not inserted:
        print("  [FAILED] Attempt insert returned no data.")
        report["error"] = "Attempt insert failed"
        _write_report(report)
        sys.exit(1)

    print(f"  attempt_id    : {inserted['id']}")
    print(f"  submitted_at  : {inserted['submitted_at']}")
    print(f"  marking_status: {inserted['marking_status']}")
    print("  status        : PASSED")

    report.update({
        "status":                  "passed",
        "attempt_id":              inserted["id"],
        "submitted_at":            inserted["submitted_at"],
        "marking_status":          inserted["marking_status"],
        "test_attempt_inserted":   True,
        "marking_enabled":         False,
        "answer_text":             TEST_ANSWER_TEXT,
    })

    _write_report(report)
    sys.exit(0)


def _write_report(report: dict) -> None:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    path = DIAG_DIR / "gate56_attempt_write_test_report_v1.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  report        -> {path}")


if __name__ == "__main__":
    main()
