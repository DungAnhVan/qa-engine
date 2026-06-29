"""
Segment Cambridge IGCSE MCQ clean.md into individual question blocks.

Usage:
    python tools/ingest/segment_mcq.py <path-to-clean.md>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/segment_mcq.py data/ingested/markitdown/cambridge_igcse_physics_0625_2025_s_p21_qp/clean.md
"""

import sys
import re
import json
from pathlib import Path

EXPECTED = 40

# "N Text" or "N  Text" — number + 1-2 spaces + uppercase-first text
# The [A-Z].+ guard prevents matching physics values like "40 kN 60 kN"
INLINE_QN_RE = re.compile(r'^(\d{1,2})[ \t]{1,2}([A-Z].+)$')

# Standalone number on its own line (page numbers OR orphaned question numbers)
STANDALONE_NUM_RE = re.compile(r'^\s*(\d{1,2})\s*$')

# Simple option line: "A text", "B text" (1-3 spaces after letter)
OPT_SIMPLE_RE = re.compile(r'^([ABCD])[ \t]{1,3}(\S.*)$')


# ---------------------------------------------------------------------------
# Option helpers
# ---------------------------------------------------------------------------

def try_inline_options(line):
    """
    Try to parse 'A x B y C z D w' from a single line.
    Only used when B, C, D all appear on the same line as A.
    Returns dict {A:.., B:.., C:.., D:..} or None.
    """
    # Quick pre-check: all four letters must be present as words
    for letter in 'BCD':
        if not re.search(r'\b' + letter + r'\b', line):
            return None
    m = re.search(r'\bA\b\s+(.+?)\s+\bB\b\s+(.+?)\s+\bC\b\s+(.+?)\s+\bD\b\s+(.+?)$', line)
    if m and all(len(g.strip()) < 100 for g in m.groups()):
        return {
            'A': m.group(1).strip(),
            'B': m.group(2).strip(),
            'C': m.group(3).strip(),
            'D': m.group(4).strip(),
        }
    return None


def extract_from_table_row(line):
    """
    Extract {letter: text} pairs from a markdown table row.
    Handles cells like '| A text |', '| A  text |', or lone '| A |' + '| text |'.
    """
    raw_cells = line.split('|')
    cells = []
    for c in raw_cells:
        c = c.strip()
        if c and not re.match(r'^-+$', c):
            cells.append(c)

    options = {}
    i = 0
    while i < len(cells):
        cell = cells[i]
        # "A text" or "A  text" inside a cell
        m = re.match(r'^([ABCD])[ \t]{0,3}(\S.+)$', cell)
        if m and m.group(1) not in options:
            options[m.group(1)] = m.group(2).strip()
            i += 1
            continue
        # Lone letter in a cell — next cell is the text
        m_lone = re.match(r'^([ABCD])$', cell)
        if m_lone and m_lone.group(1) not in options and i + 1 < len(cells):
            nxt = cells[i + 1].strip()
            if nxt and not re.match(r'^[ABCD]$', nxt):
                options[m_lone.group(1)] = nxt
                i += 2
                continue
        i += 1
    return options


def extract_options(block_lines):
    """
    Extract options A/B/C/D from a question block.
    Returns (options_dict, needs_review, issues_list).
    """
    options = {}
    current_opt = None

    for line in block_lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Table row — may contain multiple option letters
        if '|' in line:
            row_opts = extract_from_table_row(line)
            for letter, text in row_opts.items():
                if letter not in options:
                    options[letter] = text
                    current_opt = letter
            if row_opts:
                continue

        # Simple option line "A text"
        m = OPT_SIMPLE_RE.match(stripped)
        if m:
            letter = m.group(1)
            text = m.group(2).strip()
            # Check if the whole line encodes all 4 options (e.g. "A 5 B 6 C 11 D 16")
            inline = try_inline_options(stripped)
            if inline:
                options.update(inline)
                current_opt = None
                break
            if letter not in options:
                options[letter] = text
                current_opt = letter
            continue

        # Continuation of the current option (multi-line option text)
        if current_opt and stripped and not stripped.startswith('|'):
            if not re.match(r'^[-=]{3,}', stripped):
                options[current_opt] = options[current_opt] + ' ' + stripped

    missing = [l for l in 'ABCD' if l not in options]
    needs_review = bool(missing)
    issues = [f"Missing options: {missing}"] if needs_review else []
    return options, needs_review, issues


def extract_stem(block_lines, options, qnum):
    """
    Return question stem = block content before the first option marker,
    with the leading question number stripped from the first line.
    """
    # Strip leading question number from first non-empty line
    processed = list(block_lines)
    for i, line in enumerate(processed):
        if line.strip():
            m = re.match(rf'^{qnum}[ \t]{{1,2}}', line)
            if m:
                processed[i] = line[m.end():]
            break

    # Find where options begin
    for i, line in enumerate(processed):
        stripped = line.strip()
        if not stripped:
            continue
        m = OPT_SIMPLE_RE.match(stripped)
        if m and m.group(1) == 'A':
            return '\n'.join(processed[:i]).strip()
        if '|' in line:
            row_opts = extract_from_table_row(line)
            if 'A' in row_opts:
                return '\n'.join(processed[:i]).strip()
        if stripped and try_inline_options(stripped):
            return '\n'.join(processed[:i]).strip()

    return '\n'.join(processed).strip()


# ---------------------------------------------------------------------------
# Question boundary detection
# ---------------------------------------------------------------------------

def find_question_starts(lines):
    """
    Returns:
        found    — {qnum: start_line_idx}
        orphaned — set of qnums whose number appeared on a standalone line
    """
    found = {}
    orphaned = set()

    # Pass 1: inline markers "N Text" or "N  Text" (uppercase-first text)
    for i, line in enumerate(lines):
        m = INLINE_QN_RE.match(line)
        if m:
            n = int(m.group(1))
            if 1 <= n <= EXPECTED and n not in found:
                found[n] = i

    # Pass 2: standalone number lines for questions not yet found
    missing = set(range(1, EXPECTED + 1)) - set(found.keys())
    for i, line in enumerate(lines):
        m = STANDALONE_NUM_RE.match(line)
        if not m:
            continue
        n = int(m.group(1))
        if n not in missing:
            continue
        # Orphaned number: real block start may be a few lines BEFORE
        # (e.g. Q11 — stem text precedes the orphaned "11" line)
        # Scan backward to find the first blank line; block starts right after it.
        block_start = i
        for j in range(i - 1, max(i - 20, -1), -1):
            if lines[j].strip() == '':
                block_start = j + 1
                break
        found[n] = block_start
        orphaned.add(n)
        missing.discard(n)

    return found, orphaned


# ---------------------------------------------------------------------------
# Main segmentation
# ---------------------------------------------------------------------------

def segment(md_path):
    text = md_path.read_text(encoding='utf-8')
    lines = text.splitlines()

    starts, orphaned = find_question_starts(lines)
    sorted_qs = sorted(starts.items(), key=lambda x: x[1])

    questions = []
    for rank, (qnum, start_idx) in enumerate(sorted_qs):
        end_idx = sorted_qs[rank + 1][1] if rank + 1 < len(sorted_qs) else len(lines)
        block_lines = lines[start_idx:end_idx]

        # Drop trailing blank lines
        while block_lines and not block_lines[-1].strip():
            block_lines.pop()

        raw_block = '\n'.join(block_lines)
        options, needs_review, issues = extract_options(block_lines)
        stem = extract_stem(block_lines, options, qnum)

        if qnum in orphaned:
            needs_review = True
            issues.append("Question number appeared on a separate line (PDF extraction artifact)")

        questions.append({
            "question_number": qnum,
            "raw_block": raw_block,
            "stem": stem,
            "options": options,
            "needs_review": needs_review,
            "issues": issues,
        })

    questions.sort(key=lambda q: q["question_number"])

    detected_nums = {q["question_number"] for q in questions}
    missing_nums = sorted(set(range(1, EXPECTED + 1)) - detected_nums)

    result = {
        "source_markdown": str(md_path),
        "expected_questions": EXPECTED,
        "detected_questions": len(questions),
        "missing_question_numbers": missing_nums,
        "questions": questions,
    }

    out_path = md_path.parent / "questions.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"detected_questions       : {len(questions)}")
    print(f"missing_question_numbers : {missing_nums if missing_nums else 'none'}")
    print(f"output_path              : {out_path}")

    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <path-to-clean.md>")
    md_path = Path(sys.argv[1])
    if not md_path.exists():
        sys.exit(f"Error: file not found: {md_path}")
    segment(md_path)
