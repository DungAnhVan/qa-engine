# Gate 51 — Supabase Schema Design DONE

**Date:** 2026-06-30
**Status:** `passed`
**Phase:** Phase 2 — Supabase Integration

---

## What Was Delivered

### Migration Files

| File | Purpose |
|---|---|
| `supabase/migrations/000001_init_quanta_aptus_schema.sql` | 19-table core schema with extensions, triggers, indexes |
| `supabase/migrations/000002_rls_policies.sql` | Row Level Security for all 19 tables across 4 roles |

### Seed File

| File | Purpose |
|---|---|
| `supabase/seed/seed_local_mvp_demo.sql` | Organization, 22 subjects, demo student, Physics v2 package |

### Documentation

| File | Purpose |
|---|---|
| `docs/database/supabase_schema_v1.md` | Table groups, adapter fields, auth/RLS, design rationale |
| `docs/database/supabase_table_map_v1.md` | Maps 21 local JSON files to future Supabase table rows |

### Diagnostics

| File | Purpose |
|---|---|
| `data/diagnostics/supabase_schema_design_report_v1.json` | Machine-readable Gate 51 report |
| `data/diagnostics/SUPABASE_SCHEMA_GATE_51_DONE.md` | This file |

---

## Multi-subject Schema: Complete

The schema treats every subject equally from the first row:

- Every content and attempt table has a `subject_id` FK to `subjects`.
- `subjects` is seeded with all 22 IGCSE adapter-registry slugs.
- No table hard-codes Physics, Chemistry, Biology, or Mathematics.
- Adding a new subject requires only: a new `subjects` row and a new adapter registration.

---

## Auth and RLS Design: Drafted

All 19 tables have RLS enabled. Policies cover:

| Role | Key access |
|---|---|
| `admin` | Full access within their organization |
| `teacher` | Read org resources, attempts, reviews; insert reviews |
| `student` | Own attempts and reports; published resources in their org |
| `parent` | Reports and attempts for linked students only |

Source documents and source items are not readable by students or parents.

---

## Subject Adapter Fields: First-class Columns

`adapter_status`, `confidence`, and `needs_human_review` are SQL columns, not JSON keys.
This means:

- `where needs_human_review = true` is a fast indexed query.
- RLS policies can scope access by `adapter_status` if needed.
- Teacher review queue is a direct SQL filter, not an application-layer scan.

---

## Local JSON to Table Map: Complete

21 local pipeline output files mapped to target Supabase tables.
See `docs/database/supabase_table_map_v1.md` for the full mapping and migration order.

---

## What Is NOT Yet Done

- No live Supabase project created.
- No Supabase CLI configuration.
- No auth trigger for `profiles` auto-creation.
- No Supabase Edge Functions.
- No storage bucket policy for markitdown outputs.
- Pipeline scripts not yet connected to Supabase client.
- Cambridge source PDFs remain local only — must never be uploaded.

---

## Ready for Gate 52 — Supabase Project + Migration

1. Create Supabase project.
2. Apply `000001_init_quanta_aptus_schema.sql`.
3. Apply `000002_rls_policies.sql`.
4. Run `seed_local_mvp_demo.sql` with service-role.
5. Verify 22 subjects + active Physics package present.
6. Write auth trigger for `profiles` table.
7. Connect pipeline to Supabase client library.
