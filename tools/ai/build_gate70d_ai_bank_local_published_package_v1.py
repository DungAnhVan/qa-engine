"""
Gate 70D -- Build AI Bank Local Published Package v1

Reads Gate 70C package candidate and Gate 70D approval file.
Fails if approval_status != approved or allow_local_publish != true.

Outputs:
  data/ai/published/gate70d_ai_bank_package_v1/publish_package_v1.json
  data/ai/published/gate70d_ai_bank_package_v1/student_resource_payload_v1.json
  data/ai/published/gate70d_ai_bank_package_v1/teacher_resource_payload_v1.json
  data/ai/published/gate70d_ai_bank_package_v1/ai_bank_publish_manifest_v1.md
  data/ai/published/gate70d_ai_bank_package_v1/ai_bank_publish_report_v1.json
  data/diagnostics/gate70d_ai_bank_local_publish_build_report_v1.json
"""

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PKG_FILE      = ROOT / "data" / "ai" / "package_candidates" / "gate70c_ai_bank_package_candidate_v1.json"
APPROVAL_FILE = ROOT / "data" / "ai" / "package_candidates" / "gate70d_ai_bank_final_publish_approval_v1.json"
OUT_DIR       = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1"
DIAG_REPORT   = ROOT / "data" / "diagnostics" / "gate70d_ai_bank_local_publish_build_report_v1.json"

_STUDENT_EXCLUDE = {"answer_key", "marking_rubric", "teacher_notes", "provider", "model"}

print("Gate 70D -- Build AI Bank Local Published Package v1")
print("=" * 60)

# --- Guard: approval required ---
if not APPROVAL_FILE.exists():
    print("ERROR: Approval file not found. Run approve_gate70d_ai_bank_package_candidate_v1.py first.")
    sys.exit(1)

approval = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
if approval.get("approval_status") != "approved":
    print(f"ERROR: approval_status is '{approval.get('approval_status')}' — must be 'approved'.")
    sys.exit(1)
if approval.get("allow_local_publish") is not True:
    print("ERROR: allow_local_publish is not True in approval file.")
    sys.exit(1)

print(f"Approval: {approval.get('approval_status')} by {approval.get('approved_by')} at {approval.get('approved_at', '')[:19]}")

# --- Load candidate ---
if not PKG_FILE.exists():
    print("ERROR: Gate 70C package candidate not found.")
    sys.exit(1)

pkg = json.loads(PKG_FILE.read_text(encoding="utf-8"))
candidate_resources: list[dict] = pkg.get("resources", [])
print(f"Candidate resources: {len(candidate_resources)}")

now = datetime.datetime.now(datetime.timezone.utc).isoformat()

# --- Build local published package ---
resources = [dict(r) for r in candidate_resources]

publish_package = {
    "package_id":            "quanta_aptus_gate70d_ai_bank_package_v1",
    "version":               "0.1.0",
    "status":                "published_local_not_active",
    "published_at":          now,
    "source":                "gate70c_ai_bank_package_candidate",
    "package_candidate_id":  pkg.get("package_candidate_id", ""),
    "approved_by":           approval.get("approved_by"),
    "approval_notes":        approval.get("approval_notes"),
    "approved_at":           approval.get("approved_at"),
    "active_content":        False,
    "supabase_write_performed": False,
    "ai_api_called":         False,
    "teacher_final_approval": True,
    "allow_active_switch":   False,
    "allow_supabase_sync":   False,
    "resource_count":        len(resources),
    "resources":             resources,
}

student_resources = [
    {k: v for k, v in r.items() if k not in _STUDENT_EXCLUDE}
    for r in resources
]

student_payload = {
    "payload_type":   "student",
    "package_id":     "quanta_aptus_gate70d_ai_bank_package_v1",
    "status":         "published_local_not_active",
    "resource_count": len(student_resources),
    "active_content": False,
    "teacher_final_approval": True,
    "resources":      student_resources,
}

teacher_payload = {
    "payload_type":   "teacher",
    "package_id":     "quanta_aptus_gate70d_ai_bank_package_v1",
    "status":         "published_local_not_active",
    "resource_count": len(resources),
    "active_content": False,
    "teacher_final_approval": True,
    "resources":      resources,
}

manifest_lines = [
    "# AI Bank Publish Manifest — Gate 70D",
    "",
    f"- package_id: quanta_aptus_gate70d_ai_bank_package_v1",
    f"- status: published_local_not_active",
    f"- active_content: false",
    f"- supabase_write_performed: false",
    f"- ai_api_called: false",
    f"- teacher_final_approval: true",
    f"- resource_count: {len(resources)}",
    f"- published_at: {now[:19]}",
    f"- approved_by: {approval.get('approved_by')}",
    f"- approval_notes: {approval.get('approval_notes')}",
    "",
    "## Safety",
    "- Not active production content.",
    "- No Supabase write performed.",
    "- No AI API called.",
    "- Gate 70E required for Supabase sync.",
    "",
    "## Resources",
]
for r in resources:
    manifest_lines.append(f"- {r.get('resource_id')}: {r.get('title', '')[:80]}")

publish_report = {
    "package_id":         "quanta_aptus_gate70d_ai_bank_package_v1",
    "status":             "published_local_not_active",
    "published_at":       now,
    "resource_count":     len(resources),
    "active_content":     False,
    "supabase_write_performed": False,
    "ai_api_called":      False,
    "teacher_final_approval": True,
}

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "static_preview").mkdir(exist_ok=True)

(OUT_DIR / "publish_package_v1.json").write_text(json.dumps(publish_package, indent=2), encoding="utf-8")
(OUT_DIR / "student_resource_payload_v1.json").write_text(json.dumps(student_payload, indent=2), encoding="utf-8")
(OUT_DIR / "teacher_resource_payload_v1.json").write_text(json.dumps(teacher_payload, indent=2), encoding="utf-8")
(OUT_DIR / "ai_bank_publish_manifest_v1.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
(OUT_DIR / "ai_bank_publish_report_v1.json").write_text(json.dumps(publish_report, indent=2), encoding="utf-8")

for f in ["publish_package_v1.json", "student_resource_payload_v1.json",
          "teacher_resource_payload_v1.json", "ai_bank_publish_manifest_v1.md",
          "ai_bank_publish_report_v1.json"]:
    print(f"  + {(OUT_DIR / f).relative_to(ROOT)}")

diag = {
    "gate":                   "70D",
    "status":                 "passed",
    "package_id":             "quanta_aptus_gate70d_ai_bank_package_v1",
    "published_at":           now,
    "resource_count":         len(resources),
    "active_content":         False,
    "supabase_write_performed": False,
    "ai_api_called":          False,
    "teacher_final_approval": True,
}
DIAG_REPORT.parent.mkdir(parents=True, exist_ok=True)
DIAG_REPORT.write_text(json.dumps(diag, indent=2), encoding="utf-8")
print(f"Report: {DIAG_REPORT.relative_to(ROOT)}")
print("Status: PASSED")
sys.exit(0)
