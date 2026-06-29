"""
Normalize segmented MCQ questions: remove footers, convert CID characters, compute flags.

Usage:
    python tools/ingest/normalize_questions.py <path-to-questions.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/normalize_questions.py data/ingested/markitdown/cambridge_igcse_physics_0625_2025_s_p21_qp/questions.json
"""

import sys
import re
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

DIAGRAM_WORDS_RE = re.compile(
    r'\b(diagram|graph|circuit|ray|mirror|force\s+meter|arrows|field\s+pattern'
    r'|wire|screen|gold\s+foil|block|lens|cork)\b',
    re.IGNORECASE,
)

# Lines (or table cells) containing these are footer noise
FOOTER_PATTERNS = [
    re.compile(r'[©]\s*UCLES',                             re.IGNORECASE),
    re.compile(r'\d{4}/\d{2}/[A-Z]/[A-Z]/\d{2}'),          # 0625/21/M/J/25
    re.compile(r'\[Turn\s+over',                           re.IGNORECASE),
    re.compile(r'\bTurn\s+over\b',                         re.IGNORECASE),
    re.compile(r'\bPermission\s+to\s+reproduce\b',         re.IGNORECASE),
    re.compile(r'\bCambridge\s+Assessment\b',               re.IGNORECASE),
    re.compile(r'\bUniversity\s+of\s+Cambridge\b',          re.IGNORECASE),
    re.compile(r'\bwww\.cambridgeinternational\.org\b',     re.IGNORECASE),
    re.compile(r'\bLocal\s+Examinations\s+Syndicate\b',     re.IGNORECASE),
    re.compile(r'\bCopyright\s+Acknowledgements\b',         re.IGNORECASE),
    re.compile(r'\(UCLES\)',                                re.IGNORECASE),
]

# Standalone page number line
PAGE_NUM_RE = re.compile(r'^\s*(\d{1,2})\s*$')
PAGE_RANGE = (2, 16)

# CID character substitutions — specific before catch-all
CID_SUBS = [
    (re.compile(r'\(cid:1\)'),     '->'),       # arrow right (will be further replaced)
    (re.compile(r'\(cid:2\)'),     'beta'),
    (re.compile(r'\(cid:22\)'),    '(check)'),
    (re.compile(r'\(cid:26\)'),    '(cross)'),
    (re.compile(r'\(cid:(\d+)\)'), r'[cid:\1]'),  # unknown -> placeholder
]

# Trailing copyright block in option text (e.g. " 16 Permission to reproduce...")
TRAILING_COPYRIGHT_RE = re.compile(
    r'\s*\d{1,2}\s+Permission\s+to\s+reproduce.+$',
    re.DOTALL | re.IGNORECASE,
)
# Trailing standalone page number in option text (e.g. " 7", " 12")
TRAILING_PAGE_RE = re.compile(r'\s+\d{1,2}\s*$')


# ---------------------------------------------------------------------------
# Character normalization
# ---------------------------------------------------------------------------

def normalize_chars(text):
    for pattern, replacement in CID_SUBS:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# Footer detection helpers
# ---------------------------------------------------------------------------

def line_is_footer(line):
    return any(p.search(line) for p in FOOTER_PATTERNS)


def is_separator_row(line):
    return bool(re.match(r'^\|(\s*-+\s*\|)+\s*$', line.strip()))


def is_page_number_table_row(line):
    """True if table row's non-empty cells are all digits within PAGE_RANGE."""
    if '|' not in line:
        return False
    cells = [
        c.strip() for c in line.split('|')
        if c.strip() and not re.match(r'^-+$', c.strip())
    ]
    if not cells:
        return False
    try:
        return all(
            re.match(r'^\d{1,2}$', c) and PAGE_RANGE[0] <= int(c) <= PAGE_RANGE[1]
            for c in cells
        )
    except ValueError:
        return False


def is_footer_table_row(line):
    """True if a table row's every non-empty, non-separator cell is footer content."""
    if '|' not in line:
        return False
    cells = [
        c.strip() for c in line.split('|')
        if c.strip() and not re.match(r'^-+$', c.strip())
    ]
    if not cells:
        return False
    return all(line_is_footer(c) for c in cells)


# ---------------------------------------------------------------------------
# Footer removal from raw block
# ---------------------------------------------------------------------------

def remove_footers(raw_block):
    """
    Remove footer/noise lines from a raw block while preserving scientific content.
    Handles: UCLES copyright rows, page number table rows, standalone page numbers,
    the full copyright boilerplate, and orphaned separator rows.
    """
    lines = raw_block.splitlines()
    num_lines = len(lines)
    remove = [False] * num_lines

    # ---- Pass 1: mark obvious footer / noise lines ----
    copyright_block_started = False
    for i, line in enumerate(lines):
        stripped = line.strip()

        if copyright_block_started:
            remove[i] = True
            continue

        # Direct footer line
        if line_is_footer(stripped):
            remove[i] = True
            if re.search(r'\bPermission\s+to\s+reproduce\b', stripped, re.IGNORECASE):
                copyright_block_started = True
            continue

        # Table row whose every cell is footer content
        if is_footer_table_row(stripped):
            remove[i] = True
            continue

        # Table row containing only page numbers (e.g. |  5  | or |  11  |)
        if is_page_number_table_row(stripped):
            remove[i] = True
            continue

        # Standalone page number — tentative (may be un-marked in pass 2)
        m = PAGE_NUM_RE.match(stripped)
        if m and PAGE_RANGE[0] <= int(m.group(1)) <= PAGE_RANGE[1]:
            remove[i] = True

    # ---- Pass 2: un-mark standalone page numbers that are orphaned QUESTION numbers ----
    # An orphaned question number (e.g. "11" in Q11's block) sits between scientific content.
    for i, line in enumerate(lines):
        if not remove[i]:
            continue
        stripped = line.strip()
        m = PAGE_NUM_RE.match(stripped)
        if not m:
            continue  # Not a standalone number; leave removed
        n_val = int(m.group(1))
        if not (PAGE_RANGE[0] <= n_val <= PAGE_RANGE[1]):
            continue

        prev_has_content = any(
            not remove[j] and lines[j].strip()
            for j in range(max(0, i - 4), i)
        )
        remaining_after = [
            j for j in range(i + 1, num_lines)
            if lines[j].strip() and not remove[j]
        ]
        if prev_has_content and remaining_after:
            remove[i] = False   # It's an orphaned question number — keep it

    # ---- Pass 3: remove orphaned separator rows ----
    # A separator | --- | --- | with no adjacent non-removed, non-separator content is noise.
    for i, line in enumerate(lines):
        if remove[i] or not is_separator_row(line):
            continue
        prev_content = any(
            not remove[j] and lines[j].strip() and not is_separator_row(lines[j])
            for j in range(max(0, i - 2), i)
        )
        next_content = any(
            not remove[j] and lines[j].strip() and not is_separator_row(lines[j])
            for j in range(i + 1, min(num_lines, i + 3))
        )
        if not prev_content and not next_content:
            remove[i] = True

    kept = [line for i, line in enumerate(lines) if not remove[i]]

    # Collapse runs of more than 1 consecutive blank line
    result = []
    blank_run = 0
    for line in kept:
        if line.strip() == '':
            blank_run += 1
            if blank_run <= 1:
                result.append(line)
        else:
            blank_run = 0
            result.append(line)

    while result and not result[-1].strip():
        result.pop()

    return '\n'.join(result)


# ---------------------------------------------------------------------------
# Option text cleaning
# ---------------------------------------------------------------------------

def clean_option_text(text):
    """Strip trailing page numbers and copyright noise from an option value."""
    text = TRAILING_COPYRIGHT_RE.sub('', text)  # copyright block first
    text = TRAILING_PAGE_RE.sub('', text)        # then trailing page number
    text = normalize_chars(text)
    return text.strip()


def option_text_suspicious(text):
    """True if option text is likely incomplete (single letter, empty, etc.)."""
    text = text.strip()
    if not text:
        return True
    if re.match(r'^[A-Z]$', text):   # single uppercase letter (e.g. 'N', 'X')
        return True
    return False


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

def compute_flags(raw_block, stem, orig_options):
    return {
        'has_table':        '|' in raw_block,
        'has_diagram_hint': bool(DIAGRAM_WORDS_RE.search(raw_block)),
        'has_options':      bool(orig_options),
        'options_complete': bool(orig_options) and all(l in orig_options for l in 'ABCD'),
        'stem_empty':       not bool(stem.strip()),
    }


# ---------------------------------------------------------------------------
# needs_review
# ---------------------------------------------------------------------------

def compute_needs_review(q, flags, orig_options):
    issues = list(q.get('issues', []))
    needs_review = q.get('needs_review', False)

    def add(msg):
        nonlocal needs_review
        needs_review = True
        if msg not in issues:
            issues.append(msg)

    # Missing A/B/C/D
    missing = [l for l in 'ABCD' if l not in orig_options]
    if missing:
        add(f"Missing options: {missing}")

    # Empty stem
    if flags['stem_empty']:
        add('stem is empty — check raw_block for correct stem boundary')

    # Markdown table present
    if flags['has_table']:
        add('has markdown table — options may be partial')

    # Diagram / visual content
    if flags['has_diagram_hint']:
        add('has diagram/visual content — options may be labels only')

    # Option D contaminated by footer or page number
    d_text = orig_options.get('D', '')
    if d_text:
        if TRAILING_COPYRIGHT_RE.search(d_text):
            add('option D contains copyright block — stripped in normalized output')
        elif TRAILING_PAGE_RE.search(d_text):
            add('option D has trailing page number — stripped in normalized output')
        elif any(p.search(d_text) for p in FOOTER_PATTERNS):
            add('option D contaminated with footer content')

    # CID characters
    if '(cid:' in q.get('raw_block', ''):
        add('raw block contains (cid:) characters — symbol extraction may be incorrect')

    # Suspiciously short option text in table context
    if flags['has_table'] and orig_options:
        for letter, text in orig_options.items():
            if option_text_suspicious(text):
                add(f"option {letter} text appears incomplete: '{text}'")

    return needs_review, issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def normalize(questions_path):
    data = json.loads(questions_path.read_text(encoding='utf-8'))
    questions_in = data['questions']

    out_questions = []
    for q in questions_in:
        raw           = q['raw_block']
        stem          = q.get('stem', '')
        orig_options  = q.get('options', {})

        normalized_block = remove_footers(raw)
        normalized_block = normalize_chars(normalized_block)

        cleaned_options = {
            letter: clean_option_text(text)
            for letter, text in orig_options.items()
        }
        cleaned_stem = normalize_chars(stem)

        flags = compute_flags(raw, cleaned_stem, orig_options)
        needs_review, issues = compute_needs_review(q, flags, orig_options)

        out_questions.append({
            'question_number':      q['question_number'],
            'original_raw_block':   raw,
            'normalized_raw_block': normalized_block,
            'stem':                 cleaned_stem,
            'options':              cleaned_options,
            'flags':                flags,
            'needs_review':         needs_review,
            'issues':               issues,
        })

    total        = len(out_questions)
    review_qs    = [q for q in out_questions if q['needs_review']]
    review_count = len(review_qs)
    clean_count  = total - review_count

    norm_path = questions_path.parent / 'questions.normalized.json'
    norm_path.write_text(
        json.dumps(
            {'source_questions': str(questions_path), 'total_questions': total, 'questions': out_questions},
            indent=2, ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    review_path = questions_path.parent / 'review_queue.json'
    review_path.write_text(
        json.dumps(
            {
                'total_questions': total,
                'review_count':    review_count,
                'questions': [
                    {
                        'question_number':      q['question_number'],
                        'issues':               q['issues'],
                        'normalized_raw_block': q['normalized_raw_block'],
                    }
                    for q in review_qs
                ],
            },
            indent=2, ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    print(f"total_questions        : {total}")
    print(f"review_count           : {review_count}")
    print(f"clean_questions_count  : {clean_count}")
    print(f"questions.normalized   : {norm_path}")
    print(f"review_queue           : {review_path}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <path-to-questions.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    normalize(p)
