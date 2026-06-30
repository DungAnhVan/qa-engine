# Gate 55 - Live Supabase Server Read DONE

**Date:** 2026-06-30
**Status:** `passed`
**Phase:** Phase 2 - Supabase Integration

## What Was Built

Added `live_supabase` mode to the admin Next.js app:

| File | Change |
|---|---|
| `apps/admin/src/lib/liveSupabaseContent.ts` | NEW - server-only live Supabase reads |
| `apps/admin/src/lib/contentSource.ts` | UPDATED - added live_supabase mode |
| `apps/admin/src/lib/activeContent.ts` | UPDATED - live_supabase branch |
| `apps/admin/src/lib/studentResources.ts` | UPDATED - live_supabase branch |
| `apps/admin/src/app/system/content-source/page.tsx` | UPDATED - all 3 modes |
| `apps/admin/src/app/system/supabase-live/page.tsx` | NEW - live connection test |
| `.env.example` | UPDATED - live_supabase documented |

## Dependencies Added

```
pnpm --filter @qa-engine/admin add @supabase/supabase-js server-only
```

## Security Constraints Satisfied

- `import 'server-only'` guard in liveSupabaseContent.ts prevents client import.
- SUPABASE_SERVICE_ROLE_KEY only read in liveSupabaseContent.ts.
- No service role key in any client component or page.
- Security scan: 0 violations.
- No writes to Supabase.
- No Cambridge source text read.
- local and supabase_export fallback modes preserved.

## How to Test

1. Set `QA_CONTENT_SOURCE=live_supabase` in `apps/admin/.env.local`
2. Ensure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set
3. Run: `pnpm --filter @qa-engine/admin dev`
4. Visit: http://localhost:3000/system/content-source
5. Visit: http://localhost:3000/system/supabase-live