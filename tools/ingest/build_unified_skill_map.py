"""
Build the Quanta Aptus Unified Skill Map from the Unified Source Corpus.

Reads unified_source_corpus_v0.json, loads each indexed source file, and
derives one skill_unit per question. Raw Cambridge content is NOT included —
only derived metadata (topic, skill label, skill_type, short_evidence).

Usage:
    python tools/ingest/build_unified_skill_map.py \\
        data/bank/cambridge_igcse/physics_0625/source_corpus/unified_source_corpus_v0.json

Output (data/bank/cambridge_igcse/physics_0625/skill_map/):
    unified_skill_map_v0.json
    unified_skill_map_report.json
    unified_skill_map_manifest.md
"""

import sys
import re
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Skill type vocab
# ---------------------------------------------------------------------------

SKILL_TYPES = [
    "multiple_choice_concept",
    "recall_definition",
    "conceptual_explanation",
    "calculation",
    "equation_manipulation",
    "data_interpretation",
    "graphing",
    "table_design",
    "diagram_drawing",
    "measurement",
    "practical_calculation",
    "variable_control",
    "experimental_design",
    "evaluation_accuracy",
    "extended_planning",
    "unknown",
]

# ---------------------------------------------------------------------------
# Topic keyword heuristics
# ---------------------------------------------------------------------------

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "Motion, forces and energy": [
        "speed", "velocity", "acceleration", "force", "energy", "work", "power",
        "momentum", "pressure", "weight", "mass", "gravity", "newton", "friction",
        "distance", "motion", "kinetic", "potential", "elastic", "spring",
        "moment", "density", "deceleration", "uniform", "terminal velocity",
        "resultant", "displacement",
    ],
    "Thermal physics": [
        "temperature", "heat", "thermal", "specific heat", "melting", "boiling",
        "evaporation", "latent", "conduction", "convection", "expansion",
        "kelvin", "celsius", "thermometer", "steam", "ice", "absolute zero",
        "gas law", "volume of gas",
    ],
    "Waves": [
        "wave", "frequency", "wavelength", "amplitude", "sound", "light",
        "reflection", "refraction", "diffraction", "spectrum", "colour", "color",
        "echo", "ultrasound", "electromagnetic", "transverse", "longitudinal",
        "optics", "mirror", "lens", "image", "ray", "angle of incidence",
        "angle of refraction", "normal", "soap film",
    ],
    "Electricity and magnetism": [
        "electric", "voltage", "current", "resistance", "circuit", "charge",
        "field", "magnet", "magnetic", "ammeter", "voltmeter", "battery",
        "series", "parallel", "ohm", "conductor", "insulator",
        "potential difference", "wire", "coil", "motor", "generator",
        "transformer", "heater", "component", "a.c.", "d.c.",
    ],
    "Nuclear physics": [
        "nuclear", "radioactive", "decay", "half-life", "atom", "particle",
        "ionising", "alpha", "beta", "gamma", "proton", "neutron", "electron",
        "nucleus", "fission", "fusion", "isotope", "atomic number",
    ],
    "Space physics": [
        "space", "planet", "star", "galaxy", "orbit", "satellite", "moon",
        "solar", "universe", "red shift", "big bang", "nebula",
    ],
}

# ---------------------------------------------------------------------------
# Skill type keyword heuristics (ordered by priority — first match wins)
# ---------------------------------------------------------------------------

# Each entry: (skill_type, [(keyword, case_sensitive)])
# Use case_sensitive=True only for short acronyms like "MP1"

SKILL_TYPE_RULES: list[tuple[str, list[str], bool]] = [
    # Practical mark-point planning questions
    ("extended_planning", ["MP1", "MP2", "MP3", "MP4", "MP5", "MP6", "MP7"], True),
    ("equation_manipulation", ["rearrange", "express in terms", "derive an expression", "show that"], False),
    ("graphing", [
        "plot", "draw a graph", "sketch a graph", "label the axes", "draw axes",
        "complete the graph", "best-fit line", "best fit line", "draw the line",
        "draw a line of best fit",
    ], False),
    ("table_design", [
        "complete the table", "fill in the table", "design a table",
        "record in the table", "table with column",
    ], False),
    ("diagram_drawing", [
        "draw a normal", "draw the normal", "circuit diagram", "ray diagram",
        "draw the path", "complete the diagram", "draw a line", "sketch the path",
        "label the normal", "draw an arrow", "draw a diagram",
    ], False),
    ("variable_control", [
        "keep constant", "control variable", "fair test", "variable kept",
        "controlled variable", "which variable",
    ], False),
    ("experimental_design", [
        "describe how you", "how would you", "describe a method", "plan an investigation",
        "design an experiment", "circuit used", "measure and record",
        "describe the procedure",
    ], False),
    ("evaluation_accuracy", [
        "source of error", "reduce the error", "improve the accuracy",
        "uncertainty", "limitation", "systematic error", "random error",
        "more accurate", "more precise", "reliable", "valid",
    ], False),
    ("data_interpretation", [
        "use the graph", "from the graph", "from the table", "read off",
        "use your graph", "use the data", "according to the graph",
        "use fig", "from fig",
    ], False),
    ("practical_calculation", [
        "use your readings", "use your measurements", "use your results",
        "calculate from your",
    ], False),
    ("measurement", [
        "measure the length", "measure the diameter", "measure the mass",
        "measure the time", "measure and record", "read the", "reading on",
        "instrument reading",
    ], False),
    ("calculation", [
        "calculate", "find the value", "work out", "determine the value",
        "what is the value", "how many", "how much", "show that",
        "find the", "determine the",
    ], False),
    ("recall_definition", [
        "state", "define", "name the", "what is meant by", "give the unit",
        "list two", "list three", "identify the", "write down", "give one",
        "give two", "give three",
    ], False),
    ("conceptual_explanation", [
        "explain", "describe", "suggest", "why does", "how does", "what causes",
        "give a reason", "justify", "account for",
    ], False),
]


def infer_topic(text: str) -> str:
    lower = text.lower()
    scores: dict[str, int] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in lower)
        if score:
            scores[topic] = score
    return max(scores, key=lambda k: scores[k]) if scores else "Unknown"


def infer_skill_type(text: str) -> str:
    lower = text.lower()
    for skill_type, keywords, case_sensitive in SKILL_TYPE_RULES:
        for kw in keywords:
            if case_sensitive:
                if kw in text:
                    return skill_type
            else:
                if kw.lower() in lower:
                    return skill_type
    return "unknown"


def clean_text(text: str) -> str:
    text = re.sub(r'\(cid:\d+\)', ' ', text)
    text = re.sub(r'[^\x20-\x7E -ɏ–—°αβγΩμ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def short_evidence(text: str, max_len: int = 180) -> str:
    cleaned = clean_text(text)
    # Strip leading question numbers / paper-header noise
    cleaned = re.sub(r'^[\d\s]+(?=\w)', '', cleaned, count=1).strip()
    if len(cleaned) <= max_len:
        return cleaned
    idx = cleaned.rfind(' ', 0, max_len)
    cut = idx if idx > max_len // 2 else max_len
    return cleaned[:cut].rstrip('.,;:') + '...'


def derive_skill_label(text: str, skill_type: str, q_num: str) -> str:
    cleaned = clean_text(text)
    # Strip leading question number
    cleaned = re.sub(r'^\d+\s*', '', cleaned).strip()
    # Take first substantive fragment up to 80 chars
    if len(cleaned) > 80:
        for sep in ('.', ',', ';', '(', '['):
            idx = cleaned.find(sep)
            if 10 < idx < 80:
                cleaned = cleaned[:idx].strip()
                break
        else:
            cleaned = cleaned[:80].strip()
    return cleaned or f"Q{q_num} ({skill_type})"


# ---------------------------------------------------------------------------
# JSON loader
# ---------------------------------------------------------------------------

def load_json(path: Path) -> tuple[dict | list | None, str]:
    try:
        return json.loads(path.read_text(encoding='utf-8')), ''
    except FileNotFoundError:
        return None, f'Not found: {path}'
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# MCQ processor
# ---------------------------------------------------------------------------

def process_mcq_source(source: dict) -> list[dict]:
    data, err = load_json(Path(source['source_file']))
    if err or not isinstance(data, dict):
        return []

    source_id = source['source_id']
    units: list[dict] = []

    for q in data.get('questions', []):
        qn    = q.get('question_number', 0)
        stem  = q.get('stem', '') or ''
        topic = q.get('topic', 'Unknown') or 'Unknown'
        sub   = q.get('subtopic', '') or ''
        skill = q.get('skill', '') or ''

        # For MCQ the default skill_type is multiple_choice_concept;
        # override only if the stem clearly indicates calculation or graph reading
        lower = stem.lower()
        if any(kw in lower for kw in ['calculate', 'work out', 'find the value']):
            skill_type = 'calculation'
        elif any(kw in lower for kw in ['from the graph', 'use the graph', 'from the table', 'use the table']):
            skill_type = 'data_interpretation'
        else:
            skill_type = 'multiple_choice_concept'

        units.append({
            'skill_unit_id':   f'{source_id}_q{int(qn):02d}',
            'source_id':       source_id,
            'pair_id':         source['pair_id'],
            'question_number': str(qn),
            'question_part':   None,
            'component_type':  'mcq',
            'assessment_mode': 'mcq',
            'topic':           topic,
            'subtopic':        sub,
            'skill':           skill,
            'skill_type':      skill_type,
            'marks':           1,
            'short_evidence':  short_evidence(stem),
            'status':          'derived',
        })

    return units


# ---------------------------------------------------------------------------
# Structured (theory / practical) processor
# ---------------------------------------------------------------------------

def _ms_items_for_question(ms_items: list[dict], q_num: str) -> list[dict]:
    matched: list[dict] = []
    seen_ids: set[int] = set()
    for item in ms_items:
        qp = item.get('question_part', '') or ''
        # Match: "2", "2(a)", "2(a)(i)", "2MP1", "MP1" when q_num == first digit
        starts = (
            qp == q_num
            or qp.startswith(q_num + '(')
            or re.match(rf'^{re.escape(q_num)}\s*MP\d', qp)
        )
        if starts and id(item) not in seen_ids:
            matched.append(item)
            seen_ids.add(id(item))
    return matched


MAX_PLAUSIBLE_MARKS = 20  # filter out spurious year-values (e.g. 2025)


def process_structured_source(source: dict) -> list[dict]:
    data, err = load_json(Path(source['source_file']))
    if err or not isinstance(data, dict):
        return []

    source_id    = source['source_id']
    comp_type    = source['component_type']
    is_practical = comp_type == 'practical_structured'
    assessment   = 'practical' if is_practical else 'theory_written'
    ms_items     = data.get('mark_scheme_items', [])
    units: list[dict] = []

    for q in data.get('questions', []):
        q_num    = str(q.get('question_number', ''))
        raw_txt  = q.get('raw_text', '') or ''
        marks_q  = q.get('marks_total_detected', 0) or 0

        matched_ms   = _ms_items_for_question(ms_items, q_num)
        ms_guidance  = ' '.join(
            (it.get('answer_guidance', '') or '') for it in matched_ms
        )

        # Check if this question uses practical mark points (MP1…MP7)
        has_mp = any(
            re.search(r'MP\d', it.get('question_part', '') or '')
            for it in matched_ms
        )

        combined = f'{raw_txt} {ms_guidance}'

        topic = infer_topic(combined)

        if has_mp:
            skill_type = 'extended_planning'
        else:
            # Use the question raw_text primarily; fall back to guidance
            skill_type = infer_skill_type(raw_txt) or infer_skill_type(ms_guidance) or 'unknown'

        # Marks: prefer marks_total_detected from question segmenter;
        # fall back to MS items (filter out spurious values)
        marks = marks_q
        if marks == 0 and matched_ms:
            plausible = [
                it.get('marks', 0) or 0
                for it in matched_ms
                if 0 < (it.get('marks') or 0) <= MAX_PLAUSIBLE_MARKS
            ]
            marks = sum(plausible)

        skill = derive_skill_label(raw_txt, skill_type, q_num)

        units.append({
            'skill_unit_id':   f'{source_id}_q{int(q_num):02d}',
            'source_id':       source_id,
            'pair_id':         source['pair_id'],
            'question_number': q_num,
            'question_part':   None,
            'component_type':  comp_type,
            'assessment_mode': assessment,
            'topic':           topic,
            'subtopic':        '',
            'skill':           skill,
            'skill_type':      skill_type,
            'marks':           marks,
            'short_evidence':  short_evidence(raw_txt),
            'status':          'derived',
        })

    return units


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def build_summary(units: list[dict]) -> dict:
    component_types:  dict[str, int] = {}
    topics:           dict[str, int] = {}
    skill_types:      dict[str, int] = {}
    assessment_modes: dict[str, int] = {}
    total_marks = 0

    for u in units:
        component_types[u['component_type']]  = component_types.get(u['component_type'], 0) + 1
        topics[u['topic']]                     = topics.get(u['topic'], 0) + 1
        skill_types[u['skill_type']]           = skill_types.get(u['skill_type'], 0) + 1
        assessment_modes[u['assessment_mode']] = assessment_modes.get(u['assessment_mode'], 0) + 1
        total_marks += u.get('marks', 0)

    return {
        'total_skill_units':   len(units),
        'component_types':     component_types,
        'topics':              topics,
        'skill_types':         skill_types,
        'assessment_modes':    assessment_modes,
        'total_marks_indexed': total_marks,
    }


def build_report(skill_map: dict, out_files: dict) -> dict:
    units         = skill_map['skill_units']
    total         = len(units)
    unknown_count = sum(1 for u in units if u['skill_type'] == 'unknown')
    unknown_pct   = round(unknown_count / total * 100, 1) if total else 0.0

    if total == 0:
        status = 'failed'
    elif unknown_pct >= 30:
        status = 'needs_review'
    else:
        status = 'passed'

    return {
        'status':              status,
        'skill_map_id':        skill_map['skill_map_id'],
        'total_skill_units':   total,
        'derived_count':       sum(1 for u in units if u['status'] == 'derived'),
        'unknown_skill_count': unknown_count,
        'unknown_pct':         unknown_pct,
        'summary':             skill_map['summary'],
        'output_files':        out_files,
    }


def build_manifest_md(skill_map: dict, report: dict) -> str:
    sm = skill_map['summary']
    lines = [
        '# Quanta Aptus Unified Skill Map v0',
        '',
        f"- **Board:** {skill_map['board'].title()}",
        f"- **Level:** {skill_map['level'].upper()}",
        f"- **Subject:** {skill_map['subject'].title()}",
        f"- **Syllabus:** {skill_map['syllabus_code']}",
        f"- **Skill Map ID:** `{skill_map['skill_map_id']}`",
        f"- **Status:** {report['status']}",
        f"- **Created:** {skill_map['created_at']}",
        '',
        f"- **Total skill units:** {sm['total_skill_units']}",
        f"- **Total marks indexed:** {sm['total_marks_indexed']}",
        f"- **Unknown skill types:** {report['unknown_skill_count']} ({report['unknown_pct']}%)",
        '',
        '## Component Types',
        '',
    ]
    for ct, count in sm['component_types'].items():
        lines.append(f'- **{ct}:** {count} units')
    lines += ['', '## Topics', '']
    for topic, count in sorted(sm['topics'].items(), key=lambda x: -x[1]):
        lines.append(f'- **{topic}:** {count} units')
    lines += ['', '## Skill Types', '']
    for st, count in sorted(sm['skill_types'].items(), key=lambda x: -x[1]):
        lines.append(f'- **{st}:** {count} units')
    lines += ['', '## Assessment Modes', '']
    for am, count in sm['assessment_modes'].items():
        lines.append(f'- **{am}:** {count} units')
    lines += ['', '## Output Paths', '']
    for key, path in report['output_files'].items():
        lines.append(f'- **{key}:** `{path}`')
    lines += [
        '',
        '---',
        '',
        '> This skill map contains ONLY derived metadata from internal source papers.',
        '> No Cambridge question content is included or published.',
        '> For internal use by Quanta Aptus curriculum team only.',
        '',
    ]
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description='Build Quanta Aptus Unified Skill Map.')
    ap.add_argument('corpus_json', help='Path to unified_source_corpus_v0.json')
    args = ap.parse_args()

    corpus_path = Path(args.corpus_json)
    if not corpus_path.exists():
        sys.exit(f'Error: file not found: {corpus_path}')

    corpus, err = load_json(corpus_path)
    if err:
        sys.exit(f'Error reading corpus: {err}')

    out_dir = corpus_path.parent.parent / 'skill_map'
    out_dir.mkdir(parents=True, exist_ok=True)

    all_units: list[dict] = []
    for source in corpus.get('sources', []):
        if source.get('status') not in ('indexed', 'needs_human_review'):
            continue
        if source['component_type'] == 'mcq':
            units = process_mcq_source(source)
        else:
            units = process_structured_source(source)
        all_units.extend(units)

    board    = corpus.get('board', 'cambridge')
    level    = corpus.get('level', 'igcse')
    subject  = corpus.get('subject', 'physics')
    syllabus = corpus.get('syllabus_code', '0625')

    skill_map_id = f'{board}_{level}_{subject}_{syllabus}_unified_skill_map_v0'

    summary = build_summary(all_units)

    skill_map = {
        'skill_map_id':      skill_map_id,
        'version':           '0.1.0',
        'status':            'internal_derived_only',
        'created_at':        datetime.now(timezone.utc).isoformat(),
        'copyright_note':    'Derived skill metadata only. No Cambridge content published.',
        'board':             board,
        'level':             level,
        'subject':           subject,
        'syllabus_code':     syllabus,
        'source_corpus_id':  corpus.get('corpus_id', ''),
        'total_skill_units': len(all_units),
        'skill_units':       all_units,
        'summary':           summary,
    }

    sm_path  = out_dir / 'unified_skill_map_v0.json'
    rep_path = out_dir / 'unified_skill_map_report.json'
    man_path = out_dir / 'unified_skill_map_manifest.md'

    out_files = {
        'skill_map': str(sm_path),
        'report':    str(rep_path),
        'manifest':  str(man_path),
    }

    report   = build_report(skill_map, out_files)
    manifest = build_manifest_md(skill_map, report)

    sm_path.write_text(json.dumps(skill_map, indent=2, ensure_ascii=False), encoding='utf-8')
    rep_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    man_path.write_text(manifest, encoding='utf-8')

    print(f"status               : {report['status']}")
    print(f"skill_map_id         : {skill_map_id}")
    print(f"total_skill_units    : {len(all_units)}")
    print(f"unknown_skill_count  : {report['unknown_skill_count']} ({report['unknown_pct']}%)")
    print(f"component_types      : {summary['component_types']}")
    print(f"topics               : {summary['topics']}")
    print(f"skill_types          : {summary['skill_types']}")
    print(f"assessment_modes     : {summary['assessment_modes']}")
    print(f"total_marks_indexed  : {summary['total_marks_indexed']}")
    print(f"skill_map            : {sm_path}")
    print(f"report               : {rep_path}")
    print(f"manifest             : {man_path}")


if __name__ == '__main__':
    main()
