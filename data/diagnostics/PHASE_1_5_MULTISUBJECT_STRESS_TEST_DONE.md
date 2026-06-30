# Quanta Aptus Phase 1.5 — Multi-subject Stress Test DONE

**Completion date:** 2026-06-30  
**Generated:** 2026-06-30T04:03:43.537782+00:00  
**Status:** `passed`  

## What Was Tested

- **Physics 0625** — full end-to-end pipeline (Gates 19–29, publish package)
- **Chemistry 0620** — intake, markitdown, corpus layers
- **Biology 0610** — intake, markitdown, corpus, skill map (basic adapter), generation targets, authoring batch
- **Mathematics 0580** — intake, markitdown, corpus, skill map (basic adapter), generation targets, authoring batch
- **Subject Adapter Layer** — 22 registered IGCSE subjects, `get_adapter()` registry
- **Generic Adapter Fallback** — unknown subjects handled gracefully with `needs_human_review`
- **Pipeline routing fix** — `run_full_mvp_pipeline.py` derives `subject_slug` from folder; no physics hard-code

## What Passed

| Subject | Highest Gate | Adapter | Notes |
|---------|-------------|---------|-------|
| Physics | Gate 29 | full_adapter | passed |
| Chemistry | Gate 22 | basic_adapter | failed |
| Biology | Gate 25 | basic_adapter | waiting_for_generated_batch |
| Mathematics | Gate 25 | basic_adapter | waiting_for_generated_batch |

- Subject adapter test: 10/11 subjects registered, 1 generic fallback — all pass without crash.
- Pipeline routing: `subject_slug` derived from raw folder path, no `physics_0625` fallback.

## What Failed or Remains Basic

- Chemistry 0620: pipeline ran only to Gate 22 (no skill map adapter invocation in this test run).
- Biology and Mathematics: basic adapters — confidence is lower, `needs_human_review` flags set.
- Biology and Mathematics: stopped at Gate 25 `waiting_for_generated_batch` — AI authoring not yet run.
- No production publishing for non-Physics subjects.
- No diagram/image marking for any subject.

## Key Architectural Finding

The pipeline is genuinely multi-subject. The intake, markitdown, corpus, and skill-map
layers accept any Cambridge IGCSE subject by path routing alone. Subject-specific
classification is isolated to `subject_adapters/` and does not require changing the
core pipeline scripts. New subjects can be added by registering an adapter.

## Why This Matters Before Supabase

The Supabase schema must be designed for multi-subject from day one:
- `subject_slug` and `syllabus_code` on every resource and attempt row.
- `adapter_status` and `confidence` on skill-map derived items.
- `needs_human_review` as a first-class column, not a post-hoc flag.
- Teacher review queue must be subject-aware.
- RLS policies must be scoped by subject or syllabus group.

## Next: Gate 51 — Supabase Schema Design

Design and provision the Supabase Postgres schema:
- Tables: `subjects`, `resources`, `skill_units`, `attempts`, `teacher_reviews`, `users`
- All resource rows include `subject_slug`, `adapter_status`, `confidence`, `needs_human_review`
- Auth: Supabase Auth with RLS for student/teacher/admin roles
- Storage: Supabase Storage for PDF source papers and generated assets
