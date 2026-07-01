# Gate 70A — Live AI Question Generation to Bank DONE

Generated: 2026-07-01T16:22:33.018190+00:00
Status: **PASSED**

## What was done

- `ai_client_v1.py` updated: `QA_OPENAI_MODEL`/`QA_ANTHROPIC_MODEL` env vars, urllib fallback, `model` in response.
- `.env.example` and `.env.production.example` updated with model env var entries.
- `build_safe_generation_requests_from_targets_v1.py`: filters targets; falls back to safe IGCSE seeds.
- `run_live_ai_generation_to_bank_v1.py`: dry-run default; `--execute --confirm LIVE_AI_GENERATION` for real calls.
- `validate_ai_question_bank_v1.py`: validates schema, safety fields, secrets, copyright.
- `build_teacher_review_queue_from_ai_bank_v1.py`: sorted queue for teacher review.
- Admin: `aiQuestionBank.ts`, `/ai-bank`, `/system/ai-bank`, `/api/system/ai-bank`.
- `layout.tsx` updated with AI Bank and AI Bank Diag links.

## Safety guarantees

- `dry_run=True` by default — no real API calls unless `--execute --confirm LIVE_AI_GENERATION`.
- `QA_AI_DRY_RUN=false` required for real calls — explicit opt-in.
- No raw Cambridge PDF text, question text, or mark scheme sent to AI.
- All prompts built from metadata only (authoring contract enforced).
- All generated items: `status=generated_needs_teacher_review`.
- `teacher_review_required=True` on all items and bank.
- `auto_publish_enabled=False` — no automatic publication.
- `supabase_write_performed=False` — no Supabase writes.
- API keys never written to generated files or bank.

## Summary

| Category     | Result |
|:-------------|:-------|
| Deliverables | 14/14 |
| Outputs      | 5/5 |
| Policy       | 16/16 |
| Tests        | 43/43 (passed) |

## Next: Gate 70B