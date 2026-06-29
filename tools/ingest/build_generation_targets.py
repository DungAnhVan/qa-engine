"""
Build generation targets from internal bank and skill index.

Usage:
    python tools/ingest/build_generation_targets.py <internal_bank_v0.json> <skill_index_v0.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_generation_targets.py \
        data/bank/cambridge_igcse/physics_0625/internal_bank_v0.json \
        data/bank/cambridge_igcse/physics_0625/skill_index_v0.json
"""

import sys
import re
import json
from pathlib import Path

COPYRIGHT_RULE = (
    "Do not copy wording, numbers, diagrams, contexts, or option order from source. "
    "Generate original exam-style questions only."
)

TARGET_COUNTS = {1: 5, 2: 3, 3: 2}

GENERATION_MODES = {
    "ready_internal":    "original_variant",
    "needs_human_review": "original_variant",
    "not_publishable":   "original_authoring_required",
}


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[/–—]", " ", text)
    text = re.sub(r"[^a-z0-9\s_]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text.strip("_")


def skill_priority(qs):
    """
    1 = has ready_internal seed
    2 = has needs_human_review (no blocked-only)
    3 = all not_publishable
    """
    if qs["ready_internal"] > 0:
        return 1
    if qs["needs_human_review"] > 0:
        return 2
    return 3


def seed_quality_label(priority):
    if priority == 1:
        return "ready_internal"
    if priority == 2:
        return "needs_human_review"
    return "not_publishable"


def build_targets(bank, skill_index):
    # Build item lookup: item_id -> item
    item_map = {item["item_id"]: item for item in bank["items"]}

    src = bank["items"][0]["source"] if bank["items"] else {}
    board         = src.get("board", "cambridge")
    level         = src.get("level", "igcse")
    subject       = src.get("subject", "physics")
    syllabus_code = src.get("syllabus_code", "0625")

    targets = []

    for topic_obj in skill_index["topics"]:
        topic = topic_obj["topic"]
        for sub_obj in topic_obj["subtopics"]:
            subtopic = sub_obj["subtopic"]
            for skill_obj in sub_obj["skills"]:
                skill     = skill_obj["skill"]
                qs        = skill_obj["quality_summary"]
                item_ids  = skill_obj["item_ids"]
                q_numbers = skill_obj["question_numbers"]

                priority      = skill_priority(qs)
                seed_quality  = seed_quality_label(priority)
                gen_mode      = GENERATION_MODES[seed_quality]
                target_count  = TARGET_COUNTS[priority]

                notes = []
                if priority == 3:
                    notes.append(
                        "source question is not usable (diagram/table parsing failure) — "
                        "author from scratch using syllabus spec"
                    )
                elif priority == 2:
                    notes.append(
                        "source question needs human review before using as generation seed"
                    )

                subtopic_slug = slugify(subtopic)
                skill_slug    = slugify(skill)
                target_id = (
                    f"gen_{board}_{level}_{subject}_{syllabus_code}"
                    f"_{subtopic_slug}_{skill_slug}_v0"
                )

                targets.append({
                    "target_id":              target_id,
                    "board":                  board,
                    "level":                  level,
                    "subject":                subject,
                    "syllabus_code":          syllabus_code,
                    "topic":                  topic,
                    "subtopic":               subtopic,
                    "skill":                  skill,
                    "priority":               priority,
                    "target_question_count":  target_count,
                    "source_seed_item_ids":   item_ids,
                    "source_question_numbers": q_numbers,
                    "seed_quality":           seed_quality,
                    "generation_mode":        gen_mode,
                    "copyright_rule":         COPYRIGHT_RULE,
                    "recommended_formats":    ["mcq"],
                    "notes":                  notes,
                })

    # Sort: priority asc, then topic, then skill
    targets.sort(key=lambda t: (t["priority"], t["topic"], t["skill"]))
    return targets


def validate_targets(targets):
    all_ids = [t["target_id"] for t in targets]
    seen, duplicates = set(), []
    for tid in all_ids:
        if tid in seen:
            duplicates.append(tid)
        seen.add(tid)
    return len(targets) == 40, sorted(set(duplicates))


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def build_markdown(targets, total_planned, ids_unique, duplicate_ids):
    ready_targets    = [t for t in targets if t["seed_quality"] == "ready_internal"]
    review_targets   = [t for t in targets if t["seed_quality"] == "needs_human_review"]
    blocked_targets  = [t for t in targets if t["seed_quality"] == "not_publishable"]

    dup_str = ", ".join(f"`{d}`" for d in duplicate_ids) if duplicate_ids else "none"

    lines = []
    lines.append("# Cambridge IGCSE Physics 0625 Generation Targets v0")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"| ------ | ----: |")
    lines.append(f"| Total targets | {len(targets)} |")
    lines.append(f"| Total planned questions | {total_planned} |")
    lines.append(f"| Ready-seed targets (priority 1) | {len(ready_targets)} |")
    lines.append(f"| Review-seed targets (priority 2) | {len(review_targets)} |")
    lines.append(f"| Original-authoring-required (priority 3) | {len(blocked_targets)} |")
    lines.append(f"| Target IDs unique | {'yes' if ids_unique else 'NO — see duplicates'} |")
    lines.append(f"| Duplicate target IDs | {dup_str} |")
    lines.append("")

    lines.append("## All Targets")
    lines.append("")
    lines.append("| P | Topic | Skill | Seed Q# | Mode | Count |")
    lines.append("| -: | ----- | ----- | ------: | ---- | ----: |")
    for t in targets:
        q_str  = ", ".join(str(n) for n in t["source_question_numbers"])
        mode   = "variant" if t["generation_mode"] == "original_variant" else "author"
        lines.append(
            f"| {t['priority']} | {t['topic']} | {t['skill']} "
            f"| {q_str} | {mode} | {t['target_question_count']} |"
        )
    lines.append("")

    lines.append("## Start Here")
    lines.append("")
    lines.append(
        "Top 6 targets with `ready_internal` seeds — "
        "these have a clean source question to base variants on:"
    )
    lines.append("")

    for i, t in enumerate(ready_targets[:6], 1):
        q_str   = ", ".join(str(n) for n in t["source_question_numbers"])
        id_str  = ", ".join(f"`{i}`" for i in t["source_seed_item_ids"])
        lines.append(f"### {i}. {t['skill']}")
        lines.append("")
        lines.append(f"- **Topic:** {t['topic']} / {t['subtopic']}")
        lines.append(f"- **Seed item:** {id_str}  (Q{q_str})")
        lines.append(f"- **Generate:** {t['target_question_count']} original MCQ variants")
        lines.append(f"- **Target ID:** `{t['target_id']}`")
        lines.append(f"- **Rule:** {COPYRIGHT_RULE}")
        lines.append("")

    lines.append("## Priority 2: Review-Seed Targets")
    lines.append("")
    lines.append(
        "These skills have a source question but it needs human review "
        "before being used as a generation seed:"
    )
    lines.append("")
    lines.append("| Topic | Subtopic | Skill | Seed Q# | Count |")
    lines.append("| ----- | -------- | ----- | ------: | ----: |")
    for t in review_targets:
        q_str = ", ".join(str(n) for n in t["source_question_numbers"])
        lines.append(
            f"| {t['topic']} | {t['subtopic']} | {t['skill']} "
            f"| {q_str} | {t['target_question_count']} |"
        )
    lines.append("")

    lines.append("## Priority 3: Original Authoring Required")
    lines.append("")
    lines.append(
        "These skills have no usable source question. "
        "A teacher or author must write original questions from scratch "
        "using the Cambridge 0625 syllabus specification:"
    )
    lines.append("")
    lines.append("| Topic | Subtopic | Skill | Count |")
    lines.append("| ----- | -------- | ----- | ----: |")
    for t in blocked_targets:
        lines.append(
            f"| {t['topic']} | {t['subtopic']} | {t['skill']} "
            f"| {t['target_question_count']} |"
        )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(bank_path, index_path):
    bank        = json.loads(bank_path.read_text(encoding="utf-8"))
    skill_index = json.loads(index_path.read_text(encoding="utf-8"))

    targets = build_targets(bank, skill_index)

    ids_unique, duplicate_ids = validate_targets(targets)
    if not ids_unique or duplicate_ids:
        print(f"WARNING: validation failed — count_ok={ids_unique}, duplicates={duplicate_ids}")

    ready_count   = sum(1 for t in targets if t["seed_quality"] == "ready_internal")
    review_count  = sum(1 for t in targets if t["seed_quality"] == "needs_human_review")
    blocked_count = sum(1 for t in targets if t["seed_quality"] == "not_publishable")
    total_planned = sum(t["target_question_count"] for t in targets)

    md = build_markdown(targets, total_planned, ids_unique, duplicate_ids)

    out_dir = bank_path.parent
    targets_path = out_dir / "generation_targets_v0.json"
    report_path  = out_dir / "generation_targets_report.md"

    targets_path.write_text(
        json.dumps(
            {
                "total_targets":        len(targets),
                "target_ids_unique":    ids_unique and not duplicate_ids,
                "duplicate_target_ids": duplicate_ids,
                "targets":              targets,
            },
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report_path.write_text(md, encoding="utf-8")

    print(f"total_targets                      : {len(targets)}")
    print(f"total_planned_questions            : {total_planned}")
    print(f"target_ids_unique                  : {ids_unique and not duplicate_ids}")
    print(f"duplicate_target_ids               : {duplicate_ids if duplicate_ids else 'none'}")
    print(f"generation_targets_v0              : {targets_path}")
    print(f"generation_targets_report          : {report_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: python {sys.argv[0]} <internal_bank_v0.json> <skill_index_v0.json>")
    bank_p  = Path(sys.argv[1])
    index_p = Path(sys.argv[2])
    for p in (bank_p, index_p):
        if not p.exists():
            sys.exit(f"Error: file not found: {p}")
    run(bank_p, index_p)
