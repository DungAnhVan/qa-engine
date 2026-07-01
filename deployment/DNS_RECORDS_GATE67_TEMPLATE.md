# Gate 67 — DNS Records Template

Fill in this table after Vercel provides the DNS instructions for `admin.quantaaptus.com`.

---

## DNS Records for quantaaptus.com

| Host (Name) | Type | Value (Target) | TTL | Purpose | Status |
|---|---|---|---|---|---|
| `admin` | `CNAME` | `<copy from Vercel Domains settings>` | Auto | Admin app → Vercel | pending |
| `learn` | `CNAME` | `reserved` | Auto | Student app (future gate) | not_set |
| `@` | unchanged | unchanged | unchanged | Landing page (apex) | unchanged |
| `www` | unchanged | unchanged | unchanged | Landing page (www) | unchanged |

---

## Instructions

### admin.quantaaptus.com (Gate 67 target)

1. Log in to Vercel → select project `qa-engine-admin` → Settings → Domains
2. Add domain: `admin.quantaaptus.com`
3. Vercel shows a DNS instruction like:

   ```
   Type:  CNAME
   Name:  admin
   Value: cname.vercel-dns.com
   ```

4. Copy the **Value** exactly and paste it into your DNS provider for the `admin` record.
5. Update the table above — replace `<copy from Vercel Domains settings>` with the actual value.
6. Set Status to `configured` once the DNS record is saved.
7. Set Status to `verified` once Vercel shows "Valid Configuration".

### learn.quantaaptus.com (future — do not configure in Gate 67)

Reserved for the student-facing app. Leave as `not_set` until that gate.

### @ and www (do not touch in Gate 67)

These records control `quantaaptus.com` and `www.quantaaptus.com` (the landing page).
Do not modify them in Gate 67. Mark as `unchanged`.

---

## Status Definitions

| Status | Meaning |
|---|---|
| `pending` | DNS record needs to be added at DNS provider |
| `configured` | DNS record added, waiting for propagation / Vercel verification |
| `verified` | Vercel shows "Valid Configuration", SSL issued |
| `not_set` | Reserved but not yet configured |
| `unchanged` | Existing record — must not be modified |

---

## Example Filled Table (replace with real values)

| Host | Type | Value | TTL | Purpose | Status |
|---|---|---|---|---|---|
| `admin` | `CNAME` | `cname.vercel-dns.com` | Auto | Admin app → Vercel | verified |
| `learn` | `CNAME` | `reserved` | Auto | Student app (future) | not_set |
| `@` | `A` | `76.223.126.88` | unchanged | Landing page | unchanged |
| `www` | `CNAME` | `quantaaptus.com` | unchanged | Landing page | unchanged |

> The example values are illustrative. Use only the values from your actual DNS provider
> and Vercel dashboard.

---

## Supabase Auth Redirect URLs

After DNS is verified, add to Supabase Dashboard → Authentication → URL Configuration:

| Setting | Value |
|---|---|
| Redirect URLs | `https://admin.quantaaptus.com/**` |

Do not change Site URL until confirming all auth flows work on the custom domain.

---

## Verification Checklist

After adding DNS:

- [ ] DNS record saved at DNS provider
- [ ] Vercel domain shows "Valid Configuration"
- [ ] SSL certificate issued (HTTPS works, no browser warning)
- [ ] `https://admin.quantaaptus.com/system/health` returns `status: ok`
- [ ] `https://admin.quantaaptus.com/api/system/health` returns JSON with `status: ok`
- [ ] `https://admin.quantaaptus.com/login` renders the login form
- [ ] Supabase Auth redirect URL added for custom domain
- [ ] Gate 67 smoke test run and passed
- [ ] Gate 67 report builder run — `status: passed`
- [ ] `quantaaptus.com` landing page still works (verify in browser)
