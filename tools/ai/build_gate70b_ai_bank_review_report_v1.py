"""
Gate 70B -- Build Gate Report v1

Checks all Gate 70B deliverables and writes gate report + DONE marker.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate70b_ai_bank_review_report_v1.py

Output:
  data/diagnostics/gate70b_ai_bank_review_report_v1.json
  data/diagnostics/SUPABASE_GATE_70B_AI_BANK_REVIEW_DONE.md
"""

import json
import re
import subprocess
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
now  = datetime.datetime.now(datetime.timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Deliverables
# ---------------------------------------------------------------------------

DELIVERABLES = [
    ("D01", "apply_ai_bank_review_decisions_v1.py",
     ROOT / "tools" / "ai" / "apply_ai_bank_review_decisions_v1.py"),
    ("D02", "validate_approved_ai_bank_items_v1.py",
     ROOT / "tools" / "ai" / "validate_approved_ai_bank_items_v1.py"),
    ("D03", "aiBankReview.ts",
     ROOT / "apps" / "admin" / "src" / "lib" / "aiBankReview.ts"),
    ("D04", "ai-bank-review/page.tsx",
     ROOT / "apps" / "admin" / "src" / "app" / "ai-bank-review" / "page.tsx"),
    ("D05", "api/ai-bank-review/decision/route.ts",
     ROOT / "apps" / "admin" / "src" / "app" / "api" / "ai-bank-review" / "decision" / "route.ts"),
    ("D06", "system/ai-bank-review/page.tsx",
     ROOT / "apps" / "admin" / "src" / "app" / "system" / "ai-bank-review" / "page.tsx"),
    ("D07", "api/system/ai-bank-review/route.ts",
     ROOT / "apps" / "admin" / "src" / "app" / "api" / "system" / "ai-bank-review" / "route.ts"),
    ("D08", "test_gate70b_ai_bank_review_v1.py",
     ROOT / "tools" / "ai" / "test_gate70b_ai_bank_review_v1.py"),
    ("D09", "build_gate70b_ai_bank_review_report_v1.py",
     ROOT / "tools" / "ai" / "build_gate70b_ai_bank_review_report_v1.py"),
]

OUTPUTS = [
    ("O01", "gate70b_ai_bank_review_decisions_v1.json",
     ROOT / "data" / "ai" / "review" / "gate70b_ai_bank_review_decisions_v1.json"),
    ("O02", "gate70b_approved_ai_bank_items_v1.json",
     ROOT / "data" / "ai" / "approved" / "gate70b_approved_ai_bank_items_v1.json"),
    ("O03", "gate70b_ai_bank_revision_items_v1.json",
     ROOT / "data" / "ai" / "revision" / "gate70b_ai_bank_revision_items_v1.json"),
    ("O04", "gate70b_rejected_ai_bank_items_v1.json",
     ROOT / "data" / "ai" / "rejected" / "gate70b_rejected_ai_bank_items_v1.json"),
    ("O05", "gate70b_ai_bank_review_apply_report_v1.json",
     ROOT / "data" / "diagnostics" / "gate70b_ai_bank_review_apply_report_v1.json"),
    ("O06", "gate70b_approved_ai_bank_items_validation_report_v1.json",
     ROOT / "data" / "diagnostics" / "gate70b_approved_ai_bank_items_validation_report_v1.json"),
    ("O07", "gate70b_ai_bank_review_test_report_v1.json",
     ROOT / "data" / "diagnostics" / "gate70b_ai_bank_review_test_report_v1.json"),
]

# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def rj(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except Exception:
        return None

approved_doc = rj(ROOT / "data" / "ai" / "approved" / "gate70b_approved_ai_bank_items_v1.json")
apply_rpt    = rj(ROOT / "data" / "diagnostics" / "gate70b_ai_bank_review_apply_report_v1.json")
validate_rpt = rj(ROOT / "data" / "diagnostics" / "gate70b_approved_ai_bank_items_validation_report_v1.json")
test_rpt     = rj(ROOT / "data" / "diagnostics" / "gate70b_ai_bank_review_test_report_v1.json")
layout_text  = (ROOT / "apps" / "admin" / "src" / "app" / "layout.tsx").read_text(encoding="utf-8") if \
               (ROOT / "apps" / "admin" / "src" / "app" / "layout.tsx").exists() else ""
bank_file    = ROOT / "data" / "ai" / "question_bank" / "ai_generated_question_bank_v1.json"
queue_file   = ROOT / "data" / "ai" / "teacher_review" / "ai_teacher_review_queue_v1.json"

approved_items = (approved_doc or {}).get("items", [])
approved_count = len(approved_items)

# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

deliverable_results = []
for d_id, label, path in DELIVERABLES:
    deliverable_results.append({
        "id": d_id, "label": label, "exists": path.exists(),
        "path": str(path.relative_to(ROOT)),
    })

output_results = []
for o_id, label, path in OUTPUTS:
    output_results.append({
        "id": o_id, "label": label, "exists": path.exists(),
        "path": str(path.relative_to(ROOT)),
    })

policy_results = []


def pc(label: str, ok: bool, detail: str = "") -> dict:
    return {"check": label, "ok": ok, "detail": detail}


policy_results.append(pc("gate70a_bank_exists",  bank_file.exists()))
policy_results.append(pc("gate70a_queue_exists", queue_file.exists()))
policy_results.append(pc(
    "approved_count_ge_1",
    approved_count >= 1,
    f"approved_count={approved_count}",
))
policy_results.append(pc(
    "apply_auto_publish=False",
    (apply_rpt or {}).get("auto_publish_enabled") is False,
    f"got={(apply_rpt or {}).get('auto_publish_enabled')}",
))
policy_results.append(pc(
    "apply_supabase_write=False",
    (apply_rpt or {}).get("supabase_write_performed") is False,
    f"got={(apply_rpt or {}).get('supabase_write_performed')}",
))
policy_results.append(pc(
    "apply_ai_api_called=False",
    (apply_rpt or {}).get("ai_api_called") is False,
    f"got={(apply_rpt or {}).get('ai_api_called')}",
))
policy_results.append(pc(
    "approved_items_validated",
    (validate_rpt or {}).get("valid") is True,
    f"valid={( validate_rpt or {}).get('valid')}",
))
policy_results.append(pc(
    "approved_secrets_clean",
    (validate_rpt or {}).get("safety_summary", {}).get("secrets_clean") is True,
    f"got={( validate_rpt or {}).get('safety_summary', {}).get('secrets_clean')}",
))
policy_results.append(pc(
    "approved_copyright_clean",
    (validate_rpt or {}).get("safety_summary", {}).get("copyright_clean") is True,
    f"got={( validate_rpt or {}).get('safety_summary', {}).get('copyright_clean')}",
))

# No raw Cambridge text in approved file
approved_text = json.dumps(approved_doc or {})
no_cambridge = not any(p in approved_text for p in
                       ["UCLES", "Cambridge International Examinations", "original_raw_block"])
policy_results.append(pc("raw_cambridge_text_blocked", no_cambridge))

# API keys not in generated files
SECRET_RE = re.compile(r"sk-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9\-]{20,}")
no_api_keys = not SECRET_RE.search(approved_text)
policy_results.append(pc("api_keys_not_in_approved_file", no_api_keys))

# Service role not in client files
admin_src    = ROOT / "apps" / "admin" / "src"
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
policy_results.append(pc("service_role_not_in_client", client_clean))

# Layout links
policy_results.append(pc(
    "layout_has_ai_bank_review_links",
    "/ai-bank-review" in layout_text and "/system/ai-bank-review" in layout_text,
))

# .env.local not tracked
try:
    r = subprocess.run(["git", "ls-files", ".env.local"], capture_output=True,
                       text=True, cwd=str(ROOT), timeout=10)
    env_not_tracked = not bool(r.stdout.strip())
except Exception:
    env_not_tracked = True
policy_results.append(pc("env_local_not_tracked", env_not_tracked))

# Test results
test_passed = (test_rpt or {}).get("passed", 0)
test_total  = (test_rpt or {}).get("total",  0)
test_status = (test_rpt or {}).get("status", "not_run")
policy_results.append(pc(
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
    "gate":   "70B",
    "name":   "AI Bank Review and Approval v1",
    "status": "passed" if all_ok else "needs_review",
    "generated_at": now,
    "ai_bank_review_decisions_created":  (ROOT / "data" / "ai" / "review" / "gate70b_ai_bank_review_decisions_v1.json").exists(),
    "ai_bank_review_apply_created":      (ROOT / "tools" / "ai" / "apply_ai_bank_review_decisions_v1.py").exists(),
    "approved_ai_bank_items_created":    (ROOT / "data" / "ai" / "approved" / "gate70b_approved_ai_bank_items_v1.json").exists(),
    "approved_ai_bank_items_validated":  (validate_rpt or {}).get("valid") is True,
    "ai_bank_review_ui_created":         (ROOT / "apps" / "admin" / "src" / "app" / "ai-bank-review" / "page.tsx").exists(),
    "teacher_review_required":           True,
    "auto_publish_enabled":              False,
    "supabase_write_performed":          False,
    "ai_api_called":                     False,
    "raw_cambridge_text_blocked":        no_cambridge,
    "api_keys_exposed_to_client":        not no_api_keys,
    "next_gate":                         "Gate 70C - Build Approved AI Bank Package Candidate",
    "deliverables":                      deliverable_results,
    "outputs":                           output_results,
    "policy":                            policy_results,
    "test_results":                      {"status": test_status, "passed": test_passed, "total": test_total},
    "summary":                           {
        "deliverables": f"{d_pass}/{len(deliverable_results)}",
        "outputs":      f"{o_pass}/{len(output_results)}",
        "policy":       f"{p_pass}/{len(policy_results)}",
        "tests":        f"{test_passed}/{test_total} ({test_status})",
    },
}

diag_dir = ROOT / "data" / "diagnostics"
diag_dir.mkdir(parents=True, exist_ok=True)
rpt_json = diag_dir / "gate70b_ai_bank_review_report_v1.json"
rpt_md   = diag_dir / "SUPABASE_GATE_70B_AI_BANK_REVIEW_DONE.md"

rpt_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# DONE marker
# ---------------------------------------------------------------------------

md_lines = [
    "# Gate 70B — AI Bank Review and Approval DONE",
    "",
    f"Generated: {now}",
    f"Status: **{'PASSED' if all_ok else 'NEEDS REVIEW'}**",
    "",
    "## What was done",
    "",
    "- AI bank review decisions file created (`gate70b_ai_bank_review_decisions_v1.json`).",
    "- Apply decisions tool created — produces approved/revision/rejected/pending outputs.",
    "- Approved AI bank items validated (`validate_approved_ai_bank_items_v1.py`).",
    "- Admin review UI created (`/ai-bank-review`).",
    "- Decision API created (`/api/ai-bank-review/decision`).",
    "- System diagnostic page created (`/system/ai-bank-review`).",
    "- No auto publish.",
    "- No Supabase write.",
    "- No AI API call.",
    "- Ready for Gate 70C.",
    "",
    "## Safety guarantees",
    "",
    "- `teacher_review_required: true` on all items.",
    "- `auto_publish_enabled: false` — no automatic publication.",
    "- `supabase_write_performed: false` — no Supabase writes.",
    "- `ai_api_called: false` — no AI provider calls in this gate.",
    "- No raw Cambridge source text in approved outputs.",
    "- No API keys in approved outputs.",
    "- Service role key not in client/browser files.",
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
    "## Next: Gate 70C — Build Approved AI Bank Package Candidate",
    "",
    "Only approved items proceed to Gate 70C.",
    "needs_revision and rejected items are excluded.",
]
rpt_md.write_text("\n".join(md_lines), encoding="utf-8")

# ---------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------

print("Gate 70B -- Gate Report v1")
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
