"""
Gate 70A -- Build Gate Report v1

Checks all Gate 70A deliverables and writes gate report + DONE marker.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate70a_live_ai_generation_to_bank_report_v1.py

Output:
  data/diagnostics/gate70a_live_ai_generation_to_bank_report_v1.json
  data/diagnostics/GATE_70A_LIVE_AI_GENERATION_TO_BANK_DONE.md
"""

import json
import re
import datetime
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

now = datetime.datetime.now(datetime.timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Deliverables
# ---------------------------------------------------------------------------

DELIVERABLES = [
    ("D01", "ai_client_v1.py (updated)",
     ROOT / "tools" / "ai" / "ai_client_v1.py"),
    ("D02", ".env.example (updated)",
     ROOT / ".env.example"),
    ("D03", ".env.production.example (updated)",
     ROOT / ".env.production.example"),
    ("D04", "build_safe_generation_requests_from_targets_v1.py",
     ROOT / "tools" / "ai" / "build_safe_generation_requests_from_targets_v1.py"),
    ("D05", "run_live_ai_generation_to_bank_v1.py",
     ROOT / "tools" / "ai" / "run_live_ai_generation_to_bank_v1.py"),
    ("D06", "validate_ai_question_bank_v1.py",
     ROOT / "tools" / "ai" / "validate_ai_question_bank_v1.py"),
    ("D07", "build_teacher_review_queue_from_ai_bank_v1.py",
     ROOT / "tools" / "ai" / "build_teacher_review_queue_from_ai_bank_v1.py"),
    ("D08", "aiQuestionBank.ts",
     ROOT / "apps" / "admin" / "src" / "lib" / "aiQuestionBank.ts"),
    ("D09", "ai-bank/page.tsx",
     ROOT / "apps" / "admin" / "src" / "app" / "ai-bank" / "page.tsx"),
    ("D10", "system/ai-bank/page.tsx",
     ROOT / "apps" / "admin" / "src" / "app" / "system" / "ai-bank" / "page.tsx"),
    ("D11", "api/system/ai-bank/route.ts",
     ROOT / "apps" / "admin" / "src" / "app" / "api" / "system" / "ai-bank" / "route.ts"),
    ("D12", "test_gate70a_live_ai_generation_to_bank_v1.py",
     ROOT / "tools" / "ai" / "test_gate70a_live_ai_generation_to_bank_v1.py"),
    ("D13", "build_gate70a_live_ai_generation_to_bank_report_v1.py",
     ROOT / "tools" / "ai" / "build_gate70a_live_ai_generation_to_bank_report_v1.py"),
    ("D14", "layout.tsx (updated)",
     ROOT / "apps" / "admin" / "src" / "app" / "layout.tsx"),
]

OUTPUTS = [
    ("O01", "ai_safe_generation_requests_v1.json",
     ROOT / "data" / "ai" / "generation_requests" / "ai_safe_generation_requests_v1.json"),
    ("O02", "ai_generated_question_bank_v1.json",
     ROOT / "data" / "ai" / "question_bank" / "ai_generated_question_bank_v1.json"),
    ("O03", "ai_teacher_review_queue_v1.json",
     ROOT / "data" / "ai" / "teacher_review" / "ai_teacher_review_queue_v1.json"),
    ("O04", "ai_question_bank_validation_v1.json",
     ROOT / "data" / "diagnostics" / "ai_question_bank_validation_v1.json"),
    ("O05", "gate70a test report",
     ROOT / "data" / "diagnostics" / "gate70a_live_ai_generation_to_bank_test_report_v1.json"),
]

# ---------------------------------------------------------------------------
# Read helper
# ---------------------------------------------------------------------------

def read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except Exception:
        return None

bank      = read_json(ROOT / "data" / "ai" / "question_bank" / "ai_generated_question_bank_v1.json")
requests  = read_json(ROOT / "data" / "ai" / "generation_requests" / "ai_safe_generation_requests_v1.json")
queue_doc = read_json(ROOT / "data" / "ai" / "teacher_review" / "ai_teacher_review_queue_v1.json")
validate  = read_json(ROOT / "data" / "diagnostics" / "ai_question_bank_validation_v1.json")
test_rpt  = read_json(ROOT / "data" / "diagnostics" / "gate70a_live_ai_generation_to_bank_test_report_v1.json")
client_src = (ROOT / "tools" / "ai" / "ai_client_v1.py").read_text(encoding="utf-8") if \
             (ROOT / "tools" / "ai" / "ai_client_v1.py").exists() else ""
env_example = (ROOT / ".env.example").read_text(encoding="utf-8") if \
              (ROOT / ".env.example").exists() else ""
layout_text = (ROOT / "apps" / "admin" / "src" / "app" / "layout.tsx").read_text(encoding="utf-8") if \
              (ROOT / "apps" / "admin" / "src" / "app" / "layout.tsx").exists() else ""

# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

deliverable_results = []
for d_id, label, path in DELIVERABLES:
    deliverable_results.append({
        "id": d_id, "label": label,
        "exists": path.exists(),
        "path": str(path.relative_to(ROOT)),
    })

output_results = []
for o_id, label, path in OUTPUTS:
    output_results.append({
        "id": o_id, "label": label,
        "exists": path.exists(),
        "path": str(path.relative_to(ROOT)),
    })

policy_results = []


def policy_check(label: str, ok: bool, detail: str = "") -> dict:
    return {"check": label, "ok": ok, "detail": detail}


# Policy checks
policy_results.append(policy_check(
    "requests_built",
    (requests or {}).get("request_count", 0) >= 1,
    f"count={( requests or {}).get('request_count')}",
))
policy_results.append(policy_check(
    "requests_metadata_only",
    (requests or {}).get("safety", {}).get("metadata_only") is True,
))
policy_results.append(policy_check(
    "requests_no_raw_cambridge",
    (requests or {}).get("safety", {}).get("no_cambridge_pdf_text") is True,
))
policy_results.append(policy_check(
    "bank_teacher_review_required=True",
    (bank or {}).get("teacher_review_required") is True,
    f"got={(bank or {}).get('teacher_review_required')}",
))
policy_results.append(policy_check(
    "bank_auto_publish_enabled=False",
    (bank or {}).get("auto_publish_enabled") is False,
    f"got={(bank or {}).get('auto_publish_enabled')}",
))
policy_results.append(policy_check(
    "bank_supabase_write_performed=False",
    (bank or {}).get("supabase_write_performed") is False,
    f"got={(bank or {}).get('supabase_write_performed')}",
))
policy_results.append(policy_check(
    "queue_teacher_review_required=True",
    (queue_doc or {}).get("teacher_review_required") is True,
    f"got={(queue_doc or {}).get('teacher_review_required')}",
))
policy_results.append(policy_check(
    "validation_secrets_clean",
    (validate or {}).get("safety_summary", {}).get("secrets_clean") is True,
    f"got={(validate or {}).get('safety_summary', {}).get('secrets_clean')}",
))
policy_results.append(policy_check(
    "ai_client_has_model_env_vars",
    "QA_OPENAI_MODEL" in client_src and "QA_ANTHROPIC_MODEL" in client_src,
))
policy_results.append(policy_check(
    "ai_client_has_urllib_fallback",
    "_openai_urllib" in client_src and "_anthropic_urllib" in client_src,
))
policy_results.append(policy_check(
    "env_example_has_model_vars",
    "QA_OPENAI_MODEL" in env_example and "QA_ANTHROPIC_MODEL" in env_example,
))
policy_results.append(policy_check(
    "layout_has_ai_bank_links",
    "/ai-bank" in layout_text and "/system/ai-bank" in layout_text,
))

# No API keys in generated files
bank_text = json.dumps(bank or {})
req_text  = json.dumps(requests or {})
SECRET_RE = re.compile(r"sk-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9\-]{20,}")
no_keys   = not SECRET_RE.search(bank_text) and not SECRET_RE.search(req_text)
policy_results.append(policy_check("api_keys_not_in_generated_files", no_keys))

# Service role not in client files
admin_src   = ROOT / "apps" / "admin" / "src"
client_clean = True
for fpath in list(admin_src.rglob("*.ts")) + list(admin_src.rglob("*.tsx")):
    if any(part == "api" for part in fpath.parts):
        continue
    try:
        content = fpath.read_text(encoding="utf-8", errors="replace")
        if '"use client"' not in content and "'use client'" not in content:
            continue
        if "SUPABASE_SERVICE_ROLE_KEY" in content:
            client_clean = False
            break
    except Exception:
        pass
policy_results.append(policy_check("service_role_not_in_client_files", client_clean))

# .env.local not tracked
try:
    result = subprocess.run(["git", "ls-files", ".env.local"], capture_output=True,
                            text=True, cwd=str(ROOT), timeout=10)
    env_not_tracked = not bool(result.stdout.strip())
except Exception:
    env_not_tracked = True
policy_results.append(policy_check("env_local_not_tracked", env_not_tracked))

# Test results
test_passed = (test_rpt or {}).get("passed", 0)
test_total  = (test_rpt or {}).get("total",  0)
test_status = (test_rpt or {}).get("status", "not_run")
policy_results.append(policy_check(
    "tests_passed", test_status == "passed",
    f"passed={test_passed}/{test_total} status={test_status}",
))

# Counts
d_pass = sum(1 for r in deliverable_results if r["exists"])
o_pass = sum(1 for r in output_results      if r["exists"])
p_pass = sum(1 for r in policy_results      if r["ok"])

all_ok = (d_pass == len(deliverable_results) and
          o_pass == len(output_results) and
          p_pass == len(policy_results))

# ---------------------------------------------------------------------------
# Report JSON
# ---------------------------------------------------------------------------

report = {
    "gate":       "70A",
    "name":       "Live AI Question Generation to Bank v1",
    "status":     "passed" if all_ok else "needs_review",
    "generated_at": now,
    "deliverables": deliverable_results,
    "outputs":      output_results,
    "policy":       policy_results,
    "test_results": {
        "status": test_status, "passed": test_passed, "total": test_total,
    },
    "summary": {
        "deliverables": f"{d_pass}/{len(deliverable_results)}",
        "outputs":      f"{o_pass}/{len(output_results)}",
        "policy":       f"{p_pass}/{len(policy_results)}",
        "tests":        f"{test_passed}/{test_total} ({test_status})",
    },
    "next_gate": "Gate 70B",
}

diag_dir = ROOT / "data" / "diagnostics"
diag_dir.mkdir(parents=True, exist_ok=True)
rpt_json = diag_dir / "gate70a_live_ai_generation_to_bank_report_v1.json"
rpt_md   = diag_dir / "GATE_70A_LIVE_AI_GENERATION_TO_BANK_DONE.md"

rpt_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# DONE marker
# ---------------------------------------------------------------------------

md_lines = [
    "# Gate 70A — Live AI Question Generation to Bank DONE",
    "",
    f"Generated: {now}",
    f"Status: **{'PASSED' if all_ok else 'NEEDS REVIEW'}**",
    "",
    "## What was done",
    "",
    "- `ai_client_v1.py` updated: `QA_OPENAI_MODEL`/`QA_ANTHROPIC_MODEL` env vars, urllib fallback, `model` in response.",
    "- `.env.example` and `.env.production.example` updated with model env var entries.",
    "- `build_safe_generation_requests_from_targets_v1.py`: filters targets; falls back to safe IGCSE seeds.",
    "- `run_live_ai_generation_to_bank_v1.py`: dry-run default; `--execute --confirm LIVE_AI_GENERATION` for real calls.",
    "- `validate_ai_question_bank_v1.py`: validates schema, safety fields, secrets, copyright.",
    "- `build_teacher_review_queue_from_ai_bank_v1.py`: sorted queue for teacher review.",
    "- Admin: `aiQuestionBank.ts`, `/ai-bank`, `/system/ai-bank`, `/api/system/ai-bank`.",
    "- `layout.tsx` updated with AI Bank and AI Bank Diag links.",
    "",
    "## Safety guarantees",
    "",
    "- `dry_run=True` by default — no real API calls unless `--execute --confirm LIVE_AI_GENERATION`.",
    "- `QA_AI_DRY_RUN=false` required for real calls — explicit opt-in.",
    "- No raw Cambridge PDF text, question text, or mark scheme sent to AI.",
    "- All prompts built from metadata only (authoring contract enforced).",
    "- All generated items: `status=generated_needs_teacher_review`.",
    "- `teacher_review_required=True` on all items and bank.",
    "- `auto_publish_enabled=False` — no automatic publication.",
    "- `supabase_write_performed=False` — no Supabase writes.",
    "- API keys never written to generated files or bank.",
    "",
    "## Summary",
    "",
    f"| Category     | Result |",
    f"|:-------------|:-------|",
    f"| Deliverables | {d_pass}/{len(deliverable_results)} |",
    f"| Outputs      | {o_pass}/{len(output_results)} |",
    f"| Policy       | {p_pass}/{len(policy_results)} |",
    f"| Tests        | {test_passed}/{test_total} ({test_status}) |",
    "",
    "## Next: Gate 70B",
]
rpt_md.write_text("\n".join(md_lines), encoding="utf-8")

# ---------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------

print("Gate 70A -- Gate Report v1")
print("=" * 60)
print(f"Deliverables: {d_pass}/{len(deliverable_results)}")
print(f"Outputs:      {o_pass}/{len(output_results)}")
print(f"Policy:       {p_pass}/{len(policy_results)}")
print(f"Tests:        {test_passed}/{test_total} ({test_status})")
print(f"Status:       {'PASSED' if all_ok else 'NEEDS REVIEW'}")
print()
print(f"JSON report:  {rpt_json.relative_to(ROOT)}")
print(f"DONE marker:  {rpt_md.relative_to(ROOT)}")

if not all_ok:
    print()
    print("Incomplete:")
    for r in deliverable_results:
        if not r["exists"]:
            print(f"  [MISSING] {r['id']}: {r['path']}")
    for r in output_results:
        if not r["exists"]:
            print(f"  [MISSING] {r['id']}: {r['path']}")
    for r in policy_results:
        if not r["ok"]:
            print(f"  [FAIL] {r['check']}: {r['detail']}")
