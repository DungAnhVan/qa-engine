"""
Gate 69F -- Approve AI Package Candidate v1

Reads the package candidate, validates it, and writes the final publish
approval file. Approval enables local publish only — active switch and
Supabase sync remain disabled in this gate.

Usage:
  # Approve
  .venv-ingest\\Scripts\\python.exe tools\\ai\\approve_ai_package_candidate_v1.py \\
      --approve --approved-by local_demo_teacher --notes "approved for local publish"

  # Reject
  .venv-ingest\\Scripts\\python.exe tools\\ai\\approve_ai_package_candidate_v1.py \\
      --reject --approved-by local_demo_teacher --notes "needs more review"

  # Needs revision
  .venv-ingest\\Scripts\\python.exe tools\\ai\\approve_ai_package_candidate_v1.py \\
      --needs-revision --approved-by local_demo_teacher

No Supabase writes. No AI API calls. Active switch remains false.

Output:
  data/ai/package_candidates/ai_final_publish_approval_v1.json
  data/diagnostics/ai_final_publish_approval_report_v1.json
"""

import json
import sys
import argparse
import datetime
from pathlib import Path

ROOT            = Path(__file__).resolve().parents[2]
PKG_FILE        = ROOT / "data" / "ai" / "package_candidates" / "ai_resource_package_candidate_v1.json"
APPROVAL_FILE   = ROOT / "data" / "ai" / "package_candidates" / "ai_final_publish_approval_v1.json"
REPORT_FILE     = ROOT / "data" / "diagnostics" / "ai_final_publish_approval_report_v1.json"

sys.path.insert(0, str(ROOT))
from tools.ai.validate_ai_package_candidate_v1 import validate_package_candidate


def approve(decision: str, approved_by: str, notes: str | None) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # ── Load current approval file or create default ──────────────────────────
    if APPROVAL_FILE.exists():
        try:
            approval = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"ok": False, "error": f"Approval file parse error: {exc}", "generated_at": now}
    else:
        approval = {
            "approval_file_id":   "quanta_aptus_ai_final_publish_approval_v1",
            "version":            "0.1.0",
            "package_candidate_id": "quanta_aptus_ai_resource_package_candidate_v1",
            "approval_status":    "pending",
            "approved_by":        None,
            "approval_notes":     None,
            "approved_at":        None,
            "allow_local_publish": False,
            "allow_active_switch": False,
            "allow_supabase_sync": False,
        }

    # ── Validate package candidate ────────────────────────────────────────────
    if not PKG_FILE.exists():
        return {
            "ok":    False,
            "error": (
                f"Package candidate not found: {PKG_FILE}\n"
                "Run Gate 69E: .venv-ingest\\Scripts\\python.exe "
                "tools\\ai\\test_gate69e_ai_package_candidate_v1.py"
            ),
            "generated_at": now,
        }

    validation = validate_package_candidate(PKG_FILE)
    if not validation["valid"] and decision == "approve":
        return {
            "ok":    False,
            "error": "Cannot approve: package candidate validation failed",
            "issues": validation.get("issues", []),
            "generated_at": now,
        }

    # ── Apply decision ─────────────────────────────────────────────────────────
    approval["approved_by"]    = approved_by
    approval["approval_notes"] = notes
    approval["approved_at"]    = now

    if decision == "approve":
        approval["approval_status"]    = "approved"
        approval["allow_local_publish"] = True
        # active switch and Supabase sync remain disabled in this gate
        approval["allow_active_switch"] = False
        approval["allow_supabase_sync"] = False
    elif decision == "reject":
        approval["approval_status"]    = "rejected"
        approval["allow_local_publish"] = False
        approval["allow_active_switch"] = False
        approval["allow_supabase_sync"] = False
    elif decision == "needs_revision":
        approval["approval_status"]    = "needs_revision"
        approval["allow_local_publish"] = False
        approval["allow_active_switch"] = False
        approval["allow_supabase_sync"] = False

    APPROVAL_FILE.write_text(json.dumps(approval, indent=2), encoding="utf-8")
    return {
        "ok":              True,
        "decision":        decision,
        "approval_status": approval["approval_status"],
        "allow_local_publish": approval["allow_local_publish"],
        "allow_active_switch": approval["allow_active_switch"],
        "allow_supabase_sync": approval["allow_supabase_sync"],
        "validation_passed":   validation["valid"],
        "generated_at":    now,
    }


def main():
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description="Gate 69F -- Approve AI Package Candidate")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve",         action="store_true", help="Approve for local publish")
    group.add_argument("--reject",          action="store_true", help="Reject the package")
    group.add_argument("--needs-revision",  action="store_true", help="Mark as needs revision")
    parser.add_argument("--approved-by",    default="local_demo_teacher", help="Reviewer ID")
    parser.add_argument("--notes",          default=None,        help="Approval/rejection notes")
    args = parser.parse_args()

    decision = "approve" if args.approve else ("reject" if args.reject else "needs_revision")

    print("Gate 69F -- Approve AI Package Candidate v1")
    print(f"Decision: {decision}")
    print("-" * 55)

    result = approve(decision, args.approved_by, args.notes)
    now    = result["generated_at"]

    if not result["ok"]:
        print(f"\n  ! FAILED: {result['error']}")
        for iss in result.get("issues", []):
            print(f"    ! {iss}")
        report = {"status": "failed", "error": result["error"],
                  "issues": result.get("issues", []), "generated_at": now}
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport: {REPORT_FILE}")
        sys.exit(1)

    sym = lambda ok: "+" if ok else "!"
    print(f"  [{sym(result['approval_status'] == 'approved')}] approval_status:    {result['approval_status']}")
    print(f"  [{sym(result['allow_local_publish'])}] allow_local_publish: {result['allow_local_publish']}")
    print(f"  [+] allow_active_switch: {result['allow_active_switch']}")
    print(f"  [+] allow_supabase_sync: {result['allow_supabase_sync']}")
    print(f"  [{sym(result['validation_passed'])}] validation_passed:   {result['validation_passed']}")
    print(f"\nApproval file: {APPROVAL_FILE}")

    report = {
        "status":              "passed" if result["ok"] else "failed",
        "decision":            decision,
        "approval_status":     result["approval_status"],
        "allow_local_publish": result["allow_local_publish"],
        "allow_active_switch": result["allow_active_switch"],
        "allow_supabase_sync": result["allow_supabase_sync"],
        "validation_passed":   result["validation_passed"],
        "approved_by":         args.approved_by,
        "generated_at":        now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
