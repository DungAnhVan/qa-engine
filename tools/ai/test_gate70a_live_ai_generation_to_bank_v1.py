"""
Gate 70A -- Test Suite v1

Tests AI generation pipeline from safe requests to question bank.
Dry-run by default. Execute requires QA_GATE70A_EXECUTE=true env var.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate70a_live_ai_generation_to_bank_v1.py

Env vars:
  QA_GATE70A_EXECUTE=true   run real generation (requires QA_AI_DRY_RUN=false + API key)

Exit codes: 0 = all passed, 1 = one or more failures.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[2]
PYTHON = sys.executable

REQUESTS_FILE  = ROOT / "data" / "ai" / "generation_requests" / "ai_safe_generation_requests_v1.json"
BANK_FILE      = ROOT / "data" / "ai" / "question_bank" / "ai_generated_question_bank_v1.json"
QUEUE_FILE     = ROOT / "data" / "ai" / "teacher_review" / "ai_teacher_review_queue_v1.json"
VALIDATE_FILE  = ROOT / "data" / "diagnostics" / "ai_question_bank_validation_v1.json"
BATCH_DIR      = ROOT / "data" / "ai" / "generated_batches"

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"sk-ant-[A-Za-z0-9\-]{20,}",
    r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    r"SUPABASE_SERVICE_ROLE_KEY\s*[:=]\s*\S{8,}",
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


def run_script(script: Path, extra_args: list[str] | None = None) -> tuple[int, str, str]:
    cmd = [PYTHON, str(script)] + (extra_args or [])
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
            return False, f"copyright pattern: {pat}"
    return True, ""


print("Gate 70A -- Test Suite v1")
print("=" * 60)

execute_mode = os.environ.get("QA_GATE70A_EXECUTE", "").lower() == "true"
print(f"  execute_mode: {execute_mode}")
print()

# ── T01: Scripts exist ─────────────────────────────────────────────────────

for tid, script_name in [
    ("T01", "build_safe_generation_requests_from_targets_v1.py"),
    ("T02", "run_live_ai_generation_to_bank_v1.py"),
    ("T03", "validate_ai_question_bank_v1.py"),
    ("T04", "build_teacher_review_queue_from_ai_bank_v1.py"),
]:
    path = ROOT / "tools" / "ai" / script_name
    run(f"{tid}: {script_name} exists", path.exists())

# ── T05: Admin files exist ─────────────────────────────────────────────────

for tid, rel in [
    ("T05", "apps/admin/src/lib/aiQuestionBank.ts"),
    ("T06", "apps/admin/src/app/ai-bank/page.tsx"),
    ("T07", "apps/admin/src/app/system/ai-bank/page.tsx"),
    ("T08", "apps/admin/src/app/api/system/ai-bank/route.ts"),
]:
    run(f"{tid}: {rel} exists", (ROOT / rel).exists())

# ── T09: Build safe generation requests ───────────────────────────────────

rc, out, err = run_script(
    ROOT / "tools" / "ai" / "build_safe_generation_requests_from_targets_v1.py",
    ["--subject", "physics_0625", "--limit", "3"],
)
run("T09: build_safe_generation_requests exits 0", rc == 0,
    err.strip()[:300] if rc != 0 else "")

# T10: Requests file exists
run("T10: ai_safe_generation_requests_v1.json exists", REQUESTS_FILE.exists())

# T11: Requests have correct structure
req_doc = read_json(REQUESTS_FILE)
run("T11: requests doc has request_count >= 1",
    (req_doc or {}).get("request_count", 0) >= 1,
    f"count={( req_doc or {}).get('request_count')}")

# T12: Safety fields in requests
safety_req = (req_doc or {}).get("safety", {})
run("T12: requests safety.metadata_only=True",
    safety_req.get("metadata_only") is True,
    f"safety={safety_req}")

# T13: No raw source text in requests
req_text = json.dumps(req_doc or {})
ok_c, det_c = no_copyright(req_text)
run("T13: No Cambridge copyright in requests", ok_c, det_c)

# T14: No secrets in requests
ok_s, det_s = no_secrets(req_text)
run("T14: No secrets in requests", ok_s, det_s)

# T15: Requests are metadata-only (check for disallowed field names as keys)
# Pattern: look for them as JSON object keys (preceded by quote), not as substrings of other keys
disallowed_as_keys = [
    '"original_raw_block"', '"raw_block"', '"source_pdf_text"',
    '"mark_scheme_raw"', '"question_raw_text"', '"extracted_text"',
]
found_disallowed = [d for d in disallowed_as_keys if d in req_text]
run("T15: No raw source text keys in requests",
    len(found_disallowed) == 0,
    f"found: {found_disallowed}")

# ── T16-T20: Dry-run generation ────────────────────────────────────────────

rc, out, err = run_script(
    ROOT / "tools" / "ai" / "run_live_ai_generation_to_bank_v1.py",
    ["--requests", str(REQUESTS_FILE.relative_to(ROOT)),
     "--batch-id", "gate70a_test_dry_batch", "--limit", "2"],
)
run("T16: dry-run generation exits 0", rc == 0, err.strip()[:300] if rc != 0 else "")

# T17: Bank file created
run("T17: bank file exists after dry-run", BANK_FILE.exists())

# T18: Bank has teacher_review_required=True
bank = read_json(BANK_FILE)
run("T18: bank teacher_review_required=True",
    (bank or {}).get("teacher_review_required") is True,
    f"got: {(bank or {}).get('teacher_review_required')}")

# T19: Bank has auto_publish_enabled=False
run("T19: bank auto_publish_enabled=False",
    (bank or {}).get("auto_publish_enabled") is False,
    f"got: {(bank or {}).get('auto_publish_enabled')}")

# T20: Bank has supabase_write_performed=False
run("T20: bank supabase_write_performed=False",
    (bank or {}).get("supabase_write_performed") is False,
    f"got: {(bank or {}).get('supabase_write_performed')}")

# ── T21: Item-level checks ─────────────────────────────────────────────────

items = (bank or {}).get("items", [])
run("T21: bank has >= 1 item", len(items) >= 1, f"count={len(items)}")

if items:
    item = items[0]
    run("T22: item.status=generated_needs_teacher_review",
        item.get("status") == "generated_needs_teacher_review",
        f"got: {item.get('status')}")
    run("T23: item.teacher_review_required=True",
        item.get("teacher_review_required") is True, "")
    run("T24: item.auto_publish_enabled=False",
        item.get("auto_publish_enabled") is False, "")
    run("T25: item.supabase_write_performed=False",
        item.get("supabase_write_performed") is False, "")
    ok_si, det_si = no_secrets(json.dumps(item))
    run("T26: No secrets in bank item", ok_si, det_si)
else:
    for t in ["T22", "T23", "T24", "T25", "T26"]:
        run(f"{t}: (skipped — no items)", True, "no items in bank")

# ── T27-T29: Validate bank ────────────────────────────────────────────────

rc, out, err = run_script(ROOT / "tools" / "ai" / "validate_ai_question_bank_v1.py")
run("T27: validate_ai_question_bank exits 0", rc == 0, err.strip()[:200] if rc != 0 else "")

run("T28: validation report exists", VALIDATE_FILE.exists())

validate = read_json(VALIDATE_FILE)
run("T29: validation.safety_summary.secrets_clean=True",
    (validate or {}).get("safety_summary", {}).get("secrets_clean") is True,
    f"got: {(validate or {}).get('safety_summary', {}).get('secrets_clean')}")

# ── T30-T31: Teacher review queue ─────────────────────────────────────────

rc, out, err = run_script(ROOT / "tools" / "ai" / "build_teacher_review_queue_from_ai_bank_v1.py")
run("T30: build_teacher_review_queue exits 0", rc == 0, err.strip()[:200] if rc != 0 else "")
run("T31: review queue file exists", QUEUE_FILE.exists())

queue_doc = read_json(QUEUE_FILE)
run("T32: queue teacher_review_required=True",
    (queue_doc or {}).get("teacher_review_required") is True,
    f"got: {(queue_doc or {}).get('teacher_review_required')}")
run("T33: queue auto_publish_enabled=False",
    (queue_doc or {}).get("auto_publish_enabled") is False,
    f"got: {(queue_doc or {}).get('auto_publish_enabled')}")

# ── T34-T35: AI client env vars ───────────────────────────────────────────

client_src = (ROOT / "tools" / "ai" / "ai_client_v1.py").read_text(encoding="utf-8")
run("T34: ai_client_v1 has QA_OPENAI_MODEL support",
    "QA_OPENAI_MODEL" in client_src)
run("T35: ai_client_v1 has QA_ANTHROPIC_MODEL support",
    "QA_ANTHROPIC_MODEL" in client_src)
run("T36: ai_client_v1 has urllib fallback",
    "_openai_urllib" in client_src and "_anthropic_urllib" in client_src)

# ── T37-T38: Env example files updated ────────────────────────────────────

env_example_text = (ROOT / ".env.example").read_text(encoding="utf-8")
run("T37: .env.example has QA_OPENAI_MODEL",    "QA_OPENAI_MODEL" in env_example_text)
run("T38: .env.example has QA_ANTHROPIC_MODEL", "QA_ANTHROPIC_MODEL" in env_example_text)

# ── T39-T40: Layout updated ───────────────────────────────────────────────

layout_text = (ROOT / "apps" / "admin" / "src" / "app" / "layout.tsx").read_text(encoding="utf-8")
run("T39: layout.tsx has /ai-bank link",         "/ai-bank" in layout_text)
run("T40: layout.tsx has /system/ai-bank link",  "/system/ai-bank" in layout_text)

# ── Optional execute mode ──────────────────────────────────────────────────

if execute_mode:
    print("\n[EXECUTE MODE — real AI API calls]")
    rc, out, err = run_script(
        ROOT / "tools" / "ai" / "run_live_ai_generation_to_bank_v1.py",
        ["--requests", str(REQUESTS_FILE.relative_to(ROOT)),
         "--batch-id", "gate70a_test_execute_batch", "--limit", "1",
         "--execute", "--confirm", "LIVE_AI_GENERATION"],
    )
    run("T41: execute generation exits 0", rc == 0, err.strip()[:300] if rc != 0 else "")
    bank_ex = read_json(BANK_FILE)
    run("T42: execute bank still has teacher_review_required=True",
        (bank_ex or {}).get("teacher_review_required") is True, "")
    run("T43: execute bank still has supabase_write_performed=False",
        (bank_ex or {}).get("supabase_write_performed") is False, "")
else:
    print("\n[EXECUTE MODE SKIPPED — set QA_GATE70A_EXECUTE=true to run real API calls]")
    for t in ["T41", "T42", "T43"]:
        run(f"{t}: (skipped)", True, "set QA_GATE70A_EXECUTE=true")

# ---------------------------------------------------------------------------

print()
print("=" * 60)
total = PASSED + FAILED
print(f"Results: {PASSED}/{total} passed, {FAILED} failed")
print(f"Status:  {'ALL PASSED' if FAILED == 0 else 'FAILURES DETECTED'}")

diag_dir = ROOT / "data" / "diagnostics"
diag_dir.mkdir(parents=True, exist_ok=True)
report_path = diag_dir / "gate70a_live_ai_generation_to_bank_test_report_v1.json"
report_path.write_text(json.dumps({
    "gate":         "70A",
    "test_suite":   "test_gate70a_live_ai_generation_to_bank_v1",
    "execute_mode": execute_mode,
    "total":        total,
    "passed":       PASSED,
    "failed":       FAILED,
    "status":       "passed" if FAILED == 0 else "failed",
    "results":      RESULTS,
}, indent=2), encoding="utf-8")
print(f"Report:  {report_path}")

sys.exit(0 if FAILED == 0 else 1)
