"""Subject adapters for Cambridge IGCSE Language subjects."""
from __future__ import annotations
from .base import BaseSubjectAdapter

_LANG_SKILL_TYPE_RULES: list[tuple[str, list[str], bool]] = [
    ("extended_planning", [
        "write an essay", "write a story", "write a description", "write a speech",
        "write an article", "write a letter", "write a report", "composition",
        "plan your writing", "extended writing",
    ], False),
    ("data_interpretation", [
        "from the passage", "from the text", "from the extract", "according to",
        "what does the writer", "the writer suggests", "use evidence from",
    ], False),
    ("recall_definition", [
        "identify", "list", "name", "give", "write down", "find", "locate",
        "which word", "which phrase",
    ], False),
    ("conceptual_explanation", [
        "explain", "how does", "why does", "what effect", "what impression",
        "analyse", "comment on", "discuss the language", "how does the writer",
    ], False),
]

_LANG_RESOURCE_TYPE_MAP: dict[str, str] = {
    "extended_planning":      "composition_prompt",
    "data_interpretation":    "reading_analysis_task",
    "recall_definition":      "reading_analysis_task",
    "conceptual_explanation": "reading_analysis_task",
    "unknown":                "directed_writing_task",
}

_LIT_SKILL_TYPE_RULES: list[tuple[str, list[str], bool]] = [
    ("extended_planning", [
        "write an essay", "how does the writer", "analyse", "explore",
        "discuss", "evaluate", "compare",
    ], False),
    ("data_interpretation", [
        "from the extract", "from the passage", "refer to the text",
        "using evidence", "select evidence",
    ], False),
    ("recall_definition", [
        "identify", "list", "give", "name", "what happens",
    ], False),
    ("conceptual_explanation", [
        "explain", "how does", "what effect", "comment on", "describe",
        "what impression", "how is", "language",
    ], False),
]

_LIT_RESOURCE_TYPE_MAP: dict[str, str] = {
    "extended_planning":      "essay_planning_task",
    "data_interpretation":    "evidence_selection_task",
    "recall_definition":      "reading_analysis_task",
    "conceptual_explanation": "reading_analysis_task",
    "unknown":                "essay_planning_task",
}


class EnglishLanguageAdapter(BaseSubjectAdapter):
    adapter_name      = "english_language"
    adapter_status    = "basic_adapter"
    skill_type_rules  = _LANG_SKILL_TYPE_RULES
    resource_type_map = _LANG_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.40
    _per_kw_conf:     float = 0.08
    _conf_cap:        float = 0.75
    _conf_no_match:   float = 0.30

    def __init__(self, subject_slug: str = "english_first_language_0500") -> None:
        self.subject_slug = subject_slug
        self.adapter_name = f"english_language_{subject_slug}"

    topic_keywords: dict[str, list[str]] = {
        "Reading comprehension": [
            "comprehension", "read", "passage", "text", "extract", "answer questions",
        ],
        "Writer's effect": [
            "writer", "language", "effect", "technique", "imagery", "metaphor",
            "simile", "personification", "alliteration",
        ],
        "Summary writing": [
            "summary", "summarise", "main points", "key information",
        ],
        "Directed writing": [
            "letter", "report", "article", "speech", "interview", "leaflet",
            "directed writing", "format",
        ],
        "Composition": [
            "composition", "story", "narrative", "descriptive", "creative",
            "write about", "describe",
        ],
        "Argumentative writing": [
            "argue", "persuade", "discuss", "opinion", "viewpoint", "counterargument",
        ],
        "Descriptive writing": [
            "describe", "description", "setting", "scene", "atmosphere",
            "sensory", "imagery",
        ],
        "Narrative writing": [
            "story", "narrative", "character", "plot", "conflict", "resolution",
            "first person", "third person",
        ],
        "Language analysis": [
            "language", "technique", "effect", "connotation", "tone", "style",
            "structure",
        ],
    }


class LiteratureAdapter(BaseSubjectAdapter):
    adapter_name      = "english_literature_0475"
    adapter_status    = "basic_adapter"
    subject_slug      = "english_literature_0475"
    skill_type_rules  = _LIT_SKILL_TYPE_RULES
    resource_type_map = _LIT_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.40
    _per_kw_conf:     float = 0.08
    _conf_cap:        float = 0.75
    _conf_no_match:   float = 0.30

    topic_keywords: dict[str, list[str]] = {
        "Character": [
            "character", "characterisation", "protagonist", "antagonist",
            "narrator", "personality", "motivation",
        ],
        "Theme": [
            "theme", "power", "conflict", "love", "loss", "identity",
            "society", "justice", "freedom",
        ],
        "Setting": [
            "setting", "place", "time", "atmosphere", "environment",
            "context", "backdrop",
        ],
        "Plot": [
            "plot", "story", "events", "narrative", "beginning", "middle",
            "end", "climax", "resolution", "turning point",
        ],
        "Language and imagery": [
            "language", "imagery", "metaphor", "simile", "symbolism",
            "alliteration", "personification", "connotation",
        ],
        "Structure": [
            "structure", "form", "stanza", "chapter", "act", "scene",
            "chronological", "flashback", "sequence",
        ],
        "Tone": [
            "tone", "mood", "atmosphere", "voice", "register", "irony",
            "humour", "sarcasm",
        ],
        "Context": [
            "historical context", "social context", "cultural context",
            "biographical", "time period",
        ],
        "Essay argument": [
            "argue", "analyse", "evaluate", "discuss", "explore", "how does",
            "to what extent", "compare",
        ],
        "Evidence selection": [
            "evidence", "quotation", "quote", "reference", "support",
            "embed", "use evidence from",
        ],
    }
