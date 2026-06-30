"""
Quanta Aptus Full MVP Pipeline v1 Orchestrator.

Runs the full ingestion pipeline from raw PDFs to publish package v1,
with a safe stop at the AI authoring handoff point (Gate 25).

Does NOT call any AI API.  Does NOT generate content.

Usage:
    python tools/ingest/run_full_mvp_pipeline.py data/raw/cambridge_igcse/physics_0625

Optional flags:
    --batch-id 001                   batch suffix (default: 001)
    --skip-existing                  skip gates whose expected output already exists
    --stop-after-authoring-prompt    stop after Gate 25, do not wait for generated batch
    --generated-batch <path>         explicit path to generated resource batch JSON
    --resume-from-generated-batch    skip source gates 19-25 if outputs exist, run 26-29
"""

import sys
import json
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS        = PROJECT_ROOT / "tools" / "ingest"
PYTHON       = str(PROJECT_ROOT / ".venv-ingest" / "Scripts" / "python.exe")

def _derive_slug_components(raw_folder: Path) -> tuple[str, str, str, str, str, str]:
    """
    Returns (subject_slug, board, level, subject, syllabus_code, dataset_slug).

    Expects raw_folder = .../<board>_<level>/<subject>_<syllabus_code>
    e.g.  data/raw/cambridge_igcse/chemistry_0620
    """
    subject_slug = raw_folder.name          # "chemistry_0620"
    try:
        board, level = raw_folder.parent.name.rsplit("_", 1)   # "cambridge", "igcse"
    except ValueError:
        board, level = "cambridge", "igcse"
    try:
        subject, syllabus_code = subject_slug.rsplit("_", 1)   # "chemistry", "0620"
    except ValueError:
        subject, syllabus_code = subject_slug, ""
    dataset_slug = f"{board}_{level}_{subject_slug}"           # "cambridge_igcse_chemistry_0620"
    return subject_slug, board, level, subject, syllabus_code, dataset_slug


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def read_json_safe(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def extract_int(doc: dict | None, *keys: str) -> int | None:
    """Return the first matching int value, or len(list) if the value is a list."""
    if not doc:
        return None
    for k in keys:
        if k in doc:
            v = doc[k]
            if isinstance(v, int):
                return v
            if isinstance(v, list):
                return len(v)
    return None


# ---------------------------------------------------------------------------
# Stage record
# ---------------------------------------------------------------------------

def stage_record(
    gate: int,
    name: str,
    status: str,
    command: str,
    output: str | None,
) -> dict:
    return {
        "gate":    gate,
        "name":    name,
        "status":  status,
        "command": command,
        "output":  output or "",
    }


# ---------------------------------------------------------------------------
# Summary extraction
# ---------------------------------------------------------------------------

def build_summary(
    intake_dir: Path,
    bank_dir: Path,
    batch_id: str,
    generated_batch: Path,
    review_dir: Path,
    pkg_dir: Path,
) -> dict:
    raw_pairs = read_json_safe(intake_dir / "raw_document_pairs_v0.json")
    corpus    = read_json_safe(bank_dir / "source_corpus" / "unified_source_corpus_v0.json")
    skill_map = read_json_safe(bank_dir / "skill_map" / "unified_skill_map_v0.json")
    targets   = read_json_safe(bank_dir / "generation_targets" / "unified_generation_targets_v0.json")
    auth_batch= read_json_safe(bank_dir / "authoring_batches" / f"authoring_batch_v1_{batch_id}.json")
    gen_batch = read_json_safe(generated_batch) if generated_batch.exists() else None
    candidate = read_json_safe(review_dir / "publish_candidate_resource_bank_v1.json")
    review_q  = read_json_safe(review_dir / "teacher_review_queue_v1.json")
    pkg       = read_json_safe(pkg_dir / "publish_package_v1.json")

    return {
        "source_pairs":             extract_int(raw_pairs, "complete_pair_count", "pairs"),
        "source_count":             extract_int(corpus,    "source_count", "sources"),
        "skill_units":              extract_int(skill_map, "total_skill_units", "skill_units"),
        "generation_targets":       extract_int(targets,   "target_count", "targets"),
        "authoring_planned_items":  extract_int(auth_batch,"planned_item_count"),
        "generated_resources":      extract_int(gen_batch, "generated_resources"),
        "publish_ready_resources":  extract_int(candidate, "candidate_count", "items"),
        "teacher_review_resources": extract_int(review_q,  "review_item_count", "items"),
        "published_resources":      extract_int(pkg,       "resource_count", "items"),
    }


# ---------------------------------------------------------------------------
# Report and manifest builders
# ---------------------------------------------------------------------------

def build_report(
    status: str,
    raw_folder: str,
    stages: list[dict],
    current_stop: str | None,
    authoring_prompt: Path,
    expected_gen_batch: Path,
    pkg_json: Path,
    student_html: Path,
    teacher_html: Path,
    summary: dict,
    now_iso: str,
    pipeline_id: str,
    board: str,
    level: str,
    subject: str,
    syllabus_code: str,
) -> dict:
    return {
        "status":                  status,
        "pipeline_id":             pipeline_id,
        "created_at":              now_iso,
        "raw_folder":              raw_folder,
        "board":                   board,
        "level":                   level,
        "subject":                 subject,
        "syllabus_code":           syllabus_code,
        "stages":                  stages,
        "current_stop":            current_stop,
        "authoring_prompt":        str(authoring_prompt),
        "expected_generated_batch":str(expected_gen_batch),
        "publish_package":         str(pkg_json)    if pkg_json.exists()    else None,
        "student_preview":         str(student_html) if student_html.exists() else None,
        "teacher_preview":         str(teacher_html) if teacher_html.exists() else None,
        "summary":                 summary,
    }


def build_manifest_md(report: dict) -> str:
    STATUS_ICON = {
        "passed":  "OK",
        "failed":  "FAIL",
        "skipped": "SKIP",
        "waiting": "WAIT",
    }

    lines = [
        "# Quanta Aptus Full MVP Pipeline v1",
        "",
        f"- **Pipeline ID:** `{report['pipeline_id']}`",
        f"- **Status:** {report['status']}",
        f"- **Created:** {report['created_at']}",
        f"- **Raw Folder:** `{report['raw_folder']}`",
        "",
        "## Gates Run",
        "",
    ]
    for s in report["stages"]:
        icon = STATUS_ICON.get(s["status"], "-")
        lines.append(f"- Gate {s['gate']:02d} `{s['name']}`: [{icon}] {s['status']}")

    lines += ["", "## Pipeline State", ""]

    if report.get("current_stop"):
        lines.append(f"- **Current Stop:** `{report['current_stop']}`")
    if report.get("authoring_prompt"):
        lines.append(f"- **Authoring Prompt:** `{report['authoring_prompt']}`")
    if report.get("expected_generated_batch"):
        lines.append(f"- **Expected Generated Batch:** `{report['expected_generated_batch']}`")
    if report.get("publish_package"):
        lines.append(f"- **Publish Package:** `{report['publish_package']}`")
    if report.get("student_preview"):
        lines.append(f"- **Student Preview:** `{report['student_preview']}`")
    if report.get("teacher_preview"):
        lines.append(f"- **Teacher Preview:** `{report['teacher_preview']}`")

    lines += ["", "## Summary", ""]
    for k, v in report.get("summary", {}).items():
        if v is not None:
            label = k.replace("_", " ").title()
            lines.append(f"- **{label}:** {v}")

    lines += [
        "",
        "---",
        "",
        "> Cambridge source papers are internal reference only.",
        "> Published outputs are original Quanta Aptus generated resources.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run the full Quanta Aptus MVP ingestion pipeline."
    )
    ap.add_argument(
        "raw_folder",
        help="Path to raw PDF folder, e.g. data/raw/cambridge_igcse/physics_0625",
    )
    ap.add_argument("--batch-id",        default="001", dest="batch_id",
                    help="Batch suffix (default: 001)")
    ap.add_argument("--skip-existing",   action="store_true", dest="skip_existing",
                    help="Skip gates whose expected output already exists")
    ap.add_argument("--stop-after-authoring-prompt", action="store_true", dest="stop_after_prompt",
                    help="Stop after Gate 25 without waiting for generated batch")
    ap.add_argument("--generated-batch", default=None, dest="generated_batch",
                    help="Explicit path to generated resource batch JSON")
    ap.add_argument("--resume-from-generated-batch", action="store_true", dest="resume_from_gen",
                    help="Skip source gates 19-25 (if outputs exist) and continue from Gate 26")
    args = ap.parse_args()

    raw_folder = Path(args.raw_folder).resolve()
    batch_id   = args.batch_id

    if not raw_folder.exists():
        sys.exit(f"Error: raw folder not found: {raw_folder}")

    # ── Derive subject slug and components ─────────────────────────────────
    subject_slug, board, level, subject, syllabus_code, dataset_slug = (
        _derive_slug_components(raw_folder)
    )
    board_level  = raw_folder.parent.name            # e.g. "cambridge_igcse"
    PIPELINE_ID  = f"{dataset_slug}_full_mvp_pipeline_v1"
    INTAKE_PAIRS = (
        PROJECT_ROOT / "data" / "intake" / board_level / subject_slug
        / "raw_document_pairs_v0.json"
    )

    # ── Resolve all paths ──────────────────────────────────────────────────
    INTAKE   = PROJECT_ROOT / "data" / "intake"  / board_level / subject_slug
    BANK     = PROJECT_ROOT / "data" / "bank"    / board_level / subject_slug
    PUB      = PROJECT_ROOT / "data" / "publish" / board_level / subject_slug

    PAIRS_JSON        = INTAKE_PAIRS
    PIPELINE_REPORT   = INTAKE / "batch_paper_pipeline_report.json"
    CORPUS_JSON       = BANK / "source_corpus"       / "unified_source_corpus_v0.json"
    SKILL_MAP_JSON    = BANK / "skill_map"           / "unified_skill_map_v0.json"
    TARGETS_JSON      = BANK / "generation_targets"  / "unified_generation_targets_v0.json"
    AUTHORING_BATCH   = BANK / "authoring_batches"   / f"authoring_batch_v1_{batch_id}.json"
    AUTHORING_PROMPT  = BANK / "authoring_batches"   / f"authoring_prompt_v1_{batch_id}.md"
    ORIGINAL_BANK     = BANK / "original_resource_bank" / "original_resource_bank_v1.json"
    REVIEW_DIR        = BANK / "teacher_review"
    CANDIDATE_BANK    = REVIEW_DIR / "publish_candidate_resource_bank_v1.json"

    if args.generated_batch:
        GEN_BATCH = Path(args.generated_batch).resolve()
    else:
        GEN_BATCH = BANK / "generated_batches" / f"generated_resource_batch_v1_{batch_id}.json"

    VALIDATED_BATCH = GEN_BATCH.parent / (GEN_BATCH.stem + ".validated.json")
    PKG_DIR         = PUB / "resource_package_v1"
    PKG_JSON        = PKG_DIR / "publish_package_v1.json"
    STUDENT_HTML    = PKG_DIR / "static_preview" / "student_resource_preview_v1.html"
    TEACHER_HTML    = PKG_DIR / "static_preview" / "teacher_resource_preview_v1.html"

    REPORT_DIR    = PUB / "mvp_pipeline_v1"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH   = REPORT_DIR / "full_mvp_pipeline_report.json"
    MANIFEST_PATH = REPORT_DIR / "full_mvp_pipeline_manifest.md"

    now_iso = datetime.now(timezone.utc).isoformat()
    stages:  list[dict] = []

    # ── Closure: write report + manifest + print terminal summary ──────────
    def finalize(final_status: str, current_stop: str | None = None) -> None:
        summary  = build_summary(INTAKE, BANK, batch_id, GEN_BATCH, REVIEW_DIR, PKG_DIR)
        report   = build_report(
            status            = final_status,
            raw_folder        = str(raw_folder),
            stages            = stages,
            current_stop      = current_stop,
            authoring_prompt  = AUTHORING_PROMPT,
            expected_gen_batch= GEN_BATCH,
            pkg_json          = PKG_JSON,
            student_html      = STUDENT_HTML,
            teacher_html      = TEACHER_HTML,
            summary           = summary,
            now_iso           = now_iso,
            pipeline_id       = PIPELINE_ID,
            board             = board,
            level             = level,
            subject           = subject,
            syllabus_code     = syllabus_code,
        )
        manifest = build_manifest_md(report)

        REPORT_PATH.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        MANIFEST_PATH.write_text(manifest, encoding="utf-8")

        print(f"\n{'='*62}")
        print(f"pipeline_status        : {final_status}")
        for s in stages:
            print(f"  gate {s['gate']:02d} {s['name']:<32}: {s['status']}")
        print()
        print(f"authoring_prompt       : {AUTHORING_PROMPT}")
        print(f"expected_gen_batch     : {GEN_BATCH}")
        if VALIDATED_BATCH.exists():
            print(f"validated_batch        : {VALIDATED_BATCH}")
        if PKG_JSON.exists():
            print(f"publish_package        : {PKG_JSON}")
        if STUDENT_HTML.exists():
            print(f"student_preview        : {STUDENT_HTML}")
        if TEACHER_HTML.exists():
            print(f"teacher_preview        : {TEACHER_HTML}")
        print(f"report                 : {REPORT_PATH}")
        print(f"manifest               : {MANIFEST_PATH}")

    # ── Closure: run one gate ──────────────────────────────────────────────
    def run_gate(
        gate: int,
        name: str,
        script_args: list[str],
        expected_output: Path | None,
        source_phase: bool = False,
    ) -> bool:
        """
        Decide whether to skip, run, or fail for this gate.
        Returns True to continue, False to stop the pipeline.
        """
        cmd      = [PYTHON] + script_args
        cmd_str  = " ".join(cmd)
        out_str  = str(expected_output) if expected_output else None

        # ── Skip logic ─────────────────────────────────────────────────────
        if args.resume_from_gen and source_phase:
            if expected_output is None:
                # No file to verify (Gate 20) — assume done when resuming
                stages.append(stage_record(gate, name, "skipped", cmd_str, out_str))
                print(f"Gate {gate:02d} ({name}): SKIPPED (resume mode)")
                return True
            if expected_output.exists():
                stages.append(stage_record(gate, name, "skipped", cmd_str, out_str))
                print(f"Gate {gate:02d} ({name}): SKIPPED (output exists)")
                return True
            # resume requested but prerequisite is missing
            stages.append(stage_record(gate, name, "failed", cmd_str, out_str))
            print(f"Gate {gate:02d} ({name}): FAILED")
            print(f"  --resume-from-generated-batch requires: {expected_output}")
            print("  Run without --resume-from-generated-batch to rebuild the source pipeline.")
            return False

        if args.skip_existing and expected_output is not None and expected_output.exists():
            stages.append(stage_record(gate, name, "skipped", cmd_str, out_str))
            print(f"Gate {gate:02d} ({name}): SKIPPED (output exists)")
            return True

        # ── Execute ────────────────────────────────────────────────────────
        print(f"\nGate {gate:02d} ({name})")
        print(f">>> {cmd_str}", flush=True)
        result = subprocess.run(cmd)

        if result.returncode != 0:
            stages.append(stage_record(gate, name, "failed", cmd_str, out_str))
            print(f"Gate {gate:02d} ({name}): FAILED (exit code {result.returncode})")
            return False

        if expected_output is not None and not expected_output.exists():
            stages.append(stage_record(gate, name, "failed", cmd_str, out_str))
            print(f"Gate {gate:02d} ({name}): FAILED (expected output not found: {expected_output})")
            return False

        stages.append(stage_record(gate, name, "passed", cmd_str, out_str))
        print(f"Gate {gate:02d} ({name}): PASSED")
        return True

    # ── Source pipeline: Gates 19-25 ───────────────────────────────────────
    print(f"{'='*62}")
    print(f"Quanta Aptus Full MVP Pipeline v1")
    print(f"Raw folder  : {raw_folder}")
    print(f"Subject slug: {subject_slug}")
    print(f"Subject     : {subject}")
    print(f"Syllabus    : {syllabus_code}")
    print(f"Dataset slug: {dataset_slug}")
    print(f"Pipeline ID : {PIPELINE_ID}")
    print(f"Intake pairs: {PAIRS_JSON}")
    print(f"Batch ID    : {batch_id}")
    print(f"{'='*62}\n")

    if not run_gate(
        19, "raw_document_intake",
        [str(TOOLS / "build_raw_document_intake.py"), str(raw_folder)],
        PAIRS_JSON,
        source_phase=True,
    ):
        finalize("failed")
        return

    if not run_gate(
        20, "markitdown_ingest",
        [str(TOOLS / "run_batch_markitdown_ingest.py"), str(PAIRS_JSON)],
        None,  # no single output file to verify
        source_phase=True,
    ):
        finalize("failed")
        return

    if not run_gate(
        21, "batch_paper_pipeline",
        [str(TOOLS / "run_batch_paper_pipeline.py"), str(PAIRS_JSON)],
        PIPELINE_REPORT,
        source_phase=True,
    ):
        finalize("failed")
        return

    if not run_gate(
        22, "unified_source_corpus",
        [str(TOOLS / "build_unified_source_corpus.py"), str(PIPELINE_REPORT)],
        CORPUS_JSON,
        source_phase=True,
    ):
        finalize("failed")
        return

    # ── Subject adapter info ───────────────────────────────────────────────
    try:
        _tools_str = str(TOOLS)
        if _tools_str not in sys.path:
            sys.path.insert(0, _tools_str)
        from subject_adapters.registry import get_adapter as _get_adapter
        _meta = _get_adapter(subject_slug).get_adapter_metadata()
        print(f"  adapter        : {_meta['adapter_name']} ({_meta['adapter_status']})")
        if _meta.get("adapter_status") == "generic_adapter":
            print(f"  NOTE: no subject adapter for '{subject_slug}' — using generic fallback.")
            print(f"        Low-confidence classification. All items flagged needs_human_review.")
    except Exception:
        print(f"  adapter        : subject_adapters not available")

    if not run_gate(
        23, "unified_skill_map",
        [str(TOOLS / "build_unified_skill_map.py"), str(CORPUS_JSON)],
        SKILL_MAP_JSON,
        source_phase=True,
    ):
        finalize("failed")
        return

    if not run_gate(
        24, "unified_generation_targets",
        [str(TOOLS / "build_unified_generation_targets.py"), str(SKILL_MAP_JSON)],
        TARGETS_JSON,
        source_phase=True,
    ):
        finalize("failed")
        return

    if not run_gate(
        25, "authoring_batch",
        [
            str(TOOLS / "build_authoring_batch_v1.py"),
            str(TARGETS_JSON),
            "--batch-id", batch_id,
        ],
        AUTHORING_BATCH,
        source_phase=True,
    ):
        finalize("failed")
        return

    # ── AI handoff checkpoint ──────────────────────────────────────────────
    if args.stop_after_prompt:
        print(f"\nSource pipeline complete (--stop-after-authoring-prompt).")
        print(f"Authoring prompt : {AUTHORING_PROMPT}")
        finalize("waiting_for_generated_batch", "waiting_for_generated_batch")
        return

    if not GEN_BATCH.exists():
        print()
        print("Source pipeline completed. Authoring prompt is ready.")
        print("Open this prompt and generate JSON:")
        print(f"  {AUTHORING_PROMPT}")
        print("Save generated JSON to:")
        print(f"  {GEN_BATCH}")
        print("Then resume with:")
        raw_arg = args.raw_folder
        print(
            f"  .venv-ingest\\Scripts\\python.exe "
            f"tools\\ingest\\run_full_mvp_pipeline.py "
            f"{raw_arg} --resume-from-generated-batch"
        )
        finalize("waiting_for_generated_batch", "waiting_for_generated_batch")
        return

    # ── Post-generation pipeline: Gates 26-29 ─────────────────────────────
    if not run_gate(
        26, "validate_generated_batch",
        [
            str(TOOLS / "validate_generated_resource_batch_v1.py"),
            str(AUTHORING_BATCH),
            str(GEN_BATCH),
        ],
        VALIDATED_BATCH,
    ):
        finalize("failed")
        return

    if not run_gate(
        27, "original_resource_bank",
        [str(TOOLS / "build_original_resource_bank_v1.py"), str(VALIDATED_BATCH)],
        ORIGINAL_BANK,
    ):
        finalize("failed")
        return

    if not run_gate(
        28, "teacher_review_queue",
        [str(TOOLS / "build_teacher_review_queue_v1.py"), str(ORIGINAL_BANK)],
        CANDIDATE_BANK,
    ):
        finalize("failed")
        return

    if not run_gate(
        29, "publish_package",
        [str(TOOLS / "build_publish_package_v1.py"), str(CANDIDATE_BANK)],
        PKG_JSON,
    ):
        finalize("failed")
        return

    finalize("passed")


if __name__ == "__main__":
    main()
