-- ==========================================================================
-- Migration 000001: Quanta Aptus Core Schema v1
-- Gate 51 — Supabase Schema Design
-- Compatible with Supabase Postgres (PostgreSQL 15+)
-- ==========================================================================

-- --------------------------------------------------------------------------
-- Extensions
-- --------------------------------------------------------------------------
create extension if not exists "pgcrypto";

-- --------------------------------------------------------------------------
-- Helpers
-- --------------------------------------------------------------------------
-- Automatic updated_at trigger function
create or replace function _set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- --------------------------------------------------------------------------
-- 1. organizations
-- --------------------------------------------------------------------------
create table organizations (
  id              uuid        primary key default gen_random_uuid(),
  name            text        not null,
  slug            text        unique not null,
  type            text        check (type in ('learning_center','school','homeschool','private_tutor','platform')),
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

create trigger organizations_updated_at
  before update on organizations
  for each row execute function _set_updated_at();

-- --------------------------------------------------------------------------
-- 2. profiles
-- Maps to auth.users (Supabase Auth). id = auth.uid().
-- --------------------------------------------------------------------------
create table profiles (
  id              uuid        primary key,
  organization_id uuid        references organizations(id),
  display_name    text,
  email           text,
  role            text        check (role in ('admin','teacher','student','parent')),
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

create trigger profiles_updated_at
  before update on profiles
  for each row execute function _set_updated_at();

-- --------------------------------------------------------------------------
-- 3. students
-- --------------------------------------------------------------------------
create table students (
  id              uuid        primary key default gen_random_uuid(),
  organization_id uuid        references organizations(id),
  profile_id      uuid        references profiles(id),
  display_name    text        not null,
  external_code   text,
  status          text        check (status in ('active','paused','archived')) default 'active',
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

create trigger students_updated_at
  before update on students
  for each row execute function _set_updated_at();

-- --------------------------------------------------------------------------
-- 4. parent_student_links
-- --------------------------------------------------------------------------
create table parent_student_links (
  id                uuid        primary key default gen_random_uuid(),
  parent_profile_id uuid        not null references profiles(id),
  student_id        uuid        not null references students(id),
  relationship      text,
  created_at        timestamptz default now(),
  unique (parent_profile_id, student_id)
);

-- --------------------------------------------------------------------------
-- 5. subjects
-- Populated from the subject adapter registry.
-- adapter_status: full_adapter = production-grade; basic_adapter = usable,
-- lower confidence; generic_adapter = unknown subject, always needs_human_review.
-- --------------------------------------------------------------------------
create table subjects (
  id              uuid        primary key default gen_random_uuid(),
  board           text        not null,
  level           text        not null,
  subject_slug    text        unique not null,
  subject_name    text        not null,
  syllabus_code   text        not null,
  adapter_name    text,
  adapter_status  text        check (adapter_status in ('full_adapter','basic_adapter','generic_adapter')),
  adapter_version text        default 'v1',
  is_active       boolean     default true,
  created_at      timestamptz default now()
);

create index subjects_slug_idx on subjects (subject_slug);

-- --------------------------------------------------------------------------
-- 6. source_documents
-- Raw PDF metadata — internal reference only. Never expose copyright content.
-- --------------------------------------------------------------------------
create table source_documents (
  id                uuid        primary key default gen_random_uuid(),
  subject_id        uuid        references subjects(id),
  organization_id   uuid        references organizations(id),
  source_type       text        check (source_type in ('question_paper','mark_scheme','syllabus','notes','other')),
  board             text,
  level             text,
  subject_slug      text,
  syllabus_code     text,
  series            text,
  year              int,
  component         text,
  variant           text,
  original_filename text        not null,
  storage_path      text,
  checksum          text,
  copyright_status  text        check (copyright_status in ('internal_reference_only','licensed','original','unknown'))
                                default 'internal_reference_only',
  ingest_status     text        check (ingest_status in ('pending','ingested','failed','archived'))
                                default 'pending',
  created_at        timestamptz default now()
);

create index source_documents_lookup_idx
  on source_documents (subject_slug, syllabus_code, year, component);

-- --------------------------------------------------------------------------
-- 7. source_pairs
-- Links a question paper and its mark scheme.
-- --------------------------------------------------------------------------
create table source_pairs (
  id                  uuid        primary key default gen_random_uuid(),
  subject_id          uuid        references subjects(id),
  question_paper_id   uuid        references source_documents(id),
  mark_scheme_id      uuid        references source_documents(id),
  pair_key            text        unique,
  status              text        check (status in ('complete','incomplete','duplicate','failed')),
  created_at          timestamptz default now()
);

-- --------------------------------------------------------------------------
-- 8. source_items
-- Individual parsed questions. Internal reference only.
-- --------------------------------------------------------------------------
create table source_items (
  id                  uuid        primary key default gen_random_uuid(),
  subject_id          uuid        references subjects(id),
  source_document_id  uuid        references source_documents(id),
  source_pair_id      uuid        references source_pairs(id),
  item_key            text,
  question_number     text,
  component_type      text,
  route               text,
  raw_text            text,
  marks               int,
  needs_review        boolean     default false,
  created_at          timestamptz default now()
);

-- --------------------------------------------------------------------------
-- 9. skill_units
-- Output of the skill-map layer. One row per source item classified.
-- confidence, adapter_status, needs_human_review are first-class columns
-- because they affect how the resource is used and who needs to review it.
-- --------------------------------------------------------------------------
create table skill_units (
  id                  uuid        primary key default gen_random_uuid(),
  subject_id          uuid        references subjects(id),
  source_item_id      uuid        references source_items(id),
  topic               text,
  subtopic            text,
  skill_type          text,
  resource_type       text,
  confidence          numeric     check (confidence >= 0 and confidence <= 1),
  adapter_name        text,
  adapter_status      text        check (adapter_status in ('full_adapter','basic_adapter','generic_adapter')),
  adapter_version     text        default 'v1',
  needs_human_review  boolean     default false,
  matched_keywords    jsonb       default '[]'::jsonb,
  created_at          timestamptz default now()
);

create index skill_units_classify_idx
  on skill_units (subject_id, topic, skill_type);

-- --------------------------------------------------------------------------
-- 10. generation_targets
-- Each skill_unit produces one or more generation targets for authoring.
-- --------------------------------------------------------------------------
create table generation_targets (
  id                  uuid        primary key default gen_random_uuid(),
  subject_id          uuid        references subjects(id),
  skill_unit_id       uuid        references skill_units(id),
  target_key          text,
  priority            int,
  target_resource_type text,
  prompt_context      jsonb       default '{}'::jsonb,
  status              text        check (status in (
                        'planned','authoring_prompt_ready','generated',
                        'validated','rejected','published'
                      )) default 'planned',
  created_at          timestamptz default now()
);

-- --------------------------------------------------------------------------
-- 11. authoring_batches
-- Tracks one AI authoring round-trip per batch.
-- --------------------------------------------------------------------------
create table authoring_batches (
  id                    uuid        primary key default gen_random_uuid(),
  subject_id            uuid        references subjects(id),
  batch_key             text        unique,
  prompt_path           text,
  expected_output_path  text,
  model_provider        text,
  model_name            text,
  adapter_version       text,
  status                text        check (status in (
                          'draft','waiting_for_generated_batch',
                          'generated','validated','failed'
                        )) default 'draft',
  created_at            timestamptz default now()
);

-- --------------------------------------------------------------------------
-- 12. resources
-- Generated Quanta Aptus teaching resources.
-- copyright_status defaults to original_generated — only resources created
-- by the authoring pipeline with no copied content from source papers.
-- --------------------------------------------------------------------------
create table resources (
  id                    uuid        primary key default gen_random_uuid(),
  subject_id            uuid        references subjects(id),
  organization_id       uuid        references organizations(id),
  source_skill_unit_id  uuid        references skill_units(id),
  resource_key          text        unique,
  title                 text        not null,
  topic                 text,
  subtopic              text,
  skill_type            text,
  resource_type         text,
  difficulty            text        check (difficulty in ('easy','medium','hard','unknown'))
                                    default 'unknown',
  estimated_time_minutes int,
  student_prompt        text,
  worked_solution       text,
  marking_guidance      text,
  common_misconceptions jsonb       default '[]'::jsonb,
  teacher_notes         text,
  originality_statement text,
  copyright_status      text        check (copyright_status in (
                          'original_generated','internal_reference_only',
                          'needs_review','unknown'
                        )) default 'original_generated',
  adapter_status        text        check (adapter_status in (
                          'full_adapter','basic_adapter','generic_adapter'
                        )),
  confidence            numeric     check (confidence >= 0 and confidence <= 1),
  needs_human_review    boolean     default false,
  publish_status        text        check (publish_status in (
                          'draft','teacher_review','approved',
                          'rejected','published','archived'
                        )) default 'draft',
  created_at            timestamptz default now(),
  updated_at            timestamptz default now()
);

create trigger resources_updated_at
  before update on resources
  for each row execute function _set_updated_at();

create index resources_lookup_idx
  on resources (subject_id, topic, skill_type, publish_status);

-- --------------------------------------------------------------------------
-- 13. resource_packages
-- A versioned bundle of resources for a subject.
-- --------------------------------------------------------------------------
create table resource_packages (
  id                      uuid        primary key default gen_random_uuid(),
  subject_id              uuid        references subjects(id),
  package_key             text        unique not null,
  version                 int         not null,
  title                   text,
  status                  text        check (status in ('draft','active','archived'))
                                      default 'draft',
  resource_count          int         default 0,
  student_resource_count  int         default 0,
  teacher_resource_count  int         default 0,
  created_at              timestamptz default now(),
  published_at            timestamptz
);

create index resource_packages_status_idx
  on resource_packages (subject_id, status);

-- --------------------------------------------------------------------------
-- 14. resource_package_items
-- Join table: package <-> resource with sort order and visibility.
-- --------------------------------------------------------------------------
create table resource_package_items (
  id          uuid        primary key default gen_random_uuid(),
  package_id  uuid        not null references resource_packages(id) on delete cascade,
  resource_id uuid        not null references resources(id) on delete cascade,
  sort_order  int         default 0,
  visibility  text        check (visibility in ('student','teacher','teacher_only'))
                          default 'student',
  created_at  timestamptz default now(),
  unique (package_id, resource_id)
);

-- --------------------------------------------------------------------------
-- 15. attempts
-- A student's answer submission for one resource.
-- parent_attempt_id links resubmissions to first attempt.
-- superseded_by_attempt_id marks when a newer attempt replaces this one.
-- --------------------------------------------------------------------------
create table attempts (
  id                      uuid        primary key default gen_random_uuid(),
  student_id              uuid        not null references students(id),
  resource_id             uuid        not null references resources(id),
  subject_id              uuid        references subjects(id),
  attempt_type            text        check (attempt_type in ('first_attempt','resubmission'))
                                      default 'first_attempt',
  parent_attempt_id       uuid        references attempts(id),
  answer_text             text,
  answer_json             jsonb       default '{}'::jsonb,
  confidence_level        text        check (confidence_level in ('low','medium','high','unknown'))
                                      default 'unknown',
  submitted_at            timestamptz default now(),
  marking_status          text        check (marking_status in (
                            'unmarked','auto_marked','teacher_review_required',
                            'teacher_reviewed','superseded'
                          )) default 'unmarked',
  superseded_by_attempt_id uuid       references attempts(id)
);

create index attempts_student_idx
  on attempts (student_id, subject_id, submitted_at desc);

-- --------------------------------------------------------------------------
-- 16. marked_attempts
-- Marking result for an attempt. One row per marking event
-- (rule-based, teacher, or AI-assisted).
-- --------------------------------------------------------------------------
create table marked_attempts (
  id              uuid        primary key default gen_random_uuid(),
  attempt_id      uuid        not null references attempts(id) on delete cascade,
  student_id      uuid        references students(id),
  resource_id     uuid        references resources(id),
  subject_id      uuid        references subjects(id),
  marking_method  text        check (marking_method in (
                    'rule_based','teacher','ai_assisted','hybrid'
                  )),
  score           numeric,
  max_score       numeric,
  result          text        check (result in (
                    'correct','incorrect','partially_correct',
                    'needs_resubmission','pending_teacher_review'
                  )),
  feedback        text,
  skill_gap       jsonb       default '{}'::jsonb,
  created_at      timestamptz default now()
);

create index marked_attempts_student_idx
  on marked_attempts (student_id, subject_id, result);

-- --------------------------------------------------------------------------
-- 17. teacher_reviews
-- Covers both resource quality review and student attempt review.
-- --------------------------------------------------------------------------
create table teacher_reviews (
  id                  uuid        primary key default gen_random_uuid(),
  organization_id     uuid        references organizations(id),
  reviewer_profile_id uuid        references profiles(id),
  review_type         text        check (review_type in ('resource_review','attempt_review')),
  resource_id         uuid        references resources(id),
  attempt_id          uuid        references attempts(id),
  decision            text        check (decision in (
                        'approved','needs_revision','rejected',
                        'correct','incorrect','partially_correct','needs_resubmission'
                      )),
  score               numeric,
  feedback            text,
  notes               text,
  created_at          timestamptz default now()
);

create index teacher_reviews_type_idx
  on teacher_reviews (review_type, created_at desc);

-- --------------------------------------------------------------------------
-- 18. student_reports
-- Snapshot reports generated by the reporting pipeline.
-- --------------------------------------------------------------------------
create table student_reports (
  id          uuid        primary key default gen_random_uuid(),
  student_id  uuid        not null references students(id),
  subject_id  uuid        references subjects(id),
  report_type text        check (report_type in (
                'result_report','skill_gap_report',
                'parent_report','dashboard_snapshot'
              )),
  report_json jsonb       not null,
  created_at  timestamptz default now()
);

-- --------------------------------------------------------------------------
-- 19. audit_events
-- Append-only audit log. Never update or delete rows here.
-- --------------------------------------------------------------------------
create table audit_events (
  id                uuid        primary key default gen_random_uuid(),
  organization_id   uuid        references organizations(id),
  actor_profile_id  uuid        references profiles(id),
  event_type        text,
  entity_type       text,
  entity_id         uuid,
  event_json        jsonb       default '{}'::jsonb,
  created_at        timestamptz default now()
);
