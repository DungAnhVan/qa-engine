-- ==========================================================================
-- Seed: Demo Auth Profiles
-- Gate 60 — Supabase Auth + Roles Foundation
-- ==========================================================================
-- PURPOSE
-- -------
-- Inserts demo profile rows for local development and integration testing.
-- These rows allow role-based page tests WITHOUT requiring real Supabase
-- Auth users to be created first.
--
-- IMPORTANT NOTES
-- ---------------
-- 1. profiles.id normally MUST match an auth.users.id (created via Supabase
--    Auth SDK or Dashboard). These demo rows use fixed placeholder UUIDs that
--    do NOT have matching auth.users rows. They work only in a development
--    environment where RLS is bypassed (service role key) or disabled.
--
-- 2. In production, NEVER insert profiles manually. Use the auth trigger in
--    migration 000003 which auto-creates profiles when real users sign up.
--
-- 3. The demo student (external_code = 'local_demo_student') is seeded in
--    seed_local_mvp_demo.sql and is not duplicated here.
--
-- 4. All rows use ON CONFLICT (id) DO NOTHING so this file is idempotent.
--
-- DEMO UUID LEGEND
-- ----------------
--   Admin   profile: a0000000-0000-0000-0000-000000000001
--   Teacher profile: a0000000-0000-0000-0000-000000000002
--   Student profile: a0000000-0000-0000-0000-000000000003
--   Parent  profile: a0000000-0000-0000-0000-000000000004
-- ==========================================================================

-- Resolve demo organization id for use in profile rows
DO $$
DECLARE
  v_org_id uuid;
BEGIN
  SELECT id INTO v_org_id
    FROM public.organizations
   WHERE slug = 'quanta-aptus-local-demo'
   LIMIT 1;

  IF v_org_id IS NULL THEN
    RAISE NOTICE 'Demo organization not found — profiles will have NULL organization_id. Run seed_local_mvp_demo.sql first.';
  END IF;

  -- Admin demo profile
  INSERT INTO public.profiles (id, organization_id, display_name, email, role)
  VALUES (
    'a0000000-0000-0000-0000-000000000001',
    v_org_id,
    'Demo Admin',
    'admin@demo.local',
    'admin'
  )
  ON CONFLICT (id) DO NOTHING;

  -- Teacher demo profile
  INSERT INTO public.profiles (id, organization_id, display_name, email, role)
  VALUES (
    'a0000000-0000-0000-0000-000000000002',
    v_org_id,
    'Demo Teacher',
    'teacher@demo.local',
    'teacher'
  )
  ON CONFLICT (id) DO NOTHING;

  -- Student demo profile
  -- Note: the demo student row in students table uses external_code = 'local_demo_student'
  -- and UUID 20000000-0000-0000-0000-000000000001. This profile is separate.
  INSERT INTO public.profiles (id, organization_id, display_name, email, role)
  VALUES (
    'a0000000-0000-0000-0000-000000000003',
    v_org_id,
    'Demo Student',
    'student@demo.local',
    'student'
  )
  ON CONFLICT (id) DO NOTHING;

  -- Parent demo profile
  INSERT INTO public.profiles (id, organization_id, display_name, email, role)
  VALUES (
    'a0000000-0000-0000-0000-000000000004',
    v_org_id,
    'Demo Parent',
    'parent@demo.local',
    'parent'
  )
  ON CONFLICT (id) DO NOTHING;

END $$;

-- ==========================================================================
-- Verification query (run after seeding)
-- ==========================================================================
-- SELECT id, display_name, email, role FROM public.profiles ORDER BY role;
-- ==========================================================================
