# Gate 53D — Sync Source Items + Skill Units DONE

**Date:** 2026-06-30
**Status:** `passed`
**Phase:** Phase 2 — Supabase Integration

---

## What Was Synced

### source_items (134 rows total)

| Subject | Items | Source |
|---|---|---|
| biology_0610 | 54 | skill_map (per question) |
| chemistry_0620 | 2 | corpus (per paper, no skill map yet) |
| mathematics_0580 | 10 | skill_map (per question) |
| physics_0625 | 68 | skill_map (per question) |

### skill_units (132 rows total)

| Subject | Units | Adapter |
|---|---|---|
| biology_0610 | 54 | basic_adapter (v0.2.0) |
| chemistry_0620 | 0 | skipped — no skill map |
| mathematics_0580 | 10 | basic_adapter (v0.2.0) |
| physics_0625 | 68 | full_adapter (v0.1.0 fallback) |

---

## Copyright Safety Confirmed

- `raw_text = null` on every source_items row. Cambridge question text was never uploaded.
- `short_evidence` and `skill` description fields from skill map were not synced.
- Only derived adapter metadata synced to skill_units:
  `topic`, `subtopic`, `skill_type`, `resource_type`, `confidence`,
  `adapter_name`, `adapter_status`, `needs_human_review`.
- `copyright_safety.source_items_raw_text_synced = false` in report.

---

## Skill Map Version Handling

| Version | Has confidence | Has adapter_status per item |
|---|---|---|
| v0.1.0 (physics_0625) | No — null in DB | No — falls back to doc-level |
| v0.2.0 (biology, math) | Yes | Yes per item |

Physics skill units have `confidence = null` and `adapter_status = "unknown"` because the
skill map was built before Gate 50E (adapter layer). Re-running the skill map pipeline
for physics_0625 with the updated `build_unified_skill_map.py` will populate these fields.

---

## Chemistry 0620 Source Items

Chemistry has no skill map yet (skipped at Gate 23 in the stress test run).
Two source_items were created at corpus/paper level: one per source (paper-level metadata only).
Running the full pipeline for chemistry_0620 through Gate 23 will produce per-question items.

---

## Performance

Pre-fetch strategy used: 4 queries per subject (pair map, existing items, existing skill_units,
subject lookup) regardless of item count. No N+1 queries for existence checks.

---

## Ready for Gate 53E — Sync Resource Packages and Resources

Next step: sync `resource_packages` and `resources` rows from the publish layer into Supabase.

Files to read:
- `data/publish/cambridge_igcse/*/mvp_pipeline_v1/content_registry_v1.json`
- `data/publish/cambridge_igcse/*/mvp_pipeline_v1/student_resource_payload_v2.json`
- `data/publish/cambridge_igcse/*/mvp_pipeline_v1/teacher_resource_payload_v2.json`

Table targets:
- `resource_packages` (one row per content registry package)
- `resources` (one row per generated resource, student + teacher fields merged)
