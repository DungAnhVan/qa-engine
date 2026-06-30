"""Subject adapters for Cambridge IGCSE Mathematics subjects."""
from __future__ import annotations
from .base import BaseSubjectAdapter

_MATH_SKILL_TYPE_RULES: list[tuple[str, list[str], bool]] = [
    ("extended_planning", ["prove that", "justify your answer", "show all your working"], False),
    ("equation_manipulation", [
        "solve", "factorise", "expand", "simplify", "rearrange",
        "express in terms", "make the subject",
    ], False),
    ("graphing", [
        "plot", "draw a graph", "sketch", "complete the graph", "label the axes",
    ], False),
    ("table_design", [
        "complete the table", "fill in the table", "table of values",
    ], False),
    ("data_interpretation", [
        "from the graph", "use the graph", "from the table", "read off",
        "use the data", "use your graph",
    ], False),
    ("calculation", [
        "calculate", "find", "work out", "determine", "evaluate",
        "what is the value", "how many", "how much", "show that",
    ], False),
    ("recall_definition", [
        "state", "define", "write down", "give", "list", "name",
    ], False),
    ("conceptual_explanation", [
        "explain", "describe", "justify", "give a reason", "account for",
    ], False),
]

_MATH_RESOURCE_TYPE_MAP: dict[str, str] = {
    "calculation":            "calculation_drill",
    "equation_manipulation":  "algebra_drill",
    "graphing":               "graphing_drill",
    "data_interpretation":    "calculation_drill",
    "diagram_drawing":        "geometry_drill",
    "extended_planning":      "proof_or_reasoning_prompt",
    "table_design":           "marking_checklist",
    "recall_definition":      "worked_example",
    "conceptual_explanation": "worked_example",
    "multiple_choice_concept": "worked_example",
    "unknown":                "multi_step_problem",
}

_MATH_TOPICS: dict[str, list[str]] = {
    "Number": [
        "integer", "fraction", "decimal", "percentage", "ratio", "proportion",
        "standard form", "significant figure", "prime", "factor", "multiple",
        "square root", "cube root", "power", "index", "rounding", "estimation",
        "lower bound", "upper bound",
    ],
    "Algebra": [
        "algebra", "equation", "expression", "expand", "factorise", "simplify",
        "variable", "coefficient", "linear", "quadratic", "polynomial",
        "inequality", "sequence", "formula", "substitution", "simultaneous",
        "algebraic fraction",
    ],
    "Geometry": [
        "angle", "triangle", "circle", "polygon", "quadrilateral", "parallel",
        "perpendicular", "congruent", "similar", "proof", "theorem", "arc",
        "chord", "tangent", "sector", "symmetry", "isosceles", "equilateral",
        "interior angle", "exterior angle",
    ],
    "Mensuration": [
        "area", "volume", "perimeter", "surface area", "cylinder", "cone",
        "sphere", "prism", "pyramid", "radius", "diameter", "circumference",
        "cross-section",
    ],
    "Coordinate geometry": [
        "coordinate", "gradient", "slope", "y-intercept", "midpoint",
        "equation of line", "x-axis", "y-axis", "straight line", "perpendicular bisector",
    ],
    "Trigonometry": [
        "sine", "cosine", "tangent", "sin", "cos", "tan", "hypotenuse",
        "opposite", "adjacent", "trigonometry", "bearing", "Pythagoras",
        "right-angled triangle", "sine rule", "cosine rule",
    ],
    "Graphs": [
        "graph", "function", "curve", "quadratic graph", "cubic", "reciprocal",
        "exponential", "gradient of curve", "tangent to curve",
    ],
    "Probability": [
        "probability", "event", "outcome", "likelihood", "random", "sample space",
        "tree diagram", "Venn diagram", "independent", "mutually exclusive",
        "conditional probability",
    ],
    "Statistics": [
        "mean", "median", "mode", "range", "average", "frequency", "histogram",
        "pie chart", "bar chart", "scatter diagram", "correlation", "cumulative frequency",
        "interquartile range", "quartile", "percentile", "moving average",
    ],
    "Vectors and transformations": [
        "vector", "translation", "rotation", "reflection", "enlargement",
        "transformation", "column vector", "magnitude", "scale factor",
    ],
}


class MathematicsAdapter(BaseSubjectAdapter):
    adapter_name      = "mathematics_0580"
    adapter_status    = "basic_adapter"
    subject_slug      = "mathematics_0580"
    skill_type_rules  = _MATH_SKILL_TYPE_RULES
    resource_type_map = _MATH_RESOURCE_TYPE_MAP
    topic_keywords    = _MATH_TOPICS

    _base_conf_match: float = 0.45
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.85
    _conf_no_match:   float = 0.30


class AdditionalMathematicsAdapter(MathematicsAdapter):
    adapter_name = "additional_mathematics_0606"
    subject_slug = "additional_mathematics_0606"


class InternationalMathematicsAdapter(MathematicsAdapter):
    adapter_name = "international_mathematics_0607"
    subject_slug = "international_mathematics_0607"
