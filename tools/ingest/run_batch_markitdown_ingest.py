"""
Batch MarkItDown ingest for all complete pairs in raw_document_pairs_v0.json.

Usage:
    python tools/ingest/run_batch_markitdown_ingest.py <raw_document_pairs_v0.json> [--skip-existing]

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/run_batch_markitdown_ingest.py \
        data/intake/cambridge_igcse/physics_0625/raw_document_pairs_v0.json
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path

INGEST_SCRIPT = Path(__file__).parent / "markitdown_ingest.py"
PROJECT_ROOT  = Path(__file__).resolve().parents[2]
INGESTED_BASE = PROJECT_ROOT / "data" / "ingested" / "markitdown"


# ---------------------------------------------------------------------------
# Output path prediction (mirrors build_output_dir_name in markitdown_ingest.py)
# ---------------------------------------------------------------------------

def predict_output_dir(document_id: str) -> Path:
    return INGESTED_BASE / document_id


# ---------------------------------------------------------------------------
# Single document ingest
# ---------------------------------------------------------------------------

def ingest_document(pdf_path: str, document_id: str, doc_type: str, skip_existing: bool) -> dict:
    out_dir        = predict_output_dir(document_id)
    manifest_path  = out_dir / "manifest.json"
    raw_md_path    = out_dir / "raw.md"
    clean_md_path  = out_dir / "clean.md"
    quality_path   = out_dir / "quality_report.json"

    if skip_existing and manifest_path.exists():
        return {
            "document_id":    document_id,
            "document_type":  doc_type,
            "source_pdf":     pdf_path,
            "ingest_status":  "skipped_existing",
            "output_folder":  str(out_dir),
            "raw_md":         str(raw_md_path),
            "clean_md":       str(clean_md_path),
            "manifest":       str(manifest_path),
            "quality_report": str(quality_path),
        }

    result = subprocess.run(
        [sys.executable, str(INGEST_SCRIPT), pdf_path],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or "").strip()
        return {
            "document_id":   document_id,
            "document_type": doc_type,
            "source_pdf":    pdf_path,
            "ingest_status": "failed",
            "error":         error_msg,
            "return_code":   result.returncode,
        }

    return {
        "document_id":    document_id,
        "document_type":  doc_type,
        "source_pdf":     pdf_path,
        "ingest_status":  "passed",
        "output_folder":  str(out_dir),
        "raw_md":         str(raw_md_path),
        "clean_md":       str(clean_md_path),
        "manifest":       str(manifest_path),
        "quality_report": str(quality_path),
    }


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def run_batch(pairs_data: dict, skip_existing: bool) -> list:
    batch_results = []

    for pair in pairs_data.get("pairs", []):
        if pair.get("pair_status") != "complete":
            continue

        qp = pair["question_paper"]
        ms = pair["mark_scheme"]

        qp_doc_id = qp["document_id"]
        ms_doc_id = ms["document_id"]

        print(f"\n  Processing pair: {pair['pair_id']}")
        print(f"    QP: {qp['filename']}")
        qp_result = ingest_document(qp["path"], qp_doc_id, "question_paper", skip_existing)
        print(f"    QP status: {qp_result['ingest_status']}")

        print(f"    MS: {ms['filename']}")
        ms_result = ingest_document(ms["path"], ms_doc_id, "mark_scheme", skip_existing)
        print(f"    MS status: {ms_result['ingest_status']}")

        batch_results.append({
            "pair_id":                    pair["pair_id"],
            "pair_status":                "complete",
            "question_paper_document_id": qp_doc_id,
            "mark_scheme_document_id":    ms_doc_id,
            "documents":                  [qp_result, ms_result],
        })

    return batch_results


# ---------------------------------------------------------------------------
# Report and manifest builders
# ---------------------------------------------------------------------------

def build_report(pairs_data, pairs_file, batch_results, out_files):
    complete_pair_count   = sum(1 for p in pairs_data.get("pairs", []) if p.get("pair_status") == "complete")
    processed_pair_count  = len(batch_results)

    all_docs = [doc for pair in batch_results for doc in pair["documents"]]
    doc_task_count        = len(all_docs)
    passed_count          = sum(1 for d in all_docs if d["ingest_status"] == "passed")
    failed_count          = sum(1 for d in all_docs if d["ingest_status"] == "failed")
    skipped_count         = sum(1 for d in all_docs if d["ingest_status"] == "skipped_existing")

    if doc_task_count == 0:
        status = "warning_no_complete_pairs"
    elif failed_count > 0:
        status = "failed"
    else:
        status = "passed"

    return {
        "status":                  status,
        "pairs_file":              str(pairs_file),
        "complete_pair_count":     complete_pair_count,
        "processed_pair_count":    processed_pair_count,
        "document_task_count":     doc_task_count,
        "passed_count":            passed_count,
        "failed_count":            failed_count,
        "skipped_existing_count":  skipped_count,
        "pairs":                   batch_results,
        "output_files":            out_files,
    }


def build_manifest_md(report):
    lines = []
    lines.append("# Quanta Aptus Batch MarkItDown Ingest")
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
    lines.append(f"| Document tasks | {report['document_task_count']} |")
    lines.append(f"| Passed | {report['passed_count']} |")
    lines.append(f"| Failed | {report['failed_count']} |")
    lines.append(f"| Skipped (existing) | {report['skipped_existing_count']} |")
    lines.append("")

    if report["pairs"]:
        lines.append("## Processed Pairs")
        lines.append("")
        for pr in report["pairs"]:
            lines.append(f"### {pr['pair_id']}")
            lines.append("")
            for doc in pr["documents"]:
                mark = "✓" if doc["ingest_status"] == "passed" else (
                    "↷" if doc["ingest_status"] == "skipped_existing" else "✗"
                )
                lines.append(f"- {mark} `{doc['document_id']}` ({doc['document_type']}) — **{doc['ingest_status']}**")
                if doc["ingest_status"] == "failed":
                    lines.append(f"  - Error: `{doc.get('error','')}`")
            lines.append("")

    lines.append("## Output Paths")
    lines.append("")
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "> This step converts raw PDFs into internal markdown only. "
        "It does not publish source content."
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Batch MarkItDown ingest for all complete pairs."
    )
    parser.add_argument("pairs_file", help="Path to raw_document_pairs_v0.json")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip documents whose manifest.json already exists",
    )
    args = parser.parse_args()

    pairs_path = Path(args.pairs_file)
    if not pairs_path.exists():
        sys.exit(f"Error: file not found: {pairs_path}")

    pairs_data = json.loads(pairs_path.read_text(encoding="utf-8"))

    print(f"Batch MarkItDown Ingest")
    print(f"  pairs_file   : {pairs_path}")
    print(f"  skip_existing: {args.skip_existing}")

    batch_results = run_batch(pairs_data, skip_existing=args.skip_existing)

    out_dir = pairs_path.parent
    report_path   = out_dir / "batch_markitdown_ingest_report.json"
    manifest_path = out_dir / "batch_markitdown_ingest_manifest.md"

    out_files = {
        "report":   str(report_path),
        "manifest": str(manifest_path),
    }

    report   = build_report(pairs_data, pairs_path, batch_results, out_files)
    manifest = build_manifest_md(report)

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(manifest, encoding="utf-8")

    print(f"\nstatus                 : {report['status']}")
    print(f"pairs_file             : {report['pairs_file']}")
    print(f"complete_pair_count    : {report['complete_pair_count']}")
    print(f"processed_pair_count   : {report['processed_pair_count']}")
    print(f"document_task_count    : {report['document_task_count']}")
    print(f"passed_count           : {report['passed_count']}")
    print(f"failed_count           : {report['failed_count']}")
    print(f"skipped_existing_count : {report['skipped_existing_count']}")
    print(f"report                 : {report_path}")
    print(f"manifest               : {manifest_path}")


if __name__ == "__main__":
    main()
