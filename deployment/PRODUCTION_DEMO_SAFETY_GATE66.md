# Gate 66 — Production Demo Safety

## Current Demo Accounts

The following demo accounts were created during Gate 61 for local development and
internal integration testing. They exist in the Supabase Auth database connected
to production.

| Email | Role | Purpose |
|---|---|---|
| admin@quantaaptus.local | admin | Full admin access for testing |
| teacher@quantaaptus.local | teacher | Teacher-role testing |
| student@quantaaptus.local | student | Student-role testing |
| parent@quantaaptus.local | parent | Parent-role testing |

> **These accounts use documented passwords.** The password `QuantaAptusDemo123!`
> is recorded in Gate 61 documentation and this repository. It must be rotated or
> the accounts must be disabled before any public launch.

---

## Why Demo Accounts Are Risky

1. **Known credentials**: The demo password is documented in the repository.
   Anyone with repo access can log in as admin to the production Supabase instance.

2. **Admin-level access**: `admin@quantaaptus.local` has admin role — full read/write
   access to all content, user management, and system diagnostics.

3. **Production database connected**: The app uses `QA_CONTENT_SOURCE=live_supabase`,
   meaning demo admin logins affect real production data.

4. **No rate limiting on demo accounts**: Supabase Auth does not differentiate
   between demo and real accounts — brute-force protection applies to all equally.

5. **Domain `@quantaaptus.local` is non-public but not secret**: Once the URL is
   known, trial-and-error with the known email format is feasible.

---

## Before Public Launch Checklist

Complete all of these before pointing any real users or public traffic to the app.

### Must-Do (blocking public launch)

- [ ] **Rotate demo passwords** — Change all 4 demo account passwords in Supabase
      Auth dashboard. Use unique, strong, non-documented passwords.
      _Or disable/delete the demo accounts entirely._

- [ ] **Disable or delete demo admin account** — `admin@quantaaptus.local` should
      not exist as a live admin at public launch. Either delete the Supabase Auth
      user or revoke admin role in the `profiles` table.

- [ ] **Replace with real admin email** — Create a real `@quantaaptus.com` admin
      account in Supabase Auth and assign `admin` role in profiles. Verify login.

- [ ] **Confirm `QA_AUTH_DEMO_FALLBACK=false`** — This must be false in Vercel env.
      The health API confirms this: `demo_fallback: "false"`. Do not enable at launch.

- [ ] **Confirm no default password remains** — After rotation, sign out and attempt
      login with the old password `QuantaAptusDemo123!` — it must fail.

- [ ] **Verify RLS is active** — Run the RLS migration 000004 if not yet applied.
      Confirm Row Level Security is enabled on all tables in Supabase dashboard.

### Should-Do (strongly recommended)

- [ ] **Keep service role server-side only** — `SUPABASE_SERVICE_ROLE_KEY` must
      remain a Vercel server-only env var (no `NEXT_PUBLIC_` prefix). Confirm in
      Vercel dashboard under Environment Variables.

- [ ] **Audit who has Vercel project access** — Ensure only authorized team members
      can see the Vercel dashboard for this project (where env vars are stored).

- [ ] **Audit Supabase project access** — Ensure only authorized team members have
      access to the Supabase project dashboard.

- [ ] **Review auth logs** — In Supabase Auth > Logs, confirm only expected logins
      during the testing period. Revoke any unexpected sessions.

- [ ] **Set up Supabase email verification** (optional) — Enabling email confirmation
      prevents account creation with arbitrary emails.

---

## Recommended Actions (Supabase Dashboard Steps)

### Rotate Demo Passwords

1. Go to Supabase Dashboard → Authentication → Users.
2. Find each demo user (filter by `@quantaaptus.local`).
3. Click the user → "Send password reset email" or use the "Reset password" action.
4. Set a new strong password that is NOT documented anywhere.
5. Repeat for all 4 accounts.

### Disable Demo Users (alternative to rotation)

1. Go to Supabase Dashboard → Authentication → Users.
2. Select each demo user.
3. Click "Ban user" to prevent login without deleting the account.
   (Banning is reversible; deletion is not.)

### Delete Demo Users (for clean production launch)

1. Create and verify a real admin account (`admin@quantaaptus.com`) first.
2. Confirm the new admin can log in and has `admin` role in `profiles`.
3. Go to Supabase → Authentication → Users.
4. Delete each `@quantaaptus.local` user.
5. Also remove the corresponding rows from the `profiles` table.

> Do NOT delete users until a real admin account is working and verified.

### Replace Admin Email

1. Create `admin@quantaaptus.com` in Supabase Auth (invite or manual creation).
2. Insert a row in `profiles` with the new user's UUID, email, and `role = 'admin'`.
3. Sign in with the new admin account and verify it has full access.
4. Only then proceed to disable or delete `admin@quantaaptus.local`.

---

## Safe Staging Policy

Demo accounts are acceptable under these conditions:
- The production URL (`qa-engine-admin.vercel.app`) is **not publicly promoted**.
- Access is limited to the internal development team.
- The URL is not linked from any public page, email, or marketing material.
- `QA_AUTH_DEMO_FALLBACK` remains `false`.
- No real student/teacher/parent data has been loaded.

Once any of these conditions changes, demo accounts must be rotated or removed.

---

## Domain Policy

Do **not** point `admin.quantaaptus.com` (or any public domain) to this deployment
until all items in the "Must-Do" checklist above are complete.

Custom domain setup is Gate 67. Gate 67 should only begin after demo safety is resolved.

---

## Verification Commands

After completing demo safety cleanup, run:

```powershell
# Check demo account status
.venv-ingest\Scripts\python.exe tools\deploy\check_gate66_demo_user_safety_v1.py https://qa-engine-admin.vercel.app

# Build report
.venv-ingest\Scripts\python.exe tools\deploy\build_gate66_demo_safety_report_v1.py
```

Expected after full cleanup:
- `demo_profiles_found: false`
- `demo_auth_users_found: false`
- `public_launch_safe: true`

---

## Files Created in Gate 66

| File | Purpose |
|---|---|
| `deployment/PRODUCTION_DEMO_SAFETY_GATE66.md` | This document |
| `tools/deploy/check_gate66_demo_user_safety_v1.py` | Demo account check script |
| `tools/deploy/build_gate66_demo_safety_report_v1.py` | Report builder |
| `apps/admin/src/app/system/demo-safety/page.tsx` | In-app safety diagnostic |
| `apps/admin/src/app/api/system/demo-safety/route.ts` | Safety status API |
