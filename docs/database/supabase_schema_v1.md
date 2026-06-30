# Quanta Aptus Supabase Schema v1

**Gate 51 — Supabase Schema Design**
Version: v1 | Status: design complete, not yet migrated

---

## Overview

This schema supports the Quanta Aptus multi-subject learning platform on Supabase Postgres.
It is designed to be multi-subject from the first row — no table hard-codes a subject name.
All subject-specific classification metadata flows through `subject_slug`, `adapter_status`,
and `confidence` columns rather than being encoded in table structure.

The schema maps directly from the Local MVP v1 JSON pipeline outputs,
with Supabase Auth, RLS, and multi-tenant organization support added.

---

## Table Groups

### Group 1: Identity and Access

| Table | Purpose |
|---|---|
| `organizations` | A tenant unit (learning center, school, platform account) |
| `profiles` | Maps to `auth.users` — stores role and org membership |
| `students` | One row per enrolled student; links to a profile |
| `parent_student_links` | Parent profile linked to one or more student rows |

**Design note:** `profiles.id = auth.uid()`. The profile row is created on first login via a
Supabase Auth trigger. Role is set by admin; no self-promotion.

---

### Group 2: Subject Reference Data

| Table | Purpose |
|---|---|
| `subjects` | One row per Cambridge IGCSE subject; seeded from adapter registry |

The `subjects` table is the anchor for all content and attempt data.
Every resource, skill unit, attempt, and report row carries a `subject_id` foreign key.

**Adapter fields on `subjects`:**

| Column | Meaning |
|---|---|
| `adapter_name` | Python class name (e.g. `PhysicsAdapter`) |
| `adapter_status` | `full_adapter`, `basic_adapter`, or `generic_adapter` |
| `adapter_version` | Pipeline version that classified this subject |

---

### Group 3: Ingest Pipeline (Protected, Internal)

| Table | Purpose |
|---|---|
| `source_documents` | Raw PDF metadata — never exposes Cambridge copyright content |
| `source_pairs` | Links question paper + mark scheme |
| `source_items` | Individual parsed questions — internal reference only |

These tables are RLS-protected. Students and parents cannot read them.
`copyright_status = 'internal_reference_only'` is the default and must not be changed
unless a licensing agreement is in place.

---

### Group 4: Skill Classification

| Table | Purpose |
|---|---|
| `skill_units` | Output of `build_unified_skill_map.py` — one row per classified source item |

**Why `needs_human_review` is a first-class column here:**

The subject adapter layer produces a `confidence` score and an `adapter_status` per item.
A `basic_adapter` item with low confidence must be flagged for teacher review before
any generated resource based on it reaches students.
Encoding this as a column (not a tag in a JSON blob) means it can be:
- Filtered in SQL (`where needs_human_review = true`)
- Used in RLS policies
- Indexed for the teacher review queue
- Tracked over time in audit_events

---

### Group 5: Authoring Pipeline

| Table | Purpose |
|---|---|
| `generation_targets` | Planned resource slots from skill units |
| `authoring_batches` | One AI authoring round-trip (prompt in → resource out) |

These are admin/pipeline-only tables. No student or teacher RLS access.
`authoring_batches.status = 'waiting_for_generated_batch'` matches the local pipeline state
seen in Biology 0610 and Mathematics 0580 after Gate 25.

---

### Group 6: Resources and Packages

| Table | Purpose |
|---|---|
| `resources` | A generated Quanta Aptus teaching resource |
| `resource_packages` | A versioned bundle of resources for a subject |
| `resource_package_items` | Join table with visibility and sort order |

**`resources.copyright_status`:** All generated resources default to `original_generated`.
If a resource is flagged as containing text from source papers it must be set to
`internal_reference_only` and removed from student-facing packages immediately.

**`resources.needs_human_review`:** Carries forward from the skill_unit that seeded it.
A resource generated from a `basic_adapter` classification with `confidence < 0.4` is
automatically flagged. Teacher approval is required before `publish_status` can reach
`published`.

---

### Group 7: Learner Workflow

| Table | Purpose |
|---|---|
| `attempts` | Student answer submission for one resource |
| `marked_attempts` | Marking result per attempt (rule-based, teacher, or AI) |
| `teacher_reviews` | Teacher decision on a resource or an attempt |
| `student_reports` | Snapshot reports (result, skill gap, parent, dashboard) |

**Resubmission chain:** `attempts.parent_attempt_id` links a resubmission to the original.
`attempts.superseded_by_attempt_id` marks the old attempt as replaced.
`marking_status = 'superseded'` tells the reporting layer to ignore old attempts.

---

### Group 8: Audit

| Table | Purpose |
|---|---|
| `audit_events` | Append-only event log; never update or delete |

Written by service-role (Edge Function or trigger) — no client insert policy.

---

## Subject Adapter Fields

The following columns appear across multiple tables to preserve adapter metadata
from the classification layer all the way to the student-facing resource:

| Column | Tables | Purpose |
|---|---|---|
| `subject_slug` | `source_documents`, `skill_units` (via subject) | Human-readable key for routing |
| `adapter_status` | `subjects`, `skill_units`, `resources` | Classification tier |
| `adapter_version` | `subjects`, `skill_units`, `authoring_batches` | Track which pipeline version classified |
| `confidence` | `skill_units`, `resources` | Numeric classifier confidence 0–1 |
| `needs_human_review` | `source_items`, `skill_units`, `resources` | First-class review flag |
| `matched_keywords` | `skill_units` | Diagnostic — which keywords triggered the topic match |

---

## Local JSON to Supabase Mapping

See `supabase_table_map_v1.md` for the full file-by-file mapping.

---

## Why Multi-subject from Day One

The Local MVP v1 ran Physics end-to-end, Chemistry through intake, and Biology/Mathematics
to Gate 25. The schema must not treat Physics as the default subject.

Every foreign key chain starts from `subjects`, not from a physics-specific view.
The `subject_slug` column on `source_documents` and the `subject_id` FK on every other
table ensure that queries never accidentally mix rows from different subjects.

When Gate 52 runs `supabase db push`, the 22 subjects seeded in `seed_local_mvp_demo.sql`
will be immediately queryable for any subject's content pipeline.

---

## Auth and RLS Summary

| Role | Access |
|---|---|
| `admin` | Full access within their organization |
| `teacher` | Read all org resources, attempts, reviews; insert reviews |
| `student` | Read own attempts/reports; read published resources in their org |
| `parent` | Read reports and attempts for linked students |
| service-role | Bypasses RLS — used by pipeline scripts and Edge Functions |

Source documents and source items are not accessible to students or parents under any policy.

---

## Next: Gate 52 — Supabase Project + Migration

1. Create Supabase project (dashboard or CLI).
2. Set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env.local`.
3. Run `supabase db push` or apply migrations manually via Supabase SQL editor.
4. Run `seed_local_mvp_demo.sql` in SQL editor.
5. Verify 22 subjects present, demo package active.
6. Connect pipeline scripts to Supabase client.
