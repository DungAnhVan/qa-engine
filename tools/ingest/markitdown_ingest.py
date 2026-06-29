"""
Ingest a Cambridge past-paper PDF using markitdown.

Usage:
    python tools/ingest/markitdown_ingest.py <path-to-pdf>

Example:
    python tools/ingest/markitdown_ingest.py data/raw/cambridge_igcse/physics_0625/0625_s25_qp_21.pdf
"""

import sys
import re
import json
import hashlib
import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Metadata inference
# ---------------------------------------------------------------------------

SEASON_MAP = {
    "s": {"code": "s", "name": "summer", "session": "May-June"},
    "w": {"code": "w", "name": "winter", "session": "October-November"},
    "m": {"code": "m", "name": "march",  "session": "February-March"},
}

DOC_TYPE_MAP = {
    "qp":  "question_paper",
    "ms":  "mark_scheme",
    "gt":  "grade_thresholds",
    "er":  "examiner_report",
    "in":  "insert",
    "ci":  "confidential_instructions",
}

BOARD_MAP = {
    "cambridge_igcse": ("cambridge", "igcse"),
    "cambridge_alevel": ("cambridge", "alevel"),
    "cambridge_olevel": ("cambridge", "olevel"),
}

SUBJECT_FOLDER_RE = re.compile(r"^([a-z_]+?)_(\d{4})$")
FILENAME_RE = re.compile(
    r"^(\d{4})_([smw])(\d{2})_([a-z]+)_(\d{1,2})\.pdf$", re.IGNORECASE
)


def infer_metadata(pdf_path: Path) -> dict:
    """Derive all metadata from folder hierarchy and filename."""
    parts = pdf_path.parts  # e.g. [..., 'cambridge_igcse', 'physics_0625', '0625_s25_qp_21.pdf']

    # --- board / level from grandparent folder ---
    grandparent = pdf_path.parent.parent.name.lower()
    board, level = BOARD_MAP.get(grandparent, ("unknown", "unknown"))

    # --- subject / syllabus_code from parent folder ---
    parent_name = pdf_path.parent.name.lower()
    m = SUBJECT_FOLDER_RE.match(parent_name)
    if m:
        subject = m.group(1).replace("_", " ")
        syllabus_code = m.group(2)
    else:
        subject = parent_name
        syllabus_code = "unknown"

    # --- filename parts ---
    stem = pdf_path.name.lower()
    fm = FILENAME_RE.match(stem)
    if not fm:
        raise ValueError(f"Filename '{pdf_path.name}' does not match expected pattern SSSS_Syy_TYPE_NN.pdf")

    fn_syllabus  = fm.group(1)
    season_code  = fm.group(2).lower()
    year_short   = fm.group(3)
    doc_type_raw = fm.group(4).lower()
    component    = fm.group(5)   # e.g. "21"

    year = int("20" + year_short) if int(year_short) <= 99 else int(year_short)

    season_info = SEASON_MAP.get(season_code, {"code": season_code, "name": season_code, "session": season_code})
    doc_type    = DOC_TYPE_MAP.get(doc_type_raw, doc_type_raw)

    # component "21" => paper_number=2, variant=1, paper_label="p21"
    paper_number = int(component[0]) if component else 0
    variant      = int(component[1]) if len(component) > 1 else 0
    paper_label  = f"p{component}"

    return {
        "board":          board,
        "level":          level,
        "subject":        subject,
        "syllabus_code":  syllabus_code,
        "year":           year,
        "season_code":    season_code,
        "season_name":    season_info["name"],
        "session":        season_info["session"],
        "doc_type":       doc_type,
        "doc_type_raw":   doc_type_raw,
        "component":      component,
        "paper_number":   paper_number,
        "variant":        variant,
        "paper_label":    paper_label,
    }


def build_output_dir_name(meta: dict) -> str:
    """Construct deterministic output folder name from metadata."""
    return (
        f"{meta['board']}_{meta['level']}"
        f"_{meta['subject'].replace(' ', '_')}"
        f"_{meta['syllabus_code']}"
        f"_{meta['year']}"
        f"_{meta['season_code']}"
        f"_{meta['paper_label']}"
        f"_{meta['doc_type_raw']}"
    )


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

JUNK_PATTERNS = [
    re.compile(r"^\s*UCLES\b.*$",           re.IGNORECASE),
    re.compile(r"^\s*©\s*UCLES\b.*$",       re.IGNORECASE),
    re.compile(r"^\s*Turn over\s*\.?\s*$",  re.IGNORECASE),
    re.compile(r"^\s*BLANK PAGE\s*\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*Page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*\[Turn over\]\s*$",    re.IGNORECASE),
    re.compile(r"^\s*\*+\s*$"),              # lines of asterisks only
]


def is_junk_line(line: str) -> bool:
    return any(p.match(line) for p in JUNK_PATTERNS)


def clean_markdown(raw: str) -> str:
    """Mechanical cleaning only — no semantic changes."""
    lines = raw.splitlines()
    kept = []
    for line in lines:
        if is_junk_line(line):
            continue
        kept.append(line)

    # Collapse runs of more than 2 consecutive blank lines into 2
    result = []
    blank_run = 0
    for line in kept:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                result.append(line)
        else:
            blank_run = 0
            result.append(line)

    # Strip leading / trailing whitespace from the whole document
    text = "\n".join(result).strip()
    return text + "\n"


# ---------------------------------------------------------------------------
# Quality report
# ---------------------------------------------------------------------------

def build_quality_report(raw: str, clean: str, meta: dict) -> dict:
    raw_lines   = raw.splitlines()
    clean_lines = clean.splitlines()

    raw_chars   = len(raw)
    clean_chars = len(clean)
    removed     = raw_chars - clean_chars
    ratio       = round(clean_chars / raw_chars, 4) if raw_chars else 0.0

    # Count likely question markers: lines starting with a number + dot/space
    question_markers = [l for l in clean_lines if re.match(r"^\s*\d+[\.\)]\s", l)]

    return {
        "raw_line_count":   len(raw_lines),
        "clean_line_count": len(clean_lines),
        "raw_char_count":   raw_chars,
        "clean_char_count": clean_chars,
        "chars_removed":    removed,
        "clean_ratio":      ratio,
        "question_markers_found": len(question_markers),
        "warnings": [] if ratio > 0.5 else ["clean_ratio below 0.5 — check raw output"],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(pdf_path_arg: str):
    pdf_path = Path(pdf_path_arg).resolve()
    if not pdf_path.exists():
        sys.exit(f"Error: file not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        sys.exit(f"Error: expected a .pdf file, got: {pdf_path.name}")

    # 1. Infer metadata
    print(f"[1/5] Inferring metadata from path ...")
    meta = infer_metadata(pdf_path)

    # 2. Hash
    print(f"[2/5] Computing SHA-256 ...")
    sha256 = sha256_file(pdf_path)

    # 3. Convert with markitdown
    print(f"[3/5] Converting PDF with markitdown ...")
    try:
        from markitdown import MarkItDown
    except ImportError:
        sys.exit("Error: markitdown is not installed. Run: pip install markitdown")

    md_converter = MarkItDown()
    result = md_converter.convert(str(pdf_path))
    raw_md = result.text_content

    # 4. Clean
    print(f"[4/5] Cleaning markdown ...")
    clean_md = clean_markdown(raw_md)

    # 5. Write outputs
    project_root = Path(__file__).resolve().parents[2]  # tools/ingest/ -> project root
    out_dir_name = build_output_dir_name(meta)
    out_dir = project_root / "data" / "ingested" / "markitdown" / out_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    manifest = {
        "schema_version":   "1.0",
        "ingested_at":      now_iso,
        "tool":             "markitdown",
        "tool_version":     _get_markitdown_version(),
        "source_file":      pdf_path.name,
        "source_path":      str(pdf_path),
        "sha256":           sha256,
        "file_size_bytes":  pdf_path.stat().st_size,
        "output_dir":       str(out_dir),
        "metadata":         meta,
    }

    quality = build_quality_report(raw_md, clean_md, meta)

    raw_file      = out_dir / "raw.md"
    clean_file    = out_dir / "clean.md"
    manifest_file = out_dir / "manifest.json"
    quality_file  = out_dir / "quality_report.json"

    raw_file.write_text(raw_md,   encoding="utf-8")
    clean_file.write_text(clean_md, encoding="utf-8")
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    quality_file.write_text(json.dumps(quality,  indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n[5/5] Done. Output files:")
    print(f"  {raw_file}")
    print(f"  {clean_file}")
    print(f"  {manifest_file}")
    print(f"  {quality_file}")


def _get_markitdown_version() -> str:
    try:
        from importlib.metadata import version
        return version("markitdown")
    except Exception:
        return "unknown"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <path-to-pdf>")
    main(sys.argv[1])
