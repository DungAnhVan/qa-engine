"""Subject adapters for Cambridge IGCSE Science subjects."""
from __future__ import annotations
from .base import BaseSubjectAdapter, SHARED_SKILL_TYPE_RULES

# ---------------------------------------------------------------------------
# Shared science resource-type map
# ---------------------------------------------------------------------------

_SCIENCE_RESOURCE_TYPE_MAP: dict[str, str] = {
    "calculation":             "calculation_drill",
    "equation_manipulation":   "calculation_drill",
    "practical_calculation":   "calculation_drill",
    "graphing":                "graphing_drill",
    "data_interpretation":     "data_interpretation_drill",
    "diagram_drawing":         "diagram_or_graph_drill",
    "table_design":            "marking_checklist",
    "extended_planning":       "experiment_planning_task",
    "experimental_design":     "experiment_planning_task",
    "variable_control":        "experiment_planning_task",
    "evaluation_accuracy":     "marking_checklist",
    "measurement":             "data_interpretation_drill",
    "recall_definition":       "worked_example",
    "conceptual_explanation":  "worked_example",
    "multiple_choice_concept": "worked_example",
    "unknown":                 "short_answer_calculation",
}

# ---------------------------------------------------------------------------
# Physics skill-type rules — exact copy of legacy rules so existing
# Physics pipeline output is unchanged.
# ---------------------------------------------------------------------------

_PHYSICS_SKILL_TYPE_RULES: list[tuple[str, list[str], bool]] = [
    ("extended_planning", ["MP1", "MP2", "MP3", "MP4", "MP5", "MP6", "MP7"], True),
    ("equation_manipulation", [
        "rearrange", "express in terms", "derive an expression", "show that",
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


# ---------------------------------------------------------------------------
# Physics 0625 — full_adapter
# ---------------------------------------------------------------------------

class PhysicsAdapter(BaseSubjectAdapter):
    adapter_name      = "physics_0625"
    adapter_status    = "full_adapter"
    subject_slug      = "physics_0625"
    skill_type_rules  = _PHYSICS_SKILL_TYPE_RULES
    resource_type_map = _SCIENCE_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.55
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.95
    _conf_no_match:   float = 0.40

    topic_keywords: dict[str, list[str]] = {
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
# Chemistry 0620 — basic_adapter
# ---------------------------------------------------------------------------

class ChemistryAdapter(BaseSubjectAdapter):
    adapter_name      = "chemistry_0620"
    adapter_status    = "basic_adapter"
    subject_slug      = "chemistry_0620"
    skill_type_rules  = SHARED_SKILL_TYPE_RULES
    resource_type_map = _SCIENCE_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.45
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.85
    _conf_no_match:   float = 0.30

    topic_keywords: dict[str, list[str]] = {
        "Atomic structure and bonding": [
            "atom", "electron", "proton", "neutron", "shell", "orbital", "ionic",
            "covalent", "bond", "bonding", "lattice", "molecule", "ion", "charge",
            "nucleus", "structure", "metallic", "van der waals",
        ],
        "Stoichiometry": [
            "mole", "molar", "relative atomic mass", "relative molecular mass",
            "formula", "balance", "stoichiometry", "yield", "percentage yield",
            "concentration", "solution", "avogadro",
        ],
        "Periodic table": [
            "periodic", "group", "period", "halogen", "noble gas", "alkali metal",
            "transition metal", "trend", "property", "electronegativity", "reactivity",
        ],
        "Metals": [
            "metal", "reactivity series", "corrosion", "rusting", "alloy",
            "extraction", "ore", "reduction", "oxidation", "displacement",
            "electrolysis", "electrode",
        ],
        "Acids, bases and salts": [
            "acid", "base", "alkali", "salt", "pH", "neutralisation", "indicator",
            "titration", "hydrogen ion", "hydroxide", "carbonate", "sulfate",
            "nitrate", "chloride",
        ],
        "Chemical energetics": [
            "exothermic", "endothermic", "enthalpy", "bond energy",
            "activation energy", "catalyst", "energy change", "heat of reaction",
        ],
        "Rates of reaction": [
            "rate of reaction", "concentration", "temperature", "catalyst",
            "surface area", "collision theory", "particle",
        ],
        "Reversible reactions and equilibrium": [
            "equilibrium", "reversible", "dynamic equilibrium", "le chatelier",
            "forward reaction", "backward reaction", "yield",
        ],
        "Organic chemistry": [
            "organic", "carbon", "hydrocarbon", "alkane", "alkene", "alcohol",
            "ester", "polymer", "addition", "substitution", "functional group",
            "crude oil", "distillation", "ethanol", "methane", "ethene",
        ],
        "Experimental chemistry": [
            "test for", "identify", "gas", "smell", "colour change", "precipitate",
            "filtration", "crystallisation", "chromatography", "flame test",
            "limewater", "litmus",
        ],
    }


# ---------------------------------------------------------------------------
# Biology 0610 — basic_adapter
# ---------------------------------------------------------------------------

class BiologyAdapter(BaseSubjectAdapter):
    adapter_name      = "biology_0610"
    adapter_status    = "basic_adapter"
    subject_slug      = "biology_0610"
    skill_type_rules  = SHARED_SKILL_TYPE_RULES
    resource_type_map = _SCIENCE_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.45
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.85
    _conf_no_match:   float = 0.30

    topic_keywords: dict[str, list[str]] = {
        "Cells": [
            "cell", "nucleus", "membrane", "cytoplasm", "organelle", "mitochondria",
            "chloroplast", "cell wall", "vacuole", "ribosome", "diffusion", "osmosis",
            "active transport", "prokaryote", "eukaryote",
        ],
        "Biological molecules": [
            "glucose", "starch", "protein", "lipid", "fat", "carbohydrate",
            "amino acid", "fatty acid", "glycerol", "cellulose", "glycogen",
            "Benedict's", "iodine test", "biuret", "emulsion test",
        ],
        "Enzymes": [
            "enzyme", "active site", "substrate", "product", "lock and key",
            "denaturation", "amylase", "protease", "lipase", "optimum pH",
            "optimum temperature",
        ],
        "Plant nutrition": [
            "photosynthesis", "chlorophyll", "carbon dioxide", "stomata", "leaf",
            "chloroplast", "autotroph", "mineral", "nitrate", "magnesium",
            "limiting factor",
        ],
        "Animal nutrition": [
            "digestion", "absorption", "diet", "enzyme", "stomach", "intestine",
            "mouth", "teeth", "saliva", "bile", "villi", "nutrient", "vitamin",
            "mineral", "fibre", "balanced diet",
        ],
        "Transport in plants": [
            "xylem", "phloem", "transpiration", "water", "root hair",
            "translocation", "sap", "guard cell",
        ],
        "Transport in animals": [
            "blood", "heart", "artery", "vein", "capillary", "circulation",
            "red blood cell", "white blood cell", "plasma", "haemoglobin",
            "double circulation", "pulse rate",
        ],
        "Respiration": [
            "respiration", "aerobic", "anaerobic", "ATP", "lactic acid",
            "ethanol", "fermentation", "mitochondria", "oxygen debt",
        ],
        "Coordination and response": [
            "nervous system", "neurone", "synapse", "reflex", "hormone",
            "receptor", "effector", "brain", "spinal cord", "insulin",
            "glucagon", "homeostasis", "adrenaline",
        ],
        "Reproduction": [
            "reproduction", "sexual", "asexual", "gamete", "fertilisation",
            "seed", "flower", "pollen", "ovum", "sperm", "meiosis", "mitosis",
            "chromosome", "embryo", "placenta",
        ],
        "Inheritance": [
            "gene", "allele", "dominant", "recessive", "genotype", "phenotype",
            "Punnett square", "monohybrid", "inheritance", "sex-linked", "mutation",
        ],
        "Variation and selection": [
            "variation", "natural selection", "evolution", "adaptation",
            "mutation", "selective breeding", "species", "survival",
        ],
        "Organisms and environment": [
            "ecosystem", "food chain", "food web", "decomposer", "producer",
            "consumer", "nutrient cycle", "carbon cycle", "nitrogen cycle",
            "population", "community", "habitat", "niche",
        ],
        "Human influences on ecosystems": [
            "pollution", "deforestation", "habitat destruction", "endangered",
            "conservation", "global warming", "greenhouse gas", "pesticide",
            "fertiliser", "eutrophication", "biodiversity",
        ],
    }


# ---------------------------------------------------------------------------
# Combined Science 0653 / Co-ordinated Sciences 0654 — basic_adapter
# ---------------------------------------------------------------------------

class CombinedScienceAdapter(BaseSubjectAdapter):
    """Basic adapter for combined / co-ordinated science syllabuses."""

    adapter_status = "basic_adapter"
    skill_type_rules  = SHARED_SKILL_TYPE_RULES
    resource_type_map = _SCIENCE_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.40
    _per_kw_conf:     float = 0.08
    _conf_cap:        float = 0.75
    _conf_no_match:   float = 0.25

    def __init__(self, subject_slug: str = "combined_science") -> None:
        self.subject_slug = subject_slug
        self.adapter_name = subject_slug

    # Merge a subset of physics + chemistry + biology keywords
    topic_keywords: dict[str, list[str]] = {
        "Physics — Motion and Energy": ["force", "speed", "energy", "power", "velocity", "motion"],
        "Physics — Electricity": ["current", "voltage", "resistance", "circuit", "charge"],
        "Physics — Waves": ["wave", "sound", "light", "frequency", "wavelength"],
        "Chemistry — Atomic Structure": ["atom", "ion", "bond", "electron", "proton"],
        "Chemistry — Reactions": ["acid", "base", "salt", "rate", "equilibrium", "oxidation"],
        "Chemistry — Organic": ["organic", "carbon", "alkane", "alkene", "polymer"],
        "Biology — Cells": ["cell", "membrane", "osmosis", "diffusion", "nucleus"],
        "Biology — Systems": ["blood", "heart", "digestion", "respiration", "nervous"],
        "Biology — Genetics": ["gene", "allele", "inheritance", "chromosome", "evolution"],
    }


# ---------------------------------------------------------------------------
# Environmental Management 0680 — basic_adapter
# ---------------------------------------------------------------------------

class EnvironmentalManagementAdapter(BaseSubjectAdapter):
    adapter_name      = "environmental_management_0680"
    adapter_status    = "basic_adapter"
    subject_slug      = "environmental_management_0680"
    skill_type_rules  = SHARED_SKILL_TYPE_RULES
    resource_type_map = _SCIENCE_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.40
    _per_kw_conf:     float = 0.08
    _conf_cap:        float = 0.75
    _conf_no_match:   float = 0.25

    topic_keywords: dict[str, list[str]] = {
        "Atmosphere": ["atmosphere", "climate", "weather", "greenhouse", "ozone", "carbon dioxide"],
        "Hydrosphere": ["water", "ocean", "river", "lake", "rainfall", "evaporation", "aquifer"],
        "Lithosphere": ["soil", "rock", "erosion", "mining", "land use", "deforestation"],
        "Biosphere": ["ecosystem", "biodiversity", "habitat", "food chain", "food web"],
        "Human activity": ["pollution", "industry", "urbanisation", "population", "agriculture"],
        "Sustainability": ["sustainable", "renewable", "conservation", "recycling", "management"],
    }
