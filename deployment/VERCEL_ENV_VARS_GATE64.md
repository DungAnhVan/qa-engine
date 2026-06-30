# Gate 64 — Vercel Environment Variables Reference

All variables must be set in **Vercel Dashboard → Project → Settings → Environment Variables**.

Never commit real values to git. See `.env.production.example` for placeholder template.

---

## Required Variables

| Variable | Required? | Server or Client | Example Placeholder | Notes |
|---|---|---|---|---|
| `QA_CONTENT_SOURCE` | Required | Server | `live_supabase` | Must be `live_supabase` in production. Do not use `local`. |
| `QA_AUTH_DEMO_FALLBACK` | Required | Server | `false` | Must be `false` in production. `true` bypasses real auth for dev only. |
| `NODE_ENV` | Auto-set | Server | `production` | Set automatically by Vercel. Do not override. |
| `SUPABASE_URL` | Required | Server only | `https://<ref>.supabase.co` | Base URL for service-role server reads. Not browser-visible. |
| `SUPABASE_ANON_KEY` | Required | Server only | `eyJ...` | Anon key for server-side session reads. Not browser-visible directly. |
| `SUPABASE_SERVICE_ROLE_KEY` | Required | **Server only — NEVER NEXT_PUBLIC_*** | `eyJ...` | Bypasses RLS. Server-only. Critical: never expose to browser. |
| `NEXT_PUBLIC_SUPABASE_URL` | Required | Browser + Server | `https://<ref>.supabase.co` | Same URL as SUPABASE_URL. Exposed to browser (safe). |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Required | Browser + Server | `eyJ...` | Anon key for browser auth. Exposed to browser (safe — anon key is public by design). |

---

## Variable Scopes in Vercel Dashboard

Set **all** variables for the **Production** environment.

For **Preview** environments (PR previews):
- Use a separate Supabase project or restrict to read-only access.
- Do NOT share production `SUPABASE_SERVICE_ROLE_KEY` with Preview if it contains real user data.

For **Development** (local):
- Use `apps/admin/.env.local` — never commit this file.
- `QA_AUTH_DEMO_FALLBACK=true` is acceptable for local only.

---

## Where to Find Supabase Values

1. Log in at [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to **Project Settings → API**
4. Copy:
   - **URL** → use for `SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_URL`
   - **anon / public key** → use for `SUPABASE_ANON_KEY` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - **service_role / secret key** → use for `SUPABASE_SERVICE_ROLE_KEY` (server only!)

---

## Security Rules

1. `SUPABASE_SERVICE_ROLE_KEY` **must never** be prefixed with `NEXT_PUBLIC_`.
   If it appears in a `NEXT_PUBLIC_*` var, it will be embedded in the browser bundle
   and visible to all users — this bypasses all RLS policies.

2. `NEXT_PUBLIC_SUPABASE_ANON_KEY` **is intentionally browser-visible**.
   The anon key is a public credential — Supabase RLS policies control what
   the anon key can actually access. This is by design.

3. `QA_AUTH_DEMO_FALLBACK` must be `false` in production.
   If `true`, all pages render as admin without any authentication check.

4. Rotate keys immediately if:
   - A real key is accidentally committed to git
   - A real key is found in a `NEXT_PUBLIC_*` variable
   - The `SUPABASE_SERVICE_ROLE_KEY` is logged or displayed anywhere

---

## Verification

After adding all variables, visit:

```
https://<your-domain>/api/system/health
```

Expected response:
```json
{
  "status": "ok",
  "content_source": "live_supabase",
  "supabase_url_present": true,
  "anon_key_present": true,
  "service_role_present_server": true,
  "timestamp": "..."
}
```

All three `*_present` fields should be `true`.
