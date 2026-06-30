# Gate 65B — Production Readiness Runtime Patch DONE

Generated: 2026-06-30

## Problem

`/api/system/readiness` returned `status: "failed"` on the live Vercel deployment
because it used `fs.existsSync` to check source file paths such as
`apps/admin/src/app/login/page.tsx`. In Vercel's production Lambda runtime,
only the compiled `.next` output is present — source files do not exist —
so every file check returned `false`, triggering critical failures.

## Root Cause

```
process.cwd()              →  /var/task   (Vercel Lambda root)
fileCheck('src/app/login') →  /var/task/src/app/login/page.tsx  →  false
```

The file DOES exist in the local repo and IS compiled into the build, but
`existsSync` has no way to verify that in the production runtime.

## Fix Applied

### `apps/admin/src/app/api/system/readiness/route.ts`

- Added `isProduction = process.env.NODE_ENV === 'production'` detection.
- All source-file checks (`fileChecks[]` array) now return `status: 'SKIP'`
  when `isProduction` is true, with `detail: "skipped in production runtime"`.
- Critical failures in production are **env-only**:
  - `content_source_valid` — FAIL if `QA_CONTENT_SOURCE` has an invalid value
  - Supabase env checks — FAIL only when `QA_CONTENT_SOURCE=live_supabase` and the var is absent
- WARN conditions (cause `needs_review`, not `failed`):
  - `demo_fallback_off` not set to `false`
  - `content_source_is_live` is not `live_supabase`
  - Any Supabase env missing when in local mode
- Response shape updated:
  ```json
  {
    "status": "ready",
    "environment": "production",
    "content_source": "live_supabase",
    "checks": [
      { "key": "content_source_valid", "label": "...", "status": "PASS", "detail": "...", "critical": true },
      { "key": "login_ui_exists",      "label": "...", "status": "SKIP", "detail": "skipped in production runtime...", "critical": false }
    ],
    "timestamp": "..."
  }
  ```

### `apps/admin/src/app/system/readiness/page.tsx`

- Added `isProduction = process.env.NODE_ENV === 'production'` detection.
- `buildChecks(mode, isLive, isProduction)` now takes a third argument.
- All source/repo file checks call `fileCheck(label, path, repoLevel?)` helper
  which returns a SKIP entry when `isProduction` is true.
- UI changes:
  - Shows `Environment: production | development` badge prominently.
  - SKIP rows rendered in grey to distinguish from WARN/FAIL.
  - Summary line includes SKIP count: `7 PASS · 0 WARN · 0 FAIL · 12 SKIP`.
  - READY message says "Production environment looks healthy." in production.

## Acceptance Criteria (all met)

| Check | Result |
|---|---|
| `/api/system/readiness` returns `status: ready` or `needs_review` in production | Fixed |
| `status: failed` ONLY for invalid content source or missing Supabase env when live | Fixed |
| File existence checks do NOT cause failures in production | Fixed (SKIP) |
| Local dev still shows file check results as WARN (not FAIL) | Preserved |
| Gate 65 smoke test still passes: accepts `ready` or `needs_review` | Compatible |
| No secrets exposed | No change |
| `isProduction` detection uses `process.env.NODE_ENV === 'production'` | Correct |

## Files Modified

- `apps/admin/src/app/api/system/readiness/route.ts` — API route
- `apps/admin/src/app/system/readiness/page.tsx` — UI page

## Unchanged Files

- `apps/admin/src/app/api/system/health/route.ts` — health API (no file checks)
- `apps/admin/src/app/system/health/page.tsx` — health UI (no file checks)
- `tools/deploy/test_gate65_post_deploy_smoke_v1.py` — accepts `ready`/`needs_review`
- `tools/deploy/build_gate65_post_deploy_report_v1.py` — reads smoke test output

## How to Verify

After deploying to Vercel:

```powershell
# Should return status: ready or needs_review (not failed)
curl https://your-app.vercel.app/api/system/readiness

# Re-run smoke test
.venv-ingest\Scripts\python.exe tools\deploy\test_gate65_post_deploy_smoke_v1.py https://your-app.vercel.app
```

Expected production response:
```json
{
  "status": "ready",
  "environment": "production",
  "content_source": "live_supabase",
  "checks": [
    { "key": "content_source_valid",        "status": "PASS" },
    { "key": "content_source_is_live",      "status": "PASS" },
    { "key": "demo_fallback_off",           "status": "PASS" },
    { "key": "supabase_url_present",        "status": "PASS" },
    { "key": "next_public_supabase_url_present", "status": "PASS" },
    { "key": "anon_key_present",            "status": "PASS" },
    { "key": "service_role_present",        "status": "PASS" },
    { "key": "login_ui_exists",             "status": "SKIP" },
    ...
  ]
}
```
