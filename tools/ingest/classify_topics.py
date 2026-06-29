"""
Classify Cambridge IGCSE Physics MCQ questions into topics using keyword rules.

Usage:
    python tools/ingest/classify_topics.py <path-to-questions.normalized.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/classify_topics.py data/ingested/markitdown/cambridge_igcse_physics_0625_2025_s_p21_qp/questions.normalized.json
"""

import sys
import re
import json
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# Classification rules
#
# Each rule: topic, subtopic, skill, keywords (list of lowercase phrases).
# Matching uses case-insensitive substring search across:
#   normalized_raw_block + stem + joined option values.
# Score = number of distinct keywords matched.
# Confidence: >= 3 → high, 2 → medium, 1 → low, 0 → unclassified.
# Rules are evaluated in order; highest score wins (ties broken by rule order).
# ---------------------------------------------------------------------------

RULES = [
    # ======================================================================
    # Motion, forces and energy
    # ======================================================================
    {
        "topic":    "Motion, forces and energy",
        "subtopic": "Motion graphs",
        "skill":    "Analyse speed–time graph",
        "keywords": [
            "speed-time", "speed–time", "velocity-time",
            "acceleration", "racing car", "four sections",
            "crashes into a wall", "deceleration",
            "which sections", "changing",
        ],
    },
    {
        "topic":    "Motion, forces and energy",
        "subtopic": "Resultant forces",
        "skill":    "Calculate resultant of forces",
        "keywords": [
            "resultant", "four forces", "aircraft in flight",
            "direction of the resultant", "120 kn", "40 kn", "60 kn",
            "which arrow shows",
        ],
    },
    {
        "topic":    "Motion, forces and energy",
        "subtopic": "Density and mass",
        "skill":    "Identify volume and weight properties",
        "keywords": [
            "force meters", "force meter", "suspended from identical",
            "identical dimensions", "metal blocks",
            "different volumes", "equal volumes",
            "different weights", "equal weights",
        ],
    },
    {
        "topic":    "Motion, forces and energy",
        "subtopic": "Springs and Hooke's law",
        "skill":    "Calculate spring constant",
        "keywords": [
            "spring constant", "spring has a length",
            "load of 2.0n", "7.0n load", "25cm", "35cm",
            "suspended from it", "spring",
        ],
    },
    {
        "topic":    "Motion, forces and energy",
        "subtopic": "Equilibrium",
        "skill":    "Identify conditions for equilibrium",
        "keywords": [
            "equilibrium", "block of wood", "frictionless surface",
            "forces acting on its sides", "block in equilibrium",
            "diagrams e", "diagrams f", "diagrams g", "diagrams h",
        ],
    },
    {
        "topic":    "Motion, forces and energy",
        "subtopic": "Momentum and impulse",
        "skill":    "Recall and apply momentum principles",
        "keywords": [
            "momentum", "impulse", "change of momentum",
            "mass  velocity", "force acting = change",
            "conserved in all interactions",
        ],
    },
    {
        "topic":    "Motion, forces and energy",
        "subtopic": "Newton's laws of motion",
        "skill":    "Apply Newton's second law",
        "keywords": [
            "force acting on a moving ball",
            "causes its motion to change",
            "greater change in the motion",
            "total mass of the ball", "hollow centre",
            "lower density but the same mass",
        ],
    },
    {
        "topic":    "Motion, forces and energy",
        "subtopic": "Pressure",
        "skill":    "Apply pressure concept (force/area)",
        "keywords": [
            "narrow wheel", "wide wheel", "carts",
            "sink less into soft ground",
            "pressure on the ground", "less pressure",
            "greater pressure", "four narrow wheels", "four wide wheels",
        ],
    },
    # ======================================================================
    # General measurement / practical skills
    # ======================================================================
    {
        "topic":    "General measurement / practical skills",
        "subtopic": "Density practical",
        "skill":    "Select appropriate apparatus for density measurement",
        "keywords": [
            "gold necklace", "density of the gold",
            "measuring cylinder", "balance", "thermometer", "ruler",
            "apparatus", "needed", "not needed",
        ],
    },
    # ======================================================================
    # Thermal physics
    # ======================================================================
    {
        "topic":    "Thermal physics",
        "subtopic": "Particle model of matter",
        "skill":    "Compare particle separation and motion",
        "keywords": [
            "separation of gas particles", "motion of gas particles",
            "hot gas", "cool liquid", "at the same pressure",
            "faster than a cool liquid", "slower than a cool liquid",
            "greater than a cool liquid", "less than a cool liquid",
        ],
    },
    {
        "topic":    "Thermal physics",
        "subtopic": "Gas laws",
        "skill":    "Apply Boyle's law (pressure–volume)",
        "keywords": [
            "fixed mass of gas", "volume of 1.2", "volume of 1.8",
            "constant temperature", "gas expands",
            "new pressure of the gas", "200kpa",
        ],
    },
    {
        "topic":    "Thermal physics",
        "subtopic": "Gas laws and kinetic theory",
        "skill":    "Explain pressure increase using particle model",
        "keywords": [
            "sealed container of gas", "gas is heated",
            "pressure of the gas increases", "increase in pressure",
            "particles striking the walls", "gas particles collide",
            "gas particles lose more energy",
        ],
    },
    {
        "topic":    "Thermal physics",
        "subtopic": "Specific heat capacity",
        "skill":    "Interpret specific heat capacity definition",
        "keywords": [
            "specific heat capacity", "temperature by 1",
            "unit mass of solid", "raise the temperature",
            "more energy is needed", "less energy is needed",
        ],
    },
    {
        "topic":    "Thermal physics",
        "subtopic": "Evaporation",
        "skill":    "Recall what escapes during evaporation",
        "keywords": [
            "evaporates", "escapes from the surface of the water",
            "individual molecules", "individual atoms",
            "surface of the water",
        ],
    },
    {
        "topic":    "Thermal physics",
        "subtopic": "Thermal conduction",
        "skill":    "Compare thermal conduction of materials",
        "keywords": [
            "copper rod", "wooden rod", "beaker of crushed ice",
            "better conductor", "feels colder", "feels warmer",
            "conductor than wood", "conductor than copper",
        ],
    },
    {
        "topic":    "Thermal physics",
        "subtopic": "Thermal radiation",
        "skill":    "Compare absorption and emission of thermal radiation",
        "keywords": [
            "thermal radiation", "black object", "white surface",
            "rate of absorption", "rate of emission",
            "absorption and emission", "emission for x",
            "constant temperature", "object y",
        ],
    },
    # ======================================================================
    # Waves
    # ======================================================================
    {
        "topic":    "Waves",
        "subtopic": "Wave motion",
        "skill":    "Recall direction of particle vibration in transverse waves",
        "keywords": [
            "transverse waves", "cork", "water surface",
            "direction do the waves make the cork",
            "waves travel across the water", "weight attached",
        ],
    },
    {
        "topic":    "Waves",
        "subtopic": "Lenses",
        "skill":    "Describe image formed by converging lens",
        "keywords": [
            "converging lens", "magnifying glass",
            "image compare with the object",
            "real and inverted", "real and upright",
            "virtual and inverted", "virtual and upright",
        ],
    },
    {
        "topic":    "Waves",
        "subtopic": "Reflection",
        "skill":    "Apply law of reflection at plane mirrors",
        "keywords": [
            "plane mirrors", "90", "reflects off both mirrors",
            "reaching a screen", "ray of light is incident",
            "labelled point does the ray",
        ],
    },
    {
        "topic":    "Waves",
        "subtopic": "Refraction",
        "skill":    "Calculate refractive index",
        "keywords": [
            "refractive index", "speed of light in a material",
            "50% of the speed of light",
            "speed of light in air",
        ],
    },
    {
        "topic":    "Waves",
        "subtopic": "Dispersion",
        "skill":    "Recall the name of white light splitting",
        "keywords": [
            "spectrum of seven colours", "beam of white light",
            "dispersion", "split into a spectrum",
            "which name is given to this process",
        ],
    },
    {
        "topic":    "Waves",
        "subtopic": "Electromagnetic spectrum",
        "skill":    "Identify EM wave type used by satellites",
        "keywords": [
            "satellites", "electromagnetic waves",
            "geostationary", "low orbit",
            "television signals", "re-transmit",
        ],
    },
    {
        "topic":    "Waves",
        "subtopic": "Sound",
        "skill":    "Compare speed and wavelength of sound in different media",
        "keywords": [
            "sound wave", "solid block of steel",
            "speed in steel", "wavelength in steel",
            "transmitted through the steel",
            "speed and the wavelength of the sound",
        ],
    },
    # ======================================================================
    # Electricity and magnetism
    # ======================================================================
    {
        "topic":    "Electricity and magnetism",
        "subtopic": "Electric fields",
        "skill":    "Recall electric field definition and direction",
        "keywords": [
            "electric field", "electric charge",
            "charge experiences a force",
            "direction of the force on a positive charge",
            "direction of the force on a negative charge",
            "charge produces a current",
        ],
    },
    {
        "topic":    "Electricity and magnetism",
        "subtopic": "Resistance",
        "skill":    "Determine resistance–diameter relationship",
        "keywords": [
            "copper wire", "resistance r", "diameters d",
            "directly proportional to d", "inversely proportional to d",
            "fixed lengths but in various diameters",
        ],
    },
    {
        "topic":    "Electricity and magnetism",
        "subtopic": "Circuits",
        "skill":    "Calculate potential difference when switch is closed",
        "keywords": [
            "resistors", "potential difference", "p.d.",
            "switch s is open", "switch s is closed",
            "9.0v", "3.0v", "6.0v", "27v",
            "d.c. power supply",
        ],
    },
    {
        "topic":    "Electricity and magnetism",
        "subtopic": "Diodes and LEDs",
        "skill":    "Identify circuit in which LEDs conduct",
        "keywords": [
            "led", "diode", "light-emitting diodes",
            "leds be turned on", "circuits shown",
        ],
    },
    {
        "topic":    "Electricity and magnetism",
        "subtopic": "Electromagnetic induction",
        "skill":    "Identify direction of wire movement from induced current",
        "keywords": [
            "current is induced", "wire connected to a resistor",
            "direction is the wire moved",
            "moved in a magnetic field",
        ],
    },
    {
        "topic":    "Electricity and magnetism",
        "subtopic": "Generators",
        "skill":    "Identify component not found in a.c. generator",
        "keywords": [
            "a.c. generator", "split-ring commutator",
            "slip rings", "coil of wire",
            "not found in an a.c. generator", "magnetic poles",
        ],
    },
    {
        "topic":    "Electricity and magnetism",
        "subtopic": "Magnetic fields",
        "skill":    "Identify magnetic poles and field strength from field pattern",
        "keywords": [
            "bracelet", "two magnets",
            "magnetic pole at j", "magnetic pole at k",
            "field is the strongest", "arrows represent the pattern",
            "direction of the magnetic field due to the magnets",
        ],
    },
    {
        "topic":    "Electricity and magnetism",
        "subtopic": "Magnetic fields",
        "skill":    "Describe direction and pattern of magnetic field around wire",
        "keywords": [
            "straight metal wire", "direction of current",
            "pattern of the magnetic field due to the wire",
            "anticlockwise", "clockwise",
            "parallel lines", "looking from vertically above",
        ],
    },
    {
        "topic":    "Electricity and magnetism",
        "subtopic": "Transformers",
        "skill":    "Recall function of iron core in transformer",
        "keywords": [
            "transformer", "iron core",
            "primary coil", "secondary coil",
            "function of the iron core",
        ],
    },
    # ======================================================================
    # Nuclear physics
    # ======================================================================
    {
        "topic":    "Nuclear physics",
        "subtopic": "Rutherford scattering",
        "skill":    "Apply Rutherford scattering experiment results",
        "keywords": [
            "alpha particle scattering", "gold foil",
            "alpha particles", "direction do most of the alpha particles",
            "very thin piece of gold",
        ],
    },
    {
        "topic":    "Nuclear physics",
        "subtopic": "Atomic structure",
        "skill":    "Calculate neutron number from nucleon number",
        "keywords": [
            "atom of boron", "protons", "electrons", "neutrons",
            "nucleon number", "how many neutrons",
            "5 protons and 5 electrons",
        ],
    },
    {
        "topic":    "Nuclear physics",
        "subtopic": "Half-life",
        "skill":    "Calculate count rate after given number of half-lives",
        "keywords": [
            "half-life", "count rate", "background count rate",
            "counts/minute", "six hours", "three hours",
            "radioactive isotope gives a measured",
        ],
    },
    {
        "topic":    "Nuclear physics",
        "subtopic": "Radioactive decay",
        "skill":    "Interpret nuclear decay equation",
        "keywords": [
            "sodium-24", "beta radiation", "nuclear equation",
            "how sodium-24 decays", "24na",
            "radioactive isotope that emits",
        ],
    },
    {
        "topic":    "Nuclear physics",
        "subtopic": "Radiation safety",
        "skill":    "Recall gamma radiation safety precautions",
        "keywords": [
            "gamma radiation", "safety precautions",
            "shielding material", "time of exposure",
            "distance between the source",
            "source of gamma radiation",
        ],
    },
    # ======================================================================
    # Space physics
    # ======================================================================
    {
        "topic":    "Space physics",
        "subtopic": "Orbital periods",
        "skill":    "Order orbital and rotational periods of Earth and Moon",
        "keywords": [
            "earth to orbit the sun", "moon to orbit the earth",
            "rotate once on its axis", "period of time",
            "shortest period", "longest period",
            "three periods of time",
        ],
    },
    {
        "topic":    "Space physics",
        "subtopic": "Universe and redshift",
        "skill":    "Recall properties of the Universe and redshift",
        "keywords": [
            "universe", "100000 galaxies", "redshift",
            "receding galaxies", "contracting",
            "electromagnetic radiation emitted from",
            "observed wavelength",
        ],
    },
    {
        "topic":    "Space physics",
        "subtopic": "Cosmic microwave background radiation",
        "skill":    "Recall properties of CMBR",
        "keywords": [
            "cosmic microwave background", "cmbr",
            "frequency higher than", "shorter wavelength in the past",
            "universe was formed",
        ],
    },
]


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def build_search_text(q):
    """Combine all text fields for keyword search (lowercase)."""
    parts = [
        q.get("normalized_raw_block", ""),
        q.get("stem", ""),
    ]
    for v in q.get("options", {}).values():
        parts.append(str(v))
    return " ".join(parts).lower()


def classify_question(q):
    text = build_search_text(q)

    best_rule   = None
    best_score  = 0
    best_matched = []

    for rule in RULES:
        matched = [kw for kw in rule["keywords"] if kw in text]
        score   = len(matched)
        if score > best_score:
            best_score  = score
            best_rule   = rule
            best_matched = matched

    if best_rule is None or best_score == 0:
        return {
            "topic":               "Needs manual classification",
            "subtopic":            "Unknown",
            "skill":               "Unknown",
            "confidence":          "low",
            "matched_keywords":    [],
            "classification_note": "No keywords matched any rule",
        }

    if best_score >= 3:
        confidence = "high"
    elif best_score == 2:
        confidence = "medium"
    else:
        confidence = "low"

    note = (
        f"Matched {best_score} keyword(s) in subtopic "
        f"'{best_rule['subtopic']}': {best_matched}"
    )

    return {
        "topic":               best_rule["topic"],
        "subtopic":            best_rule["subtopic"],
        "skill":               best_rule["skill"],
        "confidence":          confidence,
        "matched_keywords":    best_matched,
        "classification_note": note,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def classify(normalized_path):
    data = json.loads(normalized_path.read_text(encoding="utf-8"))
    questions_in = data["questions"]

    out_questions = []
    for q in questions_in:
        clf = classify_question(q)

        needs_review = q.get("needs_review", False) or clf["confidence"] == "low"

        out_questions.append({
            "question_number":     q["question_number"],
            "topic":               clf["topic"],
            "subtopic":            clf["subtopic"],
            "skill":               clf["skill"],
            "confidence":          clf["confidence"],
            "matched_keywords":    clf["matched_keywords"],
            "needs_review":        needs_review,
            "classification_note": clf["classification_note"],
            "original_question":   q,
        })

    total = len(out_questions)

    # ---- topic_coverage ---------------------------------------------------
    topic_map = defaultdict(list)
    for q in out_questions:
        topic_map[q["topic"]].append(q["question_number"])

    coverage = sorted(
        [
            {"topic": topic, "count": len(nums), "question_numbers": sorted(nums)}
            for topic, nums in topic_map.items()
        ],
        key=lambda x: -x["count"],
    )

    low_conf_nums  = [q["question_number"] for q in out_questions if q["confidence"] == "low"]
    needs_rev_nums = [q["question_number"] for q in out_questions if q["needs_review"]]

    # ---- Write outputs ----------------------------------------------------
    out_dir = normalized_path.parent

    classified_path = out_dir / "questions.classified.json"
    classified_path.write_text(
        json.dumps(
            {
                "source_questions": str(normalized_path),
                "total_questions":  total,
                "questions":        out_questions,
            },
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    coverage_path = out_dir / "topic_coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "total_questions":          total,
                "coverage":                 coverage,
                "low_confidence_questions": low_conf_nums,
                "needs_review_questions":   needs_rev_nums,
            },
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ---- Terminal output --------------------------------------------------
    print(f"total_questions          : {total}")
    print()
    print("topic counts:")
    for c in coverage:
        print(f"  {c['count']:2d}  {c['topic']}  {c['question_numbers']}")
    print()
    print(f"low_confidence_questions : {low_conf_nums}")
    print()
    print(f"questions.classified     : {classified_path}")
    print(f"topic_coverage           : {coverage_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <path-to-questions.normalized.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    classify(p)
