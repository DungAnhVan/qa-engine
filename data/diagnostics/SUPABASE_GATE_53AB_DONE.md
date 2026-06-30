# Gate 53A/B — Supabase Client + Subject Sync DONE

**Date:** 2026-06-30
**Status:** `passed`
**Phase:** Phase 2 — Supabase Integration

---

## What Was Delivered

### Gate 53A — Supabase Client Helper

`tools/supabase/supabase_client_v1.py`

- Loads `.env.local` with a built-in minimal parser (no `python-dotenv` dependency).
- Provides `get_supabase_service_client()` — returns `(client, url)`.
- Provides `mask_secret(value)` — masks keys to `eyJhbG...abcd` format.
- Provides `load_env_file(path)` — reusable env loader for other scripts.
- Raises `SystemExit` with a clear message if `supabase` package is missing or env is unset.
- Never prints the full service role key.

### Gate 53B — Subject Sync

`tools/supabase/sync_subjects_to_supabase_v1.py`

- Reads all 22 registered slugs from `subject_adapters.registry.list_registered_slugs()`.
- Calls `get_adapter(slug).get_adapter_metadata()` to get `adapter_name` and `adapter_status`.
- Upserts one row per subject into the Supabase `subjects` table using `on_conflict="subject_slug"`.
- Safe to re-run — does not duplicate or delete rows.
- Writes `data/diagnostics/supabase_subject_sync_report_v1.json`.

---

## What Was Synced

22 IGCSE subjects from the adapter registry:

| Subject | Syllabus | Adapter |
|---|---|---|
| Physics | 0625 | full_adapter |
| Chemistry | 0620 | basic_adapter |
| Biology | 0610 | basic_adapter |
| Mathematics | 0580 | basic_adapter |
| Additional Mathematics | 0606 | basic_adapter |
| International Mathematics | 0607 | basic_adapter |
| Computer Science | 0478 | basic_adapter |
| ICT | 0417 | basic_adapter |
| Business Studies | 0450 | basic_adapter |
| Economics | 0455 | basic_adapter |
| Accounting | 0452 | basic_adapter |
| Geography | 0460 | basic_adapter |
| History | 0470 | basic_adapter |
| Global Perspectives | 0457 | basic_adapter |
| Sociology | 0495 | basic_adapter |
| Travel and Tourism | 0471 | basic_adapter |
| English First Language | 0500 | basic_adapter |
| English Second Language | 0510 | basic_adapter |
| English Literature | 0475 | basic_adapter |
| Combined Science | 0653 | basic_adapter |
| Co-ordinated Sciences | 0654 | basic_adapter |
| Environmental Management | 0680 | basic_adapter |

---

## Security Confirmed

- No Cambridge source PDFs uploaded.
- No full service role key printed — masked only.
- No existing MVP JSON data modified.
- `.env.local` remains gitignored.

---

## Ready for Gate 53C — Sync Source Documents and Source Pairs

Next step: sync `source_documents` and `source_pairs` rows from the local intake pipeline
into Supabase, using the same service-role client pattern.

Files to read:
- `data/intake/cambridge_igcse/*/raw_document_pairs_v0.json`

Table targets:
- `source_documents` (one row per PDF, `copyright_status = 'internal_reference_only'`)
- `source_pairs` (one row per QP/MS pair)
