# Gate 61 — Login UI + RLS Permission Tests DONE

Created: 2026-06-30T13:37:53.387350+00:00

## Summary

- Demo auth users created (admin / teacher / student / parent).
- Login/logout UI available at `/login` and `/logout`.
- Browser Supabase client uses anon key only (NEXT_PUBLIC vars).
- Server auth module (`serverSupabaseAuth.ts`) is server-only.
- Profiles verified via `public.profiles` table.
- RLS permission tests run (foundation — hardening deferred to Gate 62).
- Service role key not exposed to client/browser.
- `QA_AUTH_DEMO_FALLBACK=true` provides safe dev fallback when no real session.

## Diagnostic pages

- `/login` — Login form
- `/logout` — Sign out
- `/system/auth-session` — Session diagnostic
- `/system/auth-roles` — Auth roles diagnostic

## Ready for

Gate 62 - RLS Hardening + Role-Based App Access
