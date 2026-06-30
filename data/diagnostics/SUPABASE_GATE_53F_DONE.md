# Gate 53F — Read Active Package from Supabase DONE

**Date:** 2026-06-30
**Status:** `passed`
**Phase:** Phase 2 — Supabase Integration

---

## What Was Read

Queried live Supabase project and read the active resource package for `physics_0625`:

| Field | Value |
|---|---|
| Package key | `cambridge_igcse_physics_0625_resource_package_v2` |
| Version | 2 |
| Status | `active` |
| Resources read | 27 |
| Student resources | 23 |
| Teacher resources | 27 |
| Teacher-only | 4 |
| Needs human review | 1 |
| Matches expected package | `true` |

---

## Exported Files

| File | Contents |
|---|---|
| `data/supabase_exports/active_package_from_supabase_v1.json` | Full package with all 27 resources and visibility metadata |
| `data/supabase_exports/student_resource_payload_from_supabase_v1.json` | 23 student-visible resources; no `teacher_notes`, no `marking_guidance` |
| `data/supabase_exports/teacher_resource_payload_from_supabase_v1.json` | All 27 resources with teacher fields and `needs_human_review` flags |

---

## Read Path Verified

The read query chain works end-to-end:

```
subjects (subject_slug) 
  -> resource_packages (subject_id, status=active)
  -> resource_package_items (package_id, ordered by sort_order)
  -> resources (batch fetch by id list)
```

Three queries total for the full package read. This is the pattern the app layer
will use in Gate 54.

---

## Copyright Safety Confirmed

- `source_documents` and `source_items` were not queried — no Cambridge content read.
- `raw_text` (always null in source_items) was not part of the query.
- All 27 resources have `copyright_status = 'original_generated'`.
- Student payload excludes `teacher_notes` and `marking_guidance` — enforced in Python.
- `copyright_safety.generated_resources_only = true`.

---

## Gateway to the App Layer

The exported files in `data/supabase_exports/` are structurally equivalent to the
local publish payloads but with Supabase as the source of truth.
The next gate will use these exports (or direct Supabase queries) to power
the app's student and teacher views.

---

## Ready for Gate 54 — App Supabase Read Mode

Gate 54 will:
1. Replace local JSON file reads in the app layer with Supabase queries.
2. Use the `anon` key (not service role) for student-facing reads.
3. Verify RLS: students see only published resources, teachers see all.
4. Implement the `auth.uid()` → `profiles` → `organization_id` lookup chain.
