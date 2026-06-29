"""
Build the Quanta Aptus Original Resource Bank v1 from a validated generated batch.

Includes resources with validation_status = "passed" or "needs_review".
Excludes resources with validation_status = "failed".

Usage:
    python tools/ingest/build_original_resource_bank_v1.py \\
        data/bank/cambridge_igcse/physics_0625/generated_batches/\\
        generated_resource_batch_v1_001.validated.json

Output (data/bank/cambridge_igcse/physics_0625/original_resource_bank/):
    original_resource_bank_v1.json
    original_resource_bank_v1_report.json
    original_resource_bank_v1_manifest.md
"""

import sys
import re
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Fields to carry through from each validated resource into a bank item
RESOURCE_FIELDS = [
    "resource_id",
    "target_id",
    "resource_type",
    "component_type",
    "topic",
    "skill_name",
    "skill_type",
    "difficulty",
    "student_prompt",
    "options",
    "correct_answer",
    "worked_solution",
    "marking_guidance",
    "common_misconception",
    "teacher_note",
    "estimated_time_minutes",
    "originality_statement",
]


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def parse_sub_path(validated_path: Path) -> dict:
    """
    Infer board / level / subject / syllabus_code from the validated-batch
    file path.  Expected structure:
        .../bank/<board_level>/<subject_syllabus>/generated_batches/...
    e.g. .../cambridge_igcse/physics_0625/generated_batches/...
    """
    parts = validated_path.parts
    result = {
        "board":         "cambridge",
        "level":         "igcse",
        "subject":       "physics",
        "syllabus_code": "0625",
    }
    for i, part in enumerate(parts):
        m_bl = re.match(r'^([a-z]+)_([a-z_]+)$', part)
        if m_bl and i + 1 < len(parts):
            m_ss = re.match(r'^([a-z_]+?)_(\d{4})$', parts[i + 1])
            if m_ss:
                result["board"]         = m_bl.group(1)
                result["level"]         = m_bl.group(2)
                result["subject"]       = m_ss.group(1)
                result["syllabus_code"] = m_ss.group(2)
                break
    return result


# ---------------------------------------------------------------------------
# Bank item builder
# ---------------------------------------------------------------------------

BANK_ID_PREFIX = "cambridge_igcse_physics_0625_orb_v1"


def build_bank_item(res: dict, idx: int, batch_id: str, now_iso: str) -> dict:
    bank_status = (
        "publish_ready"
        if res.get("validation_status") == "passed"
        else "teacher_review_required"
    )

    item: dict = {
        "bank_item_id":       f"{BANK_ID_PREFIX}_{idx:04d}",
        "resource_id":        res.get("resource_id", ""),
        "source_batch_id":    batch_id,
        "target_id":          res.get("target_id", ""),
    }

    for field in RESOURCE_FIELDS[2:]:   # skip resource_id and target_id (already added)
        item[field] = res.get(field)

    item.update({
        "validation_status":  res.get("validation_status", ""),
        "validation_errors":  res.get("validation_errors", []),
        "validation_warnings":res.get("validation_warnings", []),
        "bank_status":         bank_status,
        "content_origin":      "quanta_aptus_original_generated",
        "copyright_status":    "original_quanta_aptus_content",
        "source_use_policy":   "generated_from_derived_skill_metadata_only",
        "created_at":          now_iso,
    })
    return item


# ---------------------------------------------------------------------------
# Summary aggregation
# ---------------------------------------------------------------------------

def build_summary(items: list[dict], excluded_failed: int) -> dict:
    resource_types:  dict[str, int] = {}
    component_types: dict[str, int] = {}
    topics:          dict[str, int] = {}
    skill_types:     dict[str, int] = {}
    difficulties:    dict[str, int] = {}
    publish_ready    = 0
    review_required  = 0

    for item in items:
        def inc(d: dict, k: str | None) -> None:
            if k:
                d[k] = d.get(k, 0) + 1

        inc(resource_types,  item.get("resource_type"))
        inc(component_types, item.get("component_type"))
        inc(topics,          item.get("topic"))
        inc(skill_types,     item.get("skill_type"))
        inc(difficulties,    item.get("difficulty"))

        if item.get("bank_status") == "publish_ready":
            publish_ready += 1
        else:
            review_required += 1

    return {
        "included_count":                 len(items),
        "publish_ready_count":            publish_ready,
        "teacher_review_required_count":  review_required,
        "excluded_failed_count":          excluded_failed,
        "resource_types":                 resource_types,
        "component_types":                component_types,
        "topics":                         topics,
        "skill_types":                    skill_types,
        "difficulties":                   difficulties,
    }


# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------

def build_bank_doc(
    items: list[dict],
    summary: dict,
    bank_id: str,
    validated_path: str,
    meta: dict,
    now_iso: str,
) -> dict:
    return {
        "bank_id":               bank_id,
        "version":               "0.1.0",
        "status":                "internal_resource_bank",
        "created_at":            now_iso,
        "board":                 meta["board"],
        "level":                 meta["level"],
        "subject":               meta["subject"],
        "syllabus_code":         meta["syllabus_code"],
        "content_origin":        "quanta_aptus_original_generated",
        "copyright_status":      "original_quanta_aptus_content",
        "source_validated_batch": validated_path,
        "item_count":            len(items),
        "items":                 items,
        "summary":               summary,
    }


def build_report(
    bank_doc: dict,
    validated_path: str,
    generated_count: int,
    out_files: dict,
) -> dict:
    sm = bank_doc["summary"]

    included = sm["included_count"]
    publish  = sm["publish_ready_count"]
    review   = sm["teacher_review_required_count"]
    failed   = sm["excluded_failed_count"]

    if included == 0:
        status = "failed"
    elif review > publish:
        status = "needs_review"
    elif failed > 0:
        status = "needs_review"
    else:
        status = "passed"

    return {
        "status":                          status,
        "bank_id":                         bank_doc["bank_id"],
        "source_validated_batch":          validated_path,
        "generated_count":                 generated_count,
        "included_count":                  included,
        "publish_ready_count":             publish,
        "teacher_review_required_count":   review,
        "excluded_failed_count":           failed,
        "resource_types":                  sm["resource_types"],
        "component_types":                 sm["component_types"],
        "topics":                          sm["topics"],
        "skill_types":                     sm["skill_types"],
        "difficulties":                    sm["difficulties"],
        "output_files":                    out_files,
    }


def build_manifest_md(bank_doc: dict, report: dict) -> str:
    sm = bank_doc["summary"]
    lines = [
        "# Quanta Aptus Original Resource Bank v1",
        "",
        f"- **Board:** {bank_doc['board'].title()}",
        f"- **Level:** {bank_doc['level'].upper()}",
        f"- **Subject:** {bank_doc['subject'].title()}",
        f"- **Syllabus:** {bank_doc['syllabus_code']}",
        f"- **Bank ID:** `{bank_doc['bank_id']}`",
        f"- **Status:** {report['status']}",
        f"- **Created:** {bank_doc['created_at']}",
        "",
        f"- **Source validated batch:** `{bank_doc['source_validated_batch']}`",
        "",
        "## Resource Counts",
        "",
        f"- **Total generated (in validated batch):** {report['generated_count']}",
        f"- **Included in bank:** {sm['included_count']}",
        f"- **Publish ready:** {sm['publish_ready_count']}",
        f"- **Teacher review required:** {sm['teacher_review_required_count']}",
        f"- **Excluded (failed validation):** {sm['excluded_failed_count']}",
        "",
        "## Resource Types",
        "",
    ]
    for rt, count in sorted(sm["resource_types"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{rt}:** {count}")

    lines += ["", "## Component Types", ""]
    for ct, count in sorted(sm["component_types"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{ct}:** {count}")

    lines += ["", "## Topics", ""]
    for topic, count in sorted(sm["topics"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{topic}:** {count}")

    lines += ["", "## Output Paths", ""]
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")

    lines += [
        "",
        "---",
        "",
        "> This bank contains original Quanta Aptus generated resources.",
        "> Cambridge source papers are not published here.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON loader
# ---------------------------------------------------------------------------

def load_json(path: Path) -> tuple[dict | list | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build Quanta Aptus Original Resource Bank v1."
    )
    ap.add_argument(
        "validated_batch",
        help="Path to generated_resource_batch_v1_NNN.validated.json",
    )
    args = ap.parse_args()

    validated_path = Path(args.validated_batch)
    if not validated_path.exists():
        sys.exit(f"Error: file not found: {validated_path}")

    val_doc, err = load_json(validated_path)
    if err:
        sys.exit(f"Error reading validated batch: {err}")

    if not isinstance(val_doc, dict):
        sys.exit("Error: validated batch must be a JSON object.")

    raw_resources = val_doc.get("resources", [])
    if not isinstance(raw_resources, list):
        sys.exit("Error: 'resources' must be a list in the validated batch.")

    batch_id       = val_doc.get("batch_id", "")
    generated_count = val_doc.get("generated_count", len(raw_resources))
    now_iso         = datetime.now(timezone.utc).isoformat()

    meta    = parse_sub_path(validated_path)
    bank_id = (
        f"{meta['board']}_{meta['level']}_{meta['subject']}_"
        f"{meta['syllabus_code']}_original_resource_bank_v1"
    )

    # ── Filter resources ───────────────────────────────────────────────────
    included: list[dict] = []
    excluded_failed = 0

    for res in raw_resources:
        vs = res.get("validation_status", "")
        if vs == "failed":
            excluded_failed += 1
        elif vs in ("passed", "needs_review"):
            included.append(res)
        # Skip items with unrecognised status (treat as excluded)

    # ── Build bank items ───────────────────────────────────────────────────
    items = [
        build_bank_item(res, idx + 1, batch_id, now_iso)
        for idx, res in enumerate(included)
    ]

    out_dir = validated_path.parent.parent / "original_resource_bank"
    out_dir.mkdir(parents=True, exist_ok=True)

    bank_path   = out_dir / "original_resource_bank_v1.json"
    report_path = out_dir / "original_resource_bank_v1_report.json"
    manifest_path = out_dir / "original_resource_bank_v1_manifest.md"

    out_files = {
        "bank":     str(bank_path),
        "report":   str(report_path),
        "manifest": str(manifest_path),
    }

    summary  = build_summary(items, excluded_failed)
    bank_doc = build_bank_doc(
        items, summary, bank_id, str(validated_path), meta, now_iso
    )
    report   = build_report(bank_doc, str(validated_path), generated_count, out_files)
    manifest = build_manifest_md(bank_doc, report)

    bank_path.write_text(
        json.dumps(bank_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    manifest_path.write_text(manifest, encoding="utf-8")

    sm = bank_doc["summary"]
    print(f"status                        : {report['status']}")
    print(f"bank_id                       : {bank_id}")
    print(f"generated_count               : {generated_count}")
    print(f"included_count                : {sm['included_count']}")
    print(f"publish_ready_count           : {sm['publish_ready_count']}")
    print(f"teacher_review_required_count : {sm['teacher_review_required_count']}")
    print(f"excluded_failed_count         : {sm['excluded_failed_count']}")
    print(f"resource_types                : {sm['resource_types']}")
    print(f"component_types               : {sm['component_types']}")
    print(f"topics                        : {sm['topics']}")
    print(f"bank                          : {bank_path}")
    print(f"report                        : {report_path}")
    print(f"manifest                      : {manifest_path}")


if __name__ == "__main__":
    main()
