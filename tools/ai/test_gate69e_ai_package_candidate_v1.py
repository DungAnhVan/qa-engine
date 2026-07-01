"""
Gate 69E -- Test AI Package Candidate Flow v1

End-to-end test:
1. Ensures Gate 69D approved candidate file exists.
2. Builds package candidate.
3. Validates package candidate.
4. Exports student/teacher payloads.
5. Renders HTML previews.
6. Verifies all policy and content checks.

No Supabase writes. No AI API calls.

Output:
  data/diagnostics/gate69e_ai_package_candidate_test_report_v1.json
"""

import json
import re
import sys
import datetime
from pathlib import Path

ROOT             = Path(__file__).resolve().parents[2]
APPROVED_FILE    = ROOT / "data" / "ai" / "approved" / "ai_approved_resource_candidates_v1.json"
PKG_FILE         = ROOT / "data" / "ai" / "package_candidates" / "ai_resource_package_candidate_v1.json"
STUDENT_FILE     = ROOT / "data" / "ai" / "package_candidates" / "student_ai_package_payload_v1.json"
TEACHER_FILE     = ROOT / "data" / "ai" / "package_candidates" / "teacher_ai_package_payload_v1.json"
PREVIEW_DIR      = ROOT / "data" / "ai" / "package_candidates" / "static_preview"
STUDENT_HTML     = PREVIEW_DIR / "student_ai_package_preview_v1.html"
TEACHER_HTML     = PREVIEW_DIR / "teacher_ai_package_preview_v1.html"
OUTPUT_FILE      = ROOT / "data" / "diagnostics" / "gate69e_ai_package_candidate_test_report_v1.json"

sys.path.insert(0, str(ROOT))
from tools.ai.build_ai_approved_package_candidate_v1 import build_package_candidate
from tools.ai.validate_ai_package_candidate_v1 import validate_package_candidate
from tools.ai.export_ai_package_candidate_payloads_v1 import export_payloads
from tools.ai.render_ai_package_candidate_preview_v1 import main as render_main

BANNED_CONTENT = [
    ("UCLES",           re.compile(r'\bUCLES\b')),
    ("cambridge_copy",  re.compile(r'©\s*Cambridge', re.IGNORECASE)),
    ("cambridge_intl",  re.compile(r'Cambridge\s+(International|Assessment)', re.IGNORECASE)),
    ("mark_scheme_hdr", re.compile(r'Question\s+Answer\s+Marks', re.IGNORECASE)),
    ("raw_block",       re.compile(r'\boriginal_raw_block\b')),
    ("raw_data_path",   re.compile(r'data[/\\]raw[/\\]')),
]

API_KEY_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9]{20,}'),
    re.compile(r'sk-ant-[A-Za-z0-9\-_]{30,}'),
    re.compile(r'eyJ[A-Za-z0-9+/=_-]{100,}'),
]


def scan_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    found = []
    for label, pat in BANNED_CONTENT:
        if pat.search(content):
            found.append(f"Banned pattern ({label}) in {path.name}")
    for pat in API_KEY_PATTERNS:
        if pat.search(content):
            found.append(f"API key pattern in {path.name}")
    return found


def run_test(name: str, passed: bool, detail: str = "") -> dict:
    sym = "+" if passed else "!"
    msg = f"  [{sym}] {name}"
    if detail:
        msg += f": {detail}"
    print(msg)
    return {"name": name, "passed": passed, "detail": detail}


def main():
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)
    now     = datetime.datetime.now(datetime.timezone.utc).isoformat()
    results: list[dict] = []

    print("Gate 69E -- AI Package Candidate Test")
    print("-" * 55)

    # ── T01: Gate 69D approved file exists ───────────────────────────────────
    if not APPROVED_FILE.exists():
        print(f"  ! Gate 69D approved file not found: {APPROVED_FILE}")
        print("  ! Run: .venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate69d_ai_teacher_review_v1.py")
        _fail(results, now, "Gate 69D approved candidate file missing")

    results.append(run_test("T01_approved_candidates_exist", True, str(APPROVED_FILE.name)))

    # ── T02: Build package candidate ──────────────────────────────────────────
    (ROOT / "data" / "ai" / "package_candidates").mkdir(parents=True, exist_ok=True)
    build_result = build_package_candidate()
    t02 = build_result["ok"]
    if t02:
        PKG_FILE.write_text(json.dumps(build_result["package"], indent=2), encoding="utf-8")
    results.append(run_test("T02_package_candidate_built", t02,
        f"{build_result['package']['resource_count']} resources" if t02
        else str(build_result.get("error"))))
    if not t02:
        _fail(results, now, "Package build failed")

    pkg = build_result["package"]

    # ── T03: resource_count >= 1 ──────────────────────────────────────────────
    rc = pkg.get("resource_count", 0)
    results.append(run_test("T03_resource_count_ge_1", rc >= 1, str(rc)))

    # ── T04: status = draft_package_candidate ─────────────────────────────────
    results.append(run_test("T04_status_draft",
        pkg.get("status") == "draft_package_candidate", str(pkg.get("status"))))

    # ── T05: auto_publish_enabled false ──────────────────────────────────────
    results.append(run_test("T05_auto_publish_disabled",
        pkg.get("auto_publish_enabled") is False, str(pkg.get("auto_publish_enabled"))))

    # ── T06: teacher_final_publish_required true ──────────────────────────────
    results.append(run_test("T06_teacher_final_required",
        pkg.get("teacher_final_publish_required") is True,
        str(pkg.get("teacher_final_publish_required"))))

    # ── T07: supabase_write_performed false ───────────────────────────────────
    results.append(run_test("T07_no_supabase_write",
        pkg.get("supabase_write_performed") is False,
        str(pkg.get("supabase_write_performed"))))

    # ── T08: Validate package candidate ──────────────────────────────────────
    val_result = validate_package_candidate(PKG_FILE)
    t08 = val_result.get("valid", False)
    results.append(run_test("T08_validation_passed", t08,
        f"{val_result.get('resources_valid')}/{val_result.get('resource_count')} valid"))

    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "diagnostics" / "ai_package_candidate_validation_report_v1.json").write_text(
        json.dumps(val_result, indent=2), encoding="utf-8")

    # ── T09: Each resource has provenance.approved_by_teacher_review=True ────
    prov_ok = all(
        r.get("provenance", {}).get("approved_by_teacher_review") is True
        for r in pkg.get("resources", [])
    )
    results.append(run_test("T09_all_approved_by_teacher", prov_ok))

    # ── T10: Export payloads ──────────────────────────────────────────────────
    export_result = export_payloads()
    t10 = export_result.get("ok", False)
    results.append(run_test("T10_payloads_exported", t10,
        f"student={export_result.get('student_resource_count')}, teacher={export_result.get('teacher_resource_count')}"
        if t10 else str(export_result.get("error"))))

    # ── T11: Student payload exists ───────────────────────────────────────────
    results.append(run_test("T11_student_payload_exists", STUDENT_FILE.exists()))

    # ── T12: Teacher payload exists ───────────────────────────────────────────
    results.append(run_test("T12_teacher_payload_exists", TEACHER_FILE.exists()))

    # ── T13: Student payload excludes answer_key ──────────────────────────────
    student_ok = True
    if STUDENT_FILE.exists():
        sdata = json.loads(STUDENT_FILE.read_text(encoding="utf-8"))
        for r in sdata.get("resources", []):
            if "answer_key" in r or "teacher_notes" in r:
                student_ok = False
                break
    results.append(run_test("T13_student_payload_no_answers", student_ok))

    # ── T14: Teacher payload includes answer_key ──────────────────────────────
    teacher_ok = True
    if TEACHER_FILE.exists():
        tdata = json.loads(TEACHER_FILE.read_text(encoding="utf-8"))
        teacher_ok = all(
            "answer_key" in r and "marking_rubric" in r
            for r in tdata.get("resources", [])
        )
    results.append(run_test("T14_teacher_payload_has_answers", teacher_ok))

    # ── T15: Render HTML previews ─────────────────────────────────────────────
    try:
        render_main()
        t15 = True
        render_detail = "OK"
    except Exception as exc:
        t15 = False
        render_detail = str(exc)
    results.append(run_test("T15_previews_rendered", t15, render_detail))

    # ── T16: Student HTML preview exists ─────────────────────────────────────
    results.append(run_test("T16_student_preview_exists", STUDENT_HTML.exists()))

    # ── T17: Teacher HTML preview exists ─────────────────────────────────────
    results.append(run_test("T17_teacher_preview_exists", TEACHER_HTML.exists()))

    # ── T18: No raw Cambridge text in output files ────────────────────────────
    content_issues: list[str] = []
    for f in [PKG_FILE, STUDENT_FILE, TEACHER_FILE, STUDENT_HTML, TEACHER_HTML]:
        content_issues.extend(scan_file(f))
    results.append(run_test("T18_no_raw_cambridge_text",
        len(content_issues) == 0,
        f"{len(content_issues)} issues" if content_issues else "clean"))

    # ── T19: No API keys in output files ─────────────────────────────────────
    results.append(run_test("T19_no_api_keys",
        len(content_issues) == 0, "all output files clean"))

    # ── Summary ───────────────────────────────────────────────────────────────
    passed_n = sum(1 for r in results if r["passed"])
    total_n  = len(results)
    status   = "passed" if passed_n == total_n else "failed"

    print(f"\n{passed_n}/{total_n} tests passed")
    print(f"\nStatus: {status}")

    report = {
        "status":                       status,
        "tests_passed":                 passed_n,
        "tests_total":                  total_n,
        "tests":                        results,
        "resource_count":               rc,
        "validation_passed":            t08,
        "student_payload_exists":       STUDENT_FILE.exists(),
        "teacher_payload_exists":       TEACHER_FILE.exists(),
        "student_preview_exists":       STUDENT_HTML.exists(),
        "teacher_preview_exists":       TEACHER_HTML.exists(),
        "auto_publish_enabled":         False,
        "supabase_write_performed":     False,
        "teacher_final_publish_required": True,
        "raw_cambridge_text_issues":    content_issues,
        "generated_at":                 now,
    }
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {OUTPUT_FILE}")


def _fail(results: list, now: str, msg: str) -> None:
    report = {
        "status":       "failed",
        "error":        msg,
        "tests_passed": sum(1 for r in results if r["passed"]),
        "tests_total":  len(results),
        "tests":        results,
        "generated_at": now,
    }
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nStatus: failed")
    print(f"Report: {OUTPUT_FILE}")
    sys.exit(1)


if __name__ == "__main__":
    main()
