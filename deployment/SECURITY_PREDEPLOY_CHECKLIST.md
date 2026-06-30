# Quanta Aptus — Security Pre-Deploy Checklist

Run this checklist before every production deployment.

---

## Environment Files

- [ ] `.env.local` is NOT tracked in git
  ```
  git ls-files apps/admin/.env.local
  # Expected: no output
  ```
- [ ] `.env.production` is NOT tracked in git
  ```
  git ls-files .env.production
  # Expected: no output
  ```
- [ ] Only `.env.example` and `.env.production.example` (placeholders) are committed
- [ ] No secrets in `.env.example` or `.env.production.example` (all values blank)

---

## Service Role Key

- [ ] `SUPABASE_SERVICE_ROLE_KEY` appears ONLY in server-only TypeScript files:
  - `apps/admin/src/lib/liveSupabaseContent.ts`
  - `apps/admin/src/lib/liveSupabaseAttempts.ts`
  - `apps/admin/src/lib/liveSupabaseMarking.ts`
  - `apps/admin/src/lib/liveSupabaseTeacherReview.ts`
  - `apps/admin/src/lib/liveSupabaseAuthContext.ts`
  - `apps/admin/src/lib/liveSupabaseStudentResults.ts`
  - `apps/admin/src/lib/serverSupabaseAuth.ts`
  - Python scripts in `tools/`
- [ ] `SUPABASE_SERVICE_ROLE_KEY` does NOT appear in any `*.tsx` client component
- [ ] `SUPABASE_SERVICE_ROLE_KEY` does NOT appear in any file with `'use client'`
- [ ] No `NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY` variable exists anywhere

Verify with pre-deploy scan:
```
.venv-ingest\Scripts\python.exe tools\deploy\check_gate63_production_readiness_v1.py
```

---

## Cambridge / Source Material

- [ ] No raw Cambridge PDFs are included in the app bundle
  (`data/raw/` is not imported by any file in `apps/admin/src/`)
- [ ] No extracted Cambridge full source text is exposed through any app route
- [ ] All `source_items` have `raw_text = null` in Supabase
- [ ] All `source_documents` have `copyright_status = 'internal_reference_only'`

---

## Data / Content

- [ ] No `skill_name` field stored in Supabase (only `skill_type`)
- [ ] No generated Quanta Aptus resources marked as third-party
- [ ] Demo student data (`local_demo_student`) not accessible via public routes

---

## Authentication

- [ ] `QA_AUTH_DEMO_FALLBACK=false` in production (not `true`)
- [ ] Demo auth users (`admin@quantaaptus.local`, etc.) removed OR passwords rotated
  before real-user traffic
- [ ] Production Supabase project uses separate anon + service role keys from local dev

---

## RLS (Row Level Security)

- [ ] Gate 62 migration applied: `supabase/migrations/000004_rls_role_hardening.sql`
- [ ] RLS enabled on all 10 core tables (verify in Supabase SQL Editor)
- [ ] Helper functions exist: `is_admin()`, `is_teacher()`, `is_student()`, `is_parent()`
- [ ] All 9 protected pages have `requireAppRole` guards

---

## Third-Party Keys

- [ ] No OpenAI API key committed (`sk-...` pattern)
- [ ] No Anthropic API key committed (`sk-ant-...` pattern)
- [ ] No other third-party API keys in committed files

---

## Build Verification

- [ ] `pnpm --filter admin build` completes with zero TypeScript errors (local mode)
- [ ] `pnpm --filter admin build` completes with zero TypeScript errors (live_supabase mode)
- [ ] No `console.log` statements that print env var values

---

## Automated Scan

Run the full pre-deploy scan and verify output:

```powershell
.venv-ingest\Scripts\python.exe tools\deploy\check_gate63_production_readiness_v1.py
```

Expected:
- `service_role_exposed_to_client: false`
- `env_local_tracked: false`
- `raw_cambridge_pdf_exposed: false`
- `overall_status: passed` (or `needs_review` for non-critical items)
