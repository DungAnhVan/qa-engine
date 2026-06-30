"""
Gate 53D — Sync Source Items + Skill Units to Supabase v1.

Reads unified_source_corpus_v0.json and unified_skill_map_v0.json
from data/bank/cambridge_igcse/<subject_slug>/ and syncs metadata into
Supabase tables: source_items and skill_units.

COPYRIGHT SAFETY:
  - raw_text is ALWAYS null — Cambridge question text is never uploaded.
  - short_evidence / skill description from skill map is not synced.
  - Only derived metadata (topic, skill_type, confidence) is synced to skill_units.

CLI:
  # All subjects:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\sync_source_items_skill_units_to_supabase_v1.py

  # Single subject:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\sync_source_items_skill_units_to_supabase_v1.py physics_0625
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
SUPABASE_TOOL = Path(__file__).parent
BANK_ROOT     = PROJECT_ROOT / "data" / "bank" / "cambridge_igcse"
DIAG_DIR      = PROJECT_ROOT / "data" / "diagnostics"

if str(SUPABASE_TOOL) not in sys.path:
    sys.path.insert(0, str(SUPABASE_TOOL))


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Supabase pre-fetch caches (one round-trip per subject per table)
# ---------------------------------------------------------------------------

def _fetch_pair_map(client, subject_id: str) -> dict[str, dict]:
    """pair_key -> {id, question_paper_id}"""
    r = (
        client.table("source_pairs")
        .select("id, pair_key, question_paper_id")
        .eq("subject_id", subject_id)
        .execute()
    )
    return {row["pair_key"]: row for row in (r.data or [])}


def _fetch_existing_source_items(client, subject_id: str) -> dict[str, str]:
    """item_key -> row id"""
    r = (
        client.table("source_items")
        .select("id, item_key")
        .eq("subject_id", subject_id)
        .execute()
    )
    return {row["item_key"]: row["id"] for row in (r.data or [])}


def _fetch_existing_skill_units(client, subject_id: str) -> dict[tuple, str]:
    """(source_item_id, topic, skill_type) -> row id"""
    r = (
        client.table("skill_units")
        .select("id, source_item_id, topic, skill_type")
        .eq("subject_id", subject_id)
        .execute()
    )
    return {
        (row["source_item_id"], row["topic"], row["skill_type"]): row["id"]
        for row in (r.data or [])
    }


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------

def _upsert_source_item(
    client,
    row: dict,
    existing: dict[str, str],
) -> Optional[str]:
    """Insert or update source_item. Returns row id."""
    item_key = row["item_key"]
    if item_key in existing:
        row_id = existing[item_key]
        update_fields = {k: v for k, v in row.items()
                         if k not in ("subject_id", "item_key")}
        client.table("source_items").update(update_fields).eq("id", row_id).execute()
        return row_id
    else:
        resp = client.table("source_items").insert(row).execute()
        if resp.data:
            new_id = resp.data[0]["id"]
            existing[item_key] = new_id  # update cache
            return new_id
        return None


def _upsert_skill_unit(
    client,
    row: dict,
    existing: dict[tuple, str],
) -> Optional[str]:
    """Insert or update skill_unit. Returns row id."""
    key = (row.get("source_item_id"), row.get("topic", ""), row.get("skill_type", ""))
    if key in existing:
        row_id = existing[key]
        client.table("skill_units").update(row).eq("id", row_id).execute()
        return row_id
    else:
        resp = client.table("skill_units").insert(row).execute()
        if resp.data:
            new_id = resp.data[0]["id"]
            existing[key] = new_id  # update cache
            return new_id
        return None


# ---------------------------------------------------------------------------
# Per-subject sync
# ---------------------------------------------------------------------------

def sync_subject(client, subject_slug: str, subject_id: str) -> dict:
    corpus_path   = BANK_ROOT / subject_slug / "source_corpus" / "unified_source_corpus_v0.json"
    skill_map_path= BANK_ROOT / subject_slug / "skill_map"    / "unified_skill_map_v0.json"

    result = {
        "subject_slug":          subject_slug,
        "corpus_found":          corpus_path.exists(),
        "skill_map_found":       skill_map_path.exists(),
        "skill_units_skipped":   False,
        "source_items_found":    0,
        "source_items_upserted": 0,
        "skill_units_found":     0,
        "skill_units_upserted":  0,
        "failed_source_items":   0,
        "failed_skill_units":    0,
        "source_item_warnings":  0,
        "skill_unit_warnings":   0,
        "errors":                [],
        "warnings":              [],
    }

    corpus    = _load(corpus_path)
    skill_map = _load(skill_map_path)

    if corpus is None and skill_map is None:
        result["errors"].append(f"No corpus or skill map found for {subject_slug}.")
        return result

    # ── Pre-fetch caches to minimise round-trips ──────────────────────────
    pair_map      = _fetch_pair_map(client, subject_id)
    existing_items= _fetch_existing_source_items(client, subject_id)
    existing_su   = _fetch_existing_skill_units(client, subject_id)

    # ── Extract document-level adapter meta from skill map ────────────────
    sm_adapter_name   = (skill_map or {}).get("adapter_name",   "unknown")
    sm_adapter_status = (skill_map or {}).get("adapter_status", "basic_adapter")

    # ── Choose source for source_items ────────────────────────────────────
    # Prefer skill_map (per-question rows). Fall back to corpus (per-paper rows).
    if skill_map:
        su_items = skill_map.get("skill_units", [])
        result["source_items_found"] = len(su_items)
        result["skill_units_found"]  = len(su_items)

        for su in su_items:
            pair_key  = su.get("pair_id", "")
            pair_info = pair_map.get(pair_key)

            if pair_info is None:
                result["source_item_warnings"] += 1
                result["warnings"].append(
                    f"Pair key '{pair_key}' not found in source_pairs — "
                    f"source_document_id and source_pair_id will be null for item {su.get('skill_unit_id','?')}."
                )

            source_doc_id  = (pair_info or {}).get("question_paper_id")
            source_pair_id = (pair_info or {}).get("id")

            # ── source_item row ───────────────────────────────────────────
            item_row = {
                "subject_id":          subject_id,
                "source_document_id":  source_doc_id,
                "source_pair_id":      source_pair_id,
                "item_key":            su["skill_unit_id"],
                "question_number":     su.get("question_number"),
                "component_type":      su.get("component_type"),
                "route":               su.get("assessment_mode"),
                "raw_text":            None,     # NEVER upload Cambridge source text
                "marks":               su.get("marks"),
                "needs_review":        su.get("needs_human_review", False),
            }
            try:
                item_id = _upsert_source_item(client, item_row, existing_items)
                if item_id:
                    result["source_items_upserted"] += 1
                else:
                    result["failed_source_items"] += 1
                    result["errors"].append(
                        f"No id returned for source_item {su.get('skill_unit_id','?')}"
                    )
            except Exception as exc:
                result["failed_source_items"] += 1
                result["errors"].append(
                    f"source_item {su.get('skill_unit_id','?')}: {str(exc)[:120]}"
                )
                item_id = None

            # ── skill_unit row ────────────────────────────────────────────
            confidence   = su.get("confidence")
            adapt_status = su.get("adapter_status", sm_adapter_status)
            adapt_name   = su.get("adapter_name",   sm_adapter_name)
            nhr          = su.get("needs_human_review", False)
            resource_type= su.get("resource_type",  "unknown")
            mkw          = su.get("matched_keywords", [])

            if item_id is None:
                result["skill_unit_warnings"] += 1
                result["warnings"].append(
                    f"skill_unit {su.get('skill_unit_id','?')}: source_item_id is null — inserting without link."
                )

            su_row = {
                "subject_id":         subject_id,
                "source_item_id":     item_id,
                "topic":              su.get("topic",     "Unknown"),
                "subtopic":           su.get("subtopic",  ""),
                "skill_type":         su.get("skill_type","unknown"),
                "resource_type":      resource_type,
                "confidence":         confidence,
                "adapter_name":       adapt_name,
                "adapter_status":     adapt_status,
                "adapter_version":    "v1",
                "needs_human_review": nhr,
                "matched_keywords":   json.dumps(mkw) if isinstance(mkw, list) else mkw,
            }
            try:
                su_id = _upsert_skill_unit(client, su_row, existing_su)
                if su_id:
                    result["skill_units_upserted"] += 1
                else:
                    result["failed_skill_units"] += 1
                    result["errors"].append(
                        f"No id returned for skill_unit {su.get('skill_unit_id','?')}"
                    )
            except Exception as exc:
                result["failed_skill_units"] += 1
                result["errors"].append(
                    f"skill_unit {su.get('skill_unit_id','?')}: {str(exc)[:120]}"
                )

    elif corpus:
        # Corpus-only path: one source_item per source/paper (no skill_units)
        result["skill_units_skipped"] = True
        sources = corpus.get("sources", [])
        result["source_items_found"] = len(sources)

        for src in sources:
            pair_key  = src.get("pair_id", "")
            pair_info = pair_map.get(pair_key)

            if pair_info is None:
                result["source_item_warnings"] += 1
                result["warnings"].append(
                    f"Pair key '{pair_key}' not in source_pairs for {subject_slug}."
                )

            item_row = {
                "subject_id":         subject_id,
                "source_document_id": (pair_info or {}).get("question_paper_id"),
                "source_pair_id":     (pair_info or {}).get("id"),
                "item_key":           src["source_id"],
                "question_number":    None,
                "component_type":     src.get("component_type"),
                "route":              src.get("route"),
                "raw_text":           None,
                "marks":              None,
                "needs_review":       False,
            }
            try:
                item_id = _upsert_source_item(client, item_row, existing_items)
                if item_id:
                    result["source_items_upserted"] += 1
                else:
                    result["failed_source_items"] += 1
                    result["errors"].append(f"No id returned for source_item {src.get('source_id','?')}")
            except Exception as exc:
                result["failed_source_items"] += 1
                result["errors"].append(f"source_item {src.get('source_id','?')}: {str(exc)[:120]}")

    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(
    now_iso: str,
    subject_results: list[dict],
    top_errors: list[str],
) -> Path:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "supabase_source_items_skill_units_sync_report_v1.json"

    total_items  = sum(r["source_items_upserted"] for r in subject_results)
    total_su     = sum(r["skill_units_upserted"]  for r in subject_results)
    total_failed = sum(r["failed_source_items"] + r["failed_skill_units"] for r in subject_results)
    item_warns   = sum(r["source_item_warnings"]  for r in subject_results)
    su_warns     = sum(r["skill_unit_warnings"]   for r in subject_results)

    status = (
        "passed"       if total_failed == 0 and not top_errors
        else "needs_review" if total_items > 0
        else "failed"
    )

    clean = [
        {k: v for k, v in r.items() if k != "warnings"}
        for r in subject_results
    ]

    report = {
        "report_id":                       "quanta_aptus_supabase_source_items_skill_units_sync_v1",
        "gate":                            "53D",
        "created_at":                      now_iso,
        "status":                          status,
        "synced_subjects":                 [r["subject_slug"] for r in subject_results],
        "subject_count":                   len(subject_results),
        "source_items_upserted_count":     total_items,
        "skill_units_upserted_count":      total_su,
        "source_item_match_warnings":      item_warns,
        "skill_unit_match_warnings":       su_warns,
        "failed_count":                    total_failed,
        "errors":                          top_errors + [e for r in subject_results for e in r["errors"]],
        "copyright_safety": {
            "uploaded_raw_pdfs":                False,
            "uploaded_extracted_text":          False,
            "source_items_raw_text_synced":     False,
            "metadata_only_for_source_items":   True,
            "derived_skill_metadata_synced":    True,
        },
        "subjects":                        clean,
        "next_gate":                       "Gate 53E - Sync Resource Packages and Resources",
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
    print("Quanta Aptus - Sync Source Items + Skill Units v1")
    print("=" * 60)

    client, url = get_supabase_service_client()
    print(f"  connected     : {mask_secret(url)}")

    # ── Determine subjects ─────────────────────────────────────────────────
    if len(sys.argv) > 1:
        slugs = [sys.argv[1]]
    else:
        slugs = sorted(
            p.name for p in BANK_ROOT.iterdir()
            if p.is_dir() and (
                (p / "source_corpus" / "unified_source_corpus_v0.json").exists()
                or (p / "skill_map" / "unified_skill_map_v0.json").exists()
            )
        )

    print(f"  subjects      : {slugs}")

    subject_results: list[dict] = []
    top_errors: list[str] = []

    for slug in slugs:
        print(f"\n  [{slug}]")

        # Look up subject_id
        r = client.table("subjects").select("id").eq("subject_slug", slug).execute()
        if not r.data:
            msg = f"Subject '{slug}' not found in Supabase subjects table. Skipping."
            print(f"    SKIP: {msg}")
            top_errors.append(msg)
            subject_results.append({
                "subject_slug":          slug,
                "corpus_found":          False,
                "skill_map_found":       False,
                "skill_units_skipped":   True,
                "source_items_found":    0,
                "source_items_upserted": 0,
                "skill_units_found":     0,
                "skill_units_upserted":  0,
                "failed_source_items":   0,
                "failed_skill_units":    0,
                "source_item_warnings":  0,
                "skill_unit_warnings":   0,
                "errors":                [msg],
            })
            continue

        subject_id = r.data[0]["id"]
        result = sync_subject(client, slug, subject_id)
        subject_results.append(result)

        print(f"    corpus_found        : {result['corpus_found']}")
        print(f"    skill_map_found     : {result['skill_map_found']}")
        print(f"    source_items_found  : {result['source_items_found']}")
        print(f"    source_items_up     : {result['source_items_upserted']}")
        if not result["skill_units_skipped"]:
            print(f"    skill_units_found   : {result['skill_units_found']}")
            print(f"    skill_units_up      : {result['skill_units_upserted']}")
        else:
            print(f"    skill_units         : skipped (no skill map)")
        if result["source_item_warnings"]:
            print(f"    item_warnings       : {result['source_item_warnings']}")
        if result["skill_unit_warnings"]:
            print(f"    su_warnings         : {result['skill_unit_warnings']}")
        if result["failed_source_items"] or result["failed_skill_units"]:
            print(f"    failed_items        : {result['failed_source_items']}")
            print(f"    failed_su           : {result['failed_skill_units']}")
        for err in result["errors"]:
            print(f"    ERROR: {err[:100]}")

    # ── Totals ────────────────────────────────────────────────────────────
    total_items  = sum(r["source_items_upserted"] for r in subject_results)
    total_su     = sum(r["skill_units_upserted"]  for r in subject_results)
    total_failed = sum(r["failed_source_items"] + r["failed_skill_units"] for r in subject_results)
    status = (
        "passed"       if total_failed == 0 and not top_errors
        else "needs_review" if total_items > 0
        else "failed"
    )

    print(f"\n  source_items_upserted : {total_items}")
    print(f"  skill_units_upserted  : {total_su}")
    print(f"  failed_count          : {total_failed}")
    print(f"  status                : {status.upper()}")

    report_path = write_report(now_iso, subject_results, top_errors)
    print(f"  report                -> {report_path}")

    sys.exit(0 if status in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
