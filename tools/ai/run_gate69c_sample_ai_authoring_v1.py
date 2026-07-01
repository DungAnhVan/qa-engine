"""
Gate 69C -- Run Sample AI Authoring v1

Generates a small sample batch of 3 original Quanta Aptus resource drafts
using the AI authoring service (mock provider by default).

Safety:
  - Uses only safe metadata — no raw Cambridge text.
  - Mock provider by default (QA_AI_DRY_RUN=true).
  - Output saved to data/ai/generated_batches/.
  - No Supabase writes.
  - No auto-publish.
  - Teacher approval required.

Output:
  data/ai/generated_batches/gate69c_sample_generated_batch_v1.json
  data/ai/generated_batches/gate69c_sample_generated_batch_preview_v1.md
  data/diagnostics/gate69c_sample_ai_authoring_report_v1.json
"""

import json
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT_BASE  = ROOT / "data" / "ai" / "generated_batches"
DIAG_DIR     = ROOT / "data" / "diagnostics"
BATCH_ID     = "gate69c_sample_generated_batch_v1"
BATCH_FILE   = OUTPUT_BASE / f"{BATCH_ID}.json"
PREVIEW_FILE = OUTPUT_BASE / f"gate69c_sample_generated_batch_preview_v1.md"
REPORT_FILE  = DIAG_DIR / "gate69c_sample_ai_authoring_report_v1.json"

from tools.ai.ai_authoring_contract_v1 import make_safe_authoring_request
from tools.ai.ai_authoring_service_v1 import generate_batch_from_requests
from tools.ai.ai_provider_config_v1 import load_ai_provider_config, load_env_local

# ---------------------------------------------------------------------------
# Sample authoring requests — safe metadata only, no raw source text
# ---------------------------------------------------------------------------

SAMPLE_REQUESTS = [
    make_safe_authoring_request(
        subject_slug="physics_0625",
        syllabus_code="9702",
        topic="Motion, forces and energy",
        subtopic="Dynamics — Newton's laws",
        skill_name="calculation_drill",
        skill_type="application",
        difficulty="medium",
        resource_type="question",
        learning_objective=(
            "Apply Newton's second law to calculate acceleration, force, "
            "or mass for a system of objects."
        ),
        student_level="A-Level Year 1",
        estimated_time_minutes=12,
        source_ids=["phys_motion_001"],
    ),
    make_safe_authoring_request(
        subject_slug="mathematics_0580",
        syllabus_code="0580",
        topic="Algebra",
        subtopic="Simultaneous equations",
        skill_name="calculation_drill",
        skill_type="application",
        difficulty="medium",
        resource_type="question",
        learning_objective=(
            "Solve a pair of simultaneous linear equations algebraically "
            "and verify the solution."
        ),
        student_level="IGCSE Year 11",
        estimated_time_minutes=10,
        source_ids=["math_algebra_002"],
    ),
    make_safe_authoring_request(
        subject_slug="biology_0610",
        syllabus_code="0610",
        topic="Animal nutrition",
        subtopic="Digestion and absorption",
        skill_name="conceptual_explanation",
        skill_type="recall",
        difficulty="easy",
        resource_type="question",
        learning_objective=(
            "Describe the role of enzymes in digestion and identify "
            "where each major class of food is broken down."
        ),
        student_level="IGCSE Year 10",
        estimated_time_minutes=8,
        source_ids=["bio_nutrition_003"],
    ),
]


# ---------------------------------------------------------------------------
# Preview builder
# ---------------------------------------------------------------------------

def build_preview_markdown(batch: dict) -> str:
    lines = [
        f"# Gate 69C — Sample AI Authoring Batch Preview",
        f"",
        f"**Batch ID:** {batch['batch_id']}  ",
        f"**Generated:** {batch['generated_at']}  ",
        f"**Provider:** {batch['provider']}  ",
        f"**Dry-run:** {batch['dry_run']}  ",
        f"**Total resources:** {batch['total']}  ",
        f"**Status:** {batch['status']}  ",
        f"",
        f"> Teacher approval required before any resource is published.",
        f"> Auto-publish is disabled.",
        f"",
        f"---",
        f"",
    ]

    for i, resource in enumerate(batch.get("resources", []), 1):
        lines += [
            f"## Resource {i}: {resource.get('title', 'Untitled')}",
            f"",
            f"| Field | Value |",
            f"|---|---|",
            f"| Resource ID | `{resource.get('resource_id', '')}` |",
            f"| Subject / Topic | {resource.get('topic', '')} |",
            f"| Skill | {resource.get('skill_name', '')} ({resource.get('skill_type', '')}) |",
            f"| Difficulty | {resource.get('difficulty', '')} |",
            f"| Time | {resource.get('estimated_time_minutes', '')} min |",
            f"| Type | {resource.get('resource_type', '')} |",
            f"",
            f"**Student prompt:**",
            f"",
            f"> {resource.get('student_prompt', '')}",
            f"",
            f"**Student instructions:** {resource.get('student_instructions', '')}",
            f"",
            f"**Answer key:**",
            f"",
            f"> {resource.get('answer_key', '')}",
            f"",
            f"**Marking rubric:**",
            f"",
        ]
        for criterion in resource.get("marking_rubric", []):
            lines.append(
                f"- **{criterion.get('criterion', '')}** "
                f"[{criterion.get('marks', 0)} mark(s)]: "
                f"{criterion.get('guidance', '')}"
            )
        lines += [
            f"",
            f"**Teacher notes:** {resource.get('teacher_notes', '')}",
            f"",
            f"**Safety declaration:**",
        ]
        decl = resource.get("safety_declaration", {})
        for k, v in decl.items():
            lines.append(f"- {k}: {v}")
        lines += ["", "---", ""]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)

    env_local = load_env_local()
    config    = load_ai_provider_config(env_local)

    print("Gate 69C -- Sample AI Authoring Run")
    print(f"  Provider:         {config['provider']}")
    print(f"  Dry-run:          {config['dry_run']}")
    print(f"  Copyright strict: {config['copyright_strict']}")
    print(f"  Resources:        {len(SAMPLE_REQUESTS)}")
    print("-" * 55)

    batch = generate_batch_from_requests(SAMPLE_REQUESTS, BATCH_ID)

    print(f"\n  Batch generated:")
    print(f"    total:        {batch['total']}")
    print(f"    draft:        {batch['draft_count']}")
    print(f"    needs_review: {batch['needs_review_count']}")
    print(f"    failed:       {batch['failed_count']}")
    print(f"    status:       {batch['status']}")
    print(f"    auto_publish: {batch['auto_publish_enabled']}")
    print(f"    teacher_req:  {batch['teacher_approval_required']}")

    for meta in batch.get("draft_metadata", []):
        sym = "+" if meta["status"] in ("draft", "passed") else "!"
        print(f"    [{sym}] [{meta['index']}] {meta['subject']} / {meta['topic'][:40]} — {meta['status']}")
        for issue in meta.get("issues", []):
            print(f"         ! {issue}")

    # ── Preview markdown ──────────────────────────────────────────────────────
    preview_md = build_preview_markdown(batch)
    PREVIEW_FILE.write_text(preview_md, encoding="utf-8")
    print(f"\n  Preview: {PREVIEW_FILE}")
    print(f"  Batch:   {BATCH_FILE}")

    # ── Authoring report ──────────────────────────────────────────────────────
    all_resources_safe = all(
        not meta.get("issues")
        for meta in batch.get("draft_metadata", [])
    )
    report = {
        "gate":                      "69C",
        "title":                     "Sample AI Authoring Run v1",
        "status":                    "passed" if batch["status"] in ("draft", "passed") and all_resources_safe else "needs_review",
        "generated_at":              datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "batch_id":                  BATCH_ID,
        "batch_file":                str(BATCH_FILE.relative_to(ROOT)),
        "preview_file":              str(PREVIEW_FILE.relative_to(ROOT)),
        "provider":                  batch["provider"],
        "dry_run":                   batch["dry_run"],
        "resources_generated":       batch["total"],
        "resources_draft":           batch["draft_count"],
        "resources_failed":          batch["failed_count"],
        "batch_status":              batch["status"],
        "teacher_approval_required": batch["teacher_approval_required"],
        "auto_publish_enabled":      batch["auto_publish_enabled"],
        "all_resources_safe":        all_resources_safe,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"  Report:  {REPORT_FILE}")
    print(f"\nStatus: {report['status']}")


if __name__ == "__main__":
    main()
