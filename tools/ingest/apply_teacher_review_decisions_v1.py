#!/usr/bin/env python3
"""
Apply teacher review decisions to the resource bank.

Reads:
  data/bank/.../teacher_review/teacher_review_queue_v1.json
  data/bank/.../teacher_review/teacher_review_decisions_v1.json
  data/bank/.../teacher_review/publish_candidate_resource_bank_v1.json
  data/bank/.../original_resource_bank/original_resource_bank_v1.json

Writes:
  data/bank/.../teacher_review/approved_resource_bank_v1.json
  data/bank/.../teacher_review/revision_required_resource_bank_v1.json
  data/bank/.../teacher_review/rejected_resource_bank_v1.json
  data/bank/.../teacher_review/publish_candidate_resource_bank_v2.json
  data/bank/.../teacher_review/teacher_review_application_report_v1.json
  data/bank/.../teacher_review/teacher_review_application_manifest_v1.md
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

REVIEW_DIR = (
    PROJECT_ROOT
    / "data" / "bank" / "cambridge_igcse" / "physics_0625" / "teacher_review"
)
ORB_DIR = (
    PROJECT_ROOT
    / "data" / "bank" / "cambridge_igcse" / "physics_0625" / "original_resource_bank"
)

QUEUE_FILE       = REVIEW_DIR / "teacher_review_queue_v1.json"
DECISIONS_FILE   = REVIEW_DIR / "teacher_review_decisions_v1.json"
CANDIDATE_V1_FILE = REVIEW_DIR / "publish_candidate_resource_bank_v1.json"
ORB_FILE         = ORB_DIR    / "original_resource_bank_v1.json"

OUT_APPROVED     = REVIEW_DIR / "approved_resource_bank_v1.json"
OUT_REVISE       = REVIEW_DIR / "revision_required_resource_bank_v1.json"
OUT_REJECTED     = REVIEW_DIR / "rejected_resource_bank_v1.json"
OUT_CANDIDATE_V2 = REVIEW_DIR / "publish_candidate_resource_bank_v2.json"
OUT_REPORT       = REVIEW_DIR / "teacher_review_application_report_v1.json"
OUT_MANIFEST     = REVIEW_DIR / "teacher_review_application_manifest_v1.md"


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Wrote: {path}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 60)
    print("apply_teacher_review_decisions_v1.py")
    print("=" * 60)
    run_at = now_iso()

    # ── Load inputs ────────────────────────────────────────────────────────────
    print("\n[1] Loading input files...")

    for path in (QUEUE_FILE, CANDIDATE_V1_FILE, ORB_FILE):
        if not path.exists():
            print(f"ERROR: Required file missing: {path}", file=sys.stderr)
            return 1

    queue          = load_json(QUEUE_FILE)
    candidate_v1   = load_json(CANDIDATE_V1_FILE)
    orb            = load_json(ORB_FILE)

    if DECISIONS_FILE.exists():
        decisions_data = load_json(DECISIONS_FILE)
    else:
        print(f"  WARNING: {DECISIONS_FILE.name} not found — treating as zero decisions.")
        decisions_data = {
            "decision_file_id": "cambridge_igcse_physics_0625_teacher_review_decisions_v1",
            "version": "0.1.0",
            "created_at": run_at,
            "updated_at": run_at,
            "source_queue_id": queue.get("queue_id", ""),
            "decisions": [],
        }

    print(f"  Queue:          {QUEUE_FILE.name}")
    print(f"  Decisions:      {DECISIONS_FILE.name}")
    print(f"  Candidate v1:   {CANDIDATE_V1_FILE.name}")
    print(f"  Original bank:  {ORB_FILE.name}")

    # ── Build lookup maps ──────────────────────────────────────────────────────
    print("\n[2] Building lookup maps...")

    queue_by_bank_item_id: dict[str, dict] = {
        it["bank_item_id"]: it for it in queue["items"]
    }

    orb_by_bank_item_id: dict[str, dict] = {
        it["bank_item_id"]: it for it in orb["items"]
    }

    decisions: list[dict] = decisions_data.get("decisions", [])

    queue_count    = len(queue["items"])
    decision_count = len(decisions)
    print(f"  Queue items:    {queue_count}")
    print(f"  Decisions:      {decision_count}")

    # ── Classify decisions ─────────────────────────────────────────────────────
    print("\n[3] Classifying decisions...")

    approved_items: list[dict] = []
    revise_items:   list[dict] = []
    rejected_items: list[dict] = []
    skipped = 0

    for decision in decisions:
        bank_item_id = decision["bank_item_id"]
        review_id    = decision["review_id"]
        verdict      = decision["decision"]

        # Source of truth for item content: original resource bank
        orb_item = orb_by_bank_item_id.get(bank_item_id)
        if orb_item is None:
            print(f"  WARNING: {bank_item_id} not in original bank — skipping.")
            skipped += 1
            continue

        # Queue item carries validation metadata (warnings, errors, suggested_action)
        queue_item = queue_by_bank_item_id.get(bank_item_id, {})

        # Build output item: start from the full original bank structure
        out_item: dict = {
            "bank_item_id":          orb_item["bank_item_id"],
            "resource_id":           orb_item["resource_id"],
            "source_batch_id":       orb_item.get("source_batch_id", ""),
            "target_id":             orb_item.get("target_id", ""),
            "resource_type":         orb_item["resource_type"],
            "component_type":        orb_item.get("component_type", ""),
            "topic":                 orb_item["topic"],
            "skill_name":            orb_item["skill_name"],
            "skill_type":            orb_item["skill_type"],
            "difficulty":            orb_item.get("difficulty"),
            "student_prompt":        orb_item.get("student_prompt"),
            "options":               orb_item.get("options"),
            "correct_answer":        orb_item.get("correct_answer"),
            "worked_solution":       orb_item.get("worked_solution"),
            "marking_guidance":      orb_item.get("marking_guidance"),
            "common_misconception":  orb_item.get("common_misconception"),
            "teacher_note":          orb_item.get("teacher_note"),
            "estimated_time_minutes": orb_item.get("estimated_time_minutes"),
            "originality_statement": orb_item.get("originality_statement", ""),
            "validation_status":     orb_item.get("validation_status", "passed"),
            # Prefer queue validation info (contains the warnings that triggered review)
            "validation_errors":     queue_item.get("validation_errors",   orb_item.get("validation_errors",   [])),
            "validation_warnings":   queue_item.get("validation_warnings", orb_item.get("validation_warnings", [])),
            "suggested_action":      queue_item.get("suggested_action"),
            "content_origin":        orb_item.get("content_origin", "quanta_aptus_original_generated"),
            "copyright_status":      orb_item.get("copyright_status", "original_quanta_aptus_content"),
            "source_use_policy":     orb_item.get("source_use_policy", "generated_from_derived_skill_metadata_only"),
            "created_at":            orb_item.get("created_at", run_at),
            # Review metadata
            "review_id":             review_id,
            "teacher_decision":      verdict,
            "teacher_notes":         decision.get("teacher_notes", ""),
            "decided_at":            decision.get("decided_at", run_at),
            "decided_by":            decision.get("decided_by", "admin_local"),
        }

        if verdict == "approved":
            out_item["bank_status"] = "approved_by_teacher"
            approved_items.append(out_item)
        elif verdict == "revise":
            out_item["bank_status"] = "revision_required"
            revise_items.append(out_item)
        elif verdict == "rejected":
            out_item["bank_status"] = "rejected"
            rejected_items.append(out_item)
        else:
            print(f"  WARNING: unknown verdict '{verdict}' for {bank_item_id} — skipping.")
            skipped += 1

    # ── Counts ─────────────────────────────────────────────────────────────────
    approved_count  = len(approved_items)
    revise_count    = len(revise_items)
    rejected_count  = len(rejected_items)
    pending_count   = queue_count - decision_count
    v1_count        = candidate_v1.get("candidate_count", len(candidate_v1.get("items", [])))
    v2_count        = v1_count + approved_count

    print(f"\n  Approved:       {approved_count}")
    print(f"  Needs revision: {revise_count}")
    print(f"  Rejected:       {rejected_count}")
    print(f"  Pending:        {pending_count}")
    print(f"  Skipped:        {skipped}")
    print(f"  v1 candidates:  {v1_count}  ->  v2 candidates: {v2_count}")

    # ── Write outputs ──────────────────────────────────────────────────────────
    print("\n[4] Writing output files...")

    # approved_resource_bank_v1.json
    write_json(OUT_APPROVED, {
        "bank_id":                  "cambridge_igcse_physics_0625_approved_resource_bank_v1",
        "version":                  "0.1.0",
        "status":                   "approved_by_teacher",
        "created_at":               run_at,
        "source_queue_id":          queue["queue_id"],
        "source_decision_file_id":  decisions_data.get("decision_file_id", ""),
        "approved_count":           approved_count,
        "items":                    approved_items,
    })

    # revision_required_resource_bank_v1.json
    write_json(OUT_REVISE, {
        "bank_id":                  "cambridge_igcse_physics_0625_revision_required_resource_bank_v1",
        "version":                  "0.1.0",
        "status":                   "revision_required",
        "created_at":               run_at,
        "source_queue_id":          queue["queue_id"],
        "source_decision_file_id":  decisions_data.get("decision_file_id", ""),
        "revision_required_count":  revise_count,
        "items":                    revise_items,
    })

    # rejected_resource_bank_v1.json
    write_json(OUT_REJECTED, {
        "bank_id":                  "cambridge_igcse_physics_0625_rejected_resource_bank_v1",
        "version":                  "0.1.0",
        "status":                   "rejected",
        "created_at":               run_at,
        "source_queue_id":          queue["queue_id"],
        "source_decision_file_id":  decisions_data.get("decision_file_id", ""),
        "rejected_count":           rejected_count,
        "items":                    rejected_items,
    })

    # publish_candidate_resource_bank_v2.json
    v2_items = list(candidate_v1.get("items", [])) + approved_items
    write_json(OUT_CANDIDATE_V2, {
        "candidate_bank_id":        "cambridge_igcse_physics_0625_publish_candidate_resource_bank_v2",
        "version":                  "0.2.0",
        "status":                   "publish_candidates",
        "created_at":               run_at,
        "source_v1_id":             candidate_v1.get("candidate_bank_id", ""),
        "source_decision_file_id":  decisions_data.get("decision_file_id", ""),
        "candidate_count":          v2_count,
        "v1_inherited_count":       v1_count,
        "newly_approved_count":     approved_count,
        "items":                    v2_items,
    })

    # teacher_review_application_report_v1.json
    report = {
        "report_id":                   "cambridge_igcse_physics_0625_teacher_review_application_report_v1",
        "version":                     "0.1.0",
        "status":                      "passed",
        "created_at":                  run_at,
        "source_queue_id":             queue["queue_id"],
        "source_decision_file_id":     decisions_data.get("decision_file_id", ""),
        "source_candidate_bank_v1_id": candidate_v1.get("candidate_bank_id", ""),
        "source_original_bank_id":     orb.get("bank_id", ""),
        "queue_item_count":            queue_count,
        "decision_count":              decision_count,
        "approved_count":              approved_count,
        "revise_count":                revise_count,
        "rejected_count":              rejected_count,
        "pending_count":               pending_count,
        "v1_candidate_count":          v1_count,
        "v2_candidate_count":          v2_count,
        "newly_approved_count":        approved_count,
        "output_files": {
            "approved_resource_bank":              str(OUT_APPROVED),
            "revision_required_resource_bank":     str(OUT_REVISE),
            "rejected_resource_bank":              str(OUT_REJECTED),
            "publish_candidate_resource_bank_v2":  str(OUT_CANDIDATE_V2),
            "report":                              str(OUT_REPORT),
            "manifest":                            str(OUT_MANIFEST),
        },
    }
    write_json(OUT_REPORT, report)

    # teacher_review_application_manifest_v1.md
    lines = [
        "# Teacher Review Application — Manifest v1",
        "",
        f"**Run at:** {run_at}",
        f"**Source queue:** `{queue['queue_id']}`",
        f"**Decision file:** `{decisions_data.get('decision_file_id', 'N/A')}`",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|------:|",
        f"| Queue items | {queue_count} |",
        f"| Decisions recorded | {decision_count} |",
        f"| Approved | {approved_count} |",
        f"| Needs revision | {revise_count} |",
        f"| Rejected | {rejected_count} |",
        f"| Pending (no decision yet) | {pending_count} |",
        f"| Publish candidates v1 | {v1_count} |",
        f"| Publish candidates v2 | {v2_count} |",
        "",
        "## Approved Items",
        "",
    ]
    if approved_items:
        for it in approved_items:
            lines.append(f"- `{it['bank_item_id']}` — {it['resource_type']} — {it['topic']}")
            if it.get("teacher_notes"):
                lines.append(f"  - Notes: {it['teacher_notes']}")
    else:
        lines.append("_(none)_")

    lines += ["", "## Needs Revision", ""]
    if revise_items:
        for it in revise_items:
            lines.append(f"- `{it['bank_item_id']}` — {it['resource_type']} — {it['topic']}")
            if it.get("teacher_notes"):
                lines.append(f"  - Notes: {it['teacher_notes']}")
    else:
        lines.append("_(none)_")

    lines += ["", "## Rejected", ""]
    if rejected_items:
        for it in rejected_items:
            lines.append(f"- `{it['bank_item_id']}` — {it['resource_type']} — {it['topic']}")
            if it.get("teacher_notes"):
                lines.append(f"  - Notes: {it['teacher_notes']}")
    else:
        lines.append("_(none)_")

    lines += [
        "",
        "## Output Files",
        "",
        f"| File | Items |",
        f"|------|------:|",
        f"| `{OUT_APPROVED.name}` | {approved_count} |",
        f"| `{OUT_REVISE.name}` | {revise_count} |",
        f"| `{OUT_REJECTED.name}` | {rejected_count} |",
        f"| `{OUT_CANDIDATE_V2.name}` | {v2_count} |",
        f"| `{OUT_REPORT.name}` | — |",
        f"| `{OUT_MANIFEST.name}` | — |",
        "",
        "---",
        "*Generated by `apply_teacher_review_decisions_v1.py`*",
    ]

    with open(OUT_MANIFEST, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Wrote: {OUT_MANIFEST}")

    # ── Final summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"Status:              passed")
    print(f"Queue items:         {queue_count}")
    print(f"Decisions applied:   {decision_count}  (approved={approved_count}, revise={revise_count}, rejected={rejected_count})")
    print(f"Pending:             {pending_count}")
    print(f"Publish v1 -> v2:    {v1_count} -> {v2_count}  (+{approved_count} newly approved)")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
