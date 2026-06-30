# Gate 64 — Vercel Deployment Setup

## Overview

This guide covers the manual steps to deploy the Quanta Aptus admin app
(a Next.js app inside a pnpm monorepo) to Vercel for the first time.

No real secrets should be committed to git. All values marked `<...>` below
must be entered in the Vercel dashboard only.

---

## Step 1 — Import the GitHub Repository

1. Go to [https://vercel.com/new](https://vercel.com/new)
2. Click **Add New Project → Import Git Repository**
3. Select the GitHub repo: `DungAnhVan/qa-engine`
4. Click **Import**

---

## Step 2 — Configure Build Settings

On the **Configure Project** screen:

| Setting | Value |
|---|---|
| **Framework Preset** | Next.js |
| **Root Directory** | *(leave blank — repo root)* |
| **Install Command** | `pnpm install` |
| **Build Command** | `pnpm --filter @qa-engine/admin build` |
| **Output Directory** | `apps/admin/.next` *(auto-filled from vercel.json)* |

> **Note:** `vercel.json` at the repo root encodes build and output settings.
> Vercel reads it automatically. You only need to verify the values match.

If Vercel does not auto-detect the Next.js framework from `vercel.json`,
set Framework Preset manually to **Next.js** in the Vercel dashboard.

---

## Step 3 — Add Environment Variables

In the **Environment Variables** section during setup (or later in
Project → Settings → Environment Variables), add:

### Server-only variables (NOT exposed to browser)

| Variable | Value |
|---|---|
| `QA_CONTENT_SOURCE` | `live_supabase` |
| `QA_AUTH_DEMO_FALLBACK` | `false` |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_ANON_KEY` | `<anon key from Supabase dashboard>` |
| `SUPABASE_SERVICE_ROLE_KEY` | `<service role key — NEVER put in NEXT_PUBLIC_*>` |

### Browser-visible variables (safe to expose)

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `<anon key>` |

> **Security:** `SUPABASE_SERVICE_ROLE_KEY` bypasses all RLS policies.
> It must NEVER appear in any `NEXT_PUBLIC_*` variable.
> Set its scope to **Production** only (not Preview if Preview uses a shared DB).

---

## Step 4 — Deploy

1. Click **Deploy**
2. Wait for the build to complete (typically 2–4 minutes)
3. Vercel shows the deployment URL: `https://<project>.vercel.app`

---

## Step 5 — Verify Health Endpoints

After deployment, open the following URLs (replace `<domain>` with your Vercel URL):

| URL | Expected Response |
|---|---|
| `https://<domain>/system/health` | Page loads, status = OK |
| `https://<domain>/system/readiness` | Page loads, status = READY or NEEDS_REVIEW |
| `https://<domain>/api/system/health` | JSON: `{"status":"ok", "content_source":"live_supabase", ...}` |
| `https://<domain>/api/system/readiness` | JSON: `{"status":"ready", ...}` |
| `https://<domain>/login` | Login form renders |
| `https://<domain>/system/auth-session` | Auth session diagnostic |
| `https://<domain>/system/role-access` | Role access matrix |

---

## Step 6 — Post-Deploy Smoke Test

1. Sign in with an admin account at `/login`
2. Verify `/content` is accessible (admin role)
3. Sign out → redirected to `/login`
4. Sign in as teacher → `/content` accessible, `/system/marking` accessible
5. Sign in as student → `/learn/supabase-results` accessible, `/content` blocked

---

## Monorepo Notes

- The pnpm workspace root is `D:\qa-engine` (repo root)
- The Next.js app is at `apps/admin`
- `pnpm --filter @qa-engine/admin build` builds only the admin app
- `apps/admin/.next` is the build output directory
- Vercel reads `vercel.json` at repo root for build/output config

If you encounter "No Next.js project found" errors on Vercel:
- Try setting **Root Directory** to `apps/admin` in Vercel dashboard
- Change **Install Command** to `cd ../.. && pnpm install` (installs from workspace root)
- Change **Build Command** to `pnpm build` (runs Next.js build from apps/admin)

---

## Rollback

If the deploy fails or produces errors:

1. In Vercel Dashboard → your project → Deployments
2. Find the last working deployment
3. Click the **...** menu → **Promote to Production**
4. Investigate the failed build logs before re-deploying

---

## Reference

- `.env.production.example` — all env var placeholders
- `deployment/VERCEL_ENV_VARS_GATE64.md` — env var reference table
- `deployment/SECURITY_PREDEPLOY_CHECKLIST.md` — security checklist
- `deployment/VERCEL_DEPLOYMENT_CHECKLIST.md` — full checklist
