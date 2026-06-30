# Gate 52 — Supabase Project Migration READY

**Date:** 2026-06-30
**Status:** `ready_for_manual_migration`
**Phase:** Phase 2 — Supabase Integration

---

## What Is Ready

### Gate 51 Schema (Complete)

The full 19-table Supabase Postgres schema is designed and ready to apply:

- `supabase/migrations/000001_init_quanta_aptus_schema.sql` — core schema
- `supabase/migrations/000002_rls_policies.sql` — RLS for all 19 tables
- `supabase/seed/seed_local_mvp_demo.sql` — org, 22 subjects, demo student, Physics v2 package

### Gate 52 Helper Scripts (Created)

| Script | Purpose |
|---|---|
| `tools/supabase/verify_supabase_env_v1.py` | Check .env.local vars without connecting to network |
| `tools/supabase/verify_supabase_schema_v1.py` | Verify live schema tables and seed counts |
| `tools/supabase/gate52_supabase_migration_checklist_v1.md` | Step-by-step manual migration guide |

### Environment Template

`.env.example` created. Copy to `.env.local` and fill in credentials.

`.gitignore` updated: `.env.*` is ignored, `!.env.example` is explicitly allowed.

---

## Waiting For

A live Supabase project with credentials. No automated migration has been run.

**Current verification status:**
- `verify_supabase_env_v1.py`: will report `missing_env` until `.env.local` is filled.
- `verify_supabase_schema_v1.py`: will stop safely with `missing_env` until env is set.

---

## Security Warnings

> **NEVER commit `.env.local` or any file containing real Supabase keys.**
> The service role key bypasses all Row Level Security policies.
> If a key is accidentally committed, rotate it immediately in the Supabase dashboard.

> **Cambridge source PDFs must remain local.**
> Files in `data/raw/` are gitignored and must never be uploaded to Supabase Storage
> or any public service. They are `internal_reference_only` by copyright policy.
> Only original Quanta Aptus generated resources may be stored in Supabase Storage.

---

## How to Proceed

1. Create a Supabase project at [https://supabase.com](https://supabase.com).
2. Follow `tools/supabase/gate52_supabase_migration_checklist_v1.md` step by step.
3. Run both verify scripts and confirm `passed`.
4. Proceed to Gate 53 — Connect Pipeline to Supabase.

---

## Next: Gate 53 — Connect Pipeline to Supabase

Update `tools/ingest/` pipeline scripts to write outputs to Supabase:

- `subjects` rows from adapter registry
- `source_documents` rows from intake pairs
- `skill_units` rows from `build_unified_skill_map.py`
- `resources` rows from authored resource output
- `attempts` rows from student submission handling

Use the Supabase Python client with `service_role` key for pipeline writes.
Use `anon` key for student-facing reads in the app layer.
