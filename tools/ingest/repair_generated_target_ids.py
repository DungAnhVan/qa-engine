"""
Repair incorrect target_ids in a generated batch using topic/subtopic/skill lookup.

Usage:
    python tools/ingest/repair_generated_target_ids.py <authoring_batch.json> <generated_batch.json>

Example:
    .venv-ingest/Scripts/python.exe tools/ingest/repair_generated_target_ids.py \
        data/bank/cambridge_igcse/physics_0625/authoring_batch_001.json \
        data/bank/cambridge_igcse/physics_0625/generated_batch_001.json
"""

import sys
import json
import copy
from pathlib import Path


def build_lookup(batch_spec):
    """
    Returns:
        valid_ids  : set of valid target_id strings
        skill_map  : (topic, subtopic, skill) -> target_id
    """
    valid_ids = set()
    skill_map = {}
    for t in batch_spec.get("targets", []):
        tid = t["target_id"]
        valid_ids.add(tid)
        key = (t["topic"], t["subtopic"], t["skill"])
        skill_map[key] = tid
    return valid_ids, skill_map


def repair(batch_spec_path, generated_path):
    batch_spec = json.loads(batch_spec_path.read_text(encoding="utf-8"))
    generated  = json.loads(generated_path.read_text(encoding="utf-8"))

    valid_ids, skill_map = build_lookup(batch_spec)

    items_out      = []
    repaired_count = 0
    unresolved     = []

    for item in generated.get("generated_items", []):
        item_out = copy.deepcopy(item)
        tid      = item.get("target_id", "")

        if tid in valid_ids:
            # Already correct — no repair needed
            items_out.append(item_out)
            continue

        # Try to resolve via topic/subtopic/skill
        key     = (item.get("topic", ""), item.get("subtopic", ""), item.get("skill", ""))
        new_tid = skill_map.get(key)

        if new_tid:
            item_out["target_id"] = new_tid
            item_out["repair"] = {
                "target_id_repaired": True,
                "old_target_id":      tid,
                "new_target_id":      new_tid,
            }
            repaired_count += 1
        else:
            item_out["repair"] = {
                "target_id_repaired": False,
                "old_target_id":      tid,
                "new_target_id":      None,
                "issue": (
                    f"no target found for topic='{item.get('topic')}', "
                    f"subtopic='{item.get('subtopic')}', skill='{item.get('skill')}'"
                ),
            }
            unresolved.append(item.get("generated_item_id", "<unknown>"))

        items_out.append(item_out)

    total = len(items_out)

    repaired_out = {
        "batch_id":        generated.get("batch_id", ""),
        "generated_items": items_out,
    }
    report_out = {
        "total_items":      total,
        "repaired_count":   repaired_count,
        "unresolved_count": len(unresolved),
        "unresolved_items": unresolved,
    }

    out_dir     = generated_path.parent
    stem        = generated_path.stem           # e.g. "generated_batch_001"
    repaired_path = out_dir / f"{stem}.repaired.json"
    report_path   = out_dir / f"{stem}.repair_report.json"

    repaired_path.write_text(
        json.dumps(repaired_out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(report_out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"total_items       : {total}")
    print(f"repaired_count    : {repaired_count}")
    print(f"unresolved_count  : {len(unresolved)}")
    print(f"repaired_json     : {repaired_path}")
    print(f"repair_report     : {report_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: python {sys.argv[0]} <authoring_batch.json> <generated_batch.json>")
    spec_p = Path(sys.argv[1])
    gen_p  = Path(sys.argv[2])
    for p in (spec_p, gen_p):
        if not p.exists():
            sys.exit(f"Error: file not found: {p}")
    repair(spec_p, gen_p)
