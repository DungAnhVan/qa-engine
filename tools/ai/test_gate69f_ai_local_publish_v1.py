"""
Gate 69F -- Test Suite v1

Acceptance tests for the AI Package Final Approval + Local Publish pipeline.
Runs the full pipeline (approve, build, validate, preview, registry) using
demo data and asserts all Gate 69F deliverables are present and correct.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate69f_ai_local_publish_v1.py

Exit codes: 0 = all passed, 1 = one or more failures.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Paths produced by Gate 69F pipeline
APPROVAL_FILE  = ROOT / "data" / "ai" / "package_candidates" / "ai_final_publish_approval_v1.json"
PUBLISHED_DIR  = ROOT / "data" / "ai" / "published" / "ai_resource_package_v1"
PUBLISH_PKG    = PUBLISHED_DIR / "publish_package_v1.json"
STUDENT_PAY    = PUBLISHED_DIR / "student_resource_payload_v1.json"
TEACHER_PAY    = PUBLISHED_DIR / "teacher_resource_payload_v1.json"
MANIFEST       = PUBLISHED_DIR / "ai_publish_manifest_v1.md"
PUBLISH_RPT    = PUBLISHED_DIR / "ai_publish_report_v1.json"
PREVIEW_DIR    = PUBLISHED_DIR / "static_preview"
STUDENT_HTML   = PREVIEW_DIR  / "student_ai_published_package_preview_v1.html"
TEACHER_HTML   = PREVIEW_DIR  / "teacher_ai_published_package_preview_v1.html"
REGISTRY_FILE  = ROOT / "data" / "ai" / "registry" / "ai_content_registry_v1.json"
VALIDATION_RPT = ROOT / "data" / "diagnostics" / "ai_local_published_package_validation_report_v1.json"

# Gate 69E package candidate (prerequisite)
PKG_CANDIDATE  = ROOT / "data" / "ai" / "package_candidates" / "ai_resource_package_candidate_v1.json"

PYTHON = sys.executable

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASSED = 0
FAILED = 0
RESULTS: list[dict] = []


def run(label: str, ok: bool, detail: str = "") -> bool:
    global PASSED, FAILED
    status = "PASS" if ok else "FAIL"
    if ok:
        PASSED += 1
    else:
        FAILED += 1
    mark = "  [OK]" if ok else "  [FAIL]"
    msg = f"{mark}  {label}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)
    RESULTS.append({"test": label, "status": status, "detail": detail})
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


SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"sk-ant-[A-Za-z0-9\-]{20,}",
    r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    r"NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY",
    r"supabase_service_role",
]

COPYRIGHT_PATTERNS = [
    "UCLES", "© Cambridge", "Cambridge International",
    "Cambridge Assessment", "Question Answer Marks",
    "original_raw_block",
]


def _no_secrets(text: str) -> tuple[bool, str]:
    for pat in SECRET_PATTERNS:
        if re.search(pat, text):
            return False, f"found secret pattern: {pat}"
    return True, ""


def _no_copyright(text: str) -> tuple[bool, str]:
    for pat in COPYRIGHT_PATTERNS:
        if pat in text:
            return False, f"found copyright pattern: {pat}"
    return True, ""


# ---------------------------------------------------------------------------
# Pipeline: reset approval to pending so tests are reproducible
# ---------------------------------------------------------------------------

def reset_approval_to_pending():
    if APPROVAL_FILE.exists():
        data = read_json(APPROVAL_FILE)
        if data:
            data["approval_status"]  = "pending"
            data["approved_by"]      = None
            data["approval_notes"]   = None
            data["approved_at"]      = None
            data["allow_local_publish"] = False
            data["allow_active_switch"] = False
            data["allow_supabase_sync"] = False
            APPROVAL_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

print("Gate 69F -- Test Suite v1")
print("=" * 60)

# T01 — Gate 69E package candidate exists
run("T01: Gate 69E package candidate exists",
    PKG_CANDIDATE.exists(),
    str(PKG_CANDIDATE) if not PKG_CANDIDATE.exists() else "")

# T02 — Gate 69E candidate has resources
if PKG_CANDIDATE.exists():
    cand = read_json(PKG_CANDIDATE)
    resources = cand.get("resources", []) if cand else []
    run("T02: Gate 69E candidate has >=1 resource", len(resources) >= 1,
        f"resource_count={len(resources)}")
else:
    run("T02: Gate 69E candidate has ≥1 resource", False, "prerequisite T01 failed")

# T03 — Final approval seed file exists
run("T03: Final approval seed file exists",
    APPROVAL_FILE.exists(),
    str(APPROVAL_FILE) if not APPROVAL_FILE.exists() else "")

# T04 — Approval file has correct structure
if APPROVAL_FILE.exists():
    approval = read_json(APPROVAL_FILE)
    required = ["approval_file_id", "approval_status", "allow_local_publish",
                "allow_active_switch", "allow_supabase_sync"]
    missing = [k for k in required if k not in (approval or {})]
    run("T04: Approval file has required fields", not missing,
        f"missing: {missing}" if missing else "")
else:
    run("T04: Approval file has required fields", False, "file missing")

# T05 — Reset approval, run approve script
reset_approval_to_pending()
rc, stdout, stderr = run_script(
    ROOT / "tools" / "ai" / "approve_ai_package_candidate_v1.py",
    ["--approve", "--approved-by", "gate69f_test_suite", "--notes", "automated test approval"])
run("T05: approve_ai_package_candidate_v1.py exits 0", rc == 0,
    stderr.strip()[:300] if rc != 0 else "")

# T06 — Approval status is now "approved"
approval = read_json(APPROVAL_FILE)
run("T06: approval_status='approved'",
    (approval or {}).get("approval_status") == "approved",
    f"got: {(approval or {}).get('approval_status')}")

# T07 — allow_local_publish=True, allow_active_switch=False, allow_supabase_sync=False
ok = (
    (approval or {}).get("allow_local_publish") is True and
    (approval or {}).get("allow_active_switch") is False and
    (approval or {}).get("allow_supabase_sync") is False
)
run("T07: allow_local_publish=True, allow_active_switch=False, allow_supabase_sync=False",
    ok, str({k: approval.get(k) for k in ["allow_local_publish", "allow_active_switch", "allow_supabase_sync"]} if approval else ""))

# T08 — Build local published package
rc, stdout, stderr = run_script(ROOT / "tools" / "ai" / "build_ai_local_published_package_v1.py")
run("T08: build_ai_local_published_package_v1.py exits 0", rc == 0,
    stderr.strip()[:300] if rc != 0 else "")

# T09 — publish_package_v1.json exists and has correct status
pkg = read_json(PUBLISH_PKG)
run("T09: publish_package_v1.json exists", PUBLISH_PKG.exists(), "")
run("T10: status='published_local_not_active'",
    (pkg or {}).get("status") == "published_local_not_active",
    f"got: {(pkg or {}).get('status')}")

# T11 — active_content=False, supabase_write_performed=False, teacher_final_approval=True
ok = (
    (pkg or {}).get("active_content")           is False and
    (pkg or {}).get("supabase_write_performed")  is False and
    (pkg or {}).get("teacher_final_approval")    is True
)
run("T11: active_content=False, supabase_write_performed=False, teacher_final_approval=True",
    ok, str({k: (pkg or {}).get(k) for k in ["active_content", "supabase_write_performed", "teacher_final_approval"]}))

# T12 — Student/teacher payloads exist
run("T12: student_resource_payload_v1.json exists", STUDENT_PAY.exists(), "")
run("T13: teacher_resource_payload_v1.json exists", TEACHER_PAY.exists(), "")

# T14 — Student payload excludes answer_key
student = read_json(STUDENT_PAY)
student_resources = (student or {}).get("resources", [])
student_has_answer = any("answer_key" in r for r in student_resources)
run("T14: Student payload excludes answer_key", not student_has_answer,
    "answer_key found in student payload" if student_has_answer else "")

# T15 — Teacher payload includes answer_key
teacher = read_json(TEACHER_PAY)
teacher_resources = (teacher or {}).get("resources", [])
teacher_has_answer = any("answer_key" in r for r in teacher_resources)
run("T15: Teacher payload includes answer_key", teacher_has_answer,
    "answer_key missing from teacher payload" if not teacher_has_answer else "")

# T16 — Validate local published package
rc, stdout, stderr = run_script(
    ROOT / "tools" / "ai" / "validate_ai_local_published_package_v1.py",
    [str(PUBLISH_PKG)])
run("T16: validate_ai_local_published_package_v1.py exits 0", rc == 0,
    stderr.strip()[:300] if rc != 0 else "")

val = read_json(VALIDATION_RPT)
run("T17: Validation report valid=True", (val or {}).get("valid") is True,
    f"valid={( val or {}).get('valid')}")

# T18 — Render previews
rc, stdout, stderr = run_script(ROOT / "tools" / "ai" / "render_ai_local_published_package_preview_v1.py")
run("T18: render_ai_local_published_package_preview_v1.py exits 0", rc == 0,
    stderr.strip()[:300] if rc != 0 else "")

run("T19: Student HTML preview exists",  STUDENT_HTML.exists(), "")
run("T20: Teacher HTML preview exists",  TEACHER_HTML.exists(), "")

# T21 — HTML previews contain status watermark
if STUDENT_HTML.exists():
    html = STUDENT_HTML.read_text(encoding="utf-8")
    run("T21: Student HTML contains 'published_local_not_active'",
        "published_local_not_active" in html, "")
else:
    run("T21: Student HTML contains 'published_local_not_active'", False, "file missing")

# T22 — Build AI local registry
rc, stdout, stderr = run_script(ROOT / "tools" / "ai" / "build_ai_local_registry_v1.py")
run("T22: build_ai_local_registry_v1.py exits 0", rc == 0,
    stderr.strip()[:300] if rc != 0 else "")

reg = read_json(REGISTRY_FILE)
run("T23: ai_content_registry_v1.json exists and has >=1 package",
    reg is not None and len((reg or {}).get("packages", [])) >= 1,
    f"packages={len((reg or {}).get('packages', []))} found" if reg else "file missing")

# T24 — Registry does not reference active_content_index_v1.json
if REGISTRY_FILE.exists():
    reg_text = REGISTRY_FILE.read_text(encoding="utf-8")
    run("T24: Registry does not reference active_content_index",
        "active_content_index" not in reg_text, "")
else:
    run("T24: Registry does not reference active_content_index", False, "file missing")

# T25 — No secrets in any output files
checked_files = [PUBLISH_PKG, STUDENT_PAY, TEACHER_PAY, REGISTRY_FILE, MANIFEST]
any_secret = False
secret_detail = ""
for f in checked_files:
    if f and f.exists():
        text = f.read_text(encoding="utf-8")
        ok_s, det = _no_secrets(text)
        if not ok_s:
            any_secret = True
            secret_detail = f"{f.name}: {det}"
            break
run("T25: No API secrets in published output files", not any_secret, secret_detail)

# T26 — No Cambridge copyright in published files
any_copy = False
copy_detail = ""
for f in [PUBLISH_PKG, STUDENT_PAY, TEACHER_PAY]:
    if f and f.exists():
        text = f.read_text(encoding="utf-8")
        ok_c, det = _no_copyright(text)
        if not ok_c:
            any_copy = True
            copy_detail = f"{f.name}: {det}"
            break
run("T26: No Cambridge copyright in published files", not any_copy, copy_detail)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print()
print("=" * 60)
total = PASSED + FAILED
print(f"Results: {PASSED}/{total} passed, {FAILED} failed")
print(f"Status:  {'ALL PASSED' if FAILED == 0 else 'FAILURES DETECTED'}")

# Write JSON report
report = {
    "gate":         "69F",
    "test_suite":   "test_gate69f_ai_local_publish_v1",
    "total":        total,
    "passed":       PASSED,
    "failed":       FAILED,
    "status":       "passed" if FAILED == 0 else "failed",
    "results":      RESULTS,
}
diag_dir = ROOT / "data" / "diagnostics"
diag_dir.mkdir(parents=True, exist_ok=True)
report_path = diag_dir / "test_gate69f_results_v1.json"
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report:  {report_path}")

sys.exit(0 if FAILED == 0 else 1)
