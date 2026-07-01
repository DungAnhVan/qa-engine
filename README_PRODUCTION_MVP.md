# Quanta Aptus Learn Online MVP

Production MVP v1 — internal testing phase.

## Production URLs

| URL | Purpose |
|---|---|
| `https://admin.quantaaptus.com` | Admin app (custom domain) |
| `https://qa-engine-admin.vercel.app` | Admin app (Vercel default, always available) |

## Current Stage

**Gate 68 — Production MVP Freeze**

- Backend: Supabase (live_supabase mode)
- Hosting: Vercel (GitHub auto-deploy)
- Auth: Supabase Auth + RLS
- Custom domain: `admin.quantaaptus.com`
- Internal testing: safe
- Public launch: blocked until demo accounts are rotated/removed

## Local Build

```powershell
# Local mode
$env:QA_CONTENT_SOURCE="local"
pnpm --filter @qa-engine/admin build

# Live Supabase mode (requires .env.local with Supabase credentials)
$env:QA_CONTENT_SOURCE="live_supabase"
pnpm --filter @qa-engine/admin build
```

Dev server:

```powershell
$env:QA_CONTENT_SOURCE="local"
pnpm --filter @qa-engine/admin dev
```

## Smoke Tests

```powershell
# Route smoke test (Vercel URL)
.\.venv-ingest\Scripts\python.exe tools\deploy\test_gate65_post_deploy_smoke_v1.py https://qa-engine-admin.vercel.app

# Demo safety check
.\.venv-ingest\Scripts\python.exe tools\deploy\check_gate66_demo_user_safety_v1.py https://qa-engine-admin.vercel.app

# Custom domain smoke test
.\.venv-ingest\Scripts\python.exe tools\deploy\test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com

# MVP freeze report
.\.venv-ingest\Scripts\python.exe tools\deploy\build_gate68_mvp_freeze_report_v1.py
```

See `deployment/PRODUCTION_SMOKE_TESTS_V1.md` for full commands and expected results.

## Documentation

| File | Purpose |
|---|---|
| `docs/QUANTA_APTUS_LEARN_ONLINE_MVP_V1.md` | Full MVP spec, gates, limitations, next phases |
| `deployment/PRODUCTION_OPERATING_GUIDE_V1.md` | Day-to-day operating guide |
| `deployment/PRODUCTION_SMOKE_TESTS_V1.md` | Smoke test commands and expected results |
| `deployment/CUSTOM_DOMAIN_GATE67.md` | Custom domain setup and DNS guide |
| `deployment/PRODUCTION_DEMO_SAFETY_GATE66.md` | Demo account safety checklist |
| `deployment/VERCEL_GATE64_SETUP.md` | Vercel setup guide |

## Diagnostics

| URL | Purpose |
|---|---|
| `/system/health` | App health |
| `/system/readiness` | Production readiness checks |
| `/system/auth-session` | Current session and role |
| `/system/demo-safety` | Demo account safety status |
| `/system/role-access` | Route access matrix by role |
| `/api/system/health` | JSON health API |
| `/api/system/readiness` | JSON readiness API |
| `/api/system/demo-safety` | JSON safety status |

Report files: `data/diagnostics/`

## No Secrets in This File

Credentials and keys are stored in Vercel environment variables only.
`.env.local` is gitignored. Do not commit `.env.local` or any key values.
