# Gate 69A — Production Credential Hardening

## Why This Gate Exists

Gate 68 froze the MVP with `public_launch_safe: false`. The blocker is that
four demo accounts (`@quantaaptus.local`) still exist in Supabase Auth with
passwords that were documented during development. Any public user who finds
these credentials can sign in with admin-level access.

This gate adds:
- Tooling to create a real admin production user
- A checklist to rotate or disable demo users
- Automated scripts to verify credential safety
- A diagnostic page showing current credential status

---

## Current Blocker

| Account | Role | Risk |
|---|---|---|
| `admin@quantaaptus.local` | admin | HIGH — full admin access |
| `teacher@quantaaptus.local` | teacher | MEDIUM |
| `student@quantaaptus.local` | student | LOW |
| `parent@quantaaptus.local` | parent | LOW |

Passwords are documented in this repository. Until they are rotated or the
accounts are disabled/deleted, public launch must remain blocked.

---

## Required Actions Before Public Launch

Complete these steps in order:

1. **Create a real admin user** with a real email address you control.
   Use `tools/deploy/create_gate69a_real_admin_user_v1.py`.

2. **Verify the real admin can log in** at `https://admin.quantaaptus.com/login`.
   Check `https://admin.quantaaptus.com/system/auth-session` — role must show `admin`.

3. **Verify the real admin profile exists** in `public.profiles` with `role = admin`.

4. **Rotate or disable demo users** using the Supabase Dashboard or
   `tools/deploy/disable_gate69a_demo_users_v1.py`.

5. **Confirm `QA_AUTH_DEMO_FALLBACK=false`** in Vercel production env vars.
   This is already set. Do not change it.

6. **Confirm `SUPABASE_SERVICE_ROLE_KEY` is server-only** — no `NEXT_PUBLIC_` prefix.

7. **Run smoke tests** from `deployment/PRODUCTION_SMOKE_TESTS_V1.md`.

8. **Run the credential safety check** to get `public_launch_safe: true`:
   ```powershell
   .\.venv-ingest\Scripts\python.exe tools\deploy\check_gate69a_credential_safety_v1.py https://admin.quantaaptus.com --real-admin-email YOUR_EMAIL
   ```

---

## Recommended Real Admin Account Policy

- Use a real email address you control (not `@quantaaptus.local`)
- Use a strong, unique password — do not reuse the demo password
- Store the password in a password manager, not in this repository
- Do not commit the password anywhere
- Enable Supabase MFA when it is supported for your project
- The real admin account must be created before demo accounts are removed

---

## Manual Supabase Steps

### Create a Real Admin User

1. Go to [Supabase Dashboard](https://supabase.com) → your project
2. Click **Authentication** → **Users** → **Add user** or **Invite user**
3. Enter your real email and a strong password
4. Note the UUID shown for the new user
5. Open **SQL Editor** and run:

```sql
INSERT INTO profiles (id, email, display_name, role)
VALUES (
  '<uuid-from-auth-users>',
  'your-real-email@example.com',
  'Quanta Aptus Admin',
  'admin'
)
ON CONFLICT (id) DO UPDATE SET role = 'admin', display_name = EXCLUDED.display_name;
```

6. Sign in at `https://admin.quantaaptus.com/login` and verify role shows `admin`

### Disable Demo Users

Only after the real admin login is verified:

1. Supabase Dashboard → **Authentication** → **Users**
2. Find each `@quantaaptus.local` user
3. Click the user → **Ban user** (reversible) or **Delete user** (permanent)
4. Confirm the banned/deleted user can no longer sign in

> Use `tools/deploy/disable_gate69a_demo_users_v1.py --execute --confirm DISABLE_DEMO_USERS`
> for a scripted approach. Review the dry-run output first.

---

## Rollback Plan

- Always keep at least one known admin account active
- Do not delete all admins from `public.profiles`
- If the real admin login fails, use Supabase Dashboard to reset the password
- The demo accounts can be re-enabled (un-banned) from Supabase Dashboard if needed

---

## Security Constraints (Unchanged)

- `SUPABASE_SERVICE_ROLE_KEY` — server-side only, never in `NEXT_PUBLIC_` vars
- No passwords in this repository
- No secrets in git commits
- `.env.local` is gitignored — do not commit it
- Demo fallback must remain `false` in production at all times
