"""
Gate 69D -- Test AI Teacher Review Flow v1

End-to-end test of the teacher review queue:
1. Ensures Gate 69C sample batch exists.
2. Builds the review queue.
3. Writes sample decisions (approve / needs_revision / reject).
4. Applies decisions.
5. Verifies all output counts and safety policy.

No Supabase writes. No AI API calls.

Output:
  data/diagnostics/gate69d_ai_teacher_review_test_report_v1.json
"""

import json
import sys
import datetime
import re
from pathlib import Path

ROOT            = Path(__file__).resolve().parents[2]
BATCH_FILE      = ROOT / "data" / "ai" / "generated_batches" / "gate69c_sample_generated_batch_v1.json"
QUEUE_FILE      = ROOT / "data" / "ai" / "review" / "ai_teacher_review_queue_v1.json"
DECISION_FILE   = ROOT / "data" / "ai" / "review" / "ai_teacher_review_decisions_v1.json"
APPROVED_FILE   = ROOT / "data" / "ai" / "approved" / "ai_approved_resource_candidates_v1.json"
REVISION_FILE   = ROOT / "data" / "ai" / "revision" / "ai_revision_queue_v1.json"
REJECTED_FILE   = ROOT / "data" / "ai" / "rejected" / "ai_rejected_resources_v1.json"
APPLY_REPORT    = ROOT / "data" / "diagnostics" / "ai_teacher_review_decisions_apply_report_v1.json"
OUTPUT_FILE     = ROOT / "data" / "diagnostics" / "gate69d_ai_teacher_review_test_report_v1.json"

sys.path.insert(0, str(ROOT))
from tools.ai.build_ai_teacher_review_queue_v1 import build_review_queue
from tools.ai.apply_ai_teacher_review_decisions_v1 import apply_decisions

BANNED_CONTENT: list[tuple[str, re.Pattern]] = [
    ("UCLES",            re.compile(r'\bUCLES\b')),
    ("cambridge_copy",   re.compile(r'©\s*Cambridge', re.IGNORECASE)),
    ("cambridge_intl",   re.compile(r'Cambridge\s+(International|Assessment)', re.IGNORECASE)),
    ("mark_scheme_hdr",  re.compile(r'Question\s+Answer\s+Marks', re.IGNORECASE)),
    ("raw_block_field",  re.compile(r'\boriginal_raw_block\b')),
    ("raw_data_path",    re.compile(r'data[/\\]raw[/\\]')),
]

API_KEY_PATTERNS: list[re.Pattern] = [
    re.compile(r'sk-[A-Za-z0-9]{20,}'),
    re.compile(r'sk-ant-[A-Za-z0-9\-_]{30,}'),
    re.compile(r'eyJ[A-Za-z0-9+/=_-]{100,}'),
]


def scan_file_for_issues(path: Path) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    found = []
    for label, pat in BANNED_CONTENT:
        if pat.search(content):
            found.append(f"Banned pattern ({label}) in {path.name}")
    for pat in API_KEY_PATTERNS:
        if pat.search(content):
            found.append(f"API key pattern in {path.name}")
    return found


def run_test(name: str, passed: bool, detail: str = "") -> dict:
    sym = "+" if passed else "!"
    msg = f"  [{sym}] {name}"
    if detail:
        msg += f": {detail}"
    print(msg)
    return {"name": name, "passed": passed, "detail": detail}


def main():
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("Gate 69D -- AI Teacher Review Flow Test")
    print("-" * 55)
    results: list[dict] = []

    # ── T01: Gate 69C sample batch exists ────────────────────────────────────
    if not BATCH_FILE.exists():
        print(f"  ! Gate 69C sample batch not found: {BATCH_FILE}")
        print(f"  ! Run: .venv-ingest\\Scripts\\python.exe tools\\ai\\run_gate69c_sample_ai_authoring_v1.py")
        report = {"status": "failed", "error": "Gate 69C sample batch missing", "generated_at": now}
        OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport: {OUTPUT_FILE}")
        sys.exit(1)
    results.append(run_test("T01_gate69c_batch_exists", True, str(BATCH_FILE.name)))

    # ── T02: Build review queue ───────────────────────────────────────────────
    queue_result = build_review_queue(BATCH_FILE)
    t02 = queue_result["ok"]
    if t02:
        queue = queue_result["queue"]
        (ROOT / "data" / "ai" / "review").mkdir(parents=True, exist_ok=True)
        QUEUE_FILE.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    results.append(run_test("T02_review_queue_built", t02,
        f"{queue_result['queue']['item_count']} items" if t02 else str(queue_result.get("error"))))

    if not t02:
        _fail_fast(results, now)

    items = queue["items"]

    # ── T03: Queue has items ──────────────────────────────────────────────────
    results.append(run_test("T03_queue_has_items", len(items) >= 1, f"{len(items)} items"))

    # ── T04: All items start as pending ──────────────────────────────────────
    all_pending = all(it["review_status"] == "pending" for it in items)
    results.append(run_test("T04_all_items_pending", all_pending))

    # ── T05: Write sample decisions ───────────────────────────────────────────
    # approve first, needs_revision second, reject third (all that exist)
    decision_labels = ["approve", "needs_revision", "reject"]
    sample_decisions = []
    for i, item in enumerate(items):
        decision = decision_labels[i] if i < len(decision_labels) else "approve"
        sample_decisions.append({
            "review_item_id": item["review_item_id"],
            "resource_id":    item["resource_id"],
            "decision":       decision,
            "reviewer_id":    "local_demo_teacher",
            "review_notes":   f"Test decision {i+1}: {decision}",
            "created_at":     now,
        })

    decisions_data = {
        "decision_file_id": "quanta_aptus_ai_teacher_review_decisions_v1",
        "version":          "0.1.0",
        "updated_at":       now,
        "decisions":        sample_decisions,
    }
    DECISION_FILE.write_text(json.dumps(decisions_data, indent=2), encoding="utf-8")
    results.append(run_test("T05_decisions_written", True, f"{len(sample_decisions)} decisions"))

    # ── T06: Apply decisions ──────────────────────────────────────────────────
    apply_report = apply_decisions()
    t06 = apply_report.get("status") == "passed"
    results.append(run_test("T06_decisions_applied", t06, apply_report.get("status")))

    APPLY_REPORT.write_text(json.dumps(apply_report, indent=2), encoding="utf-8")

    # ── T07: approved_count >= 1 ──────────────────────────────────────────────
    approved_count = apply_report.get("approved_count", 0)
    results.append(run_test("T07_approved_count_ge_1", approved_count >= 1, str(approved_count)))

    # ── T08: needs_revision_count >= 1 ───────────────────────────────────────
    revision_count = apply_report.get("needs_revision_count", 0)
    results.append(run_test("T08_needs_revision_count_ge_1", revision_count >= 1, str(revision_count)))

    # ── T09: rejected_count >= 1 ─────────────────────────────────────────────
    rejected_count = apply_report.get("rejected_count", 0)
    results.append(run_test("T09_rejected_count_ge_1", rejected_count >= 1, str(rejected_count)))

    # ── T10: pending_count = 0 ────────────────────────────────────────────────
    pending_count = apply_report.get("pending_count", 0)
    results.append(run_test("T10_pending_count_zero", pending_count == 0, str(pending_count)))

    # ── T11: auto_publish_enabled false ──────────────────────────────────────
    auto_pub = apply_report.get("auto_publish_enabled", None)
    results.append(run_test("T11_auto_publish_disabled", auto_pub is False, str(auto_pub)))

    # ── T12: supabase_write_performed false ───────────────────────────────────
    supa_write = apply_report.get("supabase_write_performed", None)
    results.append(run_test("T12_no_supabase_write", supa_write is False, str(supa_write)))

    # ── T13: Approved file exists and has resources ───────────────────────────
    if APPROVED_FILE.exists():
        approved_data = json.loads(APPROVED_FILE.read_text(encoding="utf-8"))
        approved_resources = approved_data.get("resources", [])
        t13 = len(approved_resources) >= 1 and not approved_data.get("auto_publish_enabled")
    else:
        approved_resources = []
        t13 = False
    results.append(run_test("T13_approved_bank_valid", t13,
        f"{len(approved_resources)} resources, auto_publish={approved_data.get('auto_publish_enabled') if APPROVED_FILE.exists() else 'N/A'}"))

    # ── T14: No raw Cambridge text in output files ────────────────────────────
    content_issues: list[str] = []
    for f in [APPROVED_FILE, REVISION_FILE, REJECTED_FILE, QUEUE_FILE]:
        content_issues.extend(scan_file_for_issues(f))
    results.append(run_test("T14_no_raw_cambridge_text", len(content_issues) == 0,
        f"{len(content_issues)} issues" if content_issues else "clean"))

    # ── T15: No API keys in output files ─────────────────────────────────────
    results.append(run_test("T15_no_api_keys", len(content_issues) == 0,
        "all output files clean"))

    # ── Summary ───────────────────────────────────────────────────────────────
    passed_count = sum(1 for r in results if r["passed"])
    total_count  = len(results)
    all_passed   = passed_count == total_count

    print(f"\n{passed_count}/{total_count} tests passed")

    status = "passed" if all_passed else "failed"
    print(f"\nStatus: {status}")

    report = {
        "status":                   status,
        "tests_passed":             passed_count,
        "tests_total":              total_count,
        "tests":                    results,
        "approved_count":           apply_report.get("approved_count", 0),
        "needs_revision_count":     apply_report.get("needs_revision_count", 0),
        "rejected_count":           apply_report.get("rejected_count", 0),
        "pending_count":            apply_report.get("pending_count", 0),
        "auto_publish_enabled":     False,
        "supabase_write_performed": False,
        "teacher_approval_required": True,
        "raw_cambridge_text_issues": content_issues,
        "generated_at":             now,
    }
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {OUTPUT_FILE}")


def _fail_fast(results: list, now: str) -> None:
    report = {
        "status":       "failed",
        "tests_passed": sum(1 for r in results if r["passed"]),
        "tests_total":  len(results),
        "tests":        results,
        "generated_at": now,
    }
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nStatus: failed")
    print(f"Report: {OUTPUT_FILE}")
    sys.exit(1)


if __name__ == "__main__":
    main()
