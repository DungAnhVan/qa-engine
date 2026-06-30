"""
Gate 53A/B — Sync Subject Adapter Registry to Supabase subjects table.

Reads all registered subject adapters from tools/ingest/subject_adapters/registry.py
and upserts one row per subject into the Supabase 'subjects' table.

Does NOT delete existing rows.
Does NOT upload any files.
Does NOT touch source_documents.

CLI:
    .venv-ingest\\Scripts\\python.exe tools\\supabase\\sync_subjects_to_supabase_v1.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
INGEST_TOOLS  = PROJECT_ROOT / "tools" / "ingest"
SUPABASE_TOOL = Path(__file__).parent

# Make both tools/ingest and tools/supabase importable
for _p in (str(INGEST_TOOLS), str(SUPABASE_TOOL)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DIAG_DIR = PROJECT_ROOT / "data" / "diagnostics"

# ---------------------------------------------------------------------------
# Subject display name and syllabus code lookup
# ---------------------------------------------------------------------------

_SUBJECT_DISPLAY_NAMES: dict[str, str] = {
    "physics_0625":                 "Physics",
    "chemistry_0620":               "Chemistry",
    "biology_0610":                 "Biology",
    "mathematics_0580":             "Mathematics",
    "additional_mathematics_0606":  "Additional Mathematics",
    "international_mathematics_0607": "International Mathematics",
    "computer_science_0478":        "Computer Science",
    "ict_0417":                     "ICT",
    "business_studies_0450":        "Business Studies",
    "economics_0455":               "Economics",
    "accounting_0452":              "Accounting",
    "geography_0460":               "Geography",
    "history_0470":                 "History",
    "global_perspectives_0457":     "Global Perspectives",
    "sociology_0495":               "Sociology",
    "travel_and_tourism_0471":      "Travel and Tourism",
    "english_first_language_0500":  "English First Language",
    "english_second_language_0510": "English Second Language",
    "english_literature_0475":      "English Literature",
    "combined_science_0653":        "Combined Science",
    "co_ordinated_sciences_0654":   "Co-ordinated Sciences",
    "environmental_management_0680": "Environmental Management",
}


def _syllabus_code(slug: str) -> str:
    try:
        return slug.rsplit("_", 1)[1]
    except IndexError:
        return ""


def _display_name(slug: str) -> str:
    return _SUBJECT_DISPLAY_NAMES.get(
        slug,
        slug.replace("_", " ").title(),
    )


# ---------------------------------------------------------------------------
# Build rows from adapter registry
# ---------------------------------------------------------------------------

def build_subject_rows() -> list[dict]:
    from subject_adapters.registry import get_adapter, list_registered_slugs

    rows = []
    for slug in list_registered_slugs():
        adapter  = get_adapter(slug)
        meta     = adapter.get_adapter_metadata()
        rows.append({
            "board":           "cambridge",
            "level":           "igcse",
            "subject_slug":    slug,
            "subject_name":    _display_name(slug),
            "syllabus_code":   _syllabus_code(slug),
            "adapter_name":    meta["adapter_name"],
            "adapter_status":  meta["adapter_status"],
            "adapter_version": "v1",
            "is_active":       True,
        })
    return rows


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

def upsert_subjects(client, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Upsert each row individually so we can record per-row status.
    Returns (succeeded, failed) lists.
    """
    succeeded: list[dict] = []
    failed:    list[dict] = []

    for row in rows:
        try:
            client.table("subjects").upsert(
                row,
                on_conflict="subject_slug",
            ).execute()
            succeeded.append(row)
        except Exception as exc:
            failed.append({**row, "_error": str(exc)[:200]})

    return succeeded, failed


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(
    now_iso: str,
    url: str,
    total: int,
    succeeded: list[dict],
    failed: list[dict],
) -> Path:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "supabase_subject_sync_report_v1.json"

    status = "passed" if len(failed) == 0 else "failed"

    subjects_out = []
    for r in succeeded:
        subjects_out.append({
            "subject_slug":    r["subject_slug"],
            "subject_name":    r["subject_name"],
            "syllabus_code":   r["syllabus_code"],
            "adapter_status":  r["adapter_status"],
            "sync_status":     "upserted",
        })
    for r in failed:
        subjects_out.append({
            "subject_slug":    r["subject_slug"],
            "subject_name":    r["subject_name"],
            "syllabus_code":   r["syllabus_code"],
            "adapter_status":  r["adapter_status"],
            "sync_status":     "failed",
            "error":           r.get("_error"),
        })

    report = {
        "report_id":               "quanta_aptus_supabase_subject_sync_v1",
        "gate":                    "53A/B",
        "created_at":              now_iso,
        "status":                  status,
        "connected":               True,
        "table":                   "subjects",
        "registered_subject_count": total,
        "upserted_count":          len(succeeded),
        "failed_count":            len(failed),
        "subjects":                subjects_out,
        "next_gate":               "Gate 53C - Sync Source Documents and Source Pairs",
    }

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    # ── Import client helper ───────────────────────────────────────────────
    from supabase_client_v1 import get_supabase_service_client, mask_secret

    print("=" * 60)
    print("Quanta Aptus - Supabase Subject Sync v1")
    print("=" * 60)

    # ── Connect ───────────────────────────────────────────────────────────
    client, url = get_supabase_service_client()
    print(f"  connected     : {mask_secret(url)}")

    # ── Build rows from adapter registry ──────────────────────────────────
    rows  = build_subject_rows()
    total = len(rows)
    print(f"  registered    : {total} subjects")

    # ── Upsert ────────────────────────────────────────────────────────────
    print("  upserting to subjects table...")
    succeeded, failed = upsert_subjects(client, rows)

    # ── Print per-subject summary ─────────────────────────────────────────
    for r in succeeded:
        print(f"    [OK ] {r['subject_slug']:38s} {r['adapter_status']}")
    for r in failed:
        print(f"    [FAIL] {r['subject_slug']:37s} {r.get('_error','')[:60]}")

    # ── Final summary ─────────────────────────────────────────────────────
    status = "passed" if len(failed) == 0 else "failed"
    print(f"\n  upserted_count: {len(succeeded)}")
    print(f"  failed_count  : {len(failed)}")
    print(f"  status        : {status.upper()}")

    # ── Write report ───────────────────────────────────────────────────────
    report_path = write_report(now_iso, url, total, succeeded, failed)
    print(f"  report        -> {report_path}")

    sys.exit(0 if status == "passed" else 1)


if __name__ == "__main__":
    main()
