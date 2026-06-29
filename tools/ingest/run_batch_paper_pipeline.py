"""
Component-aware batch paper pipeline for all complete pairs.

Routes each pair to the correct pipeline based on paper_code:
  1x / 2x → mcq_pipeline           (segment_mcq … reconcile_options)
  3x / 4x → structured_theory_pipeline  (segment_structured_questions … dataset)
  5x / 6x → practical_pipeline     (segment_structured_questions … dataset)

Usage:
    python tools/ingest/run_batch_paper_pipeline.py <raw_document_pairs_v0.json> [--skip-existing]

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/run_batch_paper_pipeline.py \\
        data/intake/cambridge_igcse/physics_0625/raw_document_pairs_v0.json
"""

import sys
import json
import argparse
import subprocess
import traceback as tb_module
from pathlib import Path

TOOLS_DIR     = Path(__file__).parent
PROJECT_ROOT  = Path(__file__).resolve().parents[2]
INGESTED_BASE = PROJECT_ROOT / "data" / "ingested" / "markitdown"

# All pipeline scripts (MCQ + structured)
ALL_SCRIPTS: dict[str, Path] = {
    # MCQ pipeline
    "segment_mcq":                 TOOLS_DIR / "segment_mcq.py",
    "normalize_questions":          TOOLS_DIR / "normalize_questions.py",
    "classify_topics":              TOOLS_DIR / "classify_topics.py",
    "parse_mcq_mark_scheme":        TOOLS_DIR / "parse_mcq_mark_scheme.py",
    "enrich_questions":             TOOLS_DIR / "enrich_questions.py",
    "reconcile_options":            TOOLS_DIR / "reconcile_options.py",
    # Structured pipeline
    "segment_structured_questions": TOOLS_DIR / "segment_structured_questions.py",
    "parse_structured_mark_scheme": TOOLS_DIR / "parse_structured_mark_scheme.py",
}

# Total marks by first digit of paper_code
_TOTAL_MARKS: dict[str, int] = {"3": 40, "4": 80, "5": 40, "6": 40}


# ===========================================================================
# Custom exception for subprocess step failures
# ===========================================================================

class StepFailed(RuntimeError):
    def __init__(self, step_name: str, step_result: dict):
        super().__init__(
            f"Step {step_name} failed with return code {step_result['return_code']}"
        )
        self.step_name   = step_name
        self.step_result = step_result


# ===========================================================================
# Component routing
# ===========================================================================

def get_component_type(paper_code: str) -> tuple[str, str]:
    """Returns (component_type, route) based on first digit of paper_code."""
    first = paper_code[0] if paper_code else ""
    if first in ("1", "2"):
        return "mcq", "mcq_pipeline"
    if first in ("3", "4"):
        return "theory_structured", "structured_theory_pipeline"
    if first in ("5", "6"):
        return "practical_structured", "practical_pipeline"
    return "unknown", "unknown_pipeline"


# ===========================================================================
# Helpers
# ===========================================================================

def check_scripts() -> None:
    missing = [name for name, path in ALL_SCRIPTS.items() if not path.exists()]
    if missing:
        sys.exit(f"Error: pipeline scripts not found: {missing}")


def qp_folder(qp_doc_id: str) -> Path:
    return INGESTED_BASE / qp_doc_id


def ms_folder(ms_doc_id: str) -> Path:
    return INGESTED_BASE / ms_doc_id


def run_step(name: str, args: list) -> dict:
    """Run a subprocess pipeline step; raises StepFailed on non-zero exit."""
    script = ALL_SCRIPTS[name]
    cmd     = [sys.executable, str(script)] + [str(a) for a in args]
    cmd_str = " ".join(cmd)

    print(f"      step: {name}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stdout_tail = result.stdout[-2000:] if result.stdout else ""
    stderr_tail = result.stderr[-2000:] if result.stderr else ""

    step_result = {
        "step":        name,
        "command":     cmd_str,
        "return_code": result.returncode,
        "status":      "passed" if result.returncode == 0 else "failed",
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }

    if result.returncode != 0:
        raise StepFailed(name, step_result)

    return step_result


def load_json_safe(path: Path) -> dict | list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ===========================================================================
# MCQ pipeline helpers
# ===========================================================================

def extract_mcq_summary(qp_dir: Path, ms_dir: Path) -> dict:
    questions  = load_json_safe(qp_dir / "questions.json")
    answer_key = load_json_safe(ms_dir  / "answer_key.json")
    enrichment = load_json_safe(qp_dir  / "enrichment_report.json")
    reconcile  = load_json_safe(qp_dir  / "reconcile_report.json")

    detected = len(questions.get("questions", []))
    if isinstance(answer_key, dict) and "answers" not in answer_key:
        answers_detected = len(answer_key)
    else:
        answers_detected = answer_key.get("detected_answers", 0)

    return {
        "detected_questions":           detected,
        "answers_detected":             answers_detected,
        "answers_attached":             enrichment.get("answers_attached", 0),
        "correct_answer_present_count": reconcile.get("correct_answer_present_count", 0),
    }


# ===========================================================================
# Structured pipeline helpers
# ===========================================================================

def build_structured_paper_dataset(
    pair: dict,
    component_type: str,
    qp_dir: Path,
    ms_dir: Path,
) -> tuple[dict, dict]:
    """
    Combine structured_questions.json + structured_mark_scheme.json into the
    final dataset dict.  Returns (dataset, report).
    """
    paper_code = pair.get("paper_code", "")
    first      = paper_code[0] if paper_code else ""

    sq_data  = load_json_safe(qp_dir / "structured_questions.json")
    ms_data  = load_json_safe(ms_dir  / "structured_mark_scheme.json")

    questions        = sq_data.get("questions", [])   if isinstance(sq_data, dict) else []
    mark_scheme_items = ms_data.get("items", [])       if isinstance(ms_data, dict) else []

    total_marks    = _TOTAL_MARKS.get(first, 40)
    dataset_status = (
        "internal_structured_source"
        if (questions or mark_scheme_items)
        else "internal_structured_source_empty"
    )

    dataset = {
        "paper_id":        pair["pair_id"],
        "component_type":  component_type,
        "board":           pair.get("board", "cambridge"),
        "level":           pair.get("level", "igcse"),
        "subject":         pair.get("subject", "physics"),
        "syllabus_code":   pair.get("syllabus_code", "0625"),
        "year":            pair.get("year", 0),
        "series_code":     pair.get("series_code", ""),
        "paper_code":      paper_code,
        "question_count":  len(questions),
        "total_marks":     total_marks,
        "questions":       questions,
        "mark_scheme_items": mark_scheme_items,
        "status":          dataset_status,
    }

    report = {
        "paper_id":           pair["pair_id"],
        "component_type":     component_type,
        "paper_code":         paper_code,
        "question_count":     len(questions),
        "mark_scheme_items":  len(mark_scheme_items),
        "total_marks":        total_marks,
        "status":             dataset_status,
        "structured_questions_source": str(qp_dir / "structured_questions.json"),
        "structured_ms_source":        str(ms_dir  / "structured_mark_scheme.json"),
    }

    return dataset, report


# ===========================================================================
# Per-pair pipelines
# ===========================================================================

def run_mcq_pair_pipeline(
    pair: dict,
    component_type: str,
    route: str,
    skip_existing: bool,
) -> dict:
    pair_id   = pair["pair_id"]
    qp_doc_id = pair["question_paper"]["document_id"]
    ms_doc_id = pair["mark_scheme"]["document_id"]
    qp_dir    = qp_folder(qp_doc_id)
    ms_dir    = ms_folder(ms_doc_id)
    qp_clean  = qp_dir / "clean.md"
    ms_clean  = ms_dir / "clean.md"

    # Skip-existing
    reconciled = qp_dir / "questions.reconciled.json"
    if skip_existing and reconciled.exists():
        return {
            "pair_id":          pair_id,
            "component_type":   component_type,
            "route":            route,
            "status":           "skipped_existing",
            "questions_reconciled": str(reconciled),
            "paper_pipeline_report": str(qp_dir / "paper_pipeline_report.json"),
        }

    steps: list[dict] = []
    failed_step = error_msg = traceback_str = ""

    try:
        for p in (qp_clean, ms_clean):
            if not p.exists():
                raise RuntimeError(f"Ingested markdown not found: {p}")

        steps.append(run_step("segment_mcq",         [qp_clean]))
        steps.append(run_step("normalize_questions",  [qp_dir / "questions.json"]))
        steps.append(run_step("classify_topics",      [qp_dir / "questions.normalized.json"]))
        steps.append(run_step("parse_mcq_mark_scheme",[ms_clean]))
        steps.append(run_step("enrich_questions",     [
            qp_dir / "questions.classified.json",
            ms_dir / "answer_key.json",
        ]))
        steps.append(run_step("reconcile_options",    [qp_dir / "questions.enriched.json"]))

    except StepFailed as exc:
        steps.append(exc.step_result)
        failed_step = exc.step_name
        error_msg   = str(exc)
        print(f"      FAILED step: {failed_step}")
    except Exception as exc:
        failed_step   = "unknown"
        error_msg     = str(exc)
        traceback_str = tb_module.format_exc()
        print(f"      FAILED: {error_msg}")

    return _write_mcq_pair_report(
        pair, component_type, route, steps,
        failed_step, error_msg, traceback_str,
        qp_dir, ms_dir, qp_clean, ms_clean,
    )


def run_structured_pair_pipeline(
    pair: dict,
    component_type: str,
    route: str,
    skip_existing: bool,
) -> dict:
    pair_id   = pair["pair_id"]
    qp_doc_id = pair["question_paper"]["document_id"]
    ms_doc_id = pair["mark_scheme"]["document_id"]
    paper_code = pair.get("paper_code", "")
    qp_dir    = qp_folder(qp_doc_id)
    ms_dir    = ms_folder(ms_doc_id)
    qp_clean  = qp_dir / "clean.md"
    ms_clean  = ms_dir / "clean.md"

    # Skip-existing
    dataset_path = qp_dir / "structured_paper_dataset.json"
    if skip_existing and dataset_path.exists():
        return {
            "pair_id":                 pair_id,
            "component_type":          component_type,
            "route":                   route,
            "status":                  "skipped_existing",
            "structured_paper_dataset": str(dataset_path),
            "paper_pipeline_report":   str(qp_dir / "paper_pipeline_report.json"),
        }

    steps: list[dict] = []
    failed_step = error_msg = traceback_str = ""

    try:
        for p in (qp_clean, ms_clean):
            if not p.exists():
                raise RuntimeError(f"Ingested markdown not found: {p}")

        # Step 1: segment structured questions (always exits 0)
        steps.append(run_step("segment_structured_questions", [
            qp_clean, "--paper-code", paper_code,
        ]))

        # Step 2: parse structured mark scheme (always exits 0)
        steps.append(run_step("parse_structured_mark_scheme", [
            ms_clean, "--paper-code", paper_code,
        ]))

    except StepFailed as exc:
        steps.append(exc.step_result)
        failed_step = exc.step_name
        error_msg   = str(exc)
        print(f"      FAILED step: {failed_step}")
    except Exception as exc:
        failed_step   = "unknown"
        error_msg     = str(exc)
        traceback_str = tb_module.format_exc()
        print(f"      FAILED: {error_msg}")

    # Step 3: build dataset in-process (always runs, even if earlier steps failed)
    dataset_status_str = "internal_structured_source"
    try:
        dataset, ds_report = build_structured_paper_dataset(
            pair, component_type, qp_dir, ms_dir
        )
        qp_dir.mkdir(parents=True, exist_ok=True)
        dataset_path.write_text(
            json.dumps(dataset, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        ds_report_path = qp_dir / "structured_paper_dataset_report.json"
        ds_report_path.write_text(
            json.dumps(ds_report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        steps.append({
            "step":        "build_structured_paper_dataset",
            "status":      "passed",
            "return_code": 0,
            "output":      str(dataset_path),
        })
        dataset_status_str = dataset.get("status", "internal_structured_source")
    except Exception as exc:
        build_err = str(exc)
        steps.append({
            "step":        "build_structured_paper_dataset",
            "status":      "failed",
            "return_code": 1,
            "error":       build_err,
        })
        if not failed_step:
            failed_step = "build_structured_paper_dataset"
            error_msg   = build_err

    return _write_structured_pair_report(
        pair, component_type, route, steps,
        failed_step, error_msg, traceback_str,
        qp_dir, ms_dir,
        dataset_path if dataset_path.exists() else None,
    )


def run_pair_pipeline(pair: dict, skip_existing: bool) -> dict:
    """Dispatch pair to the correct pipeline based on paper_code."""
    paper_code     = pair.get("paper_code", "")
    component_type, route = get_component_type(paper_code)

    print(f"    paper_code     : {paper_code}")
    print(f"    component_type : {component_type}")
    print(f"    route          : {route}")

    if route == "mcq_pipeline":
        return run_mcq_pair_pipeline(pair, component_type, route, skip_existing)
    else:
        return run_structured_pair_pipeline(pair, component_type, route, skip_existing)


# ===========================================================================
# Per-pair report writers
# ===========================================================================

def _write_mcq_pair_report(
    pair, component_type, route, steps,
    failed_step, error_msg, traceback_str,
    qp_dir, ms_dir, qp_clean, ms_clean,
):
    pair_id   = pair["pair_id"]
    qp_doc_id = pair["question_paper"]["document_id"]
    ms_doc_id = pair["mark_scheme"]["document_id"]
    status    = "failed" if failed_step else "passed"

    final_outputs = {
        "questions_json":       str(qp_dir / "questions.json"),
        "questions_normalized": str(qp_dir / "questions.normalized.json"),
        "questions_classified": str(qp_dir / "questions.classified.json"),
        "answer_key":           str(ms_dir / "answer_key.json"),
        "questions_enriched":   str(qp_dir / "questions.enriched.json"),
        "questions_reconciled": str(qp_dir / "questions.reconciled.json"),
    }
    summary = extract_mcq_summary(qp_dir, ms_dir) if status == "passed" else {}

    report: dict = {
        "pair_id":                    pair_id,
        "component_type":             component_type,
        "route":                      route,
        "status":                     status,
        "board":                      pair.get("board", ""),
        "level":                      pair.get("level", ""),
        "subject":                    pair.get("subject", ""),
        "syllabus_code":              pair.get("syllabus_code", ""),
        "year":                       pair.get("year", 0),
        "series_code":                pair.get("series_code", ""),
        "series_name":                pair.get("series_name", ""),
        "paper_code":                 pair.get("paper_code", ""),
        "question_paper_document_id": qp_doc_id,
        "mark_scheme_document_id":    ms_doc_id,
        "question_paper_clean_md":    str(qp_clean),
        "mark_scheme_clean_md":       str(ms_clean),
        "steps":                      steps,
        "final_outputs":              final_outputs,
        "summary":                    summary,
    }
    if failed_step:
        failed_data = next((s for s in steps if s.get("step") == failed_step), {})
        report.update({
            "failed_step":        failed_step,
            "failed_command":     failed_data.get("command", ""),
            "failed_return_code": failed_data.get("return_code", -1),
            "failed_stdout_tail": failed_data.get("stdout_tail", ""),
            "failed_stderr_tail": failed_data.get("stderr_tail", ""),
            "error":              error_msg,
            "traceback":          traceback_str,
        })

    report_path   = qp_dir / "paper_pipeline_report.json"
    manifest_path = qp_dir / "paper_pipeline_manifest.md"
    qp_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(_pipeline_manifest_md(report), encoding="utf-8")

    return {
        "pair_id":               pair_id,
        "component_type":        component_type,
        "route":                 route,
        "status":                status,
        "paper_pipeline_report": str(report_path),
        "questions_reconciled":  str(qp_dir / "questions.reconciled.json"),
        "summary":               summary,
        "failed_step":           failed_step,
        "error":                 error_msg,
    }


def _write_structured_pair_report(
    pair, component_type, route, steps,
    failed_step, error_msg, traceback_str,
    qp_dir, ms_dir, dataset_path,
):
    pair_id   = pair["pair_id"]
    qp_doc_id = pair["question_paper"]["document_id"]
    ms_doc_id = pair["mark_scheme"]["document_id"]

    # Structured pipeline: "passed" if dataset was created (even if partial)
    status = "failed" if (failed_step and dataset_path is None) else "passed"

    report: dict = {
        "pair_id":                    pair_id,
        "component_type":             component_type,
        "route":                      route,
        "status":                     status,
        "board":                      pair.get("board", ""),
        "level":                      pair.get("level", ""),
        "subject":                    pair.get("subject", ""),
        "syllabus_code":              pair.get("syllabus_code", ""),
        "year":                       pair.get("year", 0),
        "series_code":                pair.get("series_code", ""),
        "series_name":                pair.get("series_name", ""),
        "paper_code":                 pair.get("paper_code", ""),
        "question_paper_document_id": qp_doc_id,
        "mark_scheme_document_id":    ms_doc_id,
        "steps":                      steps,
        "structured_paper_dataset":   str(dataset_path) if dataset_path else "",
    }
    if failed_step:
        failed_data = next((s for s in steps if s.get("step") == failed_step), {})
        report.update({
            "failed_step":        failed_step,
            "failed_return_code": failed_data.get("return_code", -1),
            "error":              error_msg,
            "traceback":          traceback_str,
        })

    report_path   = qp_dir / "paper_pipeline_report.json"
    manifest_path = qp_dir / "paper_pipeline_manifest.md"
    qp_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(_pipeline_manifest_md(report), encoding="utf-8")

    return {
        "pair_id":                  pair_id,
        "component_type":           component_type,
        "route":                    route,
        "status":                   status,
        "paper_pipeline_report":    str(report_path),
        "structured_paper_dataset": str(dataset_path) if dataset_path else "",
        "failed_step":              failed_step,
        "error":                    error_msg,
    }


def _pipeline_manifest_md(report: dict) -> str:
    lines = []
    lines.append(f"# Paper Pipeline: {report['pair_id']}")
    lines.append("")
    lines.append(f"**Status:** {report['status']}")
    lines.append(
        f"**Component:** {report.get('component_type','')}  |  "
        f"**Route:** {report.get('route','')}  |  "
        f"**Paper:** {report.get('paper_code','')}"
    )
    lines.append("")
    lines.append("## Steps")
    lines.append("")
    for s in report.get("steps", []):
        mark = "+" if s.get("status") == "passed" else "X"
        lines.append(f"- [{mark}] **{s['step']}** (exit {s.get('return_code', '?')})")
        if s.get("status") != "passed":
            for key in ("stderr_tail", "stdout_tail", "error"):
                val = s.get(key, "")
                if val:
                    lines.append(f"  ```\n  {str(val)[:400]}\n  ```")
                    break
    lines.append("")

    if report.get("failed_step"):
        lines.append("## Failure Details")
        lines.append("")
        lines.append(f"**Failed step:** `{report['failed_step']}`")
        lines.append(f"**Error:** {report.get('error', '')}")
        if report.get("traceback"):
            lines.append("")
            lines.append("```")
            lines.append(report["traceback"][:800])
            lines.append("```")
        lines.append("")

    if report.get("summary"):
        sm = report["summary"]
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("| ------ | ----: |")
        for k, v in sm.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

    if report.get("structured_paper_dataset"):
        lines.append(f"**Structured dataset:** `{report['structured_paper_dataset']}`")
        lines.append("")

    return "\n".join(lines)


# ===========================================================================
# Batch report + manifest
# ===========================================================================

def build_batch_report(
    pairs_file: Path,
    pairs_data: dict,
    pair_results: list[dict],
    out_files: dict,
) -> dict:
    complete_pair_count  = sum(1 for p in pairs_data.get("pairs", []) if p.get("pair_status") == "complete")
    processed_pair_count = len(pair_results)
    passed_count  = sum(1 for p in pair_results if p["status"] == "passed")
    failed_count  = sum(1 for p in pair_results if p["status"] == "failed")
    skipped_count = sum(1 for p in pair_results if p["status"] == "skipped_existing")

    # Route counts
    route_counts: dict[str, int] = {}
    for pr in pair_results:
        r = pr.get("route", "unknown")
        route_counts[r] = route_counts.get(r, 0) + 1

    if processed_pair_count == 0:
        status = "warning_no_complete_pairs"
    elif failed_count > 0:
        status = "failed"
    else:
        status = "passed"

    pairs_out = []
    for pr in pair_results:
        entry: dict = {
            "pair_id":          pr["pair_id"],
            "component_type":   pr.get("component_type", ""),
            "route":            pr.get("route", ""),
            "status":           pr["status"],
            "paper_pipeline_report": pr.get("paper_pipeline_report", ""),
        }
        if pr.get("route") == "mcq_pipeline":
            entry["questions_reconciled"] = pr.get("questions_reconciled", "")
            entry["summary"]              = pr.get("summary", {})
        else:
            entry["structured_paper_dataset"] = pr.get("structured_paper_dataset", "")
        if pr["status"] == "failed":
            entry["failed_step"] = pr.get("failed_step", "")
            entry["error"]       = pr.get("error", "")
        pairs_out.append(entry)

    return {
        "status":               status,
        "pairs_file":           str(pairs_file),
        "complete_pair_count":  complete_pair_count,
        "processed_pair_count": processed_pair_count,
        "passed_pair_count":    passed_count,
        "failed_pair_count":    failed_count,
        "skipped_pair_count":   skipped_count,
        "routes":               route_counts,
        "pairs":                pairs_out,
        "output_files":         out_files,
    }


def build_batch_manifest_md(report: dict) -> str:
    lines = []
    lines.append("# Quanta Aptus Batch Paper Pipeline (Component-Aware)")
    lines.append("")
    lines.append(f"**Pairs file:** `{report['pairs_file']}`")
    lines.append(f"**Status:** {report['status']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| ------ | ----: |")
    lines.append(f"| Complete pairs | {report['complete_pair_count']} |")
    lines.append(f"| Processed pairs | {report['processed_pair_count']} |")
    lines.append(f"| Passed | {report['passed_pair_count']} |")
    lines.append(f"| Failed | {report['failed_pair_count']} |")
    lines.append(f"| Skipped (existing) | {report['skipped_pair_count']} |")
    lines.append("")

    if report.get("routes"):
        lines.append("## Routes")
        lines.append("")
        lines.append("| Route | Count |")
        lines.append("| ----- | ----: |")
        for route, count in report["routes"].items():
            lines.append(f"| {route} | {count} |")
        lines.append("")

    if report["pairs"]:
        lines.append("## Processed Pairs")
        lines.append("")
        lines.append("| Pair ID | Type | Route | Status |")
        lines.append("| ------- | ---- | ----- | ------ |")
        for pr in report["pairs"]:
            lines.append(
                f"| `{pr['pair_id']}` | {pr['component_type']} | {pr['route']} | {pr['status']} |"
            )
        lines.append("")

    lines.append("## Output Paths")
    lines.append("")
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "> This step creates internal structured datasets only. "
        "It does not publish copyrighted Cambridge source content."
    )
    lines.append("")
    return "\n".join(lines)


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Component-aware batch paper pipeline."
    )
    ap.add_argument("pairs_file", help="Path to raw_document_pairs_v0.json")
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip pairs that already have their final output file",
    )
    args = ap.parse_args()

    pairs_path = Path(args.pairs_file)
    if not pairs_path.exists():
        sys.exit(f"Error: file not found: {pairs_path}")

    check_scripts()

    pairs_data     = json.loads(pairs_path.read_text(encoding="utf-8"))
    complete_pairs = [p for p in pairs_data.get("pairs", []) if p.get("pair_status") == "complete"]

    print("Batch Paper Pipeline (Component-Aware)")
    print(f"  pairs_file    : {pairs_path}")
    print(f"  skip_existing : {args.skip_existing}")
    print(f"  complete pairs: {len(complete_pairs)}")

    pair_results = []
    for pair in complete_pairs:
        print(f"\n  [{pair['pair_id']}]")
        result = run_pair_pipeline(pair, skip_existing=args.skip_existing)
        pair_results.append(result)
        print(f"    status         : {result['status']}")
        if result.get("structured_paper_dataset"):
            print(f"    dataset        : {result['structured_paper_dataset']}")
        elif result.get("questions_reconciled"):
            print(f"    reconciled     : {result['questions_reconciled']}")

    out_dir = pairs_path.parent
    report_path   = out_dir / "batch_paper_pipeline_report.json"
    manifest_path = out_dir / "batch_paper_pipeline_manifest.md"
    out_files = {
        "report":   str(report_path),
        "manifest": str(manifest_path),
    }

    report   = build_batch_report(pairs_path, pairs_data, pair_results, out_files)
    manifest = build_batch_manifest_md(report)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(manifest, encoding="utf-8")

    # Terminal summary
    print(f"\nstatus               : {report['status']}")
    print(f"complete_pair_count  : {report['complete_pair_count']}")
    print(f"processed_pair_count : {report['processed_pair_count']}")
    print(f"passed_pair_count    : {report['passed_pair_count']}")
    print(f"failed_pair_count    : {report['failed_pair_count']}")
    print(f"routes               : {report['routes']}")
    print("")
    for pr in pair_results:
        ct  = pr.get("component_type", "")
        rt  = pr.get("route", "")
        st  = pr["status"]
        ds  = pr.get("structured_paper_dataset") or pr.get("questions_reconciled") or ""
        print(f"  {pr['pair_id']}")
        print(f"    component_type : {ct}")
        print(f"    route          : {rt}")
        print(f"    status         : {st}")
        if ds:
            print(f"    output         : {ds}")
    print(f"\nreport    : {report_path}")
    print(f"manifest  : {manifest_path}")


if __name__ == "__main__":
    main()
