# Quanta Aptus Multi-subject Stress Test Report v1

**Status:** `passed`  
**Phase:** Phase 1.5  
**Generated:** 2026-06-30T04:03:43.537782+00:00  

## Summary

- **Local Mvp Done:** True
- **Multi Subject Routing Ready:** True
- **Subject Adapter Layer Ready:** True
- **Production Ready:** False
- **Recommended Next Gate:** Gate 51 - Supabase Schema Design

## Subject Pipeline Status

| Subject | Status | Gate | Adapter | Pipeline | Questions |
|---------|--------|------|---------|----------|-----------|
| Physics | partial | 29 | full_adapter | passed | 68 |
| Chemistry | passed | 22 | basic_adapter | failed | 14 |
| Biology | passed | 25 | basic_adapter | waiting_for_generated_batch | 54 |
| Mathematics | passed | 25 | basic_adapter | waiting_for_generated_batch | 10 |

## Adapter Layer

- Registered adapters: 10
- Full adapters: 1
- Basic adapters: 9
- Generic fallback: 1

## Key Findings

- Raw intake and markitdown are fully multi-subject capable.
- Corpus layer (unified_source_corpus) is multi-subject capable.
- Skill map layer uses subject adapter registry — no more physics hard-code.
- Physics 0625 remains the strongest production-like subject (full_adapter, end-to-end).
- Biology 0610 and Mathematics 0580 now pass Gate 23 skill map using basic adapters.
- Chemistry 0620 routing is fixed — intake and markitdown use correct subject paths.
- Generic adapter fallback handles unknown subjects without crashing.
- Non-Physics subjects should not be auto-published without teacher review.
- Subject adapter architecture allows new subjects by adding a registry entry only.

## Known Limitations

- No Supabase database yet — all state in local JSON files.
- No authentication or multi-user support.
- No Claude or OpenAI API automated authoring yet.
- Adapters for non-Physics subjects are basic — confidence is lower.
- Biology and Mathematics generated resources are waiting for AI authoring batch.
- No image or diagram AI marking yet.
- No parent or student multi-user dashboard yet.
- Chemistry 0620 skill map not yet run (basic adapter available but not invoked in stress test).
