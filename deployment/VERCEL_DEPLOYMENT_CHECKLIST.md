# Quanta Aptus — Gate 63 Production Deployment Checklist

Gate 63 prepares the admin app for production deployment on Vercel.
Actual deployment happens in **Gate 64**.

---

## 1. GitHub Repo Status

- [ ] All Gate 62 changes committed and pushed to `main`
- [ ] No uncommitted changes in working tree (`git status` clean)
- [ ] `.env.local` NOT tracked in git (`git ls-files apps/admin/.env.local` returns empty)
- [ ] `.env.production` NOT tracked in git
- [ ] `pnpm-lock.yaml` committed and up to date

---

## 2. Vercel Project Settings

- [ ] Vercel project connected to GitHub repo
- [ ] Root directory set to: *(leave blank — using monorepo with pnpm workspaces)*
- [ ] Framework preset: **Next.js**
- [ ] Build command:
  ```
  pnpm install && pnpm --filter admin build
  ```
- [ ] Output directory: `apps/admin/.next` *(Vercel auto-detects this)*
- [ ] Install command: `pnpm install`
- [ ] Node.js version: `>=18`

---

## 3. Required Environment Variables

Set these in **Vercel Dashboard → Project → Settings → Environment Variables**.
Apply to: **Production** (and optionally Preview).

| Variable | Value | Visible to browser? |
|---|---|---|
| `QA_CONTENT_SOURCE` | `live_supabase` | No |
| `QA_AUTH_DEMO_FALLBACK` | `false` | No |
| `NODE_ENV` | `production` *(auto-set by Vercel)* | No |
| `SUPABASE_URL` | `https://<project>.supabase.co` | No |
| `SUPABASE_ANON_KEY` | `<anon key>` | No |
| `SUPABASE_SERVICE_ROLE_KEY` | `<service role key>` | **No — NEVER expose** |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://<project>.supabase.co` | **Yes** |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `<anon key>` | **Yes** |

> **Warning:** `SUPABASE_SERVICE_ROLE_KEY` bypasses all RLS policies.
> Never put it in a `NEXT_PUBLIC_*` variable. Never log or display it.

---

## 4. Supabase Project Requirements

- [ ] Supabase project created (not local dev instance)
- [ ] Migration 000001–000004 applied in SQL Editor
- [ ] Row Level Security enabled on all core tables (verify with `SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public'`)
- [ ] Auth email provider enabled
- [ ] Demo users removed OR passwords rotated before real-user launch
- [ ] Organization and profile seed data applied if needed

---

## 5. Build Verification (run locally before deploy)

```powershell
# Local mode — should compile with zero TS errors
$env:QA_CONTENT_SOURCE="local"
pnpm --filter admin build

# Live Supabase mode — same
$env:QA_CONTENT_SOURCE="live_supabase"
pnpm --filter admin build
```

Both builds must complete with **0 errors, 0 type errors**.

---

## 6. Health Check URLs (post-deploy)

After deploying, verify these URLs return expected responses:

| URL | Expected |
|---|---|
| `https://<domain>/system/health` | Page loads, status = ok |
| `https://<domain>/api/system/health` | JSON `{"status":"ok", ...}` |
| `https://<domain>/system/readiness` | Page loads, status = ready or needs_review |
| `https://<domain>/api/system/readiness` | JSON `{"status":"ready", ...}` |
| `https://<domain>/login` | Login form renders |
| `https://<domain>/content` | Redirects to login if not authenticated |

---

## 7. Rollback Plan

If the production deploy fails or health checks fail:

1. In Vercel Dashboard → Deployments → find last known-good deploy
2. Click **Promote to Production**
3. Investigate the failed deploy logs
4. Fix locally, re-run build verification, redeploy

---

## 8. Security Checklist

- [ ] `SUPABASE_SERVICE_ROLE_KEY` is NOT in any `NEXT_PUBLIC_*` variable
- [ ] No secrets in git history (`git log --all -S "service_role" -- apps/admin/src` returns nothing)
- [ ] RLS is enabled on all tables (Gate 62 migration applied)
- [ ] Demo user passwords rotated or users deleted before real traffic
- [ ] `QA_AUTH_DEMO_FALLBACK=false` in production
- [ ] `/system/*` diagnostic routes are admin-gated (requireAppRole guards in place)

---

## 9. Post-Deploy Smoke Test

After deploying to production:

```
1. Visit /api/system/health → status: ok
2. Visit /api/system/readiness → status: ready
3. Visit /login → form renders, no JS errors
4. Sign in with admin credentials → redirected correctly
5. Visit /content → accessible to admin
6. Sign out → redirected to /login
7. Sign in as student → content blocked, student routes accessible
```

---

## 10. Next Gate

**Gate 64 — Vercel Deployment**: Perform the actual Vercel deployment using this checklist.
