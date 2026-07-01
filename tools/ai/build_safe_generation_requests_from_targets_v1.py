"""
Gate 70A -- Build Safe Generation Requests from Targets v1

Reads generation targets for a subject, filters to usable ones (known topic,
known skill_type, resource_type != review_before_generation), and builds safe
authoring requests from metadata only.

If no usable targets exist, falls back to a set of safe seed requests based on
known Cambridge IGCSE Physics syllabus topics.

SAFETY: No raw source text, mark schemes, or PDF content is read or included.
Only metadata fields allowed by the authoring contract are used.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_safe_generation_requests_from_targets_v1.py
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_safe_generation_requests_from_targets_v1.py --subject physics_0625 --limit 10

Output:
  data/ai/generation_requests/ai_safe_generation_requests_v1.json
"""

import argparse
import json
import sys
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.ai.ai_authoring_contract_v1 import (
    make_safe_authoring_request,
    validate_safe_authoring_request,
    summarize_authoring_request,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TARGETS_DIR = ROOT / "data" / "bank" / "cambridge_igcse" / "physics_0625" / "generation_targets"
OUT_DIR     = ROOT / "data" / "ai" / "generation_requests"
OUT_FILE    = OUT_DIR / "ai_safe_generation_requests_v1.json"

SUBJECT_TARGETS_FILES = {
    "physics_0625": TARGETS_DIR / "unified_generation_targets_v0.json",
}

# ---------------------------------------------------------------------------
# Safe fallback seeds — IGCSE Physics 0625
# Only safe metadata, no source text.
# ---------------------------------------------------------------------------

PHYSICS_0625_FALLBACK_SEEDS = [
    {
        "topic": "Motion, forces and energy",
        "subtopic": "Speed and velocity",
        "skill_type": "application",
        "skill_name": "Calculate speed from distance-time data",
        "difficulty": "easy",
        "learning_objective": "Apply the speed equation to calculate average speed",
    },
    {
        "topic": "Motion, forces and energy",
        "subtopic": "Acceleration",
        "skill_type": "application",
        "skill_name": "Calculate acceleration from velocity-time data",
        "difficulty": "medium",
        "learning_objective": "Use the acceleration equation to solve problems",
    },
    {
        "topic": "Motion, forces and energy",
        "subtopic": "Newton's laws of motion",
        "skill_type": "analysis",
        "skill_name": "Apply Newton's second law to unbalanced forces",
        "difficulty": "medium",
        "learning_objective": "Apply F=ma to calculate resultant force or acceleration",
    },
    {
        "topic": "Motion, forces and energy",
        "subtopic": "Work, energy and power",
        "skill_type": "application",
        "skill_name": "Calculate work done and power output",
        "difficulty": "medium",
        "learning_objective": "Use W=Fd and P=W/t to solve energy problems",
    },
    {
        "topic": "Thermal physics",
        "subtopic": "Thermal expansion",
        "skill_type": "recall",
        "skill_name": "Describe thermal expansion in solids, liquids and gases",
        "difficulty": "easy",
        "learning_objective": "Explain thermal expansion using kinetic particle theory",
    },
    {
        "topic": "Thermal physics",
        "subtopic": "Specific heat capacity",
        "skill_type": "application",
        "skill_name": "Calculate heat energy using specific heat capacity",
        "difficulty": "medium",
        "learning_objective": "Use Q=mcDeltaT to calculate heat energy changes",
    },
    {
        "topic": "Waves",
        "subtopic": "Properties of waves",
        "skill_type": "recall",
        "skill_name": "Describe transverse and longitudinal waves",
        "difficulty": "easy",
        "learning_objective": "Distinguish between transverse and longitudinal wave motion",
    },
    {
        "topic": "Waves",
        "subtopic": "Wave speed",
        "skill_type": "application",
        "skill_name": "Calculate wave speed from frequency and wavelength",
        "difficulty": "easy",
        "learning_objective": "Use v=f*lambda to calculate wave speed",
    },
    {
        "topic": "Waves",
        "subtopic": "Light and refraction",
        "skill_type": "analysis",
        "skill_name": "Explain refraction using change in speed",
        "difficulty": "medium",
        "learning_objective": "Describe how refraction occurs at boundaries due to speed change",
    },
    {
        "topic": "Electricity and magnetism",
        "subtopic": "Current and charge",
        "skill_type": "application",
        "skill_name": "Calculate current from charge and time",
        "difficulty": "easy",
        "learning_objective": "Use I=Q/t to solve current problems",
    },
    {
        "topic": "Electricity and magnetism",
        "subtopic": "Resistance",
        "skill_type": "application",
        "skill_name": "Apply Ohm's law to resistor circuits",
        "difficulty": "medium",
        "learning_objective": "Use V=IR to calculate voltage, current, or resistance",
    },
    {
        "topic": "Electricity and magnetism",
        "subtopic": "Electrical power",
        "skill_type": "application",
        "skill_name": "Calculate electrical power and energy",
        "difficulty": "medium",
        "learning_objective": "Use P=IV and E=Pt to solve power problems",
    },
    {
        "topic": "Nuclear physics",
        "subtopic": "Radioactive decay",
        "skill_type": "recall",
        "skill_name": "Describe alpha, beta and gamma radiation",
        "difficulty": "easy",
        "learning_objective": "State the nature, charge and penetration of ionising radiations",
    },
    {
        "topic": "Nuclear physics",
        "subtopic": "Half-life",
        "skill_type": "analysis",
        "skill_name": "Interpret half-life graphs and calculate remaining activity",
        "difficulty": "hard",
        "learning_objective": "Use half-life data to determine remaining radioactive substance",
    },
    {
        "topic": "Space physics",
        "subtopic": "Solar system",
        "skill_type": "recall",
        "skill_name": "Describe features of the solar system",
        "difficulty": "easy",
        "learning_objective": "Describe the key features of planets, moons and the Sun",
    },
]

FALLBACK_SYLLABUS_CODE = "0625"

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Build safe generation requests from targets")
parser.add_argument("--subject", default="physics_0625", help="Subject slug (default: physics_0625)")
parser.add_argument("--limit",   type=int, default=10,    help="Maximum requests to build (default: 10)")
args = parser.parse_args()

subject  = args.subject
limit    = max(1, args.limit)

print(f"Gate 70A -- Build Safe Generation Requests v1")
print(f"Subject: {subject}  Limit: {limit}")
print("=" * 60)

# ---------------------------------------------------------------------------
# Load and filter targets
# ---------------------------------------------------------------------------

USABLE_RESOURCE_TYPES = {"question", "worked_example", "explanation", "practice_set"}
USABLE_SKILL_TYPES    = {"recall", "application", "analysis", "evaluation", "synthesis"}

targets_file = SUBJECT_TARGETS_FILES.get(subject)
usable: list[dict] = []
targets_loaded = 0
targets_skipped = 0

if targets_file and targets_file.exists():
    try:
        raw = json.loads(targets_file.read_text(encoding="utf-8"))
        all_targets: list[dict] = raw if isinstance(raw, list) else raw.get("targets", [])
        targets_loaded = len(all_targets)
        for t in all_targets:
            skill_type    = (t.get("skill_type") or "").lower()
            topic         = (t.get("topic") or "").strip()
            resource_type = (t.get("resource_type") or "").lower()
            skill_name    = (t.get("skill_name") or "")
            # Skip unparsed / unknown entries
            if skill_type == "unknown" or skill_type == "":
                targets_skipped += 1
                continue
            if topic in ("", "Unknown", "unknown"):
                targets_skipped += 1
                continue
            if resource_type not in USABLE_RESOURCE_TYPES:
                targets_skipped += 1
                continue
            if "[question" in skill_name.lower() and "not parsed" in skill_name.lower():
                targets_skipped += 1
                continue
            usable.append(t)
        print(f"Loaded {targets_loaded} targets, {len(usable)} usable, {targets_skipped} skipped")
    except Exception as exc:
        print(f"Warning: could not load targets file: {exc}")
else:
    print(f"No targets file found for {subject!r}")

using_fallback = len(usable) == 0
if using_fallback:
    print(f"No usable targets found -- using {len(PHYSICS_0625_FALLBACK_SEEDS)} safe fallback seeds")

# ---------------------------------------------------------------------------
# Build safe requests
# ---------------------------------------------------------------------------

requests: list[dict] = []
validation_issues: list[str] = []

if using_fallback:
    seeds = PHYSICS_0625_FALLBACK_SEEDS[:limit]
    for i, seed in enumerate(seeds, 1):
        req = make_safe_authoring_request(
            subject_slug   = subject,
            syllabus_code  = FALLBACK_SYLLABUS_CODE,
            topic          = seed["topic"],
            subtopic       = seed.get("subtopic", ""),
            skill_name     = seed.get("skill_name", ""),
            skill_type     = seed.get("skill_type", ""),
            difficulty     = seed.get("difficulty", "medium"),
            resource_type  = "question",
            learning_objective = seed.get("learning_objective", ""),
            student_level  = "IGCSE",
            estimated_time_minutes = 8,
        )
        result = validate_safe_authoring_request(req)
        if not result["valid"]:
            validation_issues.append(f"Seed {i}: {result['issues']}")
            continue
        req["_request_id"] = f"{subject}_fallback_{i:03d}"
        req["_source"]     = "fallback_seeds"
        requests.append(req)
        print(f"  [{i:02d}] {summarize_authoring_request(req)}")
else:
    usable_slice = usable[:limit]
    for i, t in enumerate(usable_slice, 1):
        req = make_safe_authoring_request(
            subject_slug   = subject,
            syllabus_code  = t.get("component_type", FALLBACK_SYLLABUS_CODE),
            topic          = t["topic"],
            subtopic       = t.get("subtopic", ""),
            skill_name     = t.get("skill_name", ""),
            skill_type     = t.get("skill_type", ""),
            difficulty     = t.get("difficulty", "medium"),
            resource_type  = t.get("resource_type", "question"),
            learning_objective = t.get("generation_goal", ""),
            student_level  = "IGCSE",
            estimated_time_minutes = 8,
            source_ids     = t.get("source_skill_unit_ids", []),
        )
        result = validate_safe_authoring_request(req)
        if not result["valid"]:
            validation_issues.append(f"Target {i} ({t.get('target_id')}): {result['issues']}")
            continue
        req["_request_id"] = t.get("target_id", f"{subject}_target_{i:03d}")
        req["_source"]     = "generation_targets"
        requests.append(req)
        print(f"  [{i:02d}] {summarize_authoring_request(req)}")

# ---------------------------------------------------------------------------
# Write output
# ---------------------------------------------------------------------------

OUT_DIR.mkdir(parents=True, exist_ok=True)

output = {
    "schema_version":    "gate70a_v1",
    "generated_at":      datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "subject":           subject,
    "limit":             limit,
    "source":            "fallback_seeds" if using_fallback else "generation_targets",
    "targets_loaded":    targets_loaded,
    "targets_skipped":   targets_skipped,
    "request_count":     len(requests),
    "validation_issues": validation_issues,
    "safety": {
        "no_raw_source_text":     True,
        "no_cambridge_pdf_text":  True,
        "no_mark_scheme_text":    True,
        "metadata_only":          True,
        "authoring_contract":     "ai_authoring_contract_v1",
    },
    "requests": requests,
}

OUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")

print()
print(f"Built {len(requests)} safe generation requests")
if validation_issues:
    print(f"  {len(validation_issues)} validation issue(s):")
    for vi in validation_issues:
        print(f"    ! {vi}")
print(f"Output: {OUT_FILE.relative_to(ROOT)}")
