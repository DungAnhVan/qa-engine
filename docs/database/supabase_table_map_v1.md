# Quanta Aptus — Local JSON to Supabase Table Map v1

**Gate 51 — Supabase Schema Design**

This document maps every significant local JSON output file from the pipeline
to its future Supabase table(s). Use this during Gate 52 migration planning.

---

## Mapping Table

| Local JSON File | Supabase Table(s) | Notes |
|---|---|---|
| `data/publish/.../mvp_pipeline_v1/content_registry_v1.json` | `resource_packages`, `resources` (summary) | Package-level metadata; individual resources expand into `resources` rows |
| `data/publish/.../mvp_pipeline_v1/active_content_index_v1.json` | `resource_packages` (`status = 'active'`) | Marks which package version is the active one |
| `data/publish/.../mvp_pipeline_v1/student_resource_payload_v2.json` | `resources` (student fields) | `student_prompt`, `topic`, `skill_type`, `resource_type`, `difficulty` |
| `data/publish/.../mvp_pipeline_v1/teacher_resource_payload_v2.json` | `resources` (teacher fields) | `worked_solution`, `marking_guidance`, `teacher_notes`, `common_misconceptions` |
| `data/bank/.../skill_map/unified_skill_map_v0.json` | `skill_units` | One row per classified item; includes `confidence`, `adapter_status`, `needs_human_review` |
| `data/bank/.../skill_map/unified_skill_map_report.json` | `skill_units` (summary stats) | Diagnostic; not stored as rows but useful for admin dashboard |
| `data/bank/.../generation_targets/generation_targets_v0.json` | `generation_targets` | One row per planned resource slot |
| `data/bank/.../authoring_batches/authoring_batch_prompt_v0.json` | `authoring_batches` (`status = 'authoring_prompt_ready'`) | Prompt path + expected output path |
| `data/bank/.../authored_resources/authored_resources_v0.json` | `resources` (draft) | Raw AI output before teacher review |
| `data/bank/.../source_corpus/unified_source_corpus_v0.json` | `source_items` | One row per parsed question/source item |
| `data/bank/.../source_corpus/unified_source_corpus_report.json` | `source_documents` (summary) | Document-level stats |
| `data/intake/.../raw_document_pairs_v0.json` | `source_pairs` | QP/MS pair metadata |
| `data/intake/.../markitdown_output/*.md` | `source_documents.storage_path` | Store as Supabase Storage object; path recorded in `storage_path` |
| `data/publish/.../mvp_pipeline_v1/student_attempts_v1.json` | `attempts` | One row per submission |
| `data/publish/.../mvp_pipeline_v1/marked_attempts_latest_v1.json` | `marked_attempts` | One row per marking event (latest) |
| `data/publish/.../mvp_pipeline_v1/teacher_attempt_review_decisions_v1.json` | `teacher_reviews` (`review_type = 'attempt_review'`) | Decision + score + feedback |
| `data/publish/.../mvp_pipeline_v1/teacher_resource_review_v1.json` | `teacher_reviews` (`review_type = 'resource_review'`) | Resource quality decisions |
| `data/publish/.../mvp_pipeline_v1/latest_learning_state_v1.json` | `student_reports` (`report_type = 'dashboard_snapshot'`) | Full student state snapshot |
| `data/publish/.../mvp_pipeline_v1/student_result_report_v1.json` | `student_reports` (`report_type = 'result_report'`) | Printable result summary |
| `data/diagnostics/subject_adapter_test_report_v1.json` | `subjects` (`adapter_name`, `adapter_status`, `adapter_version`) | Seed reference; adapter metadata belongs on subject rows |
| `data/mvp/mvp_dashboard_v1.json` | Admin dashboard query (no direct table) | Aggregated from `resource_packages` + `teacher_reviews` |
| `data/mvp/GATE_50_LOCAL_MVP_DONE.md` | `audit_events` | Record as a milestone event: `event_type = 'gate_passed'`, `entity_type = 'pipeline'` |

---

## Fields That Map to First-class Columns

These fields exist in local JSON as nested keys. In Supabase they must be top-level columns
(not buried in a JSONB blob) so they can be indexed, filtered, and used in RLS.

| Local JSON field | Target column | Target table |
|---|---|---|
| `skill_unit.confidence` | `skill_units.confidence` | `skill_units` |
| `skill_unit.adapter_status` | `skill_units.adapter_status` | `skill_units` |
| `skill_unit.needs_human_review` | `skill_units.needs_human_review` | `skill_units` |
| `skill_unit.resource_type` | `skill_units.resource_type` | `skill_units` |
| `resource.needs_human_review` | `resources.needs_human_review` | `resources` |
| `resource.publish_status` | `resources.publish_status` | `resources` |
| `resource.adapter_status` | `resources.adapter_status` | `resources` |
| `attempt.marking_status` | `attempts.marking_status` | `attempts` |
| `marked_attempt.result` | `marked_attempts.result` | `marked_attempts` |
| `teacher_review.decision` | `teacher_reviews.decision` | `teacher_reviews` |
| `package.status` | `resource_packages.status` | `resource_packages` |

---

## Fields That Stay as JSONB

These fields are rich nested structures that are not queried field-by-field in SQL.
They map to `jsonb` columns.

| Local JSON field | JSONB column | Table |
|---|---|---|
| `skill_unit.matched_keywords` | `skill_units.matched_keywords` | `skill_units` |
| `resource.common_misconceptions` | `resources.common_misconceptions` | `resources` |
| `attempt.answer_json` | `attempts.answer_json` | `attempts` |
| `marked_attempt.skill_gap` | `marked_attempts.skill_gap` | `marked_attempts` |
| `generation_target.prompt_context` | `generation_targets.prompt_context` | `generation_targets` |
| `student_report.*` (full report) | `student_reports.report_json` | `student_reports` |
| `audit_event.payload` | `audit_events.event_json` | `audit_events` |

---

## Migration Order (Gate 52)

Apply in this order to satisfy foreign key constraints:

1. `organizations`
2. `profiles`
3. `students`
4. `parent_student_links`
5. `subjects`
6. `source_documents`
7. `source_pairs`
8. `source_items`
9. `skill_units`
10. `generation_targets`
11. `authoring_batches`
12. `resources`
13. `resource_packages`
14. `resource_package_items`
15. `attempts`
16. `marked_attempts`
17. `teacher_reviews`
18. `student_reports`
19. `audit_events`

All in migration `000001_init_quanta_aptus_schema.sql`.
RLS in `000002_rls_policies.sql` (apply after all tables exist).
Seed in `seed_local_mvp_demo.sql` (apply after RLS, using service-role connection).

---

## What Is NOT Migrated in Gate 52

- Raw markitdown `.md` files — upload to Supabase Storage separately; record `storage_path`.
- Cambridge source PDFs — remain local, `internal_reference_only`, never uploaded.
- Pipeline Python scripts — remain in `tools/ingest/`; connect to Supabase client in Gate 53+.
- `.venv-ingest` Python environment — local only.
