"""
Gate 70C -- Build Package Candidate Gate Report v1

Aggregates all Gate 70C artefacts into a single gate report for review
and handoff to Gate 70D.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate70c_ai_bank_package_candidate_report_v1.py

Output:
  data/diagnostics/gate70c_full_report_v1.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "package_candidate":      ROOT / "data" / "ai" / "package_candidates" / "gate70c_ai_bank_package_candidate_v1.json",
    "student_payload":        ROOT / "data" / "ai" / "package_candidates" / "gate70c_student_payload_v1.json",
    "teacher_payload":        ROOT / "data" / "ai" / "package_candidates" / "gate70c_teacher_payload_v1.json",
    "student_preview":        ROOT / "data" / "ai" / "package_candidates" / "static_preview" / "gate70c_student_preview.html",
    "teacher_preview":        ROOT / "data" / "ai" / "package_candidates" / "static_preview" / "gate70c_teacher_preview.html",
    "validation_report":      ROOT / "data" / "diagnostics" / "gate70c_ai_bank_package_candidate_validation_report_v1.json",
    "build_report":           ROOT / "data" / "diagnostics" / "gate70c_ai_bank_package_candidate_build_report_v1.json",
}
OUT_FILE = ROOT / "data" / "diagnostics" / "gate70c_full_report_v1.json"

print("Gate 70C -- Build Full Gate Report v1")
print("=" * 60)

def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

pkg        = read_json(PATHS["package_candidate"])
validation = read_json(PATHS["validation_report"])
build      = read_json(PATHS["build_report"])
student_p  = read_json(PATHS["student_payload"])
teacher_p  = read_json(PATHS["teacher_payload"])

file_checklist = {k: PATHS[k].exists() for k in PATHS}
all_present    = all(file_checklist.values())

issues: list[str] = []
for name, exists in file_checklist.items():
    if not exists:
        issues.append(f"Missing artefact: {name}")

validation_passed = (validation or {}).get("valid", False)
build_status      = (build or {}).get("status", "not_built")

if not validation_passed:
    issues.extend((validation or {}).get("issues", ["validation report missing or invalid"]))

resource_count = (pkg or {}).get("resource_count", 0)
if resource_count == 0:
    issues.append("No resources in package candidate")

gate_status = "passed" if (all_present and validation_passed and build_status == "passed" and not issues) else "needs_review"

report = {
    "gate":           "70C",
    "gate_status":    gate_status,
    "next_gate":      "70D",
    "file_checklist": file_checklist,
    "all_artefacts_present": all_present,
    "resource_count": resource_count,
    "student_payload_count": (student_p or {}).get("resource_count", 0),
    "teacher_payload_count": (teacher_p or {}).get("resource_count", 0),
    "validation_passed":     validation_passed,
    "build_status":          build_status,
    "issues":                issues,
    "safety": {
        "teacher_final_publish_required": True,
        "auto_publish_enabled":           False,
        "supabase_write_performed":       False,
        "ai_api_called":                  False,
    },
    "gate70d_ready": gate_status == "passed",
}

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(f"Artefacts present:  {sum(file_checklist.values())}/{len(file_checklist)}")
print(f"Resources:          {resource_count}")
print(f"Validation:         {'PASSED' if validation_passed else 'NEEDS REVIEW'}")
print(f"Build status:       {build_status}")
print(f"Gate 70C status:    {gate_status.upper()}")
if issues:
    for iss in issues[:10]:
        print(f"  ! {iss}")
print(f"Report:             {OUT_FILE.relative_to(ROOT)}")
sys.exit(0 if gate_status == "passed" else 1)
