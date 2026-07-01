# Gate 67 — Custom Domain Prep

## Recommended Domain Architecture

| Domain | Purpose | Status |
|---|---|---|
| `quantaaptus.com` | Landing / brand page | unchanged — do not touch in Gate 67 |
| `admin.quantaaptus.com` | Admin app (qa-engine-admin Vercel project) | target for Gate 67 |
| `learn.quantaaptus.com` | Student-facing app | reserved for future gate |
| `qa-engine-admin.vercel.app` | Current working URL | remains active after domain add |

---

## Why Not Use the Apex Domain Immediately

1. **Avoid breaking the landing page.** `quantaaptus.com` may already serve a marketing
   or landing page. Changing the apex DNS record without coordinating the full migration
   would take it down without a rollback path.

2. **Safer rollback.** A subdomain like `admin.quantaaptus.com` can be removed (delete
   the CNAME) without affecting any other URLs. If something goes wrong, the Vercel URL
   `qa-engine-admin.vercel.app` continues to work.

3. **Clean separation of concerns.** The admin tool, student learning app, and public
   marketing site serve different audiences. Subdomains make the architecture explicit
   and allow independent deployment schedules.

4. **`quantaaptus.com` apex is a business decision.** Pointing the apex domain requires
   coordinating with whoever manages the landing page content. Gate 68+ will revisit this
   after the admin app is verified stable.

---

## Vercel Setup Steps

### Step 1 — Open Vercel Project Settings

1. Go to [https://vercel.com/dashboard](https://vercel.com/dashboard)
2. Open the project **qa-engine-admin** (or the project linked to the admin app)
3. Click **Settings** → **Domains**

### Step 2 — Add the Domain

4. Click **Add Domain**
5. Enter: `admin.quantaaptus.com`
6. Click **Add**

### Step 3 — Read the DNS Instructions

Vercel will display DNS instructions. For a subdomain, it is almost always a **CNAME** record:

| Host (Name) | Type | Value (Target) |
|---|---|---|
| `admin` | `CNAME` | `cname.vercel-dns.com` (or similar — copy the exact value Vercel shows) |

> **Copy the exact value Vercel shows.** Do not guess — Vercel's CNAME target may vary
> by plan or region.

### Step 4 — Add DNS Record at Your DNS Provider

Go to wherever `quantaaptus.com` DNS is managed (Cloudflare, GoDaddy, Namecheap, etc.):

1. Navigate to DNS records for `quantaaptus.com`
2. Create a new record:
   - **Type:** CNAME
   - **Name/Host:** `admin`
   - **Value/Target:** (the CNAME target Vercel showed in Step 3)
   - **TTL:** Auto or 300
3. Save

> **Do not delete existing records** for `@`, `www`, or other subdomains.
> Only add the new `admin` CNAME record.

### Step 5 — Wait for DNS Propagation

- DNS changes typically take 5–30 minutes for Cloudflare; up to 24–48 hours for other providers.
- Vercel automatically polls for the DNS record and issues an SSL certificate.
- The Vercel domain dashboard shows the domain as "Valid Configuration" when complete.

### Step 6 — Verify

7. Open `https://admin.quantaaptus.com/system/health`
8. Confirm the health page loads and shows `status: OK`, `content_source: live_supabase`

### Step 7 — Run Gate 67 Smoke Test

```powershell
.venv-ingest\Scripts\python.exe tools\deploy\test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com
.venv-ingest\Scripts\python.exe tools\deploy\build_gate67_custom_domain_report_v1.py
```

---

## DNS Notes

- **CNAME vs A Record:** Subdomains use CNAME. Vercel provides the CNAME target in the
  Domains settings. Do not use A records unless Vercel specifically instructs it.

- **Cloudflare proxy (orange cloud):** If your DNS is on Cloudflare, set the CNAME to
  **DNS only** (grey cloud / proxied OFF) initially. Vercel needs to verify the domain
  directly. Once Vercel shows "Valid", you may optionally re-enable Cloudflare proxy —
  but check Vercel's documentation first; some configurations cause redirect loops.

- **Do not change nameservers.** Gate 67 does not require moving DNS hosting. Only add
  a single CNAME record.

- **Do not delete existing records.** The `@`, `www`, and any other existing records for
  `quantaaptus.com` must remain untouched.

---

## Supabase Allowed Redirect URLs

After adding the custom domain, add it to Supabase Auth:

1. Go to Supabase Dashboard → Authentication → URL Configuration
2. **Site URL:** keep as-is (or update to `https://admin.quantaaptus.com` for the admin app)
3. **Redirect URLs:** add `https://admin.quantaaptus.com/**`
4. Save

Without this, Supabase Auth may reject redirects from the custom domain after login.

---

## Rollback

If something goes wrong:

1. Remove `admin.quantaaptus.com` from the Vercel project (Settings → Domains → Remove)
2. Delete the CNAME DNS record for `admin` at your DNS provider
3. Continue using `https://qa-engine-admin.vercel.app`

The rollback is clean and takes effect within minutes (DNS TTL permitting).

---

## What Not to Do in Gate 67

- Do NOT change the `@` (apex) DNS record for `quantaaptus.com`
- Do NOT change the `www` DNS record for `quantaaptus.com`
- Do NOT change nameservers
- Do NOT rotate demo account passwords in this gate (that is Gate 66's responsibility)
- Do NOT point the custom domain until Gate 66 demo safety has been resolved
- Do NOT commit secrets

---

## Files Created in Gate 67

| File | Purpose |
|---|---|
| `deployment/CUSTOM_DOMAIN_GATE67.md` | This document — setup guide |
| `deployment/DNS_RECORDS_GATE67_TEMPLATE.md` | Fillable DNS record table |
| `tools/deploy/test_gate67_custom_domain_smoke_v1.py` | Post-DNS smoke test |
| `tools/deploy/build_gate67_custom_domain_report_v1.py` | Report builder |
