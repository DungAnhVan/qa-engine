# Gate 62 — RLS Hardening Migration Checklist

## Migration File
`supabase/migrations/000004_rls_role_hardening.sql`

---

## Pre-flight

- [ ] `QA_CONTENT_SOURCE=live_supabase` confirmed in `apps/admin/.env.local`
- [ ] `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` present in `.env.local`
- [ ] Migration file present: `supabase/migrations/000004_rls_role_hardening.sql`
- [ ] Gate 60 migration applied: `000003_auth_profile_trigger.sql`
- [ ] Demo auth users created (run `tools/supabase/create_gate61_demo_auth_users_v1.py`)

---

## Apply Steps

1. Open [Supabase Dashboard → SQL Editor](https://supabase.com/dashboard)
2. Select your project
3. Paste the full contents of `supabase/migrations/000004_rls_role_hardening.sql`
4. Click **Run** (or press Ctrl+Enter)
5. Confirm "Success. No rows returned."

> **NOTE:** The migration uses `DROP POLICY IF EXISTS` before each `CREATE POLICY`.
> This is idempotent — safe to re-run. It does NOT drop tables or data.

---

## Helper Functions to Verify (Section 1)

Run this in SQL Editor after applying:

```sql
SELECT routine_name, security_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
    'current_profile_id', 'current_profile_role', 'current_organization_id',
    'is_admin', 'is_teacher', 'is_student', 'is_parent', 'is_admin_or_teacher',
    'my_student_id', 'student_ids_in_my_org', 'linked_student_ids_for_parent',
    'my_attempt_ids', 'attempt_ids_in_my_org', 'linked_attempt_ids_for_parent',
    'package_ids_in_my_org'
  )
ORDER BY routine_name;
```

Expected: **14 rows**, all with `security_type = 'DEFINER'`.

---

## RLS Enabled (Section 2)

Run this to verify RLS is enabled on all core tables:

```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'profiles', 'students', 'parent_student_links',
    'subjects', 'resources', 'resource_packages',
    'resource_package_items', 'attempts', 'marked_attempts',
    'teacher_reviews'
  )
ORDER BY tablename;
```

Expected: all `rowsecurity = true`.

---

## Policies to Verify (Section 3)

Run this to see all policies created:

```sql
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

Core expected policies per table:

| Table | Policies |
|---|---|
| `profiles` | admin_all, teacher_read_same_org, self_read, self_update |
| `students` | admin_all, teacher_same_org, student_own, parent_linked |
| `parent_student_links` | admin_all, parent_own, teacher_same_org |
| `subjects` | admin_all, authenticated_read |
| `resources` | admin_all, authenticated_read |
| `resource_packages` | admin_all, teacher_same_org_or_global, student_enrolled_org, parent_linked_student_org |
| `resource_package_items` | admin_all, authenticated_read |
| `attempts` | admin_all, teacher_same_org, student_own, parent_linked_student |
| `marked_attempts` | admin_all, teacher_same_org, student_own, parent_linked_student |
| `teacher_reviews` | admin_all, teacher_own_or_same_org |

---

## Smoke Test

After applying, run the Gate 62 permission tests:

```powershell
.venv-ingest\Scripts\python.exe tools\supabase\test_gate62_role_permissions_v1.py
```

Then build the Gate 62 report:

```powershell
.venv-ingest\Scripts\python.exe tools\supabase\build_gate62_rls_role_access_report_v1.py
```

---

## Rollback (if needed)

If something goes wrong, you can remove all Gate 62 policies:

```sql
-- Remove policies (does NOT drop tables or data)
-- Re-run the DROP POLICY IF EXISTS blocks from the migration
-- or simply re-run the full migration — it is idempotent
```

To disable RLS on a specific table (emergency only):
```sql
ALTER TABLE public.profiles DISABLE ROW LEVEL SECURITY;
-- (repeat per table as needed)
```

> Warning: disabling RLS exposes all data to the anon key. Only use in a dev environment.
