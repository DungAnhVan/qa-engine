"""Registry mapping subject_slug -> SubjectAdapter instance."""
from __future__ import annotations

from .base import BaseSubjectAdapter
from .generic import GenericAdapter
from .science import (
    PhysicsAdapter,
    ChemistryAdapter,
    BiologyAdapter,
    CombinedScienceAdapter,
    EnvironmentalManagementAdapter,
)
from .mathematics import (
    MathematicsAdapter,
    AdditionalMathematicsAdapter,
    InternationalMathematicsAdapter,
)
from .computer_science import ComputerScienceAdapter, ICTAdapter
from .business_humanities import (
    BusinessAdapter,
    EconomicsAdapter,
    AccountingAdapter,
    GeographyAdapter,
    HistoryAdapter,
    GlobalPerspectivesAdapter,
    SociologyAdapter,
    TravelTourismAdapter,
)
from .languages import EnglishLanguageAdapter, LiteratureAdapter

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, BaseSubjectAdapter] = {
    # Science
    "physics_0625":              PhysicsAdapter(),
    "chemistry_0620":            ChemistryAdapter(),
    "biology_0610":              BiologyAdapter(),
    "combined_science_0653":     CombinedScienceAdapter("combined_science_0653"),
    "co_ordinated_sciences_0654": CombinedScienceAdapter("co_ordinated_sciences_0654"),
    "environmental_management_0680": EnvironmentalManagementAdapter(),

    # Mathematics
    "mathematics_0580":          MathematicsAdapter(),
    "additional_mathematics_0606": AdditionalMathematicsAdapter(),
    "international_mathematics_0607": InternationalMathematicsAdapter(),

    # Computer Science / ICT
    "computer_science_0478":     ComputerScienceAdapter(),
    "ict_0417":                  ICTAdapter(),

    # Business / Humanities
    "business_studies_0450":     BusinessAdapter(),
    "economics_0455":            EconomicsAdapter(),
    "accounting_0452":           AccountingAdapter(),
    "geography_0460":            GeographyAdapter(),
    "history_0470":              HistoryAdapter(),
    "global_perspectives_0457":  GlobalPerspectivesAdapter(),
    "sociology_0495":            SociologyAdapter(),
    "travel_and_tourism_0471":   TravelTourismAdapter(),

    # Languages
    "english_first_language_0500": EnglishLanguageAdapter("english_first_language_0500"),
    "english_second_language_0510": EnglishLanguageAdapter("english_second_language_0510"),
    "english_literature_0475":   LiteratureAdapter(),
}


def get_adapter(subject_slug: str) -> BaseSubjectAdapter:
    """
    Return the registered adapter for subject_slug, or a GenericAdapter if none found.
    Never raises; always returns a usable adapter.
    """
    return _REGISTRY.get(subject_slug, GenericAdapter(subject_slug))


def list_registered_slugs() -> list[str]:
    return sorted(_REGISTRY.keys())
