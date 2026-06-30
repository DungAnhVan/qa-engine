# Gate 57 - Supabase Marking + Marked Attempts DONE

**Date:** 2026-06-30
**Status:** `passed`
**Phase:** Phase 2 - Supabase Integration

## What Was Built

| File | Change |
|---|---|
| `apps/admin/src/lib/liveSupabaseMarking.ts` | NEW - server-only marking module |
| `apps/admin/src/app/api/mark-attempt/route.ts` | NEW - POST marking endpoint |
| `apps/admin/src/app/learn/practice/AttemptForm.tsx` | UPDATED - auto-mark after save |
| `apps/admin/src/app/system/marking/page.tsx` | NEW - diagnostic page |
| `tools/supabase/test_gate57_mark_latest_attempt_v1.py` | NEW - integration test |

## Behavior

- Rule-based marking in `live_supabase` mode.
- `calculation_drill`, `short_answer_calculation`, `algebra_drill` → numeric overlap check.
- Graph/diagram/planning types → `pending_teacher_review`.
- Results written to `marked_attempts` table; `attempts.marking_status` updated.
- Deduplication: existing `marked_attempts` row is updated, not duplicated.
- AttemptForm auto-marks on submit; shows result with feedback.
- No OpenAI API calls.
- No Cambridge source text read or uploaded.

## Security

- `import 'server-only'` in liveSupabaseMarking.ts.
- `process.env.SUPABASE_SERVICE_ROLE_KEY` only in allowed server-only files.
- Security scan: 0 violations.

## Ready for Gate 58

Gate 58 will add teacher review UI for `pending_teacher_review` results.