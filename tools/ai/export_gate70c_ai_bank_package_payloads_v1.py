"""
Gate 70C -- Export AI Bank Package Payloads v1

Reads the package candidate and exports:
  - Student payload  (no answer_key / marking_rubric / teacher_notes)
  - Teacher payload  (full, including provenance and model metadata)

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\export_gate70c_ai_bank_package_payloads_v1.py

Output:
  data/ai/package_candidates/gate70c_student_payload_v1.json
  data/ai/package_candidates/gate70c_teacher_payload_v1.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PKG_FILE    = ROOT / "data" / "ai" / "package_candidates" / "gate70c_ai_bank_package_candidate_v1.json"
OUT_DIR     = ROOT / "data" / "ai" / "package_candidates"
STUDENT_OUT = OUT_DIR / "gate70c_student_payload_v1.json"
TEACHER_OUT = OUT_DIR / "gate70c_teacher_payload_v1.json"

_STUDENT_EXCLUDE = {"answer_key", "marking_rubric", "teacher_notes", "provider", "model", "provenance"}

print("Gate 70C -- Export AI Bank Package Payloads v1")
print("=" * 60)

if not PKG_FILE.exists():
    print(f"ERROR: Package candidate not found: {PKG_FILE.relative_to(ROOT)}")
    print("Run build_gate70c_ai_bank_package_candidate_v1.py first.")
    sys.exit(1)

doc = json.loads(PKG_FILE.read_text(encoding="utf-8"))
resources: list[dict] = doc.get("resources", [])
print(f"Resources: {len(resources)}")

student_resources = [
    {k: v for k, v in res.items() if k not in _STUDENT_EXCLUDE}
    for res in resources
]

teacher_resources = list(resources)

student_payload = {
    "payload_type":   "student",
    "package_id":     doc.get("package_candidate_id"),
    "version":        doc.get("version"),
    "resource_count": len(student_resources),
    "teacher_final_publish_required": doc.get("teacher_final_publish_required"),
    "auto_publish_enabled":           doc.get("auto_publish_enabled"),
    "supabase_write_performed":       doc.get("supabase_write_performed"),
    "ai_api_called":                  doc.get("ai_api_called"),
    "resources": student_resources,
}

teacher_payload = {
    "payload_type":   "teacher",
    "package_id":     doc.get("package_candidate_id"),
    "version":        doc.get("version"),
    "resource_count": len(teacher_resources),
    "teacher_final_publish_required": doc.get("teacher_final_publish_required"),
    "auto_publish_enabled":           doc.get("auto_publish_enabled"),
    "supabase_write_performed":       doc.get("supabase_write_performed"),
    "ai_api_called":                  doc.get("ai_api_called"),
    "resources": teacher_resources,
}

OUT_DIR.mkdir(parents=True, exist_ok=True)
STUDENT_OUT.write_text(json.dumps(student_payload, indent=2), encoding="utf-8")
TEACHER_OUT.write_text(json.dumps(teacher_payload, indent=2), encoding="utf-8")

print(f"Student payload: {STUDENT_OUT.relative_to(ROOT)}  ({len(student_resources)} resources)")
print(f"Teacher payload: {TEACHER_OUT.relative_to(ROOT)}  ({len(teacher_resources)} resources)")

# Verify exclusions
for res in student_payload["resources"]:
    for field in _STUDENT_EXCLUDE:
        if field in res:
            print(f"WARNING: student payload contains excluded field '{field}' in {res.get('resource_id')}")
            sys.exit(1)

print("Status: PASSED")
sys.exit(0)
