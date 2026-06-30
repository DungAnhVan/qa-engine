"""Generic fallback adapter for unknown subjects."""
from __future__ import annotations
from .base import BaseSubjectAdapter


class GenericAdapter(BaseSubjectAdapter):
    """
    Used when no subject-specific adapter is registered.
    Always produces low confidence and marks needs_human_review = True.
    """

    adapter_status = "generic_adapter"

    # Generic fallback topic keywords that work for any subject
    topic_keywords: dict[str, list[str]] = {}

    # Confidence calibration: always <= 0.35 per spec
    _base_conf_match: float = 0.20
    _per_kw_conf:     float = 0.03
    _conf_cap:        float = 0.35
    _conf_no_match:   float = 0.15

    resource_type_map: dict[str, str] = {}

    def __init__(self, subject_slug: str = "unknown") -> None:
        self.subject_slug = subject_slug
        self.adapter_name = f"generic_{subject_slug}"

    def classify_topic(self, text: str, component_type: str | None = None) -> dict:
        result = super().classify_topic(text, component_type)
        # Generic adapter always caps at 0.35
        result["confidence"] = min(0.35, result["confidence"])
        return result

    def classify_skill(self, text: str, component_type: str | None = None) -> dict:
        result = super().classify_skill(text, component_type)
        result["confidence"] = min(0.35, result["confidence"])
        return result

    def get_adapter_metadata(self) -> dict:
        meta = super().get_adapter_metadata()
        meta["note"] = (
            "No subject-specific adapter registered. "
            "All items will be marked needs_human_review=True."
        )
        return meta
