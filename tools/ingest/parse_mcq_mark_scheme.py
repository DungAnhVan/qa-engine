"""
Parse Cambridge IGCSE MCQ mark scheme from clean.md.

Parser modes tried in order:
  1. fallback_global_pair_regex   — global regex, handles inline / multi-column formats
  2. cambridge_vertical_blocks    — MarkItDown vertical format: block of Q-numbers
                                    then block of A-letters, separated by marks (all 1s)

Usage:
    python tools/ingest/parse_mcq_mark_scheme.py <path-to-clean.md>
"""

import sys
import re
import json
from pathlib import Path

EXPECTED   = 40
VALID_ANS  = frozenset('ABCD')


# ===========================================================================
# Parser 1 — fallback_global_pair_regex
# ===========================================================================

PAIR_RE = re.compile(
    r'(?<!\d)(40|[1-3][0-9]|[1-9])(?!\d)\s*[.):]?\s+([A-D])(?![a-zA-Z])'
)


def _normalize(text: str) -> str:
    return text.replace('|', ' ').replace('\t', ' ')


def _global_pair_scan(text: str):
    """Returns (answers_dict, sorted_dupes)."""
    normalized = _normalize(text)
    answers, conflicts = {}, set()
    for m in PAIR_RE.finditer(normalized):
        qn  = int(m.group(1))
        ans = m.group(2).upper()
        if qn not in answers:
            answers[qn] = ans
        elif answers[qn] != ans:
            conflicts.add(qn)
    return answers, sorted(conflicts)


# ===========================================================================
# Parser 2 — cambridge_vertical_blocks
# ===========================================================================

def _tokenize_lines(lines):
    """
    Strip each line; classify as:
      ('A', letter)   — exactly A/B/C/D
      ('N', int)      — integer in 1..EXPECTED
    All other lines are discarded.
    """
    tokens = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s in VALID_ANS:
            tokens.append(('A', s))
            continue
        try:
            n = int(s)
            if 1 <= n <= EXPECTED:
                tokens.append(('N', n))
        except ValueError:
            pass
    return tokens


def _group_runs(tokens):
    """Group consecutive same-type tokens into runs → list of (type, [values])."""
    if not tokens:
        return []
    runs = []
    cur_type = tokens[0][0]
    cur_vals = [tokens[0][1]]
    for t, v in tokens[1:]:
        if t == cur_type:
            cur_vals.append(v)
        else:
            runs.append((cur_type, cur_vals))
            cur_type, cur_vals = t, [v]
    runs.append((cur_type, cur_vals))
    return runs


def _find_q_blocks(nvals):
    """
    Within a sequence of N-token values, find every maximal sub-sequence
    where values are strictly consecutive (each = prev + 1) and length >= 2.
    These are candidate question-number blocks.

    Cambridge mark schemes mix marks (all 1s) with real Q-numbers in the same
    N-run, e.g. [1,1,...,1, 29,30,...,40].  Only [29,...,40] qualifies here.
    """
    if not nvals:
        return []
    blocks = []
    cur = [nvals[0]]
    for v in nvals[1:]:
        if v == cur[-1] + 1:
            cur.append(v)
        else:
            if len(cur) >= 2:
                blocks.append(list(cur))
            cur = [v]
    if len(cur) >= 2:
        blocks.append(cur)
    return blocks


def _vertical_blocks(lines):
    """
    Parse the Cambridge vertical-block format.

    Structure per page:
        Question-number block  →  1, 2, …, 28
        Answer block           →  C, B, D, …, C
        Marks block            →  1, 1, …, 1   (all 1s — NOT a Q-block)

    MarkItDown groups all consecutive N-tokens together, so a single N-run
    may look like [1,1,…,1, 29,30,…,40].  _find_q_blocks() extracts the
    strictly-consecutive sub-sequences ([29,…,40]) and ignores the marks noise.

    Returns (answers_dict, sorted_dupes, debug_info).
    """
    tokens = _tokenize_lines(lines)
    runs   = _group_runs(tokens)

    # Build debug data
    n_run_debug = []
    for rt, rv in runs:
        if rt == 'N':
            qbs = _find_q_blocks(rv)
            n_run_debug.append({
                "values_count": len(rv),
                "q_blocks": [{"values": qb, "count": len(qb)} for qb in qbs],
            })
    a_run_debug = [
        {"count": len(rv), "letters": rv}
        for rt, rv in runs if rt == 'A'
    ]

    answers, conflicts = {}, set()
    candidate_blocks   = []

    for run_idx, (rtype, rvals) in enumerate(runs):
        if rtype != 'N':
            continue
        q_blocks = _find_q_blocks(rvals)
        if not q_blocks:
            continue

        # Find the first A-run that follows this N-run
        for k in range(run_idx + 1, len(runs)):
            if runs[k][0] != 'A':
                continue
            avals = runs[k][1]

            # Match the last (rightmost) q_block whose length == len(avals)
            matched = None
            for qb in reversed(q_blocks):
                if len(qb) == len(avals):
                    matched = qb
                    break

            if matched:
                candidate_blocks.append({
                    "question_numbers": matched,
                    "answer_letters":   avals,
                    "count":            len(matched),
                })
                for qn, ans in zip(matched, avals):
                    if qn not in answers:
                        answers[qn] = ans
                    elif answers[qn] != ans:
                        conflicts.add(qn)
            break   # only pair with the first A-run found

    debug = {
        "token_count":          len(tokens),
        "vertical_number_runs": n_run_debug,
        "vertical_answer_runs": a_run_debug,
        "candidate_blocks":     candidate_blocks,
    }
    return answers, sorted(conflicts), debug


# ===========================================================================
# Shared: build result dicts
# ===========================================================================

def _build_result(answers_dict, duplicate_questions, md_path, parser_mode, debug=None):
    missing  = sorted(set(range(1, EXPECTED + 1)) - set(answers_dict))
    detected = len(answers_dict)

    if detected >= EXPECTED:
        status = "passed"
    elif detected >= 30:
        status = "needs_review"
    else:
        status = "failed"

    # List format required by enrich_questions.py:
    #   ans_lookup = {r['question_number']: r['answer'] for r in answer_key['answers']}
    answer_records = [
        {"question_number": qn, "answer": answers_dict[qn], "raw_source": parser_mode}
        for qn in sorted(answers_dict)
    ]

    result = {
        "status":                     status,
        "source_file":                str(md_path),
        "source_markdown":            str(md_path),      # legacy alias
        "parser_mode":                parser_mode,
        "expected_answers":           EXPECTED,
        "detected_answers":           detected,
        "missing_questions":          missing,
        "duplicate_questions":        duplicate_questions,
        "missing_question_numbers":   missing,           # legacy alias
        "duplicate_question_numbers": duplicate_questions,
        "invalid_answer_values":      [],
        "answers":                    answer_records,    # list — do NOT change
    }
    if status == "failed" and debug is not None:
        result["debug"] = debug
    return result


# ===========================================================================
# Main
# ===========================================================================

def parse_mark_scheme(md_path: Path):
    text = md_path.read_text(encoding='utf-8')
    actual_path = md_path

    # If clean.md is empty, fall back to raw.md in the same folder
    if not text.strip():
        raw_path = md_path.parent / "raw.md"
        if raw_path.exists() and raw_path.stat().st_size > 0:
            text = raw_path.read_text(encoding='utf-8')
            actual_path = raw_path

    lines = text.splitlines()

    # ── Stage 1: global pair regex ──────────────────────────────────────────
    ans1, dupes1 = _global_pair_scan(text)

    if len(ans1) >= 30:
        answers, dupes, parser_mode, debug = ans1, dupes1, "fallback_global_pair_regex", None
    else:
        # ── Stage 2: cambridge vertical blocks ──────────────────────────────
        ans2, dupes2, debug2 = _vertical_blocks(lines)
        if len(ans2) >= len(ans1):
            answers, dupes, parser_mode, debug = ans2, dupes2, "cambridge_vertical_blocks", debug2
        else:
            answers, dupes, parser_mode, debug = ans1, dupes1, "fallback_global_pair_regex", debug2

    result = _build_result(answers, dupes, actual_path, parser_mode, debug=debug)

    # ── Write answer_key.json ────────────────────────────────────────────────
    out_path = md_path.parent / "answer_key.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')

    # ── Write answer_key_report.json ─────────────────────────────────────────
    report = {
        "status":              result["status"],
        "source_file":         result["source_file"],
        "parser_mode":         parser_mode,
        "expected_answers":    EXPECTED,
        "detected_answers":    result["detected_answers"],
        "missing_questions":   result["missing_questions"],
        "duplicate_questions": result["duplicate_questions"],
        "answers": {
            str(r["question_number"]): r["answer"]
            for r in result["answers"]
        },
    }
    if result.get("debug"):
        report["debug"] = result["debug"]
    report_path = md_path.parent / "answer_key_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

    # ── Terminal output ───────────────────────────────────────────────────────
    missing_str = result["missing_questions"] if result["missing_questions"] else "none"
    dupes_str   = result["duplicate_questions"] if result["duplicate_questions"] else "none"
    print(f"source_file        : {md_path}")
    print(f"parser_mode        : {parser_mode}")
    print(f"detected_answers   : {result['detected_answers']}")
    print(f"missing_questions  : {missing_str}")
    print(f"duplicate_questions: {dupes_str}")
    print(f"answer_key         : {out_path}")
    print(f"report             : {report_path}")

    if result["status"] == "failed":
        sys.exit("Could not parse enough MCQ answers from mark scheme.")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <path-to-clean.md>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    parse_mark_scheme(p)
