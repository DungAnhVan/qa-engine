"""
Merge classified question data with correct answers from the mark scheme.

Usage:
    python tools/ingest/enrich_questions.py <questions.classified.json> <answer_key.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/enrich_questions.py \
        data/ingested/markitdown/cambridge_igcse_physics_0625_2025_s_p21_qp/questions.classified.json \
        data/ingested/markitdown/cambridge_igcse_physics_0625_2025_s_p21_ms/answer_key.json
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

EXPECTED = 40
VALID_ANSWERS = {'A', 'B', 'C', 'D'}

DOCUMENT_ID = "cambridge_igcse_physics_0625_2025_s_p21"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_inputs(classified, answer_key):
    errors = []

    total_q = classified.get('total_questions', 0)
    if total_q != EXPECTED:
        errors.append(f"classified JSON has total_questions={total_q}, expected {EXPECTED}")

    detected_a = answer_key.get('detected_answers', 0)
    if detected_a != EXPECTED:
        errors.append(f"answer_key has detected_answers={detected_a}, expected {EXPECTED}")

    ans_nums = {r['question_number'] for r in answer_key.get('answers', [])}
    missing_in_key = sorted(set(range(1, EXPECTED + 1)) - ans_nums)
    if missing_in_key:
        errors.append(f"answer_key missing question numbers: {missing_in_key}")

    bad_answers = [
        r for r in answer_key.get('answers', [])
        if r.get('answer') not in VALID_ANSWERS
    ]
    if bad_answers:
        errors.append(f"invalid answer values: {bad_answers}")

    return errors


# ---------------------------------------------------------------------------
# Main enrichment
# ---------------------------------------------------------------------------

def enrich(classified_path, answer_key_path):
    classified  = json.loads(classified_path.read_text(encoding='utf-8'))
    answer_key  = json.loads(answer_key_path.read_text(encoding='utf-8'))

    # Validate
    errors = validate_inputs(classified, answer_key)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    # Build answer lookup: question_number -> answer letter
    ans_lookup = {
        r['question_number']: r['answer']
        for r in answer_key['answers']
    }

    # --- Build enriched questions ---
    enriched_questions = []
    answers_attached          = 0
    missing_answers           = []
    missing_correct_option_qs = []

    for clf_q in classified['questions']:
        qnum     = clf_q['question_number']
        orig     = clf_q['original_question']

        correct  = ans_lookup.get(qnum)
        issues   = list(orig.get('issues', []))

        if correct is None:
            missing_answers.append(qnum)
        else:
            answers_attached += 1
            # Check whether the correct answer option was actually parsed
            options = orig.get('options', {})
            if correct not in options:
                missing_correct_option_qs.append(qnum)
                msg = f"correct answer '{correct}' not found in parsed options"
                if msg not in issues:
                    issues.append(msg)

        # needs_review: true if either classification or normalization flagged it,
        # or the correct answer option is missing
        needs_review = clf_q.get('needs_review', False) or (qnum in missing_correct_option_qs)

        enriched_questions.append({
            "question_number":     qnum,
            "topic":               clf_q.get('topic', ''),
            "subtopic":            clf_q.get('subtopic', ''),
            "skill":               clf_q.get('skill', ''),
            "confidence":          clf_q.get('confidence', ''),
            "stem":                orig.get('stem', ''),
            "options":             orig.get('options', {}),
            "correct_answer":      correct,
            "needs_review":        needs_review,
            "issues":              issues,
            "flags":               orig.get('flags', {}),
            "normalized_raw_block": orig.get('normalized_raw_block', ''),
            "original_raw_block":  orig.get('original_raw_block', ''),
        })

    enriched_questions.sort(key=lambda q: q['question_number'])

    # --- Topic counts ---
    topic_counts = defaultdict(int)
    for q in enriched_questions:
        topic_counts[q['topic']] += 1

    needs_review_count = sum(1 for q in enriched_questions if q['needs_review'])
    clean_ready_count  = EXPECTED - needs_review_count

    # --- Write outputs ---
    out_dir = classified_path.parent

    enriched_out = {
        "document_id":            DOCUMENT_ID,
        "question_paper_source":  str(classified_path),
        "mark_scheme_source":     str(answer_key_path),
        "total_questions":        EXPECTED,
        "questions":              enriched_questions,
    }
    enriched_path = out_dir / 'questions.enriched.json'
    enriched_path.write_text(
        json.dumps(enriched_out, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    report_out = {
        "total_questions":                      EXPECTED,
        "answers_attached":                     answers_attached,
        "missing_answers":                      missing_answers,
        "questions_with_missing_correct_option": missing_correct_option_qs,
        "needs_review_count":                   needs_review_count,
        "clean_ready_count":                    clean_ready_count,
        "topic_counts":                         dict(sorted(topic_counts.items())),
    }
    report_path = out_dir / 'enrichment_report.json'
    report_path.write_text(
        json.dumps(report_out, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    # --- Terminal output ---
    print(f"total_questions                        : {EXPECTED}")
    print(f"answers_attached                       : {answers_attached}")
    print(f"missing_answers                        : {missing_answers if missing_answers else 'none'}")
    print(f"questions_with_missing_correct_option  : {missing_correct_option_qs if missing_correct_option_qs else 'none'}")
    print(f"needs_review_count                     : {needs_review_count}")
    print(f"clean_ready_count                      : {clean_ready_count}")
    print(f"questions.enriched                     : {enriched_path}")
    print(f"enrichment_report                      : {report_path}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(f"Usage: python {sys.argv[0]} <questions.classified.json> <answer_key.json>")
    classified_p  = Path(sys.argv[1])
    answer_key_p  = Path(sys.argv[2])
    for p in (classified_p, answer_key_p):
        if not p.exists():
            sys.exit(f"Error: file not found: {p}")
    enrich(classified_p, answer_key_p)
