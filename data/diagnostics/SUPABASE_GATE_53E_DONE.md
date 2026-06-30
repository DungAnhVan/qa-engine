# Gate 53E — Sync Resources + Packages DONE

**Date:** 2026-06-30
**Status:** `passed`
**Phase:** Phase 2 — Supabase Integration

---

## What Was Synced

### resource_packages (2 rows for physics_0625)

| Package | Version | Status |
|---|---|---|
| cambridge_igcse_physics_0625_resource_package_v1 | 1 | archived |
| cambridge_igcse_physics_0625_resource_package_v2 | 2 | active |

Highest-version package per subject is automatically marked `active`.
Lower versions are marked `archived`.

### resources (27 rows)

| Metric | Count |
|---|---|
| Total resources upserted | 27 |
| Student-visible resources | 23 |
| Teacher-only resources | 4 |
| Needs human review | 1 |
| Failed | 0 |

### resource_package_items (27 rows)

Each resource linked to package v2 with `sort_order` and `visibility`:
- `student` — resource appears in student payload
- `teacher_only` — resource is in teacher payload only (marking checklists, worked examples marked teacher-only)

---

## Copyright Safety Confirmed

- No raw Cambridge PDFs uploaded.
- No extracted Cambridge text uploaded.
- `skill_name` field (which may contain partial Cambridge question text) was NOT stored.
  - `title` is derived from `resource_type` + `topic` only (both are Quanta Aptus metadata).
- `student_prompt` and `worked_solution` are original Quanta Aptus content.
- `copyright_status = 'original_generated'` on every resource row.
- `copyright_safety.source_text_copied_to_resources = false`.

---

## needs_human_review = 1

One resource has `needs_human_review = true` because its `bank_status` is not `publish_ready`.
This corresponds to the graphing attempt that was pending teacher review in the Local MVP v1 state.
The resource is in the database with `publish_status = 'teacher_review'`.
It will be updated to `published` once a teacher approves it via the teacher review flow.

---

## source_skill_unit_id Matching

Best-effort match by `(topic, skill_type)` from the skill_units table.
First match is used (skills units are per-question; multiple may share the same topic + skill_type).
Some resources may have `source_skill_unit_id = null` if no matching skill unit was found.
This is a warning, not a failure.

---

## Idempotent

The script is safe to re-run. Re-running physics_0625:
- All 27 resources: `UPDATE` (existing rows found by `resource_key`)
- All 2 packages: `UPDATE`
- All 27 package items: `UPDATE`

---

## Ready for Gate 53F — Read Active Package from Supabase

Next step: verify the Supabase data is readable by building a read-path query
that returns the active resource package and its resources for a given subject,
mimicking what the app layer will do when a student or teacher requests content.
