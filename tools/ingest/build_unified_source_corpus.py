"""
Build the Quanta Aptus Unified Source Corpus from batch paper pipeline output.

Reads batch_paper_pipeline_report.json, loads each passed pair's final output
file, and assembles a single indexed corpus of metadata + source paths.
Raw content is NOT duplicated — source_file paths point to the authoritative data.

Usage:
    python tools/ingest/build_unified_source_corpus.py \\
        data/intake/cambridge_igcse/physics_0625/batch_paper_pipeline_report.json

Output (data/bank/cambridge_igcse/physics_0625/source_corpus/):
    unified_source_corpus_v0.json
    unified_source_corpus_report.json
    unified_source_corpus_manifest.md
"""

import sys
import re
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_TYPE_MAP: dict[str, str] = {
    "mcq":                  "mcq_source",
    "theory_structured":    "theory_source",
    "practical_structured": "practical_source",
}

ROUTE_LABELS: dict[str, str] = {
    "mcq_pipeline":               "MCQ Paper (Paper 1/2)",
    "structured_theory_pipeline": "Theory Paper (Paper 3/4)",
    "practical_pipeline":         "Practical Paper (Paper 5/6)",
}


# ===========================================================================
# Utilities
# ===========================================================================

def load_json(path: Path) -> tuple[dict | list | None, str]:
    """Returns (data, error_str). error_str is '' on success."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except Exception as exc:
        return None, f"Read error: {exc}"


def parse_pair_id(pair_id: str) -> dict:
    """Extract year, series_code, paper_code from pair_id string."""
    m = re.search(r'_(\d{4})_([swm])_p(\d+)$', pair_id, re.IGNORECASE)
    if m:
        return {
            "year":        int(m.group(1)),
            "series_code": m.group(2).lower(),
            "paper_code":  m.group(3),
        }
    return {}


def parse_sub_path(parts: tuple) -> dict:
    """
    Infer board / level / subject / syllabus_code from folder name components.
    E.g. ("cambridge_igcse", "physics_0625") → board=cambridge, level=igcse,
                                                 subject=physics, syllabus_code=0625
    """
    result = {
        "board":         "cambridge",
        "level":         "igcse",
        "subject":       "physics",
        "syllabus_code": "0625",
    }
    if len(parts) >= 1:
        bl = parts[0].split("_")
        if len(bl) >= 2:
            result["board"] = bl[0]
            result["level"] = "_".join(bl[1:])
    if len(parts) >= 2:
        m = re.match(r'^([a-z_]+?)_(\d{4})$', parts[1])
        if m:
            result["subject"]       = m.group(1)
            result["syllabus_code"] = m.group(2)
    return result


# ===========================================================================
# Source-file info extraction (metadata only, no raw_text)
# ===========================================================================

def extract_mcq_info(source_file: Path) -> tuple[int, int, str]:
    """Returns (question_count, total_marks, error). total_marks = question_count for MCQ."""
    data, err = load_json(source_file)
    if err:
        return 0, 0, err
    if not isinstance(data, dict):
        return 0, 0, "Unexpected JSON format (not a dict)"
    q_count = data.get("total_questions") or len(data.get("questions", []))
    return q_count, q_count, ""   # MCQ: 1 mark per question


def extract_structured_info(source_file: Path) -> tuple[int, int, str]:
    """Returns (question_count, total_marks, error)."""
    data, err = load_json(source_file)
    if err:
        return 0, 0, err
    if not isinstance(data, dict):
        return 0, 0, "Unexpected JSON format (not a dict)"
    q_count = data.get("question_count", 0)
    marks   = data.get("total_marks", 0)
    return q_count, marks, ""


# ===========================================================================
# Corpus entry builder
# ===========================================================================

def build_corpus_entry(pair: dict) -> dict:
    pair_id        = pair["pair_id"]
    component_type = pair.get("component_type", "")
    route          = pair.get("route", "")
    source_type    = SOURCE_TYPE_MAP.get(component_type, "unknown_source")
    meta           = parse_pair_id(pair_id)

    # Determine which output file to index
    if component_type == "mcq":
        source_file_str = pair.get("questions_reconciled", "")
    else:
        source_file_str = pair.get("structured_paper_dataset", "")

    source_file = Path(source_file_str) if source_file_str else None

    # Verify file and extract counts
    entry_status   = "indexed"
    question_count = 0
    total_marks    = 0
    error_detail   = ""

    if not source_file_str:
        entry_status = "missing_source_file"
        error_detail = "No source file path in batch report"
    elif not source_file.exists():
        entry_status = "missing_source_file"
        error_detail = f"File not found: {source_file}"
    else:
        if component_type == "mcq":
            question_count, total_marks, err = extract_mcq_info(source_file)
        else:
            question_count, total_marks, err = extract_structured_info(source_file)

        if err:
            entry_status = "read_failed"
            error_detail = err
        elif question_count == 0:
            entry_status = "needs_human_review"

    entry = {
        "source_id":      pair_id,
        "pair_id":        pair_id,
        "component_type": component_type,
        "paper_code":     meta.get("paper_code", ""),
        "year":           meta.get("year", 0),
        "series_code":    meta.get("series_code", ""),
        "route":          route,
        "source_type":    source_type,
        "source_file":    source_file_str,
        "question_count": question_count,
        "total_marks":    total_marks,
        "status":         entry_status,
    }
    if error_detail:
        entry["error"] = error_detail
    return entry


# ===========================================================================
# Top-level builders
# ===========================================================================

def build_corpus(batch_report: dict, meta: dict) -> dict:
    passed_pairs = [
        p for p in batch_report.get("pairs", [])
        if p.get("status") == "passed"
    ]

    sources = [build_corpus_entry(p) for p in passed_pairs]

    # Aggregate summary
    comp_type_counts: dict[str, int] = {}
    route_counts:     dict[str, int] = {}
    total_questions   = 0
    total_marks       = 0

    for src in sources:
        ct = src["component_type"]
        rt = src["route"]
        comp_type_counts[ct] = comp_type_counts.get(ct, 0) + 1
        route_counts[rt]     = route_counts.get(rt, 0) + 1
        if src["status"] in ("indexed", "needs_human_review"):
            total_questions += src["question_count"]
            total_marks     += src["total_marks"]

    corpus_id = (
        f"{meta['board']}_{meta['level']}_{meta['subject']}_"
        f"{meta['syllabus_code']}_unified_source_corpus_v0"
    )

    return {
        "corpus_id":        corpus_id,
        "version":          "0.1.0",
        "status":           "internal_source_only",
        "created_at":       datetime.now(timezone.utc).isoformat(),
        "copyright_status": "internal_reference_only_not_publishable",
        "board":            meta["board"],
        "level":            meta["level"],
        "subject":          meta["subject"],
        "syllabus_code":    meta["syllabus_code"],
        "source_count":     len(sources),
        "sources":          sources,
        "summary": {
            "component_types": comp_type_counts,
            "routes":          route_counts,
            "total_sources":   len(sources),
            "total_questions": total_questions,
            "total_marks":     total_marks,
        },
    }


def build_report(corpus: dict, out_files: dict) -> dict:
    sources      = corpus["sources"]
    indexed      = sum(1 for s in sources if s["status"] == "indexed")
    missing      = sum(1 for s in sources if s["status"] == "missing_source_file")
    read_failed  = sum(1 for s in sources if s["status"] == "read_failed")
    needs_review = sum(1 for s in sources if s["status"] == "needs_human_review")

    status = "passed"
    if missing > 0 or read_failed > 0 or needs_review > 0:
        status = "needs_review"

    return {
        "status":               status,
        "corpus_id":            corpus["corpus_id"],
        "source_count":         corpus["source_count"],
        "indexed_source_count": indexed,
        "missing_source_count": missing,
        "read_failed_count":    read_failed,
        "needs_review_count":   needs_review,
        "component_types":      corpus["summary"]["component_types"],
        "routes":               corpus["summary"]["routes"],
        "total_questions":      corpus["summary"]["total_questions"],
        "total_marks":          corpus["summary"]["total_marks"],
        "output_files":         out_files,
    }


def build_manifest_md(corpus: dict, report: dict) -> str:
    lines = []
    lines.append("# Quanta Aptus Unified Source Corpus v0")
    lines.append("")
    lines.append(f"- **Board:** {corpus['board'].title()}")
    lines.append(f"- **Level:** {corpus['level'].upper()}")
    lines.append(f"- **Subject:** {corpus['subject'].title()}")
    lines.append(f"- **Syllabus:** {corpus['syllabus_code']}")
    lines.append(f"- **Corpus ID:** `{corpus['corpus_id']}`")
    lines.append(f"- **Status:** {corpus['status']}")
    lines.append(f"- **Copyright:** {corpus['copyright_status']}")
    lines.append(f"- **Created:** {corpus['created_at']}")
    lines.append("")
    lines.append(f"- **Source count:** {corpus['source_count']}")
    lines.append(f"- **Indexed:** {report['indexed_source_count']}")
    if report["missing_source_count"]:
        lines.append(f"- **Missing source files:** {report['missing_source_count']}")
    if report["read_failed_count"]:
        lines.append(f"- **Read failed:** {report['read_failed_count']}")
    if report["needs_review_count"]:
        lines.append(f"- **Needs human review:** {report['needs_review_count']}")
    lines.append("")
    lines.append("## Component Routes")
    lines.append("")
    for src in corpus["sources"]:
        label = ROUTE_LABELS.get(src["route"], src["route"])
        lines.append(
            f"- **{label}** - paper `{src['paper_code']}` "
            f"({src['question_count']} questions, {src['total_marks']} marks) "
            f"[{src['status']}]"
        )
    lines.append("")
    lines.append(f"- **Total questions:** {corpus['summary']['total_questions']}")
    lines.append(f"- **Total marks:** {corpus['summary']['total_marks']}")
    lines.append("")
    lines.append("## Output Paths")
    lines.append("")
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "> This corpus indexes internal source papers only.  \n"
        "> It is used to derive skills, patterns, and original Quanta Aptus resources.  \n"
        "> It must not be published as Cambridge content."
    )
    lines.append("")
    return "\n".join(lines)


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build Quanta Aptus Unified Source Corpus."
    )
    ap.add_argument("batch_report", help="Path to batch_paper_pipeline_report.json")
    args = ap.parse_args()

    report_path = Path(args.batch_report)
    if not report_path.exists():
        sys.exit(f"Error: file not found: {report_path}")

    batch_report, err = load_json(report_path)
    if err:
        sys.exit(f"Error reading batch report: {err}")

    # Derive sub-path from pairs_file in the batch report
    # e.g. data/intake/cambridge_igcse/physics_0625/raw_document_pairs_v0.json
    pairs_file = Path(batch_report.get("pairs_file", ""))
    intake_idx = next(
        (i for i, p in enumerate(pairs_file.parts) if p == "intake"),
        None,
    )
    if intake_idx is not None:
        sub_parts = pairs_file.parts[intake_idx + 1: -1]   # ("cambridge_igcse", "physics_0625")
    else:
        # Fallback: derive from report_path
        intake_idx2 = next(
            (i for i, p in enumerate(report_path.parts) if p == "intake"),
            None,
        )
        sub_parts = (
            report_path.parts[intake_idx2 + 1: -1]
            if intake_idx2 is not None else ()
        )

    meta    = parse_sub_path(sub_parts)
    sub_dir = Path(*sub_parts) if sub_parts else Path("unknown")
    out_dir = PROJECT_ROOT / "data" / "bank" / sub_dir / "source_corpus"
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus_path   = out_dir / "unified_source_corpus_v0.json"
    rep_path      = out_dir / "unified_source_corpus_report.json"
    manifest_path = out_dir / "unified_source_corpus_manifest.md"

    out_files = {
        "corpus":   str(corpus_path),
        "report":   str(rep_path),
        "manifest": str(manifest_path),
    }

    corpus   = build_corpus(batch_report, meta)
    report   = build_report(corpus, out_files)
    manifest = build_manifest_md(corpus, report)

    corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=False), encoding="utf-8")
    rep_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(manifest, encoding="utf-8")

    # Terminal output
    print(f"status               : {report['status']}")
    print(f"corpus_id            : {corpus['corpus_id']}")
    print(f"source_count         : {report['source_count']}")
    print(f"indexed_source_count : {report['indexed_source_count']}")
    print(f"component_types      : {report['component_types']}")
    print(f"routes               : {report['routes']}")
    print(f"total_questions      : {report['total_questions']}")
    print(f"total_marks          : {report['total_marks']}")
    print(f"corpus               : {corpus_path}")
    print(f"report               : {rep_path}")
    print(f"manifest             : {manifest_path}")


if __name__ == "__main__":
    main()
