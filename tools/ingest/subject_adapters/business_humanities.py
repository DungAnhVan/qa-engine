"""Subject adapters for Cambridge IGCSE Business and Humanities subjects."""
from __future__ import annotations
from .base import BaseSubjectAdapter

_BH_SKILL_TYPE_RULES: list[tuple[str, list[str], bool]] = [
    ("extended_planning", [
        "write an essay", "plan your answer", "discuss", "evaluate",
        "to what extent", "assess", "analyse",
    ], False),
    ("data_interpretation", [
        "from the data", "from the table", "from the graph", "from the source",
        "use the information", "from the extract",
    ], False),
    ("calculation", [
        "calculate", "work out", "find the value", "how much", "what is the total",
    ], False),
    ("table_design", [
        "complete the table", "fill in the table",
    ], False),
    ("recall_definition", [
        "state", "define", "name", "identify", "list", "give", "write down",
        "what is meant by",
    ], False),
    ("conceptual_explanation", [
        "explain", "describe", "why", "how", "give a reason", "suggest",
        "justify", "compare",
    ], False),
]

_BH_RESOURCE_TYPE_MAP: dict[str, str] = {
    "extended_planning":      "essay_planning_task",
    "data_interpretation":    "data_response_task",
    "calculation":            "calculation_drill",
    "table_design":           "marking_checklist",
    "recall_definition":      "short_answer_concept",
    "conceptual_explanation": "case_study_analysis",
    "unknown":                "short_answer_concept",
}

_HUMANITIES_SKILL_TYPE_RULES: list[tuple[str, list[str], bool]] = [
    ("extended_planning", [
        "write an essay", "argue", "evaluate", "to what extent", "discuss",
        "assess the significance",
    ], False),
    ("data_interpretation", [
        "from the source", "from the extract", "from the map", "use the source",
        "what does the source", "how useful",
    ], False),
    ("recall_definition", [
        "state", "name", "identify", "list", "give", "write down",
        "what was", "when did",
    ], False),
    ("conceptual_explanation", [
        "explain", "describe", "why", "how", "give a reason", "suggest",
        "compare", "account for", "what caused",
    ], False),
]

_HUMANITIES_RESOURCE_TYPE_MAP: dict[str, str] = {
    "extended_planning":      "essay_planning_task",
    "data_interpretation":    "source_analysis_task",
    "recall_definition":      "short_answer_concept",
    "conceptual_explanation": "extended_response_plan",
    "unknown":                "short_answer_concept",
}


class BusinessAdapter(BaseSubjectAdapter):
    adapter_name      = "business_studies_0450"
    adapter_status    = "basic_adapter"
    subject_slug      = "business_studies_0450"
    skill_type_rules  = _BH_SKILL_TYPE_RULES
    resource_type_map = _BH_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.45
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.85
    _conf_no_match:   float = 0.30

    topic_keywords: dict[str, list[str]] = {
        "Business activity": [
            "business", "enterprise", "entrepreneur", "profit", "revenue",
            "stakeholder", "objective", "mission", "sector", "private", "public",
        ],
        "People in business": [
            "motivation", "leadership", "management", "employee", "recruitment",
            "training", "communication", "organisation", "hierarchy",
        ],
        "Marketing": [
            "marketing", "market research", "consumer", "product", "price",
            "promotion", "place", "brand", "segmentation", "competition",
        ],
        "Operations management": [
            "production", "quality", "supply chain", "stock", "lean", "capacity",
            "efficiency", "labour", "capital intensive", "automation",
        ],
        "Finance": [
            "revenue", "cost", "profit", "loss", "cash flow", "budget",
            "balance sheet", "break even", "depreciation", "income statement",
        ],
        "External influences": [
            "economic", "government", "tax", "interest rate", "inflation",
            "environment", "globalisation", "competition", "technology",
        ],
    }


class EconomicsAdapter(BaseSubjectAdapter):
    adapter_name      = "economics_0455"
    adapter_status    = "basic_adapter"
    subject_slug      = "economics_0455"
    skill_type_rules  = _BH_SKILL_TYPE_RULES
    resource_type_map = _BH_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.45
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.85
    _conf_no_match:   float = 0.30

    topic_keywords: dict[str, list[str]] = {
        "Basic economic problem": [
            "scarcity", "choice", "opportunity cost", "resource", "need",
            "want", "factor of production", "land", "labour", "capital",
        ],
        "Allocation of resources": [
            "demand", "supply", "market", "price", "equilibrium", "elasticity",
            "consumer", "producer", "subsidy", "tax", "maximum price",
        ],
        "Microeconomic decision makers": [
            "firm", "business", "household", "worker", "bank", "saving",
            "investment", "wage", "profit", "cost",
        ],
        "Government and macroeconomy": [
            "government", "GDP", "economic growth", "inflation", "unemployment",
            "fiscal policy", "monetary policy", "interest rate", "budget deficit",
        ],
        "Economic development": [
            "development", "poverty", "HDI", "standard of living", "income",
            "inequality", "aid", "trade", "population",
        ],
        "International trade": [
            "trade", "export", "import", "tariff", "quota", "balance of payments",
            "exchange rate", "globalisation", "protectionism",
        ],
    }


class AccountingAdapter(BaseSubjectAdapter):
    adapter_name      = "accounting_0452"
    adapter_status    = "basic_adapter"
    subject_slug      = "accounting_0452"
    skill_type_rules  = _BH_SKILL_TYPE_RULES
    resource_type_map = _BH_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.45
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.85
    _conf_no_match:   float = 0.30

    topic_keywords: dict[str, list[str]] = {
        "Bookkeeping": [
            "double entry", "ledger", "debit", "credit", "journal", "trial balance",
            "account", "T-account", "transaction",
        ],
        "Financial statements": [
            "income statement", "balance sheet", "profit and loss", "revenue",
            "expense", "asset", "liability", "capital", "equity",
        ],
        "Accounting principles": [
            "accrual", "matching", "consistency", "prudence", "going concern",
            "materiality", "accounting concept",
        ],
        "Control accounts": [
            "control account", "receivables", "payables", "debtor", "creditor",
            "reconciliation",
        ],
        "Incomplete records": [
            "incomplete record", "missing figure", "mark-up", "margin",
            "gross profit", "net profit",
        ],
        "Clubs and societies": [
            "club", "society", "subscription", "receipts and payments",
            "income and expenditure",
        ],
        "Manufacturing accounts": [
            "manufacturing", "cost of production", "prime cost", "factory",
            "overhead", "work in progress",
        ],
        "Analysis and interpretation": [
            "ratio", "liquidity", "profitability", "solvency", "current ratio",
            "return on capital", "gross profit percentage",
        ],
    }


class GeographyAdapter(BaseSubjectAdapter):
    adapter_name      = "geography_0460"
    adapter_status    = "basic_adapter"
    subject_slug      = "geography_0460"
    skill_type_rules  = _HUMANITIES_SKILL_TYPE_RULES
    resource_type_map = _HUMANITIES_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.45
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.85
    _conf_no_match:   float = 0.30

    topic_keywords: dict[str, list[str]] = {
        "Population and settlement": [
            "population", "migration", "urbanisation", "city", "birth rate",
            "death rate", "settlement", "rural", "urban",
        ],
        "Natural environments": [
            "river", "coast", "weather", "climate", "erosion", "deposition",
            "ecosystem", "tropical rainforest", "desert", "tectonic",
        ],
        "Economic development": [
            "development", "GDP", "HDI", "industry", "agriculture", "tourism",
            "trade", "globalisation", "transnational",
        ],
        "Geographical skills": [
            "map", "graph", "data", "fieldwork", "survey", "questionnaire",
            "sample", "statistics",
        ],
        "Map skills": [
            "contour", "scale", "grid reference", "compass", "cross-section",
            "OS map", "topographic",
        ],
        "Data interpretation": [
            "data", "graph", "table", "chart", "statistics", "trend",
            "pattern", "correlation",
        ],
        "Fieldwork": [
            "fieldwork", "transect", "survey", "primary data", "secondary data",
            "investigation", "hypothesis",
        ],
    }


class HistoryAdapter(BaseSubjectAdapter):
    adapter_name      = "history_0470"
    adapter_status    = "basic_adapter"
    subject_slug      = "history_0470"
    skill_type_rules  = _HUMANITIES_SKILL_TYPE_RULES
    resource_type_map = _HUMANITIES_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.45
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.85
    _conf_no_match:   float = 0.30

    topic_keywords: dict[str, list[str]] = {
        "Source analysis": [
            "source", "reliable", "useful", "bias", "purpose", "provenance",
            "cross-reference", "primary", "secondary", "evidence",
        ],
        "Cause and consequence": [
            "cause", "consequence", "reason", "result", "led to", "because",
            "effect", "impact", "trigger",
        ],
        "Change and continuity": [
            "change", "continuity", "stayed the same", "changed", "development",
            "progress",
        ],
        "Similarity and difference": [
            "similar", "different", "compare", "contrast", "alike", "unlike",
            "both", "however",
        ],
        "Significance": [
            "significant", "importance", "impact", "consequences", "key",
            "turning point",
        ],
        "Essay argument": [
            "argue", "argue that", "to what extent", "how far", "assess",
            "evaluate", "discuss", "overall",
        ],
        "Evidence evaluation": [
            "evidence", "support", "contradict", "challenge", "agree",
            "disagree", "interpretation",
        ],
    }


class GlobalPerspectivesAdapter(BaseSubjectAdapter):
    adapter_name      = "global_perspectives_0457"
    adapter_status    = "basic_adapter"
    subject_slug      = "global_perspectives_0457"
    skill_type_rules  = _HUMANITIES_SKILL_TYPE_RULES
    resource_type_map = _HUMANITIES_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.40
    _per_kw_conf:     float = 0.08
    _conf_cap:        float = 0.75
    _conf_no_match:   float = 0.25

    topic_keywords: dict[str, list[str]] = {
        "Research": ["research", "source", "evidence", "information", "data"],
        "Analysis": ["analyse", "examine", "identify", "pattern", "trend"],
        "Evaluation": ["evaluate", "assess", "judge", "justify", "weigh"],
        "Reflection": ["reflect", "consider", "reconsider", "my opinion", "I think"],
        "Collaboration": ["team", "group", "work with", "collaborate", "share"],
        "Communication": ["argue", "persuade", "present", "explain", "communicate"],
        "Global issues": [
            "global", "climate", "poverty", "health", "conflict", "technology",
            "population", "migration", "sustainability",
        ],
    }


class SociologyAdapter(BaseSubjectAdapter):
    adapter_name      = "sociology_0495"
    adapter_status    = "basic_adapter"
    subject_slug      = "sociology_0495"
    skill_type_rules  = _HUMANITIES_SKILL_TYPE_RULES
    resource_type_map = _HUMANITIES_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.40
    _per_kw_conf:     float = 0.08
    _conf_cap:        float = 0.75
    _conf_no_match:   float = 0.25

    topic_keywords: dict[str, list[str]] = {
        "Theory and methods": ["sociological theory", "research method", "sample", "survey", "observation"],
        "Culture and identity": ["culture", "identity", "norm", "value", "socialisation"],
        "Social inequality": ["inequality", "class", "gender", "ethnicity", "stratification"],
        "Family": ["family", "marriage", "divorce", "household", "nuclear", "extended"],
        "Education": ["school", "curriculum", "achievement", "teacher", "hidden curriculum"],
        "Crime": ["crime", "deviance", "punishment", "police", "recidivism"],
        "Mass media": ["media", "news", "television", "social media", "representation"],
    }


class TravelTourismAdapter(BaseSubjectAdapter):
    adapter_name      = "travel_and_tourism_0471"
    adapter_status    = "basic_adapter"
    subject_slug      = "travel_and_tourism_0471"
    skill_type_rules  = _BH_SKILL_TYPE_RULES
    resource_type_map = _BH_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.40
    _per_kw_conf:     float = 0.08
    _conf_cap:        float = 0.75
    _conf_no_match:   float = 0.25

    topic_keywords: dict[str, list[str]] = {
        "Tourism": ["tourist", "visitor", "destination", "attraction", "resort"],
        "Accommodation": ["hotel", "hostel", "accommodation", "resort", "campsite"],
        "Transport": ["transport", "airline", "train", "cruise", "transfer"],
        "Customer service": ["customer", "service", "complaint", "satisfaction", "quality"],
        "Marketing": ["marketing", "promotion", "brochure", "advertising", "brand"],
        "Sustainable tourism": ["sustainable", "eco-tourism", "environment", "community", "impact"],
        "Planning and research": ["itinerary", "research", "planning", "budget", "package"],
    }
