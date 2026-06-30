# Gate 56 - Student Attempt Write to Supabase DONE

**Date:** 2026-06-30
**Status:** `passed`
**Phase:** Phase 2 - Supabase Integration

## What Was Built

| File | Change |
|---|---|
| `apps/admin/src/lib/liveSupabaseAttempts.ts` | NEW - server-only attempt write |
| `apps/admin/src/app/api/student-attempts/route.ts` | UPDATED - live_supabase branch |
| `apps/admin/src/app/learn/practice/AttemptForm.tsx` | UPDATED - Supabase feedback |
| `apps/admin/src/app/system/attempt-write/page.tsx` | NEW - diagnostic page |
| `tools/supabase/test_gate56_attempt_write_v1.py` | NEW - integration test |

## Behavior

- Student attempts can be written to Supabase in `live_supabase` mode.
- Local JSON fallback remains unchanged (default mode).
- Marking NOT enabled — `marking_status = 'unmarked'` on all new attempts.
- Demo student resolved by `external_code = 'local_demo_student'`.
- Resource resolved by `resource_key` from the resources table.
- `parent_attempt_id` validated as UUID before insert (local IDs rejected).

## Security

- `import 'server-only'` in liveSupabaseAttempts.ts.
- `process.env.SUPABASE_SERVICE_ROLE_KEY` only in allowed server-only files.
- Security scan: 0 violations.
- No Cambridge source text written.

## Ready for Gate 57

Gate 57 will implement marking of attempts in Supabase (`marked_attempts` table).