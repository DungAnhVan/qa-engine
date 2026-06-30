-- ==========================================================================
-- Migration 000004: RLS Hardening + Role-Based Policies
-- Gate 62 — Quanta Aptus
-- ==========================================================================
--
-- PURPOSE
-- -------
-- Enables Row Level Security (RLS) on all core tables and creates
-- role-aware policies for admin / teacher / student / parent roles.
--
-- IMPORTANT NOTES
-- ---------------
-- 1. This migration uses DROP POLICY IF EXISTS before CREATE POLICY.
--    It does NOT drop tables, columns, views, or data.
-- 2. It is safe to re-run (idempotent).
-- 3. Helper functions use SECURITY DEFINER to avoid RLS recursion when
--    reading the profiles table to determine the current user's role.
-- 4. The application server uses the service role key which bypasses RLS.
--    These policies protect direct/client-side access via the anon key.
-- 5. If a table listed here does not exist in your project, comment out
--    that section and apply the rest.
--
-- HOW TO APPLY
-- ------------
-- Open the Supabase Dashboard SQL Editor and paste this file.
-- A notice about DROP POLICY may appear — that is expected and safe.
-- No destructive DDL (no table or data drops) is present in this file.
--
-- VERIFICATION
-- ------------
-- SELECT trigger_name FROM information_schema.triggers
-- WHERE trigger_schema = 'public';
--
-- SELECT schemaname, tablename, rowsecurity
-- FROM pg_tables WHERE schemaname = 'public'
-- ORDER BY tablename;
-- ==========================================================================

-- ==========================================================================
-- SECTION 1: Helper functions (SECURITY DEFINER — bypasses RLS recursion)
-- ==========================================================================

-- Returns auth.uid() — convenience wrapper
CREATE OR REPLACE FUNCTION public.current_profile_id()
RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT auth.uid();
$$;

-- Returns the role text for the current authenticated user (reads profiles)
CREATE OR REPLACE FUNCTION public.current_profile_role()
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT role::text FROM public.profiles WHERE id = auth.uid() LIMIT 1;
$$;

-- Returns the organization_id for the current authenticated user
CREATE OR REPLACE FUNCTION public.current_organization_id()
RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT organization_id FROM public.profiles WHERE id = auth.uid() LIMIT 1;
$$;

-- Boolean role helpers
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT public.current_profile_role() = 'admin';
$$;

CREATE OR REPLACE FUNCTION public.is_teacher()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT public.current_profile_role() = 'teacher';
$$;

CREATE OR REPLACE FUNCTION public.is_student()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT public.current_profile_role() = 'student';
$$;

CREATE OR REPLACE FUNCTION public.is_parent()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT public.current_profile_role() = 'parent';
$$;

CREATE OR REPLACE FUNCTION public.is_admin_or_teacher()
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT public.current_profile_role() IN ('admin', 'teacher');
$$;

-- Returns UUID of the student row linked to current authenticated user
CREATE OR REPLACE FUNCTION public.my_student_id()
RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT id FROM public.students WHERE profile_id = auth.uid() LIMIT 1;
$$;

-- Returns all student ids in the same organization as the current user
CREATE OR REPLACE FUNCTION public.student_ids_in_my_org()
RETURNS SETOF uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT id FROM public.students
  WHERE organization_id = public.current_organization_id();
$$;

-- Returns student ids linked to the current parent profile
CREATE OR REPLACE FUNCTION public.linked_student_ids_for_parent()
RETURNS SETOF uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT student_id FROM public.parent_student_links
  WHERE parent_profile_id = auth.uid();
$$;

-- Returns attempt ids for the current student's own record
CREATE OR REPLACE FUNCTION public.my_attempt_ids()
RETURNS SETOF uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT id FROM public.attempts
  WHERE student_id = public.my_student_id();
$$;

-- Returns attempt ids for all students in same org (for admin/teacher)
CREATE OR REPLACE FUNCTION public.attempt_ids_in_my_org()
RETURNS SETOF uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT a.id FROM public.attempts a
  JOIN public.students s ON s.id = a.student_id
  WHERE s.organization_id = public.current_organization_id();
$$;

-- Returns attempt ids for students linked to the current parent
CREATE OR REPLACE FUNCTION public.linked_attempt_ids_for_parent()
RETURNS SETOF uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT id FROM public.attempts
  WHERE student_id IN (SELECT public.linked_student_ids_for_parent());
$$;

-- Returns resource_package ids in same org as current user
CREATE OR REPLACE FUNCTION public.package_ids_in_my_org()
RETURNS SETOF uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT id FROM public.resource_packages
  WHERE organization_id = public.current_organization_id();
$$;

-- ==========================================================================
-- SECTION 2: Enable RLS on all core tables
-- Note: ALTER TABLE ... ENABLE ROW LEVEL SECURITY is idempotent.
-- ==========================================================================

ALTER TABLE public.profiles             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.students             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parent_student_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subjects             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resources            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resource_packages    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resource_package_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attempts             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.marked_attempts      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.teacher_reviews      ENABLE ROW LEVEL SECURITY;

-- Enable on optional tables (comment out if table does not exist)
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'student_reports'
  ) THEN
    EXECUTE 'ALTER TABLE public.student_reports ENABLE ROW LEVEL SECURITY';
  END IF;
END $$;

DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'audit_events'
  ) THEN
    EXECUTE 'ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY';
  END IF;
END $$;

-- ==========================================================================
-- SECTION 3: Drop existing policies (idempotent — safe to re-run)
-- ==========================================================================

-- profiles
DROP POLICY IF EXISTS "profiles_select_own"               ON public.profiles;
DROP POLICY IF EXISTS "profiles_select_admin_same_org"    ON public.profiles;
DROP POLICY IF EXISTS "profiles_update_own"               ON public.profiles;
DROP POLICY IF EXISTS "profiles_update_admin"             ON public.profiles;

-- students
DROP POLICY IF EXISTS "students_select_own"               ON public.students;
DROP POLICY IF EXISTS "students_select_admin_teacher"     ON public.students;
DROP POLICY IF EXISTS "students_select_parent_linked"     ON public.students;
DROP POLICY IF EXISTS "students_insert_admin"             ON public.students;
DROP POLICY IF EXISTS "students_update_admin"             ON public.students;

-- parent_student_links
DROP POLICY IF EXISTS "psl_select_admin_teacher"          ON public.parent_student_links;
DROP POLICY IF EXISTS "psl_select_parent_own"             ON public.parent_student_links;
DROP POLICY IF EXISTS "psl_select_student_self"           ON public.parent_student_links;
DROP POLICY IF EXISTS "psl_insert_admin"                  ON public.parent_student_links;
DROP POLICY IF EXISTS "psl_update_admin"                  ON public.parent_student_links;
DROP POLICY IF EXISTS "psl_delete_admin"                  ON public.parent_student_links;

-- subjects
DROP POLICY IF EXISTS "subjects_select_authenticated"     ON public.subjects;
DROP POLICY IF EXISTS "subjects_insert_admin"             ON public.subjects;
DROP POLICY IF EXISTS "subjects_update_admin"             ON public.subjects;

-- resources
DROP POLICY IF EXISTS "resources_select_authenticated"    ON public.resources;
DROP POLICY IF EXISTS "resources_insert_admin_teacher"    ON public.resources;
DROP POLICY IF EXISTS "resources_update_admin_teacher"    ON public.resources;
DROP POLICY IF EXISTS "resources_delete_admin"            ON public.resources;

-- resource_packages
DROP POLICY IF EXISTS "rp_select_authenticated"           ON public.resource_packages;
DROP POLICY IF EXISTS "rp_insert_admin"                   ON public.resource_packages;
DROP POLICY IF EXISTS "rp_update_admin"                   ON public.resource_packages;

-- resource_package_items
DROP POLICY IF EXISTS "rpi_select_authenticated"          ON public.resource_package_items;
DROP POLICY IF EXISTS "rpi_insert_admin"                  ON public.resource_package_items;
DROP POLICY IF EXISTS "rpi_delete_admin"                  ON public.resource_package_items;

-- attempts
DROP POLICY IF EXISTS "attempts_select_student_own"       ON public.attempts;
DROP POLICY IF EXISTS "attempts_select_admin_teacher"     ON public.attempts;
DROP POLICY IF EXISTS "attempts_select_parent_linked"     ON public.attempts;
DROP POLICY IF EXISTS "attempts_insert_student_own"       ON public.attempts;
DROP POLICY IF EXISTS "attempts_update_admin_teacher"     ON public.attempts;

-- marked_attempts
DROP POLICY IF EXISTS "ma_select_student_own"             ON public.marked_attempts;
DROP POLICY IF EXISTS "ma_select_admin_teacher"           ON public.marked_attempts;
DROP POLICY IF EXISTS "ma_select_parent_linked"           ON public.marked_attempts;
DROP POLICY IF EXISTS "ma_insert_admin_teacher"           ON public.marked_attempts;
DROP POLICY IF EXISTS "ma_update_admin_teacher"           ON public.marked_attempts;

-- teacher_reviews
DROP POLICY IF EXISTS "tr_select_admin_teacher"           ON public.teacher_reviews;
DROP POLICY IF EXISTS "tr_select_student_own_feedback"    ON public.teacher_reviews;
DROP POLICY IF EXISTS "tr_select_parent_linked_feedback"  ON public.teacher_reviews;
DROP POLICY IF EXISTS "tr_insert_admin_teacher"           ON public.teacher_reviews;
DROP POLICY IF EXISTS "tr_update_admin_teacher"           ON public.teacher_reviews;

-- student_reports (optional table)
DROP POLICY IF EXISTS "sr_select_student_own"             ON public.student_reports;
DROP POLICY IF EXISTS "sr_select_admin_teacher"           ON public.student_reports;
DROP POLICY IF EXISTS "sr_select_parent_linked"           ON public.student_reports;
DROP POLICY IF EXISTS "sr_insert_admin_teacher"           ON public.student_reports;

-- audit_events (optional table)
DROP POLICY IF EXISTS "ae_select_admin"                   ON public.audit_events;

-- ==========================================================================
-- SECTION 4: profiles policies
-- ==========================================================================

-- Any authenticated user can read their own profile row
CREATE POLICY "profiles_select_own"
ON public.profiles FOR SELECT
USING (id = auth.uid());

-- Admin can read all profiles in the same organization
CREATE POLICY "profiles_select_admin_same_org"
ON public.profiles FOR SELECT
USING (
  public.is_admin()
  AND organization_id = public.current_organization_id()
);

-- Any user can update their own profile's display_name / email
-- (server should enforce column restrictions in app layer)
CREATE POLICY "profiles_update_own"
ON public.profiles FOR UPDATE
USING (id = auth.uid())
WITH CHECK (id = auth.uid());

-- Admin can update any profile in the same org
CREATE POLICY "profiles_update_admin"
ON public.profiles FOR UPDATE
USING (
  public.is_admin()
  AND organization_id = public.current_organization_id()
)
WITH CHECK (
  public.is_admin()
  AND organization_id = public.current_organization_id()
);

-- ==========================================================================
-- SECTION 5: students policies
-- ==========================================================================

-- Student can read their own student record (via profile_id link)
CREATE POLICY "students_select_own"
ON public.students FOR SELECT
USING (profile_id = auth.uid());

-- Admin and teacher can read students in the same organization
CREATE POLICY "students_select_admin_teacher"
ON public.students FOR SELECT
USING (
  public.is_admin_or_teacher()
  AND organization_id = public.current_organization_id()
);

-- Parent can read students linked to them
CREATE POLICY "students_select_parent_linked"
ON public.students FOR SELECT
USING (
  public.is_parent()
  AND id IN (SELECT public.linked_student_ids_for_parent())
);

-- Only admin can insert/update student records
CREATE POLICY "students_insert_admin"
ON public.students FOR INSERT
WITH CHECK (
  public.is_admin()
  AND organization_id = public.current_organization_id()
);

CREATE POLICY "students_update_admin"
ON public.students FOR UPDATE
USING (
  public.is_admin()
  AND organization_id = public.current_organization_id()
)
WITH CHECK (
  public.is_admin()
  AND organization_id = public.current_organization_id()
);

-- ==========================================================================
-- SECTION 6: parent_student_links policies
-- ==========================================================================

-- Admin/teacher can read all links for students in their org
CREATE POLICY "psl_select_admin_teacher"
ON public.parent_student_links FOR SELECT
USING (
  public.is_admin_or_teacher()
  AND student_id IN (SELECT public.student_ids_in_my_org())
);

-- Parent can read their own links
CREATE POLICY "psl_select_parent_own"
ON public.parent_student_links FOR SELECT
USING (parent_profile_id = auth.uid());

-- Student can read links where they are the student
CREATE POLICY "psl_select_student_self"
ON public.parent_student_links FOR SELECT
USING (student_id = public.my_student_id());

-- Only admin can create/update/delete links
CREATE POLICY "psl_insert_admin"
ON public.parent_student_links FOR INSERT
WITH CHECK (public.is_admin());

CREATE POLICY "psl_update_admin"
ON public.parent_student_links FOR UPDATE
USING (public.is_admin())
WITH CHECK (public.is_admin());

CREATE POLICY "psl_delete_admin"
ON public.parent_student_links FOR DELETE
USING (public.is_admin());

-- ==========================================================================
-- SECTION 7: subjects policies
-- ==========================================================================

-- All authenticated users can read subjects in their organization
CREATE POLICY "subjects_select_authenticated"
ON public.subjects FOR SELECT
USING (
  auth.uid() IS NOT NULL
  AND organization_id = public.current_organization_id()
);

-- Only admin can manage subjects
CREATE POLICY "subjects_insert_admin"
ON public.subjects FOR INSERT
WITH CHECK (public.is_admin() AND organization_id = public.current_organization_id());

CREATE POLICY "subjects_update_admin"
ON public.subjects FOR UPDATE
USING (public.is_admin() AND organization_id = public.current_organization_id())
WITH CHECK (public.is_admin() AND organization_id = public.current_organization_id());

-- ==========================================================================
-- SECTION 8: resources policies
-- ==========================================================================

-- All authenticated users in same org can read resources
CREATE POLICY "resources_select_authenticated"
ON public.resources FOR SELECT
USING (
  auth.uid() IS NOT NULL
  AND organization_id = public.current_organization_id()
);

-- Admin/teacher can manage resources (create study content)
CREATE POLICY "resources_insert_admin_teacher"
ON public.resources FOR INSERT
WITH CHECK (
  public.is_admin_or_teacher()
  AND organization_id = public.current_organization_id()
);

CREATE POLICY "resources_update_admin_teacher"
ON public.resources FOR UPDATE
USING (
  public.is_admin_or_teacher()
  AND organization_id = public.current_organization_id()
)
WITH CHECK (
  public.is_admin_or_teacher()
  AND organization_id = public.current_organization_id()
);

-- Only admin can hard-delete resources
CREATE POLICY "resources_delete_admin"
ON public.resources FOR DELETE
USING (public.is_admin() AND organization_id = public.current_organization_id());

-- ==========================================================================
-- SECTION 9: resource_packages policies
-- ==========================================================================

CREATE POLICY "rp_select_authenticated"
ON public.resource_packages FOR SELECT
USING (
  auth.uid() IS NOT NULL
  AND organization_id = public.current_organization_id()
);

CREATE POLICY "rp_insert_admin"
ON public.resource_packages FOR INSERT
WITH CHECK (public.is_admin() AND organization_id = public.current_organization_id());

CREATE POLICY "rp_update_admin"
ON public.resource_packages FOR UPDATE
USING (public.is_admin() AND organization_id = public.current_organization_id())
WITH CHECK (public.is_admin() AND organization_id = public.current_organization_id());

-- ==========================================================================
-- SECTION 10: resource_package_items policies
-- ==========================================================================

-- Items are accessible to authenticated users if the parent package is in their org
CREATE POLICY "rpi_select_authenticated"
ON public.resource_package_items FOR SELECT
USING (
  auth.uid() IS NOT NULL
  AND package_id IN (SELECT public.package_ids_in_my_org())
);

CREATE POLICY "rpi_insert_admin"
ON public.resource_package_items FOR INSERT
WITH CHECK (public.is_admin());

CREATE POLICY "rpi_delete_admin"
ON public.resource_package_items FOR DELETE
USING (public.is_admin());

-- ==========================================================================
-- SECTION 11: attempts policies
-- ==========================================================================

-- Student can read own attempts (via their student record)
CREATE POLICY "attempts_select_student_own"
ON public.attempts FOR SELECT
USING (student_id = public.my_student_id());

-- Admin/teacher can read attempts for students in same org
CREATE POLICY "attempts_select_admin_teacher"
ON public.attempts FOR SELECT
USING (
  public.is_admin_or_teacher()
  AND student_id IN (SELECT public.student_ids_in_my_org())
);

-- Parent can read attempts for linked students
CREATE POLICY "attempts_select_parent_linked"
ON public.attempts FOR SELECT
USING (
  public.is_parent()
  AND student_id IN (SELECT public.linked_student_ids_for_parent())
);

-- Student can only insert attempts for their own student record
CREATE POLICY "attempts_insert_student_own"
ON public.attempts FOR INSERT
WITH CHECK (student_id = public.my_student_id());

-- Admin/teacher can update attempts (e.g. marking_status field)
CREATE POLICY "attempts_update_admin_teacher"
ON public.attempts FOR UPDATE
USING (
  public.is_admin_or_teacher()
  AND student_id IN (SELECT public.student_ids_in_my_org())
)
WITH CHECK (
  public.is_admin_or_teacher()
  AND student_id IN (SELECT public.student_ids_in_my_org())
);

-- ==========================================================================
-- SECTION 12: marked_attempts policies
-- ==========================================================================

-- Student can read marked results for own attempts
CREATE POLICY "ma_select_student_own"
ON public.marked_attempts FOR SELECT
USING (attempt_id IN (SELECT public.my_attempt_ids()));

-- Admin/teacher can read all marked attempts in same org
CREATE POLICY "ma_select_admin_teacher"
ON public.marked_attempts FOR SELECT
USING (
  public.is_admin_or_teacher()
  AND attempt_id IN (SELECT public.attempt_ids_in_my_org())
);

-- Parent can read marked attempts for linked students
CREATE POLICY "ma_select_parent_linked"
ON public.marked_attempts FOR SELECT
USING (
  public.is_parent()
  AND attempt_id IN (SELECT public.linked_attempt_ids_for_parent())
);

-- Only admin/teacher (via server marking pipeline) may insert/update marked_attempts
CREATE POLICY "ma_insert_admin_teacher"
ON public.marked_attempts FOR INSERT
WITH CHECK (public.is_admin_or_teacher());

CREATE POLICY "ma_update_admin_teacher"
ON public.marked_attempts FOR UPDATE
USING (public.is_admin_or_teacher())
WITH CHECK (public.is_admin_or_teacher());

-- ==========================================================================
-- SECTION 13: teacher_reviews policies
-- ==========================================================================

-- Admin/teacher can read all reviews for attempts in same org
CREATE POLICY "tr_select_admin_teacher"
ON public.teacher_reviews FOR SELECT
USING (
  public.is_admin_or_teacher()
  AND attempt_id IN (SELECT public.attempt_ids_in_my_org())
);

-- Student can read teacher feedback for their own attempts
CREATE POLICY "tr_select_student_own_feedback"
ON public.teacher_reviews FOR SELECT
USING (
  public.is_student()
  AND attempt_id IN (SELECT public.my_attempt_ids())
);

-- Parent can read teacher feedback for linked student attempts
CREATE POLICY "tr_select_parent_linked_feedback"
ON public.teacher_reviews FOR SELECT
USING (
  public.is_parent()
  AND attempt_id IN (SELECT public.linked_attempt_ids_for_parent())
);

-- Only admin/teacher may write reviews
CREATE POLICY "tr_insert_admin_teacher"
ON public.teacher_reviews FOR INSERT
WITH CHECK (public.is_admin_or_teacher());

CREATE POLICY "tr_update_admin_teacher"
ON public.teacher_reviews FOR UPDATE
USING (public.is_admin_or_teacher())
WITH CHECK (public.is_admin_or_teacher());

-- ==========================================================================
-- SECTION 14: student_reports policies (if table exists)
-- ==========================================================================

DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'student_reports'
  ) THEN

    EXECUTE $pol$
      CREATE POLICY "sr_select_student_own"
      ON public.student_reports FOR SELECT
      USING (student_id = public.my_student_id());
    $pol$;

    EXECUTE $pol$
      CREATE POLICY "sr_select_admin_teacher"
      ON public.student_reports FOR SELECT
      USING (
        public.is_admin_or_teacher()
        AND student_id IN (SELECT public.student_ids_in_my_org())
      );
    $pol$;

    EXECUTE $pol$
      CREATE POLICY "sr_select_parent_linked"
      ON public.student_reports FOR SELECT
      USING (
        public.is_parent()
        AND student_id IN (SELECT public.linked_student_ids_for_parent())
      );
    $pol$;

    EXECUTE $pol$
      CREATE POLICY "sr_insert_admin_teacher"
      ON public.student_reports FOR INSERT
      WITH CHECK (public.is_admin_or_teacher());
    $pol$;

  END IF;
END $$;

-- ==========================================================================
-- SECTION 15: audit_events policies (if table exists)
-- ==========================================================================

DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'audit_events'
  ) THEN
    -- Only admin may read audit events; service role inserts bypass RLS
    EXECUTE $pol$
      CREATE POLICY "ae_select_admin"
      ON public.audit_events FOR SELECT
      USING (public.is_admin());
    $pol$;
  END IF;
END $$;

-- ==========================================================================
-- VERIFICATION QUERIES (run after applying)
-- ==========================================================================
-- Check RLS is enabled on all tables:
--   SELECT tablename, rowsecurity FROM pg_tables
--   WHERE schemaname = 'public' ORDER BY tablename;
--
-- Check policies created:
--   SELECT schemaname, tablename, policyname, cmd, qual
--   FROM pg_policies WHERE schemaname = 'public' ORDER BY tablename, policyname;
--
-- Check helper functions:
--   SELECT routine_name FROM information_schema.routines
--   WHERE routine_schema = 'public' AND routine_name LIKE 'is_%' OR routine_name LIKE 'current_%'
--   OR routine_name LIKE 'my_%' OR routine_name LIKE 'linked_%' OR routine_name LIKE 'attempt_%'
--   OR routine_name LIKE 'student_%' OR routine_name LIKE 'package_%'
--   ORDER BY routine_name;
-- ==========================================================================
