"""
Scan raw PDF folder and build document inventory + pair manifest.

Usage:
    python tools/ingest/build_raw_document_intake.py <raw_pdf_folder>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_raw_document_intake.py \
        data/raw/cambridge_igcse/physics_0625
"""

import sys
import re
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Cambridge short filename: 0625_s25_qp_21.pdf
PATTERN = re.compile(
    r'^(\d{4})_([swm])(\d{2})_(qp|ms)_(\d+)\.pdf$',
    re.IGNORECASE,
)

SERIES_NAMES = {
    's': 'May/June',
    'w': 'October/November',
    'm': 'February/March',
}

DOC_TYPES = {
    'qp': 'question_paper',
    'ms': 'mark_scheme',
}


# ---------------------------------------------------------------------------
# Folder metadata extraction
# ---------------------------------------------------------------------------

def extract_folder_metadata(input_dir):
    """
    Derive board/level/subject/syllabus_code from folder hierarchy.
    Expects: .../<board>_<level>/<subject>_<syllabus_code>/
    """
    try:
        level_board = input_dir.parent.name        # e.g. "cambridge_igcse"
        board, level = level_board.rsplit("_", 1)  # "cambridge", "igcse"
        subj_syl = input_dir.name                  # e.g. "physics_0625"
        subject, syllabus_code = subj_syl.rsplit("_", 1)
        return board, level, subject, syllabus_code
    except Exception:
        return "cambridge", "igcse", "physics", "0625"


# ---------------------------------------------------------------------------
# Document parser
# ---------------------------------------------------------------------------

def parse_document(pdf_path, board, level, subject, syllabus_code):
    filename = pdf_path.name
    m = PATTERN.match(filename)

    if not m:
        return {
            "filename": filename,
            "path":     str(pdf_path),
            "status":   "unrecognized",
            "reason":   "filename does not match Cambridge short filename pattern",
        }

    series_code    = m.group(2).lower()
    year_2         = m.group(3)
    doc_type_code  = m.group(4).lower()
    paper_code     = m.group(5)

    year         = 2000 + int(year_2)
    series_name  = SERIES_NAMES[series_code]
    doc_type     = DOC_TYPES[doc_type_code]
    paper_number = paper_code[0] if paper_code else ""
    variant      = paper_code[1] if len(paper_code) > 1 else ""

    document_id = (
        f"{board}_{level}_{subject}_{syllabus_code}"
        f"_{year}_{series_code}_p{paper_code}_{doc_type_code}"
    )

    return {
        "document_id":       document_id,
        "filename":          filename,
        "path":              str(pdf_path),
        "board":             board,
        "level":             level,
        "subject":           subject,
        "syllabus_code":     syllabus_code,
        "series_code":       series_code,
        "series_name":       series_name,
        "year":              year,
        "document_type":     doc_type,
        "document_type_code": doc_type_code,
        "paper_code":        paper_code,
        "paper_number":      paper_number,
        "variant":           variant,
        "status":            "recognized",
    }


# ---------------------------------------------------------------------------
# Pair builder
# ---------------------------------------------------------------------------

def doc_ref(doc):
    return {
        "document_id": doc["document_id"],
        "filename":    doc["filename"],
        "path":        doc["path"],
    }


def build_pairs(recognized_docs, board, level, subject, syllabus_code):
    groups = defaultdict(lambda: {"qp": [], "ms": []})
    for doc in recognized_docs:
        key = (doc["year"], doc["series_code"], doc["paper_code"])
        groups[key][doc["document_type_code"]].append(doc)

    pairs = []
    for (year, series_code, paper_code), slots in sorted(groups.items()):
        qps = slots["qp"]
        mss = slots["ms"]
        series_name  = SERIES_NAMES[series_code]
        paper_number = paper_code[0] if paper_code else ""
        variant      = paper_code[1] if len(paper_code) > 1 else ""
        pair_id      = (
            f"{board}_{level}_{subject}_{syllabus_code}"
            f"_{year}_{series_code}_p{paper_code}"
        )

        pair = {
            "pair_id":      pair_id,
            "board":        board,
            "level":        level,
            "subject":      subject,
            "syllabus_code": syllabus_code,
            "year":         year,
            "series_code":  series_code,
            "series_name":  series_name,
            "paper_code":   paper_code,
            "paper_number": paper_number,
            "variant":      variant,
        }

        if len(qps) > 1 or len(mss) > 1:
            pair["pair_status"] = "duplicate_documents"
            pair["duplicates"]  = {
                "question_papers": [d["filename"] for d in qps],
                "mark_schemes":    [d["filename"] for d in mss],
            }
            pair["question_paper"] = doc_ref(qps[0]) if qps else None
            pair["mark_scheme"]    = doc_ref(mss[0]) if mss else None
        elif qps and mss:
            pair["pair_status"]    = "complete"
            pair["question_paper"] = doc_ref(qps[0])
            pair["mark_scheme"]    = doc_ref(mss[0])
        elif qps and not mss:
            pair["pair_status"]    = "missing_mark_scheme"
            pair["question_paper"] = doc_ref(qps[0])
            pair["mark_scheme"]    = None
        else:
            pair["pair_status"]    = "missing_question_paper"
            pair["question_paper"] = None
            pair["mark_scheme"]    = doc_ref(mss[0]) if mss else None

        pairs.append(pair)

    return pairs


# ---------------------------------------------------------------------------
# Stats aggregation
# ---------------------------------------------------------------------------

def aggregate_stats(recognized_docs):
    years, series, paper_codes, doc_types = (
        defaultdict(int), defaultdict(int),
        defaultdict(int), defaultdict(int),
    )
    for doc in recognized_docs:
        years[str(doc["year"])] += 1
        series[doc["series_name"]] += 1
        paper_codes[doc["paper_code"]] += 1
        doc_types[doc["document_type"]] += 1
    return (
        dict(years),
        dict(series),
        dict(paper_codes),
        dict(doc_types),
    )


# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------

def build_inventory(documents, input_dir, board, level, subject, syllabus_code):
    inv_id = f"{board}_{level}_{subject}_{syllabus_code}_raw_document_inventory_v0"
    recognized   = sum(1 for d in documents if d.get("status") == "recognized")
    unrecognized = len(documents) - recognized
    return {
        "inventory_id":      inv_id,
        "version":           "0.1.0",
        "created_at":        datetime.now(timezone.utc).isoformat(),
        "input_folder":      str(input_dir),
        "board":             board,
        "level":             level,
        "subject":           subject,
        "syllabus_code":     syllabus_code,
        "document_count":    len(documents),
        "recognized_count":  recognized,
        "unrecognized_count": unrecognized,
        "documents":         documents,
    }


def build_pairs_json(pairs, input_dir, board, level, subject, syllabus_code):
    pairs_id = f"{board}_{level}_{subject}_{syllabus_code}_raw_document_pairs_v0"
    complete   = sum(1 for p in pairs if p["pair_status"] == "complete")
    incomplete = sum(
        1 for p in pairs
        if p["pair_status"] in ("missing_question_paper", "missing_mark_scheme")
    )
    duplicate  = sum(1 for p in pairs if p["pair_status"] == "duplicate_documents")
    return {
        "pairs_id":             pairs_id,
        "version":              "0.1.0",
        "created_at":           datetime.now(timezone.utc).isoformat(),
        "input_folder":         str(input_dir),
        "complete_pair_count":  complete,
        "incomplete_pair_count": incomplete,
        "duplicate_pair_count": duplicate,
        "pairs":                pairs,
    }


def build_report(inv, pairs_json, years, series, paper_codes, doc_types, out_files):
    status = (
        "warning_no_pdf_found"
        if inv["document_count"] == 0
        else "passed"
    )
    return {
        "status":               status,
        "input_folder":         inv["input_folder"],
        "document_count":       inv["document_count"],
        "recognized_count":     inv["recognized_count"],
        "unrecognized_count":   inv["unrecognized_count"],
        "complete_pair_count":  pairs_json["complete_pair_count"],
        "incomplete_pair_count": pairs_json["incomplete_pair_count"],
        "duplicate_pair_count": pairs_json["duplicate_pair_count"],
        "years":                years,
        "series":               series,
        "paper_codes":          paper_codes,
        "document_types":       doc_types,
        "output_files":         out_files,
    }


def build_manifest_md(report):
    lines = []
    lines.append("# Quanta Aptus Raw Document Intake v0")
    lines.append("")
    lines.append(f"**Input folder:** `{report['input_folder']}`")
    lines.append(f"**Status:** {report['status']}")
    lines.append("")
    lines.append("## Document Counts")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| ------ | ----: |")
    lines.append(f"| Total PDFs | {report['document_count']} |")
    lines.append(f"| Recognized | {report['recognized_count']} |")
    lines.append(f"| Unrecognized | {report['unrecognized_count']} |")
    lines.append(f"| Complete pairs | {report['complete_pair_count']} |")
    lines.append(f"| Incomplete pairs | {report['incomplete_pair_count']} |")
    lines.append(f"| Duplicate pairs | {report['duplicate_pair_count']} |")
    lines.append("")

    def kv_table(title, d):
        if not d:
            return
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Value | Count |")
        lines.append("| ----- | ----: |")
        for k, v in sorted(d.items()):
            lines.append(f"| {k} | {v} |")
        lines.append("")

    kv_table("Years Detected", report["years"])
    kv_table("Series Detected", report["series"])
    kv_table("Paper Codes Detected", report["paper_codes"])

    lines.append("## Output Paths")
    lines.append("")
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "> This intake layer only indexes raw documents. "
        "It does not publish copyrighted source content."
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(input_dir):
    board, level, subject, syllabus_code = extract_folder_metadata(input_dir)

    pdf_paths = sorted(input_dir.glob("*.pdf"))
    documents = [
        parse_document(p, board, level, subject, syllabus_code)
        for p in pdf_paths
    ]

    recognized_docs = [d for d in documents if d.get("status") == "recognized"]
    pairs           = build_pairs(recognized_docs, board, level, subject, syllabus_code)
    years, series, paper_codes, doc_types = aggregate_stats(recognized_docs)

    inv        = build_inventory(documents, input_dir, board, level, subject, syllabus_code)
    pairs_json = build_pairs_json(pairs, input_dir, board, level, subject, syllabus_code)

    out_dir = Path("data") / "intake" / input_dir.parent.name / input_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    inv_path      = out_dir / "raw_document_inventory_v0.json"
    pairs_path    = out_dir / "raw_document_pairs_v0.json"
    report_path   = out_dir / "raw_document_intake_report.json"
    manifest_path = out_dir / "raw_document_intake_manifest.md"

    out_files = {
        "inventory": str(inv_path),
        "pairs":     str(pairs_path),
        "report":    str(report_path),
        "manifest":  str(manifest_path),
    }

    report   = build_report(inv, pairs_json, years, series, paper_codes, doc_types, out_files)
    manifest = build_manifest_md(report)

    inv_path.write_text(
        json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    pairs_path.write_text(
        json.dumps(pairs_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    manifest_path.write_text(manifest, encoding="utf-8")

    print(f"status                 : {report['status']}")
    print(f"input_folder           : {report['input_folder']}")
    print(f"document_count         : {report['document_count']}")
    print(f"recognized_count       : {report['recognized_count']}")
    print(f"unrecognized_count     : {report['unrecognized_count']}")
    print(f"complete_pair_count    : {report['complete_pair_count']}")
    print(f"incomplete_pair_count  : {report['incomplete_pair_count']}")
    print(f"duplicate_pair_count   : {report['duplicate_pair_count']}")
    print(f"inventory              : {inv_path}")
    print(f"pairs                  : {pairs_path}")
    print(f"report                 : {report_path}")
    print(f"manifest               : {manifest_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <raw_pdf_folder>")
    p = Path(sys.argv[1])
    if not p.is_dir():
        sys.exit(f"Error: not a directory: {p}")
    run(p)
