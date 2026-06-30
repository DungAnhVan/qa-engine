# Gate 52 — Supabase Migration Checklist v1

**Project:** Quanta Aptus
**Phase:** Phase 2 — Supabase Integration
**Prerequisite:** Gate 51 DONE (`data/diagnostics/SUPABASE_SCHEMA_GATE_51_DONE.md`)

Complete each step in order. Check the box when done.

---

## Step 1 — Create a Supabase Project

- [ ] Go to [https://supabase.com](https://supabase.com) and sign in.
- [ ] Click **New project**.
- [ ] Set project name: `quanta-aptus` (or similar).
- [ ] Set a strong database password. **Save it — you will need it.**
- [ ] Select a region close to your users.
- [ ] Wait for the project to finish provisioning (~2 minutes).

---

## Step 2 — Collect Project Credentials

- [ ] Open the project dashboard.
- [ ] Go to **Settings > API**.
- [ ] Copy:
  - **Project URL** (e.g. `https://abcdefghij.supabase.co`)
  - **anon / public** key
  - **service_role** key
- [ ] Go to **Settings > Database**.
- [ ] Copy the **database password** you set in Step 1.
- [ ] Note the **Project Ref** (the short ID in your project URL).

> **WARNING:** The `service_role` key bypasses Row Level Security.
> Never expose it in client-side code, browser, or public repositories.

---

## Step 3 — Create `.env.local`

- [ ] In the project root, copy `.env.example` to `.env.local`:
  ```
  copy .env.example .env.local
  ```
- [ ] Open `.env.local` and fill in the values:
  ```
  SUPABASE_URL=https://your-project-ref.supabase.co
  SUPABASE_ANON_KEY=your-anon-key
  SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
  SUPABASE_DB_PASSWORD=your-db-password
  SUPABASE_PROJECT_REF=your-project-ref
  ```
- [ ] Verify `.env.local` is listed in `.gitignore` (it is — already configured).
- [ ] **Never commit `.env.local`.**

---

## Step 4 — Verify Environment Variables

- [ ] Run:
  ```
  .\.venv-ingest\Scripts\python.exe tools\supabase\verify_supabase_env_v1.py
  ```
- [ ] Confirm output shows `[ENV_OK]`.
- [ ] Confirm no full key values are printed (only masked: `eyJhbG...abcd`).
- [ ] Check report at `data/diagnostics/supabase_env_check_report_v1.json`.

---

## Step 5 — Apply Core Schema Migration

- [ ] Open the Supabase **SQL Editor** in your project dashboard.
- [ ] Click **New query**.
- [ ] Open `supabase/migrations/000001_init_quanta_aptus_schema.sql` locally.
- [ ] **Copy the entire file content** and paste into the SQL Editor.
- [ ] Click **Run**.
- [ ] Confirm: no errors. Expected result: tables created, triggers installed.
- [ ] In **Table Editor**, verify these tables are visible:
  `organizations`, `profiles`, `students`, `subjects`, `resources`,
  `attempts`, `skill_units` (and the other 12 tables).

---

## Step 6 — Apply RLS Policies

- [ ] In the SQL Editor, click **New query**.
- [ ] Open `supabase/migrations/000002_rls_policies.sql` locally.
- [ ] Copy and paste the entire file content.
- [ ] Click **Run**.
- [ ] Confirm: no errors.
- [ ] In **Authentication > Policies**, verify RLS is enabled on all 19 tables.

---

## Step 7 — Run Seed Data

- [ ] In the SQL Editor, click **New query**.
- [ ] Open `supabase/seed/seed_local_mvp_demo.sql` locally.
- [ ] Copy and paste the entire file content.
- [ ] Click **Run**.
- [ ] Confirm: no errors. Expected rows inserted:
  - 1 organization (`quanta-aptus-local-demo`)
  - 22 subjects (all Cambridge IGCSE adapter-registry slugs)
  - 1 demo student (`local_demo_student`)
  - 1 resource package (`cambridge_igcse_physics_0625_resource_package_v2`, status = `active`)

> **IMPORTANT:** The seed script uses `on conflict ... do nothing`.
> It is safe to run multiple times without duplicating rows.

---

## Step 8 — Verify Schema in Live Project

- [ ] Install the Supabase Python client if not already installed:
  ```
  .\.venv-ingest\Scripts\pip.exe install supabase
  ```
- [ ] Run:
  ```
  .\.venv-ingest\Scripts\python.exe tools\supabase\verify_supabase_schema_v1.py
  ```
- [ ] Confirm output shows `[PASSED]`.
- [ ] Check report at `data/diagnostics/supabase_schema_verify_report_v1.json`.
- [ ] Confirm:
  - `tables_ok: true`
  - `seed_checks.subjects.count >= 22`
  - `seed_checks.active_physics_package.active: true`

---

## Step 9 — Copyright / Data Safety Check

- [ ] Confirm **no Cambridge source PDFs** have been uploaded to Supabase Storage.
  - Source PDFs remain in `data/raw/` (local only, gitignored).
  - Markitdown `.md` outputs may be uploaded in a later gate with explicit licensing review.
- [ ] Confirm `source_documents.copyright_status` defaults to `internal_reference_only`.
- [ ] Confirm no student-generated content contains copied Cambridge question text.

---

## Step 10 — Gate 52 Complete

- [ ] All 9 steps above are checked.
- [ ] `data/diagnostics/supabase_schema_verify_report_v1.json` shows `status: passed`.
- [ ] `data/diagnostics/supabase_env_check_report_v1.json` shows `status: env_ok`.
- [ ] Supabase dashboard shows 19 tables, RLS enabled, 22 subjects seeded.

Gate 52 is complete. Proceed to:

> **Gate 53 — Connect Pipeline to Supabase**
> Update `tools/ingest/` scripts to write intake, corpus, and skill-map outputs
> to Supabase tables using the service-role client. Start with `subjects` and
> `source_documents` inserts from the ingest pipeline.

---

## Quick Reference

| File | Purpose |
|---|---|
| `.env.example` | Template — copy to `.env.local` |
| `supabase/migrations/000001_init_quanta_aptus_schema.sql` | Core 19-table schema |
| `supabase/migrations/000002_rls_policies.sql` | RLS for all tables |
| `supabase/seed/seed_local_mvp_demo.sql` | Demo org, 22 subjects, student, package |
| `tools/supabase/verify_supabase_env_v1.py` | Check env vars (no network) |
| `tools/supabase/verify_supabase_schema_v1.py` | Verify live schema + seed |
| `docs/database/supabase_schema_v1.md` | Schema design rationale |
| `docs/database/supabase_table_map_v1.md` | Local JSON to Supabase table mapping |
