"""Base class and shared rules for Quanta Aptus subject adapters."""
from __future__ import annotations

# Shared skill-type rules: assessment-format patterns that apply across subjects.
# Entry: (skill_type, [keywords], case_sensitive)
SHARED_SKILL_TYPE_RULES: list[tuple[str, list[str], bool]] = [
    ("extended_planning", ["MP1", "MP2", "MP3", "MP4", "MP5", "MP6", "MP7"], True),
    ("equation_manipulation", [
        "rearrange", "express in terms", "derive an expression",
    ], False),
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
        "draw the path", "complete the diagram", "sketch the path",
        "draw an arrow", "draw a diagram",
    ], False),
    ("variable_control", [
        "keep constant", "control variable", "fair test", "variable kept",
        "controlled variable", "which variable",
    ], False),
    ("experimental_design", [
        "describe how you", "how would you", "describe a method", "plan an investigation",
        "design an experiment", "measure and record", "describe the procedure",
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


class BaseSubjectAdapter:
    """Base class for all Quanta Aptus subject adapters."""

    adapter_name:   str = "base"
    adapter_status: str = "generic_adapter"
    subject_slug:   str = ""

    topic_keywords:    dict[str, list[str]] = {}
    skill_type_rules:  list[tuple[str, list[str], bool]] = SHARED_SKILL_TYPE_RULES
    resource_type_map: dict[str, str] = {}

    # Confidence calibration (overridden per tier in subclasses)
    _base_conf_match: float = 0.35
    _per_kw_conf:     float = 0.08
    _conf_cap:        float = 0.80
    _conf_no_match:   float = 0.20

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _match_topic(self, text: str) -> tuple[str, list[str], float]:
        """Returns (topic, matched_keywords, confidence)."""
        lower = text.lower()
        best_topic:   str       = "Unknown"
        best_matched: list[str] = []
        best_count:   int       = 0

        for topic, keywords in self.topic_keywords.items():
            matched = [kw for kw in keywords if kw.lower() in lower]
            if len(matched) > best_count:
                best_count   = len(matched)
                best_topic   = topic
                best_matched = matched

        if best_count == 0:
            return "Unknown", [], self._conf_no_match

        confidence = min(self._conf_cap, self._base_conf_match + self._per_kw_conf * best_count)
        return best_topic, best_matched, round(confidence, 3)

    def _match_skill_type(self, text: str) -> tuple[str, list[str]]:
        """Returns (skill_type, matched_keywords). First-match wins."""
        lower = text.lower()
        for skill_type, keywords, case_sensitive in self.skill_type_rules:
            for kw in keywords:
                if case_sensitive:
                    if kw in text:
                        return skill_type, [kw]
                else:
                    if kw.lower() in lower:
                        return skill_type, [kw]
        return "unknown", []

    def _map_resource_type(self, skill_type: str, component_type: str | None = None) -> str:
        return self.resource_type_map.get(skill_type, "short_answer_concept")

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def classify_topic(self, text: str, component_type: str | None = None) -> dict:
        topic, matched_kws, confidence = self._match_topic(text)
        skill_type, _ = self._match_skill_type(text)
        resource_type  = self._map_resource_type(skill_type, component_type)
        return {
            "topic":            topic,
            "subtopic":         "",
            "skill_type":       skill_type,
            "resource_type":    resource_type,
            "confidence":       confidence,
            "adapter_status":   self.adapter_status,
            "matched_keywords": matched_kws,
        }

    def classify_skill(self, text: str, component_type: str | None = None) -> dict:
        skill_type, matched_kws = self._match_skill_type(text)
        resource_type           = self._map_resource_type(skill_type, component_type)
        _, __, confidence       = self._match_topic(text)
        return {
            "topic":            "Unknown",
            "subtopic":         "",
            "skill_type":       skill_type,
            "resource_type":    resource_type,
            "confidence":       confidence,
            "adapter_status":   self.adapter_status,
            "matched_keywords": matched_kws,
        }

    def infer_resource_type(self, text: str, component_type: str | None = None) -> dict:
        skill_type, matched_kws = self._match_skill_type(text)
        resource_type           = self._map_resource_type(skill_type, component_type)
        conf = 0.6 if skill_type != "unknown" else 0.3
        return {
            "topic":            "Unknown",
            "subtopic":         "",
            "skill_type":       skill_type,
            "resource_type":    resource_type,
            "confidence":       conf,
            "adapter_status":   self.adapter_status,
            "matched_keywords": matched_kws,
        }

    def get_resource_type(self, skill_type: str, component_type: str | None = None) -> str:
        return self._map_resource_type(skill_type, component_type)

    def get_adapter_metadata(self) -> dict:
        return {
            "adapter_name":   self.adapter_name,
            "adapter_status": self.adapter_status,
            "subject_slug":   self.subject_slug,
            "topic_count":    len(self.topic_keywords),
            "topics":         list(self.topic_keywords.keys()),
        }
