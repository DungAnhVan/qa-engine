# Gate 53C — Sync Source Documents + Source Pairs DONE

**Date:** 2026-06-30
**Status:** `passed` (single subject) / `needs_review` (all subjects — physics_empty_test skipped as expected)
**Phase:** Phase 2 — Supabase Integration

---

## What Was Synced

### source_documents (28 rows total across 4 subjects)

| Subject | Documents Upserted |
|---|---|
| biology_0610 | 6 |
| chemistry_0620 | 6 |
| mathematics_0580 | 4 |
| physics_0625 | 12 |

### source_pairs (14 rows total)

| Subject | Pairs Upserted |
|---|---|
| biology_0610 | 3 |
| chemistry_0620 | 3 |
| mathematics_0580 | 2 |
| physics_0625 | 6 |

---

## Copyright Safety Confirmed

- No raw Cambridge PDFs uploaded.
- No extracted Cambridge text (markitdown `.md` outputs) uploaded.
- Only metadata synced: filename, series, year, paper code, variant, source_type, document_id.
- `storage_path` stores a local relative path only — the file remains on disk.
- `copyright_status = 'internal_reference_only'` on every row.
- `ingest_status = 'ingested'` (document was processed locally; not available remotely).

---

## Deduplication Strategy

No `UNIQUE` constraint exists on `source_documents` in the current schema.
The sync script uses manual deduplication:

1. For `source_documents`: query by `(subject_slug, original_filename)` before insert.
2. For `source_pairs`: query by `pair_key` before insert.
3. If found: `UPDATE` existing row.
4. If not found: `INSERT` new row.

The script is safe to re-run — idempotent by design.

---

## physics_empty_test Skipped

`physics_empty_test` is a local test folder used during pipeline development.
It is not registered in the subject adapter registry and has no corresponding
`subjects` row in Supabase. The script skips it with a clear message and records
it in the report `errors` array. This is expected behavior.

---

## Ready for Gate 53D — Sync Source Items and Skill Units

Next step: sync `source_items` rows from the parsed corpus output and
`skill_units` rows from the unified skill map into Supabase.

Files to read:
- `data/bank/cambridge_igcse/*/source_corpus/unified_source_corpus_v0.json`
- `data/bank/cambridge_igcse/*/skill_map/unified_skill_map_v0.json`

Table targets:
- `source_items` (one row per parsed question, linked to source_documents)
- `skill_units` (one row per classified item, linked to source_items + subjects)
