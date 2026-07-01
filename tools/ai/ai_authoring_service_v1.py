"""
Gate 69C -- AI Authoring Service v1

Generates original Quanta Aptus resource drafts from safe authoring requests.

Rules:
  - Validates input using ai_authoring_contract_v1.
  - Builds prompts using ai_prompt_builder_v1.
  - Calls ai_client_v1.generate_text().
  - Mock / dry-run returns a deterministic structured draft (not raw text).
  - Generated drafts are NEVER published or written to Supabase.
  - Generated drafts are saved to data/ai/generated_batches/.
  - Teacher approval is always required before publish.

Security:
  - No API keys in output.
  - No raw source text in generated drafts.
  - Copyright guard runs on all generated content.
"""

import json
import hashlib
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT_BASE = ROOT / "data" / "ai" / "generated_batches"

from tools.ai.ai_authoring_contract_v1 import validate_safe_authoring_request
from tools.ai.ai_prompt_builder_v1 import build_resource_authoring_prompt
from tools.ai.ai_client_v1 import generate_text
from tools.ai.copyright_safety_guard_v1 import scan_generated_content_for_risk
from tools.ai.ai_provider_config_v1 import load_ai_provider_config, load_env_local

# ---------------------------------------------------------------------------
# Mock resource templates (deterministic by subject + topic hash)
# ---------------------------------------------------------------------------

_MOCK_STUDENT_PROMPTS = [
    (
        "A uniform rod of length 1.2 m and mass 0.8 kg is pivoted at one end. "
        "A vertical force F is applied at the other end to hold the rod at 30° "
        "to the horizontal. Calculate the magnitude of F. Show your working."
    ),
    (
        "A solution contains 0.25 mol of sodium chloride dissolved in 500 cm³ "
        "of water. Calculate the molar concentration of the solution. "
        "State the unit of your answer."
    ),
    (
        "Explain how the structure of a villus is adapted for the efficient "
        "absorption of digested food products. Refer to at least three structural "
        "features in your answer."
    ),
    (
        "A transformer has 400 turns on its primary coil and 50 turns on its "
        "secondary coil. The primary voltage is 240 V. "
        "Calculate the secondary voltage. State any assumption you make."
    ),
    (
        "Factorise fully: 6x² − 11x − 10. "
        "Hence, or otherwise, solve 6x² − 11x − 10 = 0, "
        "giving your answers as fractions in their simplest form."
    ),
]

_MOCK_ANSWER_KEYS = [
    "F = mg cos(θ) / 2 = (0.8 × 10 × cos30°) / 2 ≈ 3.46 N [accept 3.5 N with working shown]",
    "Concentration = moles / volume = 0.25 / 0.500 = 0.50 mol dm⁻³",
    "Large surface area (finger-like projections); thin epithelium (one cell thick); good blood supply (capillary network); lacteals for fat absorption",
    "Vs = Vp × (Ns/Np) = 240 × (50/400) = 30 V. Assumption: 100% efficiency.",
    "6x² − 11x − 10 = (2x − 5)(3x + 2). Solutions: x = 5/2 or x = −2/3",
]

_MOCK_RUBRICS = [
    [{"criterion": "Correct moment equation", "marks": 1, "guidance": "Accepts Fl = mg(l/2)cos θ"},
     {"criterion": "Correct value of F", "marks": 2, "guidance": "3.4–3.5 N, with valid working shown"}],
    [{"criterion": "Uses concentration = n/V", "marks": 1, "guidance": "Formula stated or implied"},
     {"criterion": "Correct calculation and unit", "marks": 2, "guidance": "0.50 mol dm⁻³"}],
    [{"criterion": "Three structural adaptations named", "marks": 3, "guidance": "One mark each for: large SA, thin epithelium, blood supply (or lacteal)"}],
    [{"criterion": "Correct transformer ratio used", "marks": 1, "guidance": "Vs/Vp = Ns/Np"},
     {"criterion": "Correct secondary voltage", "marks": 1, "guidance": "30 V"},
     {"criterion": "Assumption stated", "marks": 1, "guidance": "100% efficiency or ideal transformer"}],
    [{"criterion": "Correct factorisation", "marks": 2, "guidance": "(2x−5)(3x+2)"},
     {"criterion": "Both solutions correct", "marks": 2, "guidance": "x = 5/2 and x = −2/3"}],
]

_MOCK_TEACHER_NOTES = [
    "Common error: students forget to include cos(θ) factor. Check moment equation carefully.",
    "Ensure students convert cm³ to dm³ (divide by 1000). Unit must be stated.",
    "Award marks for any three of: microvilli/brush border, thin walls, capillaries, lacteals, goblet cells.",
    "Remind students that 100% efficiency is assumed unless stated otherwise in the question.",
    "Watch for sign errors when factorising. Both solutions must be expressed as fractions.",
]

_MOCK_TITLES = [
    "Moments and Equilibrium — Rod Pivoted at One End",
    "Molar Concentration Calculation",
    "Adaptations of the Villus for Absorption",
    "Transformer Voltage Calculation",
    "Quadratic Factorisation and Equation Solving",
]


def _deterministic_index(subject_slug: str, topic: str, seed: int = 0) -> int:
    h = int(hashlib.md5(f"{subject_slug}|{topic}|{seed}".encode()).hexdigest(), 16)
    return h % len(_MOCK_STUDENT_PROMPTS)


def _build_mock_resource(request: dict, resource_index: int = 0) -> dict:
    """Build a deterministic mock resource that satisfies the output schema."""
    subject_slug  = str(request.get("subject_slug", "unknown"))
    topic         = str(request.get("topic", "General"))
    subtopic      = str(request.get("subtopic", ""))
    skill_name    = str(request.get("skill_name", ""))
    skill_type    = str(request.get("skill_type", "application"))
    difficulty    = str(request.get("difficulty", "medium"))
    resource_type = str(request.get("resource_type", "question"))
    constraints   = request.get("constraints", {})
    est_time      = int(constraints.get("estimated_time_minutes", 10)) if isinstance(constraints, dict) else 10

    idx = _deterministic_index(subject_slug, topic, seed=resource_index)

    resource_id = f"qa_{subject_slug}_{hashlib.md5(f'{topic}{resource_index}'.encode()).hexdigest()[:8]}"

    return {
        "resource_id":          resource_id,
        "resource_type":        resource_type,
        "title":                _MOCK_TITLES[idx],
        "topic":                topic,
        "subtopic":             subtopic,
        "skill_name":           skill_name,
        "skill_type":           skill_type,
        "difficulty":           difficulty,
        "estimated_time_minutes": est_time,
        "student_prompt":       _MOCK_STUDENT_PROMPTS[idx],
        "student_instructions": "Show all working. Give your answer to 3 significant figures unless stated otherwise.",
        "answer_key":           _MOCK_ANSWER_KEYS[idx],
        "marking_rubric":       _MOCK_RUBRICS[idx],
        "teacher_notes":        _MOCK_TEACHER_NOTES[idx],
        "safety_declaration": {
            "original_content":          True,
            "no_raw_source_text_used":   True,
            "no_mark_scheme_copied":     True,
        },
    }


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------

def generate_resource_draft(authoring_request: dict) -> dict:
    """
    Generate a single resource draft from a safe authoring request.

    Returns a draft dict with status, metadata, and the resource content.
    Does NOT write to Supabase. Does NOT publish.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 1. Validate the authoring request
    validation = validate_safe_authoring_request(authoring_request)
    if not validation["valid"]:
        return {
            "status":           "failed",
            "issues":           validation["issues"],
            "resource":         None,
            "ai_provider":      "none",
            "dry_run":          True,
            "copyright_strict": True,
            "created_at":       now,
        }

    # 2. Build prompt
    prompt_result = build_resource_authoring_prompt(authoring_request)
    if not prompt_result["safe"]:
        return {
            "status":           "failed",
            "issues":           prompt_result["issues"],
            "resource":         None,
            "ai_provider":      "none",
            "dry_run":          True,
            "copyright_strict": True,
            "created_at":       now,
        }

    # 3. Load config
    env_local = load_env_local()
    config = load_ai_provider_config(env_local)
    provider        = config["provider"]
    dry_run         = config["dry_run"]
    copyright_strict = config["copyright_strict"]

    # 4. Call AI client
    client_result = generate_text(
        prompt_result["full_prompt"],
        provider=provider,
        dry_run=dry_run,
        copyright_strict=copyright_strict,
    )

    if client_result["status"] == "failed":
        return {
            "status":           "failed",
            "issues":           client_result["issues"],
            "resource":         None,
            "ai_provider":      provider,
            "dry_run":          dry_run,
            "copyright_strict": copyright_strict,
            "created_at":       now,
        }

    # 5. Parse or build resource
    resource: dict | None = None
    parse_issues: list[str] = []

    if dry_run or provider == "mock":
        # Mock path: build deterministic structured resource
        resource = _build_mock_resource(authoring_request)
    else:
        # Real provider path: try to parse JSON response
        raw_text = client_result.get("text", "")
        try:
            # Strip markdown fences if present
            clean_text = raw_text.strip()
            if clean_text.startswith("```"):
                clean_text = clean_text.split("\n", 1)[-1]
                if clean_text.endswith("```"):
                    clean_text = clean_text.rsplit("```", 1)[0]
            resource = json.loads(clean_text)
        except (json.JSONDecodeError, ValueError) as exc:
            parse_issues.append(f"JSON parse failed: {exc}; falling back to mock resource")
            resource = _build_mock_resource(authoring_request)

    # 6. Validate resource fields
    field_issues: list[str] = []
    required_resource_fields = {
        "resource_id", "student_prompt", "answer_key", "marking_rubric", "safety_declaration"
    }
    missing = required_resource_fields - set(resource.keys() if resource else [])
    if missing:
        field_issues.append(f"Resource missing required fields: {sorted(missing)}")

    if resource:
        decl = resource.get("safety_declaration", {})
        if not isinstance(decl, dict) or not all(decl.get(k) for k in (
            "original_content", "no_raw_source_text_used", "no_mark_scheme_copied"
        )):
            field_issues.append("safety_declaration fields are not all True")

    # 7. Copyright scan on generated content
    content_text = json.dumps(resource) if resource else ""
    content_safety = scan_generated_content_for_risk(content_text)
    if not content_safety["safe"]:
        field_issues.extend([f"Generated content risk: {i}" for i in content_safety["issues"]])

    all_issues = parse_issues + field_issues
    status = (
        "draft"        if resource and not all_issues else
        "needs_review" if resource else
        "failed"
    )

    return {
        "status":           status,
        "issues":           all_issues,
        "resource":         resource,
        "ai_provider":      provider,
        "dry_run":          dry_run,
        "copyright_strict": copyright_strict,
        "created_at":       now,
    }


def generate_batch_from_requests(
    requests: list[dict],
    batch_id: str,
) -> dict:
    """
    Generate a batch of resource drafts and save to data/ai/generated_batches/.

    Does NOT publish. Does NOT write to Supabase.

    Returns the batch summary dict.
    """
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    env_local = load_env_local()
    config    = load_ai_provider_config(env_local)

    drafts: list[dict] = []
    for i, req in enumerate(requests):
        draft = generate_resource_draft(req)
        # Attach request metadata for traceability
        draft["request_index"] = i
        draft["subject_slug"]  = req.get("subject_slug", "")
        draft["topic"]         = req.get("topic", "")
        drafts.append(draft)

    passed  = [d for d in drafts if d["status"] in ("draft", "passed")]
    failed  = [d for d in drafts if d["status"] == "failed"]
    reviews = [d for d in drafts if d["status"] == "needs_review"]

    batch = {
        "batch_id":          batch_id,
        "generated_at":      now,
        "provider":          config["provider"],
        "dry_run":           config["dry_run"],
        "copyright_strict":  config["copyright_strict"],
        "total":             len(drafts),
        "draft_count":       len(passed),
        "needs_review_count": len(reviews),
        "failed_count":      len(failed),
        "status":            "draft" if not failed else "needs_review",
        "teacher_approval_required": True,
        "auto_publish_enabled":      False,
        "resources":         [d["resource"] for d in drafts if d.get("resource")],
        "draft_metadata":    [
            {
                "index":       d["request_index"],
                "subject":     d.get("subject_slug", ""),
                "topic":       d.get("topic", ""),
                "status":      d["status"],
                "ai_provider": d["ai_provider"],
                "dry_run":     d["dry_run"],
                "created_at":  d["created_at"],
                "issues":      d.get("issues", []),
            }
            for d in drafts
        ],
    }

    out_path = OUTPUT_BASE / f"{batch_id}.json"
    out_path.write_text(json.dumps(batch, indent=2), encoding="utf-8")

    return batch


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from tools.ai.ai_authoring_contract_v1 import make_safe_authoring_request

    req = make_safe_authoring_request(
        subject_slug="physics",
        topic="Electromagnetic Induction",
        difficulty="hard",
        resource_type="question",
    )
    draft = generate_resource_draft(req)
    print(f"status:    {draft['status']}")
    print(f"provider:  {draft['ai_provider']}")
    print(f"dry_run:   {draft['dry_run']}")
    if draft["resource"]:
        print(f"resource_id: {draft['resource'].get('resource_id')}")
        print(f"title:       {draft['resource'].get('title')}")
