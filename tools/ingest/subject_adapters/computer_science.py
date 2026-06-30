"""Subject adapters for Cambridge IGCSE Computer Science and ICT subjects."""
from __future__ import annotations
from .base import BaseSubjectAdapter

_CS_SKILL_TYPE_RULES: list[tuple[str, list[str], bool]] = [
    ("extended_planning", [
        "write an algorithm", "write pseudocode", "design an algorithm",
        "draw a flowchart", "complete the algorithm",
    ], False),
    ("data_interpretation", [
        "trace", "dry run", "trace table", "state the output", "complete the trace",
        "what is the value of",
    ], False),
    ("calculation", [
        "convert", "calculate", "binary", "denary", "hexadecimal",
        "two's complement", "how many bits",
    ], False),
    ("table_design", [
        "complete the table", "fill in the table",
    ], False),
    ("recall_definition", [
        "state", "define", "name", "give", "list", "identify", "write down",
    ], False),
    ("conceptual_explanation", [
        "explain", "describe", "why", "how does", "compare", "give a reason",
        "give an advantage", "give a disadvantage",
    ], False),
]

_CS_RESOURCE_TYPE_MAP: dict[str, str] = {
    "extended_planning":      "algorithm_design_task",
    "data_interpretation":    "pseudocode_trace",
    "calculation":            "code_reasoning_task",
    "table_design":           "database_query_task",
    "recall_definition":      "short_answer_concept",
    "conceptual_explanation": "short_answer_concept",
    "unknown":                "short_answer_concept",
}

_ICT_SKILL_TYPE_RULES: list[tuple[str, list[str], bool]] = [
    ("table_design", ["spreadsheet", "database", "query", "field", "record"], False),
    ("calculation", ["formula", "function", "vlookup", "if function", "calculate"], False),
    ("extended_planning", ["design", "plan", "create", "produce", "develop"], False),
    ("data_interpretation", ["from the data", "from the table", "analyse", "interpret"], False),
    ("recall_definition", ["state", "define", "name", "list", "give", "identify"], False),
    ("conceptual_explanation", ["explain", "describe", "compare", "advantage", "disadvantage"], False),
]

_ICT_RESOURCE_TYPE_MAP: dict[str, str] = {
    "extended_planning":      "algorithm_design_task",
    "table_design":           "database_query_task",
    "calculation":            "code_reasoning_task",
    "data_interpretation":    "pseudocode_trace",
    "recall_definition":      "short_answer_concept",
    "conceptual_explanation": "short_answer_concept",
    "unknown":                "short_answer_concept",
}


class ComputerScienceAdapter(BaseSubjectAdapter):
    adapter_name      = "computer_science_0478"
    adapter_status    = "basic_adapter"
    subject_slug      = "computer_science_0478"
    skill_type_rules  = _CS_SKILL_TYPE_RULES
    resource_type_map = _CS_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.45
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.85
    _conf_no_match:   float = 0.30

    topic_keywords: dict[str, list[str]] = {
        "Data representation": [
            "binary", "denary", "hexadecimal", "bit", "byte", "ASCII", "Unicode",
            "two's complement", "floating point", "overflow", "sound sampling",
            "pixel", "image resolution",
        ],
        "Communication and internet technologies": [
            "network", "internet", "protocol", "TCP/IP", "HTTP", "HTTPS", "FTP",
            "email", "bandwidth", "packet", "router", "URL", "IP address",
            "MAC address", "WiFi", "LAN", "WAN",
        ],
        "Hardware and software": [
            "CPU", "RAM", "ROM", "storage", "input", "output", "operating system",
            "application software", "compiler", "interpreter", "processor",
            "clock speed", "cache", "secondary storage", "SSD", "HDD",
        ],
        "Security": [
            "password", "encryption", "firewall", "virus", "malware", "phishing",
            "hacking", "authentication", "cybersecurity", "backup",
        ],
        "Ethics": [
            "copyright", "privacy", "data protection", "digital divide",
            "intellectual property", "plagiarism", "piracy", "environmental impact",
        ],
        "Algorithm design": [
            "algorithm", "pseudocode", "flowchart", "sequence", "selection",
            "iteration", "loop", "condition", "IF", "WHILE", "FOR",
        ],
        "Programming concepts": [
            "variable", "constant", "data type", "integer", "string", "boolean",
            "array", "function", "procedure", "parameter", "library", "module",
            "debugging", "testing",
        ],
        "Databases": [
            "database", "table", "field", "record", "primary key", "query",
            "SQL", "SELECT", "WHERE", "sort", "relational database",
        ],
        "Boolean logic": [
            "logic gate", "AND", "OR", "NOT", "NAND", "NOR", "XOR",
            "truth table", "Boolean", "logic circuit",
        ],
    }


class ICTAdapter(BaseSubjectAdapter):
    adapter_name      = "ict_0417"
    adapter_status    = "basic_adapter"
    subject_slug      = "ict_0417"
    skill_type_rules  = _ICT_SKILL_TYPE_RULES
    resource_type_map = _ICT_RESOURCE_TYPE_MAP

    _base_conf_match: float = 0.45
    _per_kw_conf:     float = 0.10
    _conf_cap:        float = 0.85
    _conf_no_match:   float = 0.30

    topic_keywords: dict[str, list[str]] = {
        "Document production": [
            "word processor", "document", "formatting", "font", "style", "header",
            "footer", "mail merge", "template", "text",
        ],
        "Data manipulation": [
            "database", "query", "sort", "filter", "field", "record", "table",
            "search", "report",
        ],
        "Presentations": [
            "presentation", "slide", "animation", "transition", "audience",
            "PowerPoint", "slideshow",
        ],
        "Spreadsheets": [
            "spreadsheet", "cell", "formula", "function", "IF", "VLOOKUP",
            "chart", "graph", "row", "column", "SUM", "AVERAGE",
        ],
        "Website authoring": [
            "website", "HTML", "CSS", "hyperlink", "webpage", "web page",
            "browser", "URL", "image", "multimedia",
        ],
        "Networks": [
            "network", "internet", "LAN", "WAN", "router", "server",
            "client", "bandwidth", "protocol",
        ],
        "Safety and security": [
            "password", "virus", "firewall", "backup", "encryption",
            "privacy", "phishing", "cyberbullying", "copyright",
        ],
        "Systems life cycle": [
            "analysis", "design", "development", "testing", "implementation",
            "maintenance", "system", "requirements", "user",
        ],
    }
