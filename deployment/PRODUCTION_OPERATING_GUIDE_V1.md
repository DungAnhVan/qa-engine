# Production Operating Guide v1

## Daily Health Check URLs

Open these in a browser after signing in as admin to verify the system is healthy:

| URL | What to check |
|---|---|
| `https://admin.quantaaptus.com/system/health` | `status: OK`, `content_source: live_supabase`, `demo_fallback: false` |
| `https://admin.quantaaptus.com/system/readiness` | All critical checks PASS, no FAIL rows |
| `https://admin.quantaaptus.com/system/auth-session` | Shows your email and role correctly |
| `https://admin.quantaaptus.com/system/demo-safety` | `internal_testing_safe: YES`, warning visible |

Quick JSON API checks (no login required):

```
https://admin.quantaaptus.com/api/system/health
https://admin.quantaaptus.com/api/system/readiness
https://admin.quantaaptus.com/api/system/demo-safety
```

---

## How to Redeploy

### Automatic (normal workflow)

Every push to `main` on GitHub triggers a Vercel auto-deploy:

```powershell
git add <files>
git commit -m "Your message"
git push origin main
```

Vercel builds and deploys within ~2 minutes. Check Vercel dashboard for build logs.

### Manual Redeploy

1. Go to [https://vercel.com/dashboard](https://vercel.com/dashboard)
2. Open project **qa-engine-admin**
3. Click **Deployments** tab
4. Find the target deployment → click **...** → **Redeploy**

---

## How to Check Environment Variables

1. Go to Vercel → project **qa-engine-admin** → **Settings** → **Environment Variables**
2. Filter by **Production** environment

### Required Environment Variables

| Variable | Scope | Purpose |
|---|---|---|
| `QA_CONTENT_SOURCE` | Server | Must be `live_supabase` in production |
| `QA_AUTH_DEMO_FALLBACK` | Server | Must be `false` in production |
| `SUPABASE_URL` | Server | Supabase project URL (server-side) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server | Service role key — **never in NEXT_PUBLIC_*** |
| `NEXT_PUBLIC_SUPABASE_URL` | Browser | Supabase project URL (browser-safe) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Browser | Anon key (browser-safe, low privilege) |

> `SUPABASE_ANON_KEY` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` should have the same value.
> The `NEXT_PUBLIC_` prefix makes them available to the browser — this is safe for the
> anon key only. **Never add `NEXT_PUBLIC_` to the service role key.**

---

## DNS Configuration

| Domain | DNS Provider | Record | Points To |
|---|---|---|---|
| `quantaaptus.com` | Netlify DNS | A / managed | Netlify landing site |
| `www.quantaaptus.com` | Netlify DNS | CNAME / managed | Netlify landing site |
| `admin.quantaaptus.com` | Netlify DNS | CNAME | Vercel (cname.vercel-dns.com or similar) |
| `learn.quantaaptus.com` | — | reserved | not yet configured |

> **Do not change `@` or `www` DNS records** during MVP testing. These serve the landing page.

---

## How to Rollback

### Option 1 — Promote a Previous Vercel Deployment

1. Vercel → project qa-engine-admin → Deployments
2. Find a stable previous deployment
3. Click **...** → **Promote to Production**

This is instant — no rebuild required.

### Option 2 — Remove Custom Domain

If `admin.quantaaptus.com` has an issue:

1. Go to your DNS provider (Netlify DNS) → find `admin` CNAME record
2. Temporarily delete or change the record
3. Use `https://qa-engine-admin.vercel.app` in the meantime

The Vercel default URL always works as a fallback.

---

## How to Disable Demo Users

1. Go to [Supabase Dashboard](https://supabase.com) → your project
2. Click **Authentication** → **Users**
3. Find each `@quantaaptus.local` user
4. Click the user → **Ban user** (reversible) or **Delete user** (permanent)

> Delete only after a real admin account is created and verified.

---

## How to Rotate Demo Passwords

1. Supabase Dashboard → Authentication → Users
2. Find the demo user
3. Click **Send password reset email** (if email is configured)
   — or —
   Use the Supabase Auth API via a server-side script with the service role key
4. Set a strong, undocumented password
5. Verify the old password no longer works

---

## How to Add a Real Admin User

1. Supabase Dashboard → Authentication → Users → **Invite user** or **Add user**
2. Enter the real email (e.g., `admin@quantaaptus.com`)
3. Set a strong password
4. In Supabase SQL Editor, insert a profiles row:

```sql
INSERT INTO profiles (id, email, display_name, role)
VALUES (
  '<uuid from Auth Users>',
  'admin@quantaaptus.com',
  'Admin',
  'admin'
);
```

5. Sign in via `https://admin.quantaaptus.com/login` and verify the role shows `admin`
   on the auth-session page.

> Do not run this SQL until you have the UUID from the newly created Auth user.
> Do not modify existing profile rows unless explicitly intended.

---

## What NOT to Do

| Do Not | Reason |
|---|---|
| Commit `.env.local` to git | Contains secrets; gitignored for this reason |
| Put `SUPABASE_SERVICE_ROLE_KEY` in a `NEXT_PUBLIC_` var | Exposes key to browser / all users |
| Delete production Supabase tables or data without a backup | Permanent data loss |
| Change `quantaaptus.com` apex DNS (`@` record) during MVP testing | Takes down the landing page |
| Enable `QA_AUTH_DEMO_FALLBACK=true` in production | Bypasses real auth for all users |
| Point `admin.quantaaptus.com` to an untested deployment | Breaks live users |
| Share service role key in Slack, docs, or emails | Allows unrestricted database access |

---

## Supabase Dashboard Bookmarks

| Section | Purpose |
|---|---|
| Authentication → Users | View / manage users and sessions |
| Authentication → Logs | Review recent sign-in activity |
| Authentication → URL Configuration | Add custom domain redirect URLs |
| Database → Tables | Inspect data (read-only during MVP) |
| Database → RLS Policies | Verify RLS is enabled |
| SQL Editor | Run approved migrations only |
| Settings → API | Retrieve URL and anon key (safe to view) |

> The service role key in Settings → API is sensitive. Do not copy-paste it into
> any document, chat, or browser console.
