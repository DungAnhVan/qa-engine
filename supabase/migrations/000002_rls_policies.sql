-- ==========================================================================
-- Migration 000002: Row Level Security (RLS) Policies
-- Gate 51 — Supabase Schema Design
-- ==========================================================================
-- Design philosophy:
-- - All user-facing tables have RLS enabled.
-- - source_documents and source_items are protected (internal only).
-- - Policies use auth.uid() -> profiles.id to resolve role + organization.
-- - Conservative first: prefer restrictive policies with TODO where exact
--   logic depends on product decisions still pending.
-- ==========================================================================

-- --------------------------------------------------------------------------
-- Helper view: current user's profile
-- Makes role/org lookup reusable without a function call per row.
-- --------------------------------------------------------------------------
create or replace view _my_profile as
  select id, organization_id, role
  from profiles
  where id = auth.uid();

-- --------------------------------------------------------------------------
-- Enable RLS
-- --------------------------------------------------------------------------
alter table organizations           enable row level security;
alter table profiles                enable row level security;
alter table students                enable row level security;
alter table parent_student_links    enable row level security;
alter table subjects                enable row level security;
alter table source_documents        enable row level security;
alter table source_pairs            enable row level security;
alter table source_items            enable row level security;
alter table skill_units             enable row level security;
alter table generation_targets      enable row level security;
alter table authoring_batches       enable row level security;
alter table resources               enable row level security;
alter table resource_packages       enable row level security;
alter table resource_package_items  enable row level security;
alter table attempts                enable row level security;
alter table marked_attempts         enable row level security;
alter table teacher_reviews         enable row level security;
alter table student_reports         enable row level security;
alter table audit_events            enable row level security;

-- ==========================================================================
-- organizations
-- ==========================================================================
-- Admin can see their own org.
create policy "org: admin can read own org"
  on organizations for select
  using (
    id in (select organization_id from _my_profile where role = 'admin')
  );

-- TODO: org create/update controlled at service-role level for now.

-- ==========================================================================
-- profiles
-- ==========================================================================
-- Users can always read their own profile.
create policy "profiles: read own"
  on profiles for select
  using (id = auth.uid());

-- Users can update their own profile.
create policy "profiles: update own"
  on profiles for update
  using (id = auth.uid());

-- Admin can read all profiles in their org.
create policy "profiles: admin can read org profiles"
  on profiles for select
  using (
    organization_id in (
      select organization_id from _my_profile where role = 'admin'
    )
  );

-- Teacher can read profiles in their org.
create policy "profiles: teacher can read org profiles"
  on profiles for select
  using (
    organization_id in (
      select organization_id from _my_profile where role = 'teacher'
    )
  );

-- ==========================================================================
-- students
-- ==========================================================================
-- Admin: full access within their org.
create policy "students: admin full access"
  on students for all
  using (
    organization_id in (
      select organization_id from _my_profile where role = 'admin'
    )
  );

-- Teacher: read all students in their org.
create policy "students: teacher read org students"
  on students for select
  using (
    organization_id in (
      select organization_id from _my_profile where role = 'teacher'
    )
  );

-- Student: can only read their own student row.
create policy "students: student read own"
  on students for select
  using (
    profile_id = auth.uid()
  );

-- Parent: can read linked students.
create policy "students: parent read linked students"
  on students for select
  using (
    id in (
      select student_id
      from parent_student_links
      where parent_profile_id = auth.uid()
    )
  );

-- ==========================================================================
-- parent_student_links
-- ==========================================================================
create policy "parent_links: parent read own"
  on parent_student_links for select
  using (parent_profile_id = auth.uid());

create policy "parent_links: admin full access"
  on parent_student_links for all
  using (
    exists (
      select 1 from _my_profile where role = 'admin'
    )
  );

-- ==========================================================================
-- subjects
-- subjects are reference data — all authenticated users can read.
-- Only service-role can insert/update (done via migration/seed).
-- ==========================================================================
create policy "subjects: authenticated read all"
  on subjects for select
  using (auth.uid() is not null);

-- ==========================================================================
-- source_documents / source_pairs / source_items
-- PROTECTED — internal reference only. No student or parent access.
-- ==========================================================================
create policy "source_documents: admin and teacher read"
  on source_documents for select
  using (
    exists (
      select 1 from _my_profile
      where role in ('admin','teacher')
        and organization_id = source_documents.organization_id
    )
  );

-- source_pairs and source_items: same protection level.
create policy "source_pairs: admin and teacher read"
  on source_pairs for select
  using (
    exists (select 1 from _my_profile where role in ('admin','teacher'))
  );

create policy "source_items: admin and teacher read"
  on source_items for select
  using (
    exists (select 1 from _my_profile where role in ('admin','teacher'))
  );

-- ==========================================================================
-- skill_units
-- Internal to teachers/admins. Not directly exposed to students.
-- ==========================================================================
create policy "skill_units: admin and teacher read"
  on skill_units for select
  using (
    exists (select 1 from _my_profile where role in ('admin','teacher'))
  );

-- ==========================================================================
-- generation_targets / authoring_batches
-- Admin only — part of content pipeline.
-- ==========================================================================
create policy "generation_targets: admin only"
  on generation_targets for all
  using (
    exists (select 1 from _my_profile where role = 'admin')
  );

create policy "authoring_batches: admin only"
  on authoring_batches for all
  using (
    exists (select 1 from _my_profile where role = 'admin')
  );

-- ==========================================================================
-- resources
-- Students can read published resources.
-- Teachers can read all resources in their org.
-- Admins have full access.
-- ==========================================================================
create policy "resources: student reads published"
  on resources for select
  using (
    publish_status = 'published'
    and organization_id in (
      select p.organization_id
      from students s
      join profiles p on p.id = s.profile_id
      where s.profile_id = auth.uid()
    )
  );

create policy "resources: teacher reads org resources"
  on resources for select
  using (
    organization_id in (
      select organization_id from _my_profile where role = 'teacher'
    )
  );

create policy "resources: admin full access"
  on resources for all
  using (
    organization_id in (
      select organization_id from _my_profile where role = 'admin'
    )
  );

-- TODO: teacher update for needs_human_review resources requires
-- an additional policy scoped to teacher_review publish_status.

-- ==========================================================================
-- resource_packages / resource_package_items
-- ==========================================================================
create policy "resource_packages: authenticated read active"
  on resource_packages for select
  using (
    status = 'active'
    and auth.uid() is not null
  );

create policy "resource_packages: admin full access"
  on resource_packages for all
  using (
    exists (select 1 from _my_profile where role = 'admin')
  );

create policy "resource_package_items: authenticated read"
  on resource_package_items for select
  using (auth.uid() is not null);

-- ==========================================================================
-- attempts
-- Students can insert and read own attempts.
-- Teachers/admins can read all attempts in their org.
-- ==========================================================================
create policy "attempts: student insert own"
  on attempts for insert
  with check (
    student_id in (
      select id from students where profile_id = auth.uid()
    )
  );

create policy "attempts: student read own"
  on attempts for select
  using (
    student_id in (
      select id from students where profile_id = auth.uid()
    )
  );

create policy "attempts: teacher and admin read org"
  on attempts for select
  using (
    exists (select 1 from _my_profile where role in ('teacher','admin'))
  );

create policy "attempts: parent read linked student"
  on attempts for select
  using (
    student_id in (
      select student_id from parent_student_links
      where parent_profile_id = auth.uid()
    )
  );

-- ==========================================================================
-- marked_attempts
-- ==========================================================================
create policy "marked_attempts: student read own"
  on marked_attempts for select
  using (
    student_id in (
      select id from students where profile_id = auth.uid()
    )
  );

create policy "marked_attempts: teacher and admin read"
  on marked_attempts for select
  using (
    exists (select 1 from _my_profile where role in ('teacher','admin'))
  );

create policy "marked_attempts: parent read linked student"
  on marked_attempts for select
  using (
    student_id in (
      select student_id from parent_student_links
      where parent_profile_id = auth.uid()
    )
  );

-- ==========================================================================
-- teacher_reviews
-- ==========================================================================
create policy "teacher_reviews: teacher insert own"
  on teacher_reviews for insert
  with check (reviewer_profile_id = auth.uid());

create policy "teacher_reviews: teacher read org"
  on teacher_reviews for select
  using (
    organization_id in (
      select organization_id from _my_profile where role in ('teacher','admin')
    )
  );

create policy "teacher_reviews: admin full access"
  on teacher_reviews for all
  using (
    organization_id in (
      select organization_id from _my_profile where role = 'admin'
    )
  );

-- ==========================================================================
-- student_reports
-- ==========================================================================
create policy "student_reports: student read own"
  on student_reports for select
  using (
    student_id in (
      select id from students where profile_id = auth.uid()
    )
  );

create policy "student_reports: teacher read org"
  on student_reports for select
  using (
    exists (select 1 from _my_profile where role in ('teacher','admin'))
  );

create policy "student_reports: parent read linked"
  on student_reports for select
  using (
    student_id in (
      select student_id from parent_student_links
      where parent_profile_id = auth.uid()
    )
  );

-- ==========================================================================
-- audit_events
-- Admin read only. Never student-visible.
-- ==========================================================================
create policy "audit_events: admin read"
  on audit_events for select
  using (
    organization_id in (
      select organization_id from _my_profile where role = 'admin'
    )
  );

-- Service role bypasses RLS for insert (append-only audit log).
-- TODO: Use Supabase Edge Function or trigger to write audit_events
-- so no client-side insert policy is needed.
