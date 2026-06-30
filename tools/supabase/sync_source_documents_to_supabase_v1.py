"""
Gate 53C — Sync Source Documents and Source Pairs to Supabase v1.

Reads raw_document_inventory_v0.json and raw_document_pairs_v0.json
from data/intake/cambridge_igcse/<subject_slug>/ and syncs METADATA ONLY
into Supabase tables: source_documents and source_pairs.

SAFETY:
  - No raw Cambridge PDFs are uploaded.
  - No extracted Cambridge text is uploaded.
  - copyright_status = 'internal_reference_only' on every row.
  - storage_path stores a relative local path only, never the file content.

CLI:
  # All subjects:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\sync_source_documents_to_supabase_v1.py

  # Single subject:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\sync_source_documents_to_supabase_v1.py physics_0625
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
SUPABASE_TOOL = Path(__file__).parent
INTAKE_ROOT   = PROJECT_ROOT / "data" / "intake" / "cambridge_igcse"
DIAG_DIR      = PROJECT_ROOT / "data" / "diagnostics"

if str(SUPABASE_TOOL) not in sys.path:
    sys.path.insert(0, str(SUPABASE_TOOL))

# ---------------------------------------------------------------------------
# Source type mapping
# ---------------------------------------------------------------------------

_SOURCE_TYPE_MAP: dict[str, str] = {
    "qp":  "question_paper",
    "ms":  "mark_scheme",
}


def _source_type(doc_type_code: str) -> str:
    return _SOURCE_TYPE_MAP.get(doc_type_code.lower(), "other")


def _rel_path(abs_path: str) -> str:
    """Convert absolute Windows path to a relative project path for storage_path."""
    try:
        return str(Path(abs_path).relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return abs_path.replace("\\", "/")


# ---------------------------------------------------------------------------
# Supabase lookup helpers
# ---------------------------------------------------------------------------

def _lookup_subject_id(client, subject_slug: str) -> Optional[str]:
    r = (
        client.table("subjects")
        .select("id")
        .eq("subject_slug", subject_slug)
        .execute()
    )
    if r.data:
        return r.data[0]["id"]
    return None


def _lookup_org_id(client, org_slug: str = "quanta-aptus-local-demo") -> Optional[str]:
    r = (
        client.table("organizations")
        .select("id")
        .eq("slug", org_slug)
        .execute()
    )
    if r.data:
        return r.data[0]["id"]
    return None


def _upsert_source_document(client, row: dict) -> Optional[str]:
    """
    Manual dedupe: query by subject_slug + original_filename.
    Update if found, insert if not. Returns the row id.
    """
    existing = (
        client.table("source_documents")
        .select("id")
        .eq("subject_slug", row["subject_slug"])
        .eq("original_filename", row["original_filename"])
        .execute()
    )
    if existing.data:
        row_id = existing.data[0]["id"]
        # Update all mutable fields except subject_slug/filename
        update_fields = {k: v for k, v in row.items()
                         if k not in ("subject_slug", "original_filename")}
        client.table("source_documents").update(update_fields).eq("id", row_id).execute()
        return row_id
    else:
        inserted = client.table("source_documents").insert(row).execute()
        if inserted.data:
            return inserted.data[0]["id"]
        return None


def _upsert_source_pair(client, row: dict) -> Optional[str]:
    """
    Manual dedupe: query by pair_key.
    Update if found, insert if not. Returns the row id.
    """
    existing = (
        client.table("source_pairs")
        .select("id")
        .eq("pair_key", row["pair_key"])
        .execute()
    )
    if existing.data:
        row_id = existing.data[0]["id"]
        update_fields = {k: v for k, v in row.items() if k != "pair_key"}
        client.table("source_pairs").update(update_fields).eq("id", row_id).execute()
        return row_id
    else:
        inserted = client.table("source_pairs").insert(row).execute()
        if inserted.data:
            return inserted.data[0]["id"]
        return None


# ---------------------------------------------------------------------------
# Per-subject sync
# ---------------------------------------------------------------------------

def sync_subject(
    client,
    subject_slug: str,
    subject_id:   str,
    org_id:       str,
) -> dict:
    """Sync one subject. Returns a result summary dict."""
    inventory_path = INTAKE_ROOT / subject_slug / "raw_document_inventory_v0.json"
    pairs_path     = INTAKE_ROOT / subject_slug / "raw_document_pairs_v0.json"

    result = {
        "subject_slug":             subject_slug,
        "inventory_found":          inventory_path.exists(),
        "pairs_found":              pairs_path.exists(),
        "documents_in_inventory":   0,
        "pairs_in_file":            0,
        "documents_upserted":       0,
        "pairs_upserted":           0,
        "failed_documents":         0,
        "failed_pairs":             0,
        "errors":                   [],
        # doc_id -> supabase row id, for pair linking
        "_doc_id_to_row_id":        {},
    }

    # ── Load inventory ─────────────────────────────────────────────────────
    if not inventory_path.exists():
        result["errors"].append(f"raw_document_inventory_v0.json not found for {subject_slug}")
        return result

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    docs      = inventory.get("documents", [])
    syllabus  = inventory.get("syllabus_code", "")
    result["documents_in_inventory"] = len(docs)

    # ── Sync documents ─────────────────────────────────────────────────────
    for doc in docs:
        row = {
            "subject_id":        subject_id,
            "organization_id":   org_id,
            "source_type":       _source_type(doc.get("document_type_code", "")),
            "board":             doc.get("board", "cambridge"),
            "level":             doc.get("level", "igcse"),
            "subject_slug":      subject_slug,
            "syllabus_code":     doc.get("syllabus_code", syllabus),
            "series":            doc.get("series_name"),
            "year":              doc.get("year"),
            "component":         doc.get("paper_code"),
            "variant":           doc.get("variant"),
            "original_filename": doc["filename"],
            "storage_path":      _rel_path(doc.get("path", "")),
            "checksum":          doc.get("checksum"),
            "copyright_status":  "internal_reference_only",
            "ingest_status":     "ingested",
        }
        try:
            row_id = _upsert_source_document(client, row)
            if row_id:
                result["documents_upserted"] += 1
                result["_doc_id_to_row_id"][doc["document_id"]] = row_id
            else:
                result["failed_documents"] += 1
                result["errors"].append(f"No id returned for document {doc['filename']}")
        except Exception as exc:
            result["failed_documents"] += 1
            result["errors"].append(f"Document {doc['filename']}: {str(exc)[:120]}")

    # ── Load pairs ─────────────────────────────────────────────────────────
    if not pairs_path.exists():
        result["errors"].append(f"raw_document_pairs_v0.json not found for {subject_slug}")
        return result

    pairs_doc = json.loads(pairs_path.read_text(encoding="utf-8"))
    pairs     = pairs_doc.get("pairs", [])
    result["pairs_in_file"] = len(pairs)

    # ── Sync pairs ─────────────────────────────────────────────────────────
    id_map = result["_doc_id_to_row_id"]

    for pair in pairs:
        qp_doc_id = pair.get("question_paper", {}).get("document_id", "")
        ms_doc_id = pair.get("mark_scheme", {}).get("document_id", "")

        qp_row_id = id_map.get(qp_doc_id)
        ms_row_id = id_map.get(ms_doc_id)

        if not qp_row_id or not ms_row_id:
            # Fall back to querying by filename
            qp_fn = pair.get("question_paper", {}).get("filename", "")
            ms_fn = pair.get("mark_scheme", {}).get("filename", "")
            if not qp_row_id and qp_fn:
                r = (client.table("source_documents")
                     .select("id")
                     .eq("subject_slug", subject_slug)
                     .eq("original_filename", qp_fn)
                     .execute())
                qp_row_id = r.data[0]["id"] if r.data else None
            if not ms_row_id and ms_fn:
                r = (client.table("source_documents")
                     .select("id")
                     .eq("subject_slug", subject_slug)
                     .eq("original_filename", ms_fn)
                     .execute())
                ms_row_id = r.data[0]["id"] if r.data else None

        if not qp_row_id or not ms_row_id:
            result["failed_pairs"] += 1
            result["errors"].append(
                f"Pair {pair.get('pair_id','?')}: could not resolve document ids "
                f"(qp={bool(qp_row_id)} ms={bool(ms_row_id)})"
            )
            continue

        pair_status = pair.get("pair_status", "")
        row = {
            "subject_id":         subject_id,
            "question_paper_id":  qp_row_id,
            "mark_scheme_id":     ms_row_id,
            "pair_key":           pair["pair_id"],
            "status":             "complete" if pair_status == "complete" else pair_status,
        }
        try:
            pair_id = _upsert_source_pair(client, row)
            if pair_id:
                result["pairs_upserted"] += 1
            else:
                result["failed_pairs"] += 1
                result["errors"].append(f"No id returned for pair {pair.get('pair_id','?')}")
        except Exception as exc:
            result["failed_pairs"] += 1
            result["errors"].append(f"Pair {pair.get('pair_id','?')}: {str(exc)[:120]}")

    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(
    now_iso: str,
    subject_results: list[dict],
    errors: list[str],
) -> Path:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "supabase_source_document_sync_report_v1.json"

    total_docs   = sum(r["documents_upserted"] for r in subject_results)
    total_pairs  = sum(r["pairs_upserted"]     for r in subject_results)
    total_failed = sum(r["failed_documents"] + r["failed_pairs"] for r in subject_results)

    if total_failed == 0 and len(errors) == 0:
        status = "passed"
    elif total_docs > 0:
        status = "needs_review"
    else:
        status = "failed"

    # Strip internal _doc_id_to_row_id before writing
    clean_results = [
        {k: v for k, v in r.items() if not k.startswith("_")}
        for r in subject_results
    ]

    report = {
        "report_id":                    "quanta_aptus_supabase_source_document_sync_v1",
        "gate":                         "53C",
        "created_at":                   now_iso,
        "status":                       status,
        "synced_subjects":              [r["subject_slug"] for r in subject_results],
        "subject_count":                len(subject_results),
        "source_document_upserted_count": total_docs,
        "source_pair_upserted_count":   total_pairs,
        "failed_count":                 total_failed,
        "errors":                       errors + [e for r in subject_results for e in r["errors"]],
        "copyright_safety": {
            "uploaded_raw_pdfs":        False,
            "uploaded_extracted_text":  False,
            "metadata_only":            True,
            "copyright_status":         "internal_reference_only",
        },
        "subjects":                     clean_results,
        "next_gate":                    "Gate 53D - Sync Source Items and Skill Units",
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

    from supabase_client_v1 import get_supabase_service_client, mask_secret

    print("=" * 60)
    print("Quanta Aptus - Sync Source Documents v1")
    print("=" * 60)

    client, url = get_supabase_service_client()
    print(f"  connected     : {mask_secret(url)}")

    # ── Resolve organization id once ──────────────────────────────────────
    org_id = _lookup_org_id(client)
    if not org_id:
        print("[ERROR] Organization 'quanta-aptus-local-demo' not found in Supabase.")
        print("  Run seed_local_mvp_demo.sql first.")
        sys.exit(1)

    # ── Determine which subjects to sync ──────────────────────────────────
    if len(sys.argv) > 1:
        slugs_to_sync = [sys.argv[1]]
    else:
        slugs_to_sync = sorted(
            p.name for p in INTAKE_ROOT.iterdir()
            if p.is_dir() and (p / "raw_document_inventory_v0.json").exists()
        )

    print(f"  subjects      : {slugs_to_sync}")

    subject_results: list[dict] = []
    top_level_errors: list[str] = []

    for slug in slugs_to_sync:
        print(f"\n  [{slug}]")

        subject_id = _lookup_subject_id(client, slug)
        if not subject_id:
            msg = f"Subject '{slug}' not found in Supabase subjects table. Skipping."
            print(f"    SKIP: {msg}")
            top_level_errors.append(msg)
            subject_results.append({
                "subject_slug":           slug,
                "inventory_found":        False,
                "pairs_found":            False,
                "documents_in_inventory": 0,
                "pairs_in_file":          0,
                "documents_upserted":     0,
                "pairs_upserted":         0,
                "failed_documents":       0,
                "failed_pairs":           0,
                "errors":                 [msg],
            })
            continue

        result = sync_subject(client, slug, subject_id, org_id)
        subject_results.append(result)

        print(f"    inventory_found   : {result['inventory_found']}")
        print(f"    documents_found   : {result['documents_in_inventory']}")
        print(f"    pairs_found       : {result['pairs_in_file']}")
        print(f"    documents_upserted: {result['documents_upserted']}")
        print(f"    pairs_upserted    : {result['pairs_upserted']}")
        if result["failed_documents"] or result["failed_pairs"]:
            print(f"    failed_docs       : {result['failed_documents']}")
            print(f"    failed_pairs      : {result['failed_pairs']}")
        for err in result["errors"]:
            print(f"    ERROR: {err}")

    # ── Totals ────────────────────────────────────────────────────────────
    total_docs   = sum(r["documents_upserted"] for r in subject_results)
    total_pairs  = sum(r["pairs_upserted"]     for r in subject_results)
    total_failed = sum(r["failed_documents"] + r["failed_pairs"] for r in subject_results)

    status = (
        "passed"       if total_failed == 0 and not top_level_errors
        else "needs_review" if total_docs > 0
        else "failed"
    )

    print(f"\n  total documents upserted : {total_docs}")
    print(f"  total pairs upserted     : {total_pairs}")
    print(f"  failed_count             : {total_failed}")
    print(f"  status                   : {status.upper()}")

    report_path = write_report(now_iso, subject_results, top_level_errors)
    print(f"  report                   -> {report_path}")

    sys.exit(0 if status in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
