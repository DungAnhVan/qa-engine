# Gate 54 - Admin App Supabase Read Mode DONE

**Date:** 2026-06-30
**Status:** `passed`
**Phase:** Phase 2 - Supabase Integration

## What Was Built

Added `QA_CONTENT_SOURCE` mode switching to the admin Next.js app:

| File | Change |
|---|---|
| `apps/admin/src/lib/contentSource.ts` | NEW - ContentSourceMode type + getContentSourceMode() |
| `apps/admin/src/lib/supabaseExportContent.ts` | NEW - server-side Supabase export readers |
| `apps/admin/src/lib/activeContent.ts` | UPDATED - branches on mode |
| `apps/admin/src/lib/studentResources.ts` | UPDATED - branches on mode |
| `apps/admin/src/lib/contentRegistry.ts` | UPDATED - sourceMode in RegistryResult |
| `apps/admin/src/app/system/content-source/page.tsx` | NEW - diagnostic page |
| `.env.example` | UPDATED - QA_CONTENT_SOURCE=local |

## Security Constraints Satisfied

- Browser never connects to Supabase directly.
- Service role key never in frontend code.
- Local JSON mode fully preserved (default).
- Supabase schema not modified.
- No existing data modified.
- No Cambridge source text reached the frontend.

## How to Enable Supabase Export Mode

In `apps/admin/.env.local`:
```
QA_CONTENT_SOURCE=supabase_export
```

Run the export script first if not already done:
```
.venv-ingest\Scripts\python.exe tools\supabase\read_active_package_from_supabase_v1.py
```

Then visit `/system/content-source` to verify the mode is active.