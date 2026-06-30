-- ==========================================================================
-- Migration 000003: Auth Profile Trigger
-- Gate 60 — Supabase Auth + Roles Foundation
-- ==========================================================================
-- When a new user is created in auth.users (via Supabase Auth SDK or
-- Dashboard), automatically insert a matching row in public.profiles.
--
-- Role is read from raw_user_meta_data->>'role'.
-- Valid values: admin, teacher, student, parent.
-- Defaults to 'student' if missing or invalid.
--
-- organization_id defaults to the org with slug 'quanta-aptus-local-demo'
-- if that org exists; otherwise NULL.
--
-- display_name is read from raw_user_meta_data->>'display_name'; falls
-- back to the auth email address.
--
-- Safe to run multiple times:
--   CREATE OR REPLACE FUNCTION (idempotent)
--   DROP TRIGGER IF EXISTS before CREATE TRIGGER
-- ==========================================================================

-- --------------------------------------------------------------------------
-- Function: public.handle_new_user
-- Fired AFTER INSERT on auth.users.
-- --------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_role         text;
  v_org_id       uuid;
  v_display_name text;
BEGIN
  -- Resolve role — accept only the four valid values, else default to student
  v_role := (new.raw_user_meta_data ->> 'role');
  IF v_role NOT IN ('admin', 'teacher', 'student', 'parent') THEN
    v_role := 'student';
  END IF;

  -- Resolve organization — default to demo org if present
  SELECT id
    INTO v_org_id
    FROM public.organizations
   WHERE slug = 'quanta-aptus-local-demo'
   LIMIT 1;

  -- Resolve display name — prefer metadata, fall back to email
  v_display_name := COALESCE(
    new.raw_user_meta_data ->> 'display_name',
    new.email
  );

  -- Insert profile row; skip if already exists (e.g. seed re-runs)
  INSERT INTO public.profiles (id, organization_id, display_name, email, role)
  VALUES (new.id, v_org_id, v_display_name, new.email, v_role)
  ON CONFLICT (id) DO NOTHING;

  RETURN new;
END;
$$;

-- --------------------------------------------------------------------------
-- Trigger: on_auth_user_created
-- Drop first so re-running this file is safe.
-- --------------------------------------------------------------------------
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- --------------------------------------------------------------------------
-- Verification comment
-- --------------------------------------------------------------------------
-- To verify the trigger is installed:
--   SELECT trigger_name, event_manipulation, event_object_schema, event_object_table
--   FROM information_schema.triggers
--   WHERE trigger_name = 'on_auth_user_created';
--
-- To test (with a real auth user signed up via Supabase Auth):
--   SELECT id, email, role, organization_id
--   FROM public.profiles
--   ORDER BY created_at DESC
--   LIMIT 5;
-- ==========================================================================
