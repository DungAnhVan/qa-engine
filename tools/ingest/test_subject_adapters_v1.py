"""
Gate 50E — Subject Adapter Test Script v1.
Tests classify_topic, classify_skill, and infer_resource_type for a range of subject slugs.
Writes a JSON report and markdown manifest to data/diagnostics/.

CLI:
    .venv-ingest\\Scripts\\python.exe tools\\ingest\\test_subject_adapters_v1.py
"""
from __future__ import annotations

import sys
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from subject_adapters.registry import get_adapter, list_registered_slugs

# ---------------------------------------------------------------------------
# Test subjects and sample texts
# ---------------------------------------------------------------------------

TEST_CASES: list[dict] = [
    {
        "subject_slug": "physics_0625",
        "sample_topic_text": "Calculate the force when mass is 5 kg and acceleration is 3 m/s2.",
        "sample_skill_text": "Calculate the velocity of the object after 4 seconds.",
    },
    {
        "subject_slug": "chemistry_0620",
        "sample_topic_text": "State the number of protons, neutrons and electrons in a sodium ion.",
        "sample_skill_text": "Calculate the percentage yield of the reaction.",
    },
    {
        "subject_slug": "biology_0610",
        "sample_topic_text": "Describe the role of enzymes in the process of digestion in the small intestine.",
        "sample_skill_text": "Explain how osmosis occurs across a partially permeable membrane in a plant cell.",
    },
    {
        "subject_slug": "mathematics_0580",
        "sample_topic_text": "Factorise the expression 2x^2 + 5x - 3 and solve the quadratic equation.",
        "sample_skill_text": "Calculate the area of the cylinder with radius 4 cm and height 10 cm.",
    },
    {
        "subject_slug": "computer_science_0478",
        "sample_topic_text": "Trace through the algorithm and state the output when n = 5.",
        "sample_skill_text": "Write pseudocode for a binary search algorithm.",
    },
    {
        "subject_slug": "business_studies_0450",
        "sample_topic_text": "Explain two ways in which motivation can improve employee performance.",
        "sample_skill_text": "Calculate the break-even output given fixed costs of $5000 and contribution per unit of $25.",
    },
    {
        "subject_slug": "economics_0455",
        "sample_topic_text": "Explain how a decrease in price leads to an extension in demand using a diagram.",
        "sample_skill_text": "From the data, calculate the percentage change in GDP from 2020 to 2022.",
    },
    {
        "subject_slug": "geography_0460",
        "sample_topic_text": "Describe the process of urbanisation and its effects on population distribution.",
        "sample_skill_text": "From the map, identify the contour lines and calculate the gradient.",
    },
    {
        "subject_slug": "english_first_language_0500",
        "sample_topic_text": "How does the writer use language to create a sense of tension in the extract?",
        "sample_skill_text": "Write a summary of the key information in the passage in no more than 120 words.",
    },
    {
        "subject_slug": "english_literature_0475",
        "sample_topic_text": "How does the writer develop the character of the protagonist throughout the text?",
        "sample_skill_text": "Select evidence from the extract to support your argument about the theme of power.",
    },
    {
        "subject_slug": "unknown_9999",
        "sample_topic_text": "Analyse the impact of globalisation on developing economies.",
        "sample_skill_text": "Describe the main features of the system under study.",
    },
]

# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

def run_tests() -> list[dict]:
    results = []
    registered = list_registered_slugs()

    for case in TEST_CASES:
        slug      = case["subject_slug"]
        topic_txt = case["sample_topic_text"]
        skill_txt = case["sample_skill_text"]

        adapter    = get_adapter(slug)
        meta       = adapter.get_adapter_metadata()
        is_registered = slug in registered

        topic_result = adapter.classify_topic(topic_txt)
        skill_result = adapter.classify_skill(skill_txt)
        restype_result = adapter.infer_resource_type(skill_txt)

        needs_review = (
            meta["adapter_status"] == "generic_adapter"
            or topic_result["confidence"] < 0.4
        )

        result = {
            "subject_slug":    slug,
            "is_registered":   is_registered,
            "adapter_name":    meta["adapter_name"],
            "adapter_status":  meta["adapter_status"],
            "topic_count":     meta.get("topic_count", 0),
            "topic_result": {
                "topic":            topic_result["topic"],
                "skill_type":       topic_result["skill_type"],
                "resource_type":    topic_result["resource_type"],
                "confidence":       topic_result["confidence"],
                "matched_keywords": topic_result["matched_keywords"][:5],
            },
            "skill_result": {
                "skill_type":       skill_result["skill_type"],
                "resource_type":    skill_result["resource_type"],
                "confidence":       skill_result["confidence"],
                "matched_keywords": skill_result["matched_keywords"][:5],
            },
            "resource_type_result": {
                "resource_type":    restype_result["resource_type"],
                "skill_type":       restype_result["skill_type"],
                "confidence":       restype_result["confidence"],
            },
            "needs_human_review": needs_review,
        }
        results.append(result)

        # Print
        print(f"\n{'-'*62}")
        print(f"Subject slug : {slug}")
        print(f"Adapter      : {meta['adapter_name']} ({meta['adapter_status']})")
        print(f"Registered   : {is_registered}")
        print(f"Topic        : {topic_result['topic']} (conf={topic_result['confidence']})")
        print(f"Skill type   : {skill_result['skill_type']}")
        print(f"Resource type: {restype_result['resource_type']}")
        print(f"NHR          : {needs_review}")
        if topic_result["matched_keywords"]:
            print(f"Matched kws  : {topic_result['matched_keywords'][:4]}")

    return results


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(results: list[dict], now_iso: str) -> dict:
    total         = len(results)
    registered    = sum(1 for r in results if r["is_registered"])
    generic_count = sum(1 for r in results if r["adapter_status"] == "generic_adapter")
    nhr_count     = sum(1 for r in results if r["needs_human_review"])
    full_count    = sum(1 for r in results if r["adapter_status"] == "full_adapter")
    basic_count   = sum(1 for r in results if r["adapter_status"] == "basic_adapter")

    return {
        "report_id":         "quanta_aptus_subject_adapter_test_report_v1",
        "version":           "0.1.0",
        "created_at":        now_iso,
        "total_tested":      total,
        "registered_count":  registered,
        "full_adapter_count": full_count,
        "basic_adapter_count": basic_count,
        "generic_adapter_count": generic_count,
        "needs_human_review_count": nhr_count,
        "all_registered_slugs": list_registered_slugs(),
        "results":           results,
    }


def build_manifest_md(report: dict) -> str:
    lines = [
        "# Subject Adapter Test Report v1",
        "",
        f"**Generated:** {report['created_at']}",
        f"**Total tested:** {report['total_tested']}",
        f"**Registered adapters:** {report['registered_count']} / {report['total_tested']}",
        f"**Full adapters:** {report['full_adapter_count']}",
        f"**Basic adapters:** {report['basic_adapter_count']}",
        f"**Generic fallback:** {report['generic_adapter_count']}",
        f"**Needs human review:** {report['needs_human_review_count']}",
        "",
        "## Test Results",
        "",
        "| Subject Slug | Adapter | Status | Topic | Skill Type | Resource Type | Conf | NHR |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        tr = r["topic_result"]
        sr = r["skill_result"]
        rr = r["resource_type_result"]
        nhr = "YES" if r["needs_human_review"] else "no"
        lines.append(
            f"| {r['subject_slug']} | {r['adapter_status']} | "
            f"{r['adapter_name']} | {tr['topic'][:30]} | {sr['skill_type']} | "
            f"{rr['resource_type']} | {tr['confidence']} | {nhr} |"
        )

    lines += [
        "",
        "## All Registered Subject Slugs",
        "",
    ]
    for slug in report["all_registered_slugs"]:
        lines.append(f"- `{slug}`")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    print("=" * 62)
    print("Quanta Aptus Subject Adapter Test v1")
    print(f"Registered adapters: {len(list_registered_slugs())}")
    print("=" * 62)

    results  = run_tests()
    report   = build_report(results, now_iso)
    manifest = build_manifest_md(report)

    out_dir = PROJECT_ROOT / "data" / "diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "subject_adapter_test_report_v1.json"
    md_path   = out_dir / "subject_adapter_test_manifest_v1.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(manifest, encoding="utf-8")

    print(f"\n{'='*62}")
    print(f"total_tested         : {report['total_tested']}")
    print(f"registered_count     : {report['registered_count']}")
    print(f"full_adapter_count   : {report['full_adapter_count']}")
    print(f"basic_adapter_count  : {report['basic_adapter_count']}")
    print(f"generic_count        : {report['generic_adapter_count']}")
    print(f"needs_human_review   : {report['needs_human_review_count']}")
    print(f"report               -> {json_path}")
    print(f"manifest             -> {md_path}")


if __name__ == "__main__":
    main()
