# Gate 65 — Post-Deploy Smoke Test

Run this after deploying the admin app to Vercel (Gate 64).

---

## Automated Smoke Test

### Run

Replace `<YOUR-VERCEL-URL>` with the actual Vercel deployment URL.

```powershell
.venv-ingest\Scripts\python.exe tools\deploy\test_gate65_post_deploy_smoke_v1.py https://<YOUR-VERCEL-URL>.vercel.app
```

Then build the Gate 65 report:

```powershell
.venv-ingest\Scripts\python.exe tools\deploy\build_gate65_post_deploy_report_v1.py
```

---

## URLs Tested

| Path | Type | What is checked |
|---|---|---|
| `/` | HTML | HTTP 200/redirect |
| `/login` | HTML | HTTP 200, "Sign in" text present |
| `/system/health` | HTML | HTTP 200 |
| `/system/readiness` | HTML | HTTP 200 |
| `/api/system/health` | JSON | status = "ok", content_source = "live_supabase" |
| `/api/system/readiness` | JSON | status = "ready" or "needs_review" (not "failed") |
| `/system/auth-session` | HTML | HTTP 200 |
| `/system/role-access` | HTML | HTTP 200 |

---

## Status Meaning

| Status | Meaning |
|---|---|
| `passed` | All routes OK, health/readiness OK, no secrets exposed, live_supabase mode |
| `needs_review` | Critical checks OK but some routes or env flags need attention |
| `failed` | Health API down, login unreachable, or secrets found in response |

Critical failures (status = `failed`):
- `/api/system/health` returns non-200 or `status != ok`
- `/login` returns non-200
- Secret pattern found in any response body

---

## Security Checks

The smoke test scans every response body for:

| Pattern | Description |
|---|---|
| JWT token (300+ chars) | Would indicate a real Supabase key value leaked into a response |
| `sk-[40+ chars]` | OpenAI API key format |
| `sk-ant-[50+ chars]` | Anthropic API key format |
| `data/raw/` in path | Raw Cambridge material path |
| `original_raw_block` | Cambridge raw source field |
| `normalized_raw_block` | Cambridge normalized source field |

> **Note:** The health/readiness pages display label text like
> "SUPABASE_SERVICE_ROLE_KEY" — this is expected and not flagged as a secret.
> Only actual key VALUES (long JWT strings) are considered security issues.

---

## Manual Browser Checks

After running the automated test, also verify manually in a browser:

1. **`/login`** — Login form renders with email/password fields. No JS errors in console.

2. **`/system/health`** — Page requires login (shows "Access denied" if not signed in).
   After signing in as admin: shows `status: OK`, env vars present as true/false.

3. **`/system/readiness`** — After signing in: shows READY or NEEDS_REVIEW checklist.
   All critical checks (login UI, role modules, Supabase env) should be PASS.

4. **`/system/auth-session`** — Shows current session email and role.

5. **`/system/role-access`** — Shows route access matrix. Admin should have access to all routes.

---

## Login Test

Use the demo admin credentials created in Gate 61:

| Field | Value |
|---|---|
| Email | `admin@quantaaptus.local` |
| Password | `QuantaAptusDemo123!` |

1. Go to `/login`
2. Enter email and password
3. Click Sign in
4. Expect redirect to `/system/auth-session`
5. Confirm role shows `admin`

> **Warning:** Rotate demo passwords before allowing real users to access the system.
> The password `QuantaAptusDemo123!` is documented in this repository.
> Use Supabase Auth dashboard to update or delete demo accounts.

---

## Expected API Responses

### `/api/system/health`

```json
{
  "status": "ok",
  "app": "quanta-aptus-admin",
  "content_source": "live_supabase",
  "demo_fallback": "false",
  "node_env": "production",
  "supabase_url_present": true,
  "anon_key_present": true,
  "service_role_present_server": true,
  "timestamp": "2026-..."
}
```

### `/api/system/readiness`

```json
{
  "status": "ready",
  "checks": {
    "content_source_valid": true,
    "content_source_is_live": true,
    "demo_fallback_off": true,
    "supabase_url_present": true,
    "anon_key_present": true,
    "service_role_present": true,
    "login_ui_exists": true,
    "role_access_module_exists": true,
    ...
  },
  "content_source": "live_supabase",
  "timestamp": "2026-..."
}
```

---

## Report Location

After running the smoke test and report builder:

- `data/diagnostics/gate65_post_deploy_smoke_test_report_v1.json` — raw results
- `data/diagnostics/gate65_post_deploy_report_v1.json` — structured summary
- `data/diagnostics/SUPABASE_GATE_65_POST_DEPLOY_SMOKE_DONE.md` — completion marker

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `/api/system/health` returns `content_source: local` | `QA_CONTENT_SOURCE` env var not set | Add `QA_CONTENT_SOURCE=live_supabase` in Vercel dashboard |
| `service_role_present_server: false` | `SUPABASE_SERVICE_ROLE_KEY` not set | Add it in Vercel env vars (server-only, not NEXT_PUBLIC_*) |
| `/login` shows blank page | Build error or missing `NEXT_PUBLIC_SUPABASE_*` vars | Check Vercel build logs and env vars |
| Status is `needs_review` | Not critical — check `issues` array in report | Fix the listed issues for full READY status |
