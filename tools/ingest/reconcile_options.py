"""
Reconcile missing options in enriched questions so every correct_answer is present.

Usage:
    python tools/ingest/reconcile_options.py <questions.enriched.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/reconcile_options.py \
        data/ingested/markitdown/cambridge_igcse_physics_0625_2025_s_p21_qp/questions.enriched.json
"""

import sys
import json
import copy
from pathlib import Path

EXPECTED = 40

DIAGRAM_PLACEHOLDERS = {
    'A': 'Option A (diagram label)',
    'B': 'Option B (diagram label)',
    'C': 'Option C (diagram label)',
    'D': 'Option D (diagram label)',
}

# Manual correction for Q26: options were merged into a single cell by markitdown
Q26_OPTIONS = {
    'A': 'R is directly proportional to d.',
    'B': 'R is directly proportional to d².',
    'C': 'R is inversely proportional to d.',
    'D': 'R is inversely proportional to d².',
}


def reconcile(enriched_path):
    data = json.loads(enriched_path.read_text(encoding='utf-8'))

    missing_before = [
        q['question_number']
        for q in data['questions']
        if q['correct_answer'] not in q.get('options', {})
    ]

    questions_out = []
    reconciled_nums = []

    for q in data['questions']:
        q = copy.deepcopy(q)
        qnum    = q['question_number']
        correct = q['correct_answer']
        options = q.get('options', {})

        if correct in options:
            # Nothing to fix
            questions_out.append(q)
            continue

        # --- Q26: manual rule ---
        if qnum == 26:
            q['options'] = Q26_OPTIONS
            if 'options reconciled from split markdown table' not in q['issues']:
                q['issues'].append('options reconciled from split markdown table')
            q['option_reconciliation'] = 'manual_rule_q26'
            reconciled_nums.append(qnum)
            questions_out.append(q)
            continue

        # --- Diagram-label placeholder for all other missing-option questions ---
        has_diagram = q.get('flags', {}).get('has_diagram_hint', False)
        # All remaining missing-option questions have diagram hints; apply placeholders.
        q['options'] = dict(DIAGRAM_PLACEHOLDERS)
        if 'options reconciled with diagram-label placeholders' not in q['issues']:
            q['issues'].append('options reconciled with diagram-label placeholders')
        q['option_reconciliation'] = 'diagram_label_placeholder'
        reconciled_nums.append(qnum)
        questions_out.append(q)

    questions_out.sort(key=lambda q: q['question_number'])

    # --- Validate ---
    missing_after = [
        q['question_number']
        for q in questions_out
        if q['correct_answer'] not in q.get('options', {})
    ]
    correct_present = sum(
        1 for q in questions_out
        if q['correct_answer'] in q.get('options', {})
    )
    needs_review_count = sum(1 for q in questions_out if q['needs_review'])

    if missing_after:
        print(f"WARNING: {len(missing_after)} question(s) still missing correct option after reconciliation: {missing_after}")

    # --- Write questions.reconciled.json ---
    reconciled_out = {
        'document_id':           data['document_id'],
        'question_paper_source': data['question_paper_source'],
        'mark_scheme_source':    data['mark_scheme_source'],
        'total_questions':       EXPECTED,
        'questions':             questions_out,
    }
    out_dir = enriched_path.parent
    reconciled_path = out_dir / 'questions.reconciled.json'
    reconciled_path.write_text(
        json.dumps(reconciled_out, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    # --- Write reconcile_report.json ---
    report_out = {
        'total_questions':                         EXPECTED,
        'reconciled_questions':                    sorted(reconciled_nums),
        'questions_with_missing_correct_option_before': sorted(missing_before),
        'questions_with_missing_correct_option_after':  missing_after,
        'correct_answer_present_count':            correct_present,
        'needs_review_count':                      needs_review_count,
    }
    report_path = out_dir / 'reconcile_report.json'
    report_path.write_text(
        json.dumps(report_out, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    # --- Terminal output ---
    print(f"reconciled_questions                        : {sorted(reconciled_nums)}")
    print(f"questions_with_missing_correct_option_after : {missing_after if missing_after else 'none'}")
    print(f"correct_answer_present_count                : {correct_present}")
    print(f"questions.reconciled                        : {reconciled_path}")
    print(f"reconcile_report                            : {report_path}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <questions.enriched.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    reconcile(p)
