"""
Gate 70B -- Test Suite v1

Tests AI bank review and approval pipeline.
Writes sample decisions, applies them, validates approved items.

No AI API calls. No Supabase writes. No publish.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate70b_ai_bank_review_v1.py

Exit codes: 0 = all passed, 1 = one or more failures.
"""

import json
import re
import subprocess
import sys
import datetime
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[2]
PYTHON = sys.executable

BANK_FILE      = ROOT / "data" / "ai" / "question_bank" / "ai_generated_question_bank_v1.json"
QUEUE_FILE     = ROOT / "data" / "ai" / "teacher_review" / "ai_teacher_review_queue_v1.json"
DECISIONS_FILE = ROOT / "data" / "ai" / "review" / "gate70b_ai_bank_review_decisions_v1.json"
APPROVED_FILE  = ROOT / "data" / "ai" / "approved" / "gate70b_approved_ai_bank_items_v1.json"
REVISION_FILE  = ROOT / "data" / "ai" / "revision" / "gate70b_ai_bank_revision_items_v1.json"
REJECTED_FILE  = ROOT / "data" / "ai" / "rejected" / "gate70b_rejected_ai_bank_items_v1.json"
PENDING_FILE   = ROOT / "data" / "ai" / "review" / "gate70b_pending_ai_bank_review_items_v1.json"
APPLY_REPORT   = ROOT / "data" / "diagnostics" / "gate70b_ai_bank_review_apply_report_v1.json"
VALIDATE_RPT   = ROOT / "data" / "diagnostics" / "gate70b_approved_ai_bank_items_validation_report_v1.json"

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"sk-ant-[A-Za-z0-9\-]{20,}",
    r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    r"SUPABASE_SERVICE_ROLE_KEY\s*[:=]\s*\S{8,}",
    r"NEXT_PUBLIC_OPENAI",
    r"NEXT_PUBLIC_ANTHROPIC",
]

COPYRIGHT_PATTERNS = [
    "UCLES", "Cambridge International Examinations",
    "original_raw_block", "Question Answer Marks",
]

PASSED = 0
FAILED = 0
RESULTS: list[dict] = []


def run(label: str, ok: bool, detail: str = "") -> bool:
    global PASSED, FAILED
    PASSED += ok
    FAILED += not ok
    mark = "  [OK]" if ok else "  [FAIL]"
    msg = f"{mark}  {label}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)
    RESULTS.append({"test": label, "status": "PASS" if ok else "FAIL", "detail": detail})
    return ok


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_script(script: Path, extra: list[str] | None = None) -> tuple[int, str, str]:
    cmd = [PYTHON, str(script)] + (extra or [])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return result.returncode, result.stdout, result.stderr


def no_secrets(text: str) -> tuple[bool, str]:
    for pat in SECRET_PATTERNS:
        if re.search(pat, text):
            return False, f"secret pattern: {pat[:50]}"
    return True, ""


def no_copyright(text: str) -> tuple[bool, str]:
    for pat in COPYRIGHT_PATTERNS:
        if pat in text:
            return False, f"copyright: {pat}"
    return True, ""


print("Gate 70B -- Test Suite v1")
print("=" * 60)
print()

# ── T01-T02: Gate 70A prerequisites ───────────────────────────────────────

run("T01: Gate 70A bank file exists", BANK_FILE.exists(), str(BANK_FILE.relative_to(ROOT)))
run("T02: Gate 70A queue file exists", QUEUE_FILE.exists(), str(QUEUE_FILE.relative_to(ROOT)))

# ── T03: Decisions file exists (seed) ─────────────────────────────────────

run("T03: gate70b decisions file exists", DECISIONS_FILE.exists())

# ── T04-T05: Tool scripts exist ────────────────────────────────────────────

for tid, name in [
    ("T04", "apply_ai_bank_review_decisions_v1.py"),
    ("T05", "validate_approved_ai_bank_items_v1.py"),
]:
    run(f"{tid}: {name} exists", (ROOT / "tools" / "ai" / name).exists())

# ── T06-T09: Admin files exist ────────────────────────────────────────────

for tid, rel in [
    ("T06", "apps/admin/src/lib/aiBankReview.ts"),
    ("T07", "apps/admin/src/app/ai-bank-review/page.tsx"),
    ("T08", "apps/admin/src/app/api/ai-bank-review/decision/route.ts"),
    ("T09", "apps/admin/src/app/system/ai-bank-review/page.tsx"),
]:
    run(f"{tid}: {rel} exists", (ROOT / rel).exists())

# ── T10: Write sample decisions ────────────────────────────────────────────

print()
print("  [Writing sample decisions]")

bank   = read_json(BANK_FILE)
queue  = read_json(QUEUE_FILE)
bank_items  = (bank or {}).get("items", [])
queue_items = (queue or {}).get("queue", [])

# Produce decisions: approve first, needs_revision second, reject third
decisions = []
now = datetime.datetime.now(datetime.timezone.utc).isoformat()

for idx, item in enumerate(bank_items[:3]):
    bid = item["bank_id"]
    if idx == 0:
        decision_val = "approve"
        notes = "Content is original and educationally sound. Approved for Gate 70C."
    elif idx == 1:
        decision_val = "needs_revision"
        notes = "Correct topic but needs clearer worked steps. Please revise."
    else:
        decision_val = "reject"
        notes = "Not suitable for this difficulty level. Reject."

    import hashlib
    h = hashlib.md5(bid.encode()).hexdigest()[:8]
    decisions.append({
        "review_item_id": f"review_{bid}",
        "bank_item_id":   bid,
        "resource_id":    f"ai_res_70b_{h}",
        "decision":       decision_val,
        "reviewer_id":    "local_demo_teacher",
        "review_notes":   notes,
        "created_at":     now,
    })

# If only 1 item exists, approve it
if len(bank_items) == 1 and len(decisions) == 1:
    decisions[0]["decision"] = "approve"
    decisions[0]["review_notes"] = "Only item — approved for Gate 70C."

# Reset decisions to known state and write
DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
dec_doc = {
    "decision_file_id": "quanta_aptus_gate70b_ai_bank_review_decisions_v1",
    "version":          "0.1.0",
    "source_queue":     "data/ai/teacher_review/ai_teacher_review_queue_v1.json",
    "updated_at":       now,
    "decisions":        decisions,
}
DECISIONS_FILE.write_text(json.dumps(dec_doc, indent=2), encoding="utf-8")

run("T10: sample decisions written", DECISIONS_FILE.exists() and len(decisions) >= 1,
    f"decisions written: {len(decisions)}")
run("T11: at least one approve decision",
    any(d["decision"] == "approve" for d in decisions),
    f"decisions: {[d['decision'] for d in decisions]}")

# ── T12: Apply decisions ──────────────────────────────────────────────────

print()
rc, out, err = run_script(ROOT / "tools" / "ai" / "apply_ai_bank_review_decisions_v1.py")
run("T12: apply_ai_bank_review_decisions exits 0", rc == 0, err.strip()[:300] if rc != 0 else "")

# T13: Approved file exists
run("T13: approved file exists", APPROVED_FILE.exists())

# T14-T15: Apply report checks
apply_rpt = read_json(APPLY_REPORT)
run("T14: apply report approved_count >= 1",
    (apply_rpt or {}).get("approved_count", 0) >= 1,
    f"approved_count={( apply_rpt or {}).get('approved_count')}")
run("T15: apply report auto_publish_enabled=False",
    (apply_rpt or {}).get("auto_publish_enabled") is False, "")
run("T16: apply report supabase_write_performed=False",
    (apply_rpt or {}).get("supabase_write_performed") is False, "")
run("T17: apply report ai_api_called=False",
    (apply_rpt or {}).get("ai_api_called") is False, "")

# ── T18: Approved item structure ──────────────────────────────────────────

approved_doc = read_json(APPROVED_FILE)
approved_items = (approved_doc or {}).get("items", [])
run("T18: approved items count >= 1", len(approved_items) >= 1, f"count={len(approved_items)}")

if approved_items:
    item = approved_items[0]
    run("T19: approved item has resource_id",    bool(item.get("resource_id")))
    run("T20: approved item has student_prompt", bool(item.get("student_prompt", "").strip()))
    run("T21: approved item has answer_key",     bool(item.get("answer_key", "").strip()))
    run("T22: approved item has marking_rubric", isinstance(item.get("marking_rubric"), list) and len(item["marking_rubric"]) > 0)
    run("T23: approved item has safety_declaration", isinstance(item.get("safety_declaration"), dict))
    run("T24: approved item teacher_review_required=True", item.get("teacher_review_required") is True)
    run("T25: approved item auto_publish_enabled=False",   item.get("auto_publish_enabled") is False)
    run("T26: approved item supabase_write_performed=False", item.get("supabase_write_performed") is False)
    run("T27: approved item status=approved_pending_package",
        item.get("status") == "approved_pending_package",
        f"got: {item.get('status')}")
else:
    for t in ["T19", "T20", "T21", "T22", "T23", "T24", "T25", "T26", "T27"]:
        run(f"{t}: (skipped — no approved items)", True, "no approved items")

# ── T28: Validate approved items ──────────────────────────────────────────

rc, out, err = run_script(
    ROOT / "tools" / "ai" / "validate_approved_ai_bank_items_v1.py",
    [str(APPROVED_FILE.relative_to(ROOT))],
)
run("T28: validate_approved exits 0", rc == 0, err.strip()[:300] if rc != 0 else "")

validate = read_json(VALIDATE_RPT)
run("T29: validation report valid=True",
    (validate or {}).get("valid") is True,
    f"valid={( validate or {}).get('valid')}")
run("T30: validation secrets_clean=True",
    (validate or {}).get("safety_summary", {}).get("secrets_clean") is True, "")

# ── T31-T32: No secrets / copyright in output files ───────────────────────

approved_text = APPROVED_FILE.read_text(encoding="utf-8") if APPROVED_FILE.exists() else ""
ok_s, det_s = no_secrets(approved_text)
run("T31: No secrets in approved file", ok_s, det_s)
ok_c, det_c = no_copyright(approved_text)
run("T32: No Cambridge copyright in approved file", ok_c, det_c)

# ── T33: Revision / rejected files exist ─────────────────────────────────

if len(decisions) >= 2:
    run("T33: revision items file exists", REVISION_FILE.exists())
else:
    run("T33: revision items file exists (skipped — no revision decisions)", True, "")

# ── T34: Layout has review links ─────────────────────────────────────────

layout_text = (ROOT / "apps" / "admin" / "src" / "app" / "layout.tsx").read_text(encoding="utf-8")
run("T34: layout has /ai-bank-review link",        "/ai-bank-review" in layout_text)
run("T35: layout has /system/ai-bank-review link", "/system/ai-bank-review" in layout_text)

# ---------------------------------------------------------------------------

print()
print("=" * 60)
total = PASSED + FAILED
print(f"Results: {PASSED}/{total} passed, {FAILED} failed")
print(f"Status:  {'ALL PASSED' if FAILED == 0 else 'FAILURES DETECTED'}")

diag_dir = ROOT / "data" / "diagnostics"
diag_dir.mkdir(parents=True, exist_ok=True)
rpt = diag_dir / "gate70b_ai_bank_review_test_report_v1.json"
rpt.write_text(json.dumps({
    "gate":    "70B",
    "test_suite": "test_gate70b_ai_bank_review_v1",
    "total":   total, "passed": PASSED, "failed": FAILED,
    "status":  "passed" if FAILED == 0 else "failed",
    "results": RESULTS,
}, indent=2), encoding="utf-8")
print(f"Report:  {rpt}")
sys.exit(0 if FAILED == 0 else 1)
