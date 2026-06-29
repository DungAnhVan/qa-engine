"""
Build topic/subtopic/skill index from internal_bank_v0.json.

Usage:
    python tools/ingest/build_skill_index.py <internal_bank_v0.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/build_skill_index.py \
        data/bank/cambridge_igcse/physics_0625/internal_bank_v0.json
"""

import sys
import json
from pathlib import Path
from collections import defaultdict, OrderedDict


# ---------------------------------------------------------------------------
# Tree builder
# ---------------------------------------------------------------------------

def build_tree(items):
    """
    Returns OrderedDict: topic -> subtopic -> skill -> list[item]
    Sorted alphabetically at each level.
    """
    raw = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for item in items:
        raw[item["topic"]][item["subtopic"]][item["skill"]].append(item)

    tree = {}
    for topic in sorted(raw):
        tree[topic] = {}
        for subtopic in sorted(raw[topic]):
            tree[topic][subtopic] = {}
            for skill in sorted(raw[topic][subtopic]):
                tree[topic][subtopic][skill] = raw[topic][subtopic][skill]
    return tree


def skill_entry(skill_name, skill_items):
    qs = {"ready_internal": 0, "needs_human_review": 0, "not_publishable": 0}
    for item in skill_items:
        qs[item["quality_status"]] += 1
    return {
        "skill":            skill_name,
        "count":            len(skill_items),
        "item_ids":         [item["item_id"] for item in skill_items],
        "question_numbers": [item["question_number"] for item in skill_items],
        "quality_summary":  qs,
    }


def build_json_output(bank, tree):
    src = bank["items"][0]["source"] if bank["items"] else {}
    topics_list = []
    for topic, subtopics in tree.items():
        subtopic_list = []
        for subtopic, skills in subtopics.items():
            skill_list = []
            for skill, items in skills.items():
                skill_list.append(skill_entry(skill, items))
            subtopic_list.append({
                "subtopic": subtopic,
                "count":    sum(s["count"] for s in skill_list),
                "skills":   skill_list,
            })
        topics_list.append({
            "topic":     topic,
            "count":     sum(s["count"] for s in subtopic_list),
            "subtopics": subtopic_list,
        })

    return {
        "board":        src.get("board", "cambridge"),
        "level":        src.get("level", "igcse"),
        "subject":      src.get("subject", "physics"),
        "syllabus_code": src.get("syllabus_code", "0625"),
        "total_items":  bank["total_items"],
        "topics":       topics_list,
    }


# ---------------------------------------------------------------------------
# Markdown report builder
# ---------------------------------------------------------------------------

def qstatus_bar(qs):
    parts = []
    if qs["ready_internal"]:
        parts.append(f"ready={qs['ready_internal']}")
    if qs["needs_human_review"]:
        parts.append(f"review={qs['needs_human_review']}")
    if qs["not_publishable"]:
        parts.append(f"blocked={qs['not_publishable']}")
    return "  ".join(parts) if parts else "—"


def build_markdown(bank, tree, total_items, total_topics, total_skills):
    lines = []

    lines.append("# Cambridge IGCSE Physics 0625 Skill Index v0")
    lines.append("")
    lines.append(f"Source: `{bank.get('document_id', '')}` — {total_items} items total")
    lines.append("")

    # Summary table
    lines.append("## Topic Summary")
    lines.append("")
    lines.append("| Topic | Items | Ready | Review | Blocked |")
    lines.append("| ----- | ----: | ----: | -----: | ------: |")

    topic_status_totals = {}
    for topic, subtopics in tree.items():
        all_items = [i for subs in subtopics.values() for skill_items in subs.values() for i in skill_items]
        qs = {"ready_internal": 0, "needs_human_review": 0, "not_publishable": 0}
        for item in all_items:
            qs[item["quality_status"]] += 1
        topic_status_totals[topic] = qs
        lines.append(
            f"| {topic} | {len(all_items)} "
            f"| {qs['ready_internal']} "
            f"| {qs['needs_human_review']} "
            f"| {qs['not_publishable']} |"
        )

    lines.append("")
    lines.append(f"**Total:** {total_items} items across {total_topics} topics and {total_skills} skills")
    lines.append("")

    # Per-topic detail
    lines.append("## Skills by Topic")
    lines.append("")

    for topic, subtopics in tree.items():
        qs_total = topic_status_totals[topic]
        lines.append(f"### {topic}  ({sum(len(si) for subs in subtopics.values() for si in subs.values())} items)")
        lines.append("")

        for subtopic, skills in subtopics.items():
            sub_count = sum(len(si) for si in skills.values())
            lines.append(f"#### {subtopic}  ({sub_count})")
            lines.append("")

            for skill, skill_items in skills.items():
                qs = {"ready_internal": 0, "needs_human_review": 0, "not_publishable": 0}
                for item in skill_items:
                    qs[item["quality_status"]] += 1
                qnums = sorted(item["question_number"] for item in skill_items)
                lines.append(f"- **{skill}**  (n={len(skill_items)})")
                lines.append(f"  - Q: {qnums}")
                lines.append(f"  - {qstatus_bar(qs)}")

            lines.append("")

    # Gaps section
    lines.append("## Gaps and Next Build Targets")
    lines.append("")

    # Skills with only 1 question
    one_q_skills = []
    all_blocked_skills = []
    generate_first_skills = []

    for topic, subtopics in tree.items():
        for subtopic, skills in subtopics.items():
            for skill, skill_items in skills.items():
                qs = {"ready_internal": 0, "needs_human_review": 0, "not_publishable": 0}
                for item in skill_items:
                    qs[item["quality_status"]] += 1

                if len(skill_items) == 1:
                    one_q_skills.append((topic, subtopic, skill, skill_items[0]["question_number"], qs))
                if qs["not_publishable"] == len(skill_items):
                    all_blocked_skills.append((topic, subtopic, skill, [i["question_number"] for i in skill_items]))
                # Good targets: thin AND has at least 1 non-blocked item
                if len(skill_items) == 1 and (qs["ready_internal"] + qs["needs_human_review"]) > 0:
                    generate_first_skills.append((topic, subtopic, skill, skill_items[0]["question_number"], qs))

    lines.append("### Skills with only 1 question (thin coverage)")
    lines.append("")
    lines.append(f"All {len(one_q_skills)} skills currently have exactly 1 question. High-priority skills for new items:")
    lines.append("")
    lines.append("| Topic | Skill | Q# | Status |")
    lines.append("| ----- | ----- | -: | ------ |")
    for topic, subtopic, skill, qnum, qs in one_q_skills:
        lines.append(f"| {topic} | {skill} | {qnum} | {qstatus_bar(qs)} |")
    lines.append("")

    lines.append("### Skills where all questions are blocked (not_publishable)")
    lines.append("")
    if all_blocked_skills:
        lines.append("These skills have no usable source question — original authoring needed before variants:")
        lines.append("")
        for topic, subtopic, skill, qnums in all_blocked_skills:
            lines.append(f"- **{topic} / {subtopic} / {skill}** — Q{qnums}")
    else:
        lines.append("None — every skill has at least one non-blocked question.")
    lines.append("")

    lines.append("### Recommended: generate original variants first")
    lines.append("")
    lines.append(
        "Skills with exactly 1 question AND at least one ready/review item — "
        "best candidates for variant generation because a real question exists to model from:"
    )
    lines.append("")
    lines.append("| Priority | Topic | Skill | Q# | Status |")
    lines.append("| -------: | ----- | ----- | -: | ------ |")

    # Sort: ready_internal first, then needs_human_review, then by topic
    generate_first_skills.sort(key=lambda x: (-x[4]["ready_internal"], x[0], x[2]))
    for rank, (topic, subtopic, skill, qnum, qs) in enumerate(generate_first_skills, 1):
        lines.append(f"| {rank} | {topic} | {skill} | {qnum} | {qstatus_bar(qs)} |")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_index(bank_path):
    bank  = json.loads(bank_path.read_text(encoding="utf-8"))
    items = bank["items"]

    tree = build_tree(items)

    total_topics = len(tree)
    total_skills = sum(
        len(skills)
        for subtopics in tree.values()
        for skills in subtopics.values()
    )

    json_out = build_json_output(bank, tree)
    md_out   = build_markdown(bank, tree, bank["total_items"], total_topics, total_skills)

    out_dir = bank_path.parent
    index_path  = out_dir / "skill_index_v0.json"
    report_path = out_dir / "skill_index_report.md"

    index_path.write_text(
        json.dumps(json_out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(md_out, encoding="utf-8")

    print(f"total_items  : {bank['total_items']}")
    print(f"topic_count  : {total_topics}")
    print(f"skill_count  : {total_skills}")
    print(f"skill_index  : {index_path}")
    print(f"skill_report : {report_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python {sys.argv[0]} <internal_bank_v0.json>")
    p = Path(sys.argv[1])
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    build_index(p)
