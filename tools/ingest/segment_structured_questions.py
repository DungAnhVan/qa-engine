"""
Segment a Cambridge structured (non-MCQ) question paper into a skeleton of
questions and sub-parts.  Best-effort — always exits 0; status field carries
confidence level.

Supported paper types:
  Paper 3 / 4  — Theory (Core / Extended)   : Q1–Q10
  Paper 5 / 6  — Practical / Alt-Practical  : Q1–Q4

Usage:
    python segment_structured_questions.py <clean.md> [--paper-code CODE]

Output (in same folder as clean.md):
    structured_questions.json
    structured_questions_report.json
"""

import sys
import re
import json
import argparse
from pathlib import Path

# Expected Q counts and total marks by first digit of paper_code
EXPECTED_Q:     dict[str, int] = {"3": 8,  "4": 10, "5": 5,  "6": 4}
EXPECTED_MARKS: dict[str, int] = {"3": 40, "4": 80, "5": 40, "6": 40}

# Sub-part / nested sub-part patterns
SUBPART_RE = re.compile(
    r'^\(([a-z]|i{1,3}|iv|vi{0,3}|vii|viii|ix|x)\)',
    re.IGNORECASE,
)
NESTED_SUBPART_RE = re.compile(
    r'\(([a-z])\)\s*\((i{1,3}|iv|vi{0,3}|vii|viii|ix|x)\)',
    re.IGNORECASE,
)
MARKS_RE = re.compile(r'\[(\d+)\]')


def get_component_type(paper_code: str) -> str:
    first = paper_code[0] if paper_code else ""
    if first in ("3", "4"):
        return "theory_structured"
    if first in ("5", "6"):
        return "practical_structured"
    return "structured"


def infer_paper_code(md_path: Path) -> str:
    """Derive paper_code from folder name, e.g. ...p41_qp -> '41'."""
    m = re.search(r'_p(\d+)_', md_path.parent.name)
    return m.group(1) if m else ""


def split_into_question_blocks(lines: list[str], max_q: int) -> dict[int, list[str]]:
    """
    Split document lines into question blocks.
    Returns {question_number: [lines]}.

    A question boundary is:
      - a line whose stripped content is exactly an integer 1..max_q, OR
      - a line whose stripped content starts with that integer followed by
        a non-digit (e.g. "1 Space and time", "2(a)...")
    """
    Q_BOUNDARY = re.compile(r'^(\d{1,2})(?:\s|$|\()')
    blocks: dict[int, list[str]] = {}
    current_q: int | None = None
    current_lines: list[str] = []

    for line in lines:
        s = line.strip()
        matched_q = None
        if s:
            m = Q_BOUNDARY.match(s)
            if m:
                n = int(m.group(1))
                if 1 <= n <= max_q:
                    matched_q = n

        if matched_q is not None:
            if current_q is not None:
                blocks.setdefault(current_q, [])
                blocks[current_q] += current_lines
            current_q    = matched_q
            current_lines = [line]
        else:
            if current_q is not None:
                current_lines.append(line)

    if current_q is not None:
        blocks.setdefault(current_q, [])
        blocks[current_q] += current_lines

    return blocks


def detect_subparts(lines: list[str], q_num: int) -> list[str]:
    """Detect sub-part labels within a question block."""
    parts: list[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        full = f"{q_num}{label}"
        if full not in seen:
            seen.add(full)
            parts.append(full)

    for line in lines:
        s = line.strip()
        m = SUBPART_RE.match(s)
        if m:
            add(m.group(0))
        for mn in NESTED_SUBPART_RE.finditer(line):
            add(f"({mn.group(1)})({mn.group(2)})")

    return parts


def count_marks(lines: list[str]) -> int:
    return sum(int(m.group(1)) for l in lines for m in MARKS_RE.finditer(l))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Segment structured Cambridge question paper."
    )
    ap.add_argument("clean_md",    help="Path to clean.md")
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
    first      = paper_code[0] if paper_code else "4"
    comp_type  = get_component_type(paper_code)
    max_q      = EXPECTED_Q.get(first, 10)

    lines  = text.splitlines()
    blocks = split_into_question_blocks(lines, max_q)

    # Question-ID prefix: strip the _qp suffix from folder name
    id_prefix = re.sub(r'_qp$', '', md_path.parent.name)

    questions = []
    for qn in range(1, max_q + 1):
        block_lines  = blocks.get(qn, [])
        raw_text     = "\n".join(block_lines).strip()
        subparts     = detect_subparts(block_lines, qn)
        marks_detect = count_marks(block_lines)

        questions.append({
            "question_id":          f"{id_prefix}_q{qn:02d}",
            "question_number":      str(qn),
            "component_type":       comp_type,
            "raw_text":             raw_text or f"[question {qn} not parsed]",
            "detected_subparts":    subparts,
            "marks_total_detected": marks_detect,
            "status":               "parsed" if raw_text else "needs_human_review",
        })

    parsed_count = sum(1 for q in questions if q["status"] == "parsed")

    result = {
        "source_file":        str(actual_path),
        "paper_code":         paper_code,
        "component_type":     comp_type,
        "expected_questions": max_q,
        "detected_questions": parsed_count,
        "total_questions":    len(questions),
        "questions":          questions,
    }
    out_path = md_path.parent / "structured_questions.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    report = {
        "status":                   "passed" if parsed_count > 0 else "needs_human_review",
        "source_file":              str(actual_path),
        "paper_code":               paper_code,
        "component_type":           comp_type,
        "expected_questions":       max_q,
        "detected_questions":       parsed_count,
        "questions_with_marks":     sum(1 for q in questions if q["marks_total_detected"] > 0),
        "questions_with_subparts":  sum(1 for q in questions if q["detected_subparts"]),
    }
    report_path = md_path.parent / "structured_questions_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"source_file          : {actual_path}")
    print(f"paper_code           : {paper_code}")
    print(f"component_type       : {comp_type}")
    print(f"expected_questions   : {max_q}")
    print(f"detected_questions   : {parsed_count}")
    print(f"structured_questions : {out_path}")
    print(f"report               : {report_path}")
    # Always exit 0 — partial parse is acceptable


if __name__ == "__main__":
    main()
