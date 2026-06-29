"""
Parse a Cambridge structured (non-MCQ) mark scheme into a skeleton of mark-scheme
items.  Best-effort — always exits 0; status field carries confidence level.

Supported mark codes:
  Theory (Paper 3/4)  : B1, B2, C1, C2, A1, A2, A3, M1, M2
  Practical (Paper 5/6): MP1 … MP7

Usage:
    python parse_structured_mark_scheme.py <clean.md> [--paper-code CODE]

Output (in same folder as clean.md):
    structured_mark_scheme.json
    structured_mark_scheme_report.json
"""

import sys
import re
import json
import argparse
from pathlib import Path

# Mark-code patterns
MARK_CODE_RE  = re.compile(r'\b(MP\d|B\d|C\d|A\d|M\d)\b')
TRAILING_INT  = re.compile(r'\b(\d+)\s*$')
BRACKETS_INT  = re.compile(r'\[(\d+)\]')

# Question-part header patterns (ordered most-specific first)
# Group 1: full header string for display
PART_PATTERNS = [
    # "1(a)(i)", "1 (a)(i)", "1(b)(iii)"
    re.compile(r'^(\d{1,2}\s*\([a-z]\)\s*\([ivx]+\))', re.IGNORECASE),
    # "1(a)", "1 (a)"
    re.compile(r'^(\d{1,2}\s*\([a-z]\))', re.IGNORECASE),
    # "4 MP1", "4MP1", "MP1" (practical mark points)
    re.compile(r'^(\d{0,2}\s*MP\d+)', re.IGNORECASE),
    # Bare question number "1" (catch-all for unnested items)
    re.compile(r'^(\d{1,2})\s*$'),
]


def get_component_type(paper_code: str) -> str:
    first = paper_code[0] if paper_code else ""
    if first in ("3", "4"):
        return "theory_structured"
    if first in ("5", "6"):
        return "practical_structured"
    return "structured"


def infer_paper_code(md_path: Path) -> str:
    m = re.search(r'_p(\d+)_', md_path.parent.name)
    return m.group(1) if m else ""


def is_part_header(line: str) -> str | None:
    """
    Return the normalised question-part label if this line is a header,
    else None.
    """
    s = line.strip()
    if not s:
        return None
    for pat in PART_PATTERNS:
        m = pat.match(s)
        if m:
            return re.sub(r'\s+', '', m.group(1))  # e.g. "1(a)(i)"
    return None


def extract_mark_info(lines: list[str]) -> tuple[int, str]:
    """
    From a list of lines belonging to one mark-scheme item, extract:
      - total marks (int)
      - primary mark code (str, e.g. "B1")
    """
    marks = 0
    codes: list[str] = []

    for line in lines:
        # [N] bracket marks
        for m in BRACKETS_INT.finditer(line):
            marks += int(m.group(1))
        # Mark codes
        for m in MARK_CODE_RE.finditer(line):
            codes.append(m.group(1))

    # If no bracket marks, try trailing integer on any line
    if marks == 0:
        for line in reversed(lines):
            m = TRAILING_INT.search(line.strip())
            if m:
                marks = int(m.group(1))
                break

    primary_code = codes[0] if codes else ""
    return marks, primary_code


def parse_items(lines: list[str]) -> list[dict]:
    """
    Segment lines into mark-scheme items using PART_PATTERNS as boundaries.
    Returns list of raw item dicts.
    """
    segments: list[tuple[str, list[str]]] = []  # (label, lines)
    current_label: str | None = None
    current_lines: list[str]  = []

    for line in lines:
        header = is_part_header(line)
        if header is not None:
            if current_label is not None:
                segments.append((current_label, current_lines))
            current_label = header
            current_lines = [line]
        else:
            if current_label is not None:
                current_lines.append(line)

    if current_label is not None:
        segments.append((current_label, current_lines))

    items = []
    for label, seg_lines in segments:
        raw = "\n".join(seg_lines).strip()
        # Answer guidance: non-empty lines that are NOT pure mark codes or integers
        guidance_lines = [
            l.strip() for l in seg_lines
            if l.strip()
            and not re.match(r'^(MP\d|B\d|C\d|A\d|M\d|\d+)$', l.strip(), re.IGNORECASE)
        ]
        guidance = " ".join(guidance_lines).strip()

        marks, code = extract_mark_info(seg_lines)

        # Status: "parsed" if we have guidance or a clear mark code
        status = "parsed" if (guidance or code) else "needs_human_review"

        items.append({
            "question_part":    label,
            "answer_guidance":  guidance or "[not parsed]",
            "marks":            marks,
            "mark_code":        code or None,
            "raw_text":         raw,
            "status":           status,
        })

    return items


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Parse structured Cambridge mark scheme."
    )
    ap.add_argument("clean_md",     help="Path to clean.md")
    ap.add_argument("--paper-code", default="", dest="paper_code")
    args = ap.parse_args()

    md_path = Path(args.clean_md)
    if not md_path.exists():
        sys.exit(f"Error: file not found: {md_path}")

    # Fall back to raw.md if clean.md is empty
    text = md_path.read_text(encoding="utf-8")
    actual_path = md_path
    if not text.strip():
        raw_path = md_path.parent / "raw.md"
        if raw_path.exists() and raw_path.stat().st_size > 0:
            text = raw_path.read_text(encoding="utf-8")
            actual_path = raw_path

    paper_code = args.paper_code or infer_paper_code(md_path)
    comp_type  = get_component_type(paper_code)
    lines      = text.splitlines()

    items = parse_items(lines)

    parsed_count = sum(1 for it in items if it["status"] == "parsed")
    total_marks  = sum(it["marks"] for it in items)

    result = {
        "source_file":    str(actual_path),
        "paper_code":     paper_code,
        "component_type": comp_type,
        "total_items":    len(items),
        "parsed_count":   parsed_count,
        "total_marks":    total_marks,
        "items":          items,
    }
    out_path = md_path.parent / "structured_mark_scheme.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    report = {
        "status":         "passed" if parsed_count > 0 else "needs_human_review",
        "source_file":    str(actual_path),
        "paper_code":     paper_code,
        "component_type": comp_type,
        "total_items":    len(items),
        "parsed_count":   parsed_count,
        "needs_review":   len(items) - parsed_count,
        "total_marks":    total_marks,
    }
    report_path = md_path.parent / "structured_mark_scheme_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"source_file           : {actual_path}")
    print(f"paper_code            : {paper_code}")
    print(f"component_type        : {comp_type}")
    print(f"total_items           : {len(items)}")
    print(f"parsed_count          : {parsed_count}")
    print(f"total_marks_detected  : {total_marks}")
    print(f"structured_mark_scheme: {out_path}")
    print(f"report                : {report_path}")
    # Always exit 0 — partial parse is acceptable


if __name__ == "__main__":
    main()
