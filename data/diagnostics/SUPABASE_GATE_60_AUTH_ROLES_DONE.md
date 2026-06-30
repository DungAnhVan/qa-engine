# Gate 60 — Supabase Auth + Roles Foundation DONE

**Date:** 2026-06-30
**Status:** `passed`
**Phase:** Phase 2 - Supabase Integration

## What Was Built

| File | Change |
|---|---|
| `supabase/migrations/000003_auth_profile_trigger.sql` | NEW - auth profile trigger |
| `supabase/seed/seed_demo_auth_profiles.sql` | NEW - demo profile seed |
| `tools/supabase/verify_auth_roles_v1.py` | NEW - roles verify script |
| `apps/admin/src/lib/liveSupabaseAuthContext.ts` | NEW - server-only auth context |
| `apps/admin/src/app/system/auth-roles/page.tsx` | NEW - diagnostic page |

## Behavior

- Auth profile trigger migration created.
  - Fires AFTER INSERT on auth.users.
  - Inserts matching row in public.profiles.
  - Role from raw_user_meta_data->>'role'; defaults to 'student'.
  - organization_id defaults to quanta-aptus-local-demo if present.
- Role foundation ready: admin, teacher, student, parent.
- Demo auth context available via getDemoAuthContext().
- Login UI not yet enabled — Gate 61.

## To Apply Auth Trigger

Paste `supabase/migrations/000003_auth_profile_trigger.sql` into
the Supabase Dashboard SQL Editor and run it.

## Security

- `import 'server-only'` in liveSupabaseAuthContext.ts.
- `process.env.SUPABASE_SERVICE_ROLE_KEY` only in allowed server-only files.
- Security scan: 0 violations.
- No OpenAI API calls.

## Ready for Gate 61

Gate 61 will add login UI and RLS permission tests.