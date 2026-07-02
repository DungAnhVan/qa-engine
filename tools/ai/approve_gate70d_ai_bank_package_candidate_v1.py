"""
Gate 70D -- Approve / Reject / Needs-Revision AI Bank Package Candidate v1

CLI:
  Approve:
    .venv-ingest\\Scripts\\python.exe tools\\ai\\approve_gate70d_ai_bank_package_candidate_v1.py
        --approve --approved-by local_demo_teacher --notes "approved for local publish"

  Reject:
    .venv-ingest\\Scripts\\python.exe tools\\ai\\approve_gate70d_ai_bank_package_candidate_v1.py
        --reject --approved-by local_demo_teacher --notes "not ready"

  Needs revision:
    .venv-ingest\\Scripts\\python.exe tools\\ai\\approve_gate70d_ai_bank_package_candidate_v1.py
        --needs-revision --approved-by local_demo_teacher --notes "revise before publishing"

Safety:
  - Never enable allow_supabase_sync or allow_active_switch.
  - Does not call AI API.
  - Does not write Supabase.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PKG_FILE      = ROOT / "data" / "ai" / "package_candidates" / "gate70c_ai_bank_package_candidate_v1.json"
APPROVAL_FILE = ROOT / "data" / "ai" / "package_candidates" / "gate70d_ai_bank_final_publish_approval_v1.json"
REPORT_FILE   = ROOT / "data" / "diagnostics" / "gate70d_ai_bank_final_publish_approval_report_v1.json"

parser = argparse.ArgumentParser(description="Gate 70D: final approval for AI bank package candidate")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--approve",         action="store_true")
group.add_argument("--reject",          action="store_true")
group.add_argument("--needs-revision",  action="store_true")
parser.add_argument("--approved-by",    default="local_demo_teacher")
parser.add_argument("--notes",          default="")
args = parser.parse_args()

print("Gate 70D -- Approve AI Bank Package Candidate v1")
print("=" * 60)

issues: list[str] = []

# Validate prerequisites
if not PKG_FILE.exists():
    print(f"ERROR: Package candidate not found: {PKG_FILE.relative_to(ROOT)}")
    print("Run Gate 70C first.")
    sys.exit(1)

pkg = json.loads(PKG_FILE.read_text(encoding="utf-8"))

# Basic validation of candidate
if pkg.get("status") != "draft_package_candidate":
    issues.append(f"Candidate status is not draft_package_candidate: {pkg.get('status')}")
if pkg.get("resource_count", 0) == 0:
    issues.append("Candidate has 0 resources")
if pkg.get("auto_publish_enabled") is not False:
    issues.append("Candidate auto_publish_enabled is not False — unsafe")
if pkg.get("supabase_write_performed") is not False:
    issues.append("Candidate supabase_write_performed is not False")
if pkg.get("ai_api_called") is not False:
    issues.append("Candidate ai_api_called is not False")

if issues:
    print("Candidate validation failed:")
    for iss in issues:
        print(f"  ! {iss}")
    sys.exit(1)

print(f"Candidate validated: {pkg.get('resource_count')} resources, status={pkg.get('status')}")

# Determine decision
if args.approve:
    decision = "approved"
    allow_local_publish = True
elif args.reject:
    decision = "rejected"
    allow_local_publish = False
else:
    decision = "needs_revision"
    allow_local_publish = False

now = datetime.datetime.now(datetime.timezone.utc).isoformat()

# Load and update approval file
if APPROVAL_FILE.exists():
    approval = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
else:
    approval = {
        "approval_file_id": "quanta_aptus_gate70d_ai_bank_final_publish_approval_v1",
        "version": "0.1.0",
        "source_package_candidate": "data/ai/package_candidates/gate70c_ai_bank_package_candidate_v1.json",
        "package_candidate_id": "quanta_aptus_gate70c_ai_bank_package_candidate_v1",
    }

approval.update({
    "approval_status":    decision,
    "approved_by":        args.approved_by,
    "approval_notes":     args.notes,
    "approved_at":        now,
    "allow_local_publish": allow_local_publish,
    "allow_supabase_sync": False,   # never in this gate
    "allow_active_switch": False,   # never in this gate
})

APPROVAL_FILE.write_text(json.dumps(approval, indent=2), encoding="utf-8")
print(f"Approval updated: status={decision}, allow_local_publish={allow_local_publish}")

report = {
    "gate":               "70D",
    "approval_status":    decision,
    "approved_by":        args.approved_by,
    "approval_notes":     args.notes,
    "approved_at":        now,
    "allow_local_publish": allow_local_publish,
    "allow_supabase_sync": False,
    "allow_active_switch": False,
    "candidate_resource_count": pkg.get("resource_count", 0),
    "ai_api_called":       False,
    "supabase_write_performed": False,
    "issues":              issues,
}

REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report: {REPORT_FILE.relative_to(ROOT)}")
print(f"Status: {'APPROVED' if decision == 'approved' else decision.upper()}")
sys.exit(0)
