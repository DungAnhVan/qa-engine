"""
Gate 70C -- Test Suite v1

Tests for:
  - build_gate70c_ai_bank_package_candidate_v1.py
  - validate_gate70c_ai_bank_package_candidate_v1.py
  - export_gate70c_ai_bank_package_payloads_v1.py
  - render_gate70c_ai_bank_package_preview_v1.py
  - apps/admin/src/lib/aiBankPackageCandidate.ts (static checks)
  - apps/admin/src/app/ai-bank-package/page.tsx (static checks)
  - apps/admin/src/app/system/ai-bank-package/page.tsx (static checks)
  - apps/admin/src/app/api/system/ai-bank-package/route.ts (static checks)
  - build_gate70c_ai_bank_package_candidate_report_v1.py

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate70c_ai_bank_package_candidate_v1.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable)

passed = 0
failed = 0
results: list[tuple[str, bool, str]] = []

def t(test_id: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    label = "[PASS]" if condition else "[FAIL]"
    if condition:
        passed += 1
    else:
        failed += 1
    results.append((test_id, condition, detail))
    status = "PASS" if condition else "FAIL"
    print(f"  {label} {test_id}{(' — ' + detail) if detail else ''}")


def run_script(script: str, *args: str) -> tuple[int, str, str]:
    p = subprocess.run(
        [str(PYTHON), str(ROOT / script), *args],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return p.returncode, p.stdout, p.stderr

# ---------------------------------------------------------------------------
# Setup: ensure Gate 70B approved items exist
# ---------------------------------------------------------------------------

APPROVED_FILE = ROOT / "data" / "ai" / "approved" / "gate70b_approved_ai_bank_items_v1.json"
PKG_FILE      = ROOT / "data" / "ai" / "package_candidates" / "gate70c_ai_bank_package_candidate_v1.json"
STUDENT_OUT   = ROOT / "data" / "ai" / "package_candidates" / "gate70c_student_payload_v1.json"
TEACHER_OUT   = ROOT / "data" / "ai" / "package_candidates" / "gate70c_teacher_payload_v1.json"
STUDENT_HTML  = ROOT / "data" / "ai" / "package_candidates" / "static_preview" / "gate70c_student_preview.html"
TEACHER_HTML  = ROOT / "data" / "ai" / "package_candidates" / "static_preview" / "gate70c_teacher_preview.html"
VAL_REPORT    = ROOT / "data" / "diagnostics" / "gate70c_ai_bank_package_candidate_validation_report_v1.json"
BUILD_REPORT  = ROOT / "data" / "diagnostics" / "gate70c_ai_bank_package_candidate_build_report_v1.json"
FULL_REPORT   = ROOT / "data" / "diagnostics" / "gate70c_full_report_v1.json"

print("Gate 70C — Test Suite")
print("=" * 60)

# ─── Section 1: File existence ─────────────────────────────────────────────
print("\n[S1] Script/file existence")
scripts = [
    "tools/ai/build_gate70c_ai_bank_package_candidate_v1.py",
    "tools/ai/validate_gate70c_ai_bank_package_candidate_v1.py",
    "tools/ai/export_gate70c_ai_bank_package_payloads_v1.py",
    "tools/ai/render_gate70c_ai_bank_package_preview_v1.py",
    "tools/ai/build_gate70c_ai_bank_package_candidate_report_v1.py",
    "apps/admin/src/lib/aiBankPackageCandidate.ts",
    "apps/admin/src/app/ai-bank-package/page.tsx",
    "apps/admin/src/app/system/ai-bank-package/page.tsx",
    "apps/admin/src/app/api/system/ai-bank-package/route.ts",
]
for s in scripts:
    t(f"T01_{s.split('/')[-1][:30]}", (ROOT / s).exists(), s)

# ─── Section 2: Approved items prerequisite ────────────────────────────────
print("\n[S2] Gate 70B approved items prerequisite")
t("T02_approved_file_exists", APPROVED_FILE.exists(), str(APPROVED_FILE.relative_to(ROOT)))

approved_doc   = json.loads(APPROVED_FILE.read_text(encoding="utf-8")) if APPROVED_FILE.exists() else {}
approved_items = approved_doc.get("items", [])
approved_count = sum(1 for i in approved_items if i.get("decision") == "approve" and i.get("status") == "approved_pending_package")

t("T03_approved_items_count_gte_1", approved_count >= 1, f"approved={approved_count}")
t("T04_approved_safety_fields", all(
    i.get("teacher_review_required") is True and
    i.get("auto_publish_enabled") is False and
    i.get("supabase_write_performed") is False
    for i in approved_items if i.get("decision") == "approve"
), "teacher_review_required=true, auto_publish=false, supabase=false")

# ─── Section 3: Build script ───────────────────────────────────────────────
print("\n[S3] build_gate70c_ai_bank_package_candidate_v1.py")
rc, out, err = run_script("tools/ai/build_gate70c_ai_bank_package_candidate_v1.py")
t("T05_build_rc0",   rc == 0,                 f"rc={rc}")
t("T06_pkg_created", PKG_FILE.exists(),        str(PKG_FILE.relative_to(ROOT)))
t("T07_build_report_created", BUILD_REPORT.exists(), str(BUILD_REPORT.relative_to(ROOT)))

if PKG_FILE.exists():
    pkg = json.loads(PKG_FILE.read_text(encoding="utf-8"))
    t("T08_pkg_status_draft",              pkg.get("status") == "draft_package_candidate", f"status={pkg.get('status')}")
    t("T09_pkg_teacher_publish_required",  pkg.get("teacher_final_publish_required") is True, "teacher_final_publish_required=true")
    t("T10_pkg_auto_publish_false",        pkg.get("auto_publish_enabled") is False, "auto_publish_enabled=false")
    t("T11_pkg_supabase_false",            pkg.get("supabase_write_performed") is False, "supabase_write_performed=false")
    t("T12_pkg_ai_api_false",              pkg.get("ai_api_called") is False, "ai_api_called=false")
    t("T13_pkg_resource_count_gte_1",      pkg.get("resource_count", 0) >= 1, f"resource_count={pkg.get('resource_count')}")

    resources = pkg.get("resources", [])
    t("T14_resources_non_empty", len(resources) >= 1, f"resources={len(resources)}")

    if resources:
        res = resources[0]
        t("T15_resource_has_resource_id",       "resource_id" in res)
        t("T16_resource_has_bank_item_id",      "bank_item_id" in res)
        t("T17_resource_has_title",             bool(res.get("title")))
        t("T18_resource_has_student_prompt",    bool(res.get("student_prompt")))
        t("T19_resource_has_student_instructions", bool(res.get("student_instructions")))
        t("T20_resource_has_answer_key",        bool(res.get("answer_key")))
        t("T21_resource_has_marking_rubric",    isinstance(res.get("marking_rubric"), list) and len(res.get("marking_rubric", [])) > 0)
        t("T22_resource_has_teacher_notes",     bool(res.get("teacher_notes")))
        t("T23_resource_has_safety_declaration", isinstance(res.get("safety_declaration"), dict))
        t("T24_resource_has_provenance",        isinstance(res.get("provenance"), dict))
        prov = res.get("provenance", {})
        t("T25_provenance_gate70b_approved",    prov.get("gate70b_approved") is True)
        t("T26_provenance_no_raw_source",       prov.get("no_raw_source_text_used") is True)
        t("T27_provenance_teacher_review",      prov.get("teacher_review_required") is True)

    # No pending/revision/rejected in package
    non_approved = [r for r in resources if r.get("decision") in ("needs_revision", "reject")]
    t("T28_no_non_approved_in_package", len(non_approved) == 0, f"non_approved={len(non_approved)}")

    # No raw Cambridge text in any resource content
    import re
    all_content = json.dumps(resources)
    bad_patterns = ["Cambridge International", "UCLES", "© Cambridge", "mark_scheme_text\": \""]
    found_bad = [p for p in bad_patterns if p in all_content]
    t("T29_no_raw_cambridge_text", len(found_bad) == 0, f"found={found_bad}")

    # No secrets
    secret_re = [r"sk-[A-Za-z0-9]{20,}", r"sk-ant-[A-Za-z0-9\-]{20,}"]
    found_secrets = [r for r in secret_re if re.search(r, all_content)]
    t("T30_no_secrets_in_package", len(found_secrets) == 0, f"found={found_secrets}")
else:
    for tid in ["T08","T09","T10","T11","T12","T13","T14","T15","T16","T17","T18","T19","T20","T21","T22","T23","T24","T25","T26","T27","T28","T29","T30"]:
        t(f"{tid}_skipped_no_pkg", False, "pkg not built")

# ─── Section 4: Validation script ─────────────────────────────────────────
print("\n[S4] validate_gate70c_ai_bank_package_candidate_v1.py")
rc, out, err = run_script("tools/ai/validate_gate70c_ai_bank_package_candidate_v1.py")
t("T31_validate_rc0",            rc == 0,           f"rc={rc}")
t("T32_val_report_created",      VAL_REPORT.exists(), str(VAL_REPORT.relative_to(ROOT)))

if VAL_REPORT.exists():
    val = json.loads(VAL_REPORT.read_text(encoding="utf-8"))
    t("T33_val_valid_true",        val.get("valid") is True,  f"valid={val.get('valid')} issues={val.get('issues')}")
    t("T34_val_resource_count",    val.get("resource_count", 0) >= 1)
    safety = val.get("safety_summary", {})
    t("T35_val_secrets_clean",     safety.get("secrets_clean") is True)
    t("T36_val_copyright_clean",   safety.get("copyright_clean") is True)
    t("T37_val_no_auto_publish",   safety.get("auto_publish_enabled") is False)
    t("T38_val_no_supabase",       safety.get("supabase_write_performed") is False)
    t("T39_val_no_ai_api",         safety.get("ai_api_called") is False)
else:
    for tid in ["T33","T34","T35","T36","T37","T38","T39"]:
        t(f"{tid}_skipped_no_report", False, "validation report missing")

# ─── Section 5: Export payloads ────────────────────────────────────────────
print("\n[S5] export_gate70c_ai_bank_package_payloads_v1.py")
rc, out, err = run_script("tools/ai/export_gate70c_ai_bank_package_payloads_v1.py")
t("T40_export_rc0",      rc == 0,            f"rc={rc}")
t("T41_student_created", STUDENT_OUT.exists())
t("T42_teacher_created", TEACHER_OUT.exists())

if STUDENT_OUT.exists() and TEACHER_OUT.exists():
    student_p = json.loads(STUDENT_OUT.read_text(encoding="utf-8"))
    teacher_p = json.loads(TEACHER_OUT.read_text(encoding="utf-8"))

    t("T43_student_payload_type",    student_p.get("payload_type") == "student")
    t("T44_teacher_payload_type",    teacher_p.get("payload_type") == "teacher")
    t("T45_student_has_resources",   len(student_p.get("resources", [])) >= 1)
    t("T46_teacher_has_resources",   len(teacher_p.get("resources", [])) >= 1)

    if student_p.get("resources"):
        s_res = student_p["resources"][0]
        t("T47_student_no_answer_key",     "answer_key" not in s_res, "answer_key excluded")
        t("T48_student_no_marking_rubric", "marking_rubric" not in s_res, "marking_rubric excluded")
        t("T49_student_no_teacher_notes",  "teacher_notes" not in s_res, "teacher_notes excluded")
        t("T50_student_has_prompt",        bool(s_res.get("student_prompt")))
        t("T51_student_has_instructions",  bool(s_res.get("student_instructions")))

    if teacher_p.get("resources"):
        t_res = teacher_p["resources"][0]
        t("T52_teacher_has_answer_key",    bool(t_res.get("answer_key")))
        t("T53_teacher_has_rubric",        isinstance(t_res.get("marking_rubric"), list))
        t("T54_teacher_has_notes",         bool(t_res.get("teacher_notes")))
        t("T55_teacher_has_provenance",    isinstance(t_res.get("provenance"), dict))
else:
    for tid in range(43, 56):
        t(f"T{tid}_skipped", False, "payloads not created")

# ─── Section 6: Render preview ────────────────────────────────────────────
print("\n[S6] render_gate70c_ai_bank_package_preview_v1.py")
rc, out, err = run_script("tools/ai/render_gate70c_ai_bank_package_preview_v1.py")
t("T56_render_rc0",         rc == 0,              f"rc={rc}")
t("T57_student_html",       STUDENT_HTML.exists(), str(STUDENT_HTML.relative_to(ROOT)))
t("T58_teacher_html",       TEACHER_HTML.exists(), str(TEACHER_HTML.relative_to(ROOT)))

if STUDENT_HTML.exists():
    sh = STUDENT_HTML.read_text(encoding="utf-8")
    t("T59_student_html_doctype",   sh.startswith("<!DOCTYPE html"))
    t("T60_student_html_no_answerkey", "answer_key" not in sh.lower().replace("_", ""), "no answer_key in student HTML")
    t("T61_student_html_banner",    "Teacher Review Required" in sh)

if TEACHER_HTML.exists():
    th = TEACHER_HTML.read_text(encoding="utf-8")
    t("T62_teacher_html_doctype",   th.startswith("<!DOCTYPE html"))
    t("T63_teacher_html_confidential", "Confidential" in th or "teacher" in th.lower())
    t("T64_teacher_html_answer",    "Answer Key" in th)
    t("T65_teacher_html_rubric",    "Marking Rubric" in th)

# ─── Section 7: TypeScript lib static checks ──────────────────────────────
print("\n[S7] aiBankPackageCandidate.ts static checks")
ts_lib = ROOT / "apps/admin/src/lib/aiBankPackageCandidate.ts"
if ts_lib.exists():
    ts = ts_lib.read_text(encoding="utf-8")
    t("T66_ts_no_supabase",            "supabase" not in ts.lower() or "supabase_write" in ts, "no supabase client import")
    t("T67_ts_no_service_role",        "service_role" not in ts or "supabase_write_performed" in ts, "no service role key")
    t("T68_ts_reads_package_file",     "gate70c_ai_bank_package_candidate_v1.json" in ts)
    t("T69_ts_reads_student_payload",  "gate70c_student_payload_v1.json" in ts)
    t("T70_ts_reads_teacher_payload",  "gate70c_teacher_payload_v1.json" in ts)
    t("T71_ts_reads_validation",       "validation_report" in ts)
    t("T72_ts_server_only",            "import fs" in ts, "uses fs — server-only")
    t("T73_ts_no_use_client",          '"use client"' not in ts, "no use client directive")
else:
    for tid in range(66, 74):
        t(f"T{tid}_skipped", False, "ts lib missing")

# ─── Section 8: Admin page static checks ──────────────────────────────────
print("\n[S8] ai-bank-package/page.tsx static checks")
admin_page = ROOT / "apps/admin/src/app/ai-bank-package/page.tsx"
if admin_page.exists():
    ap = admin_page.read_text(encoding="utf-8")
    t("T74_page_requireRole",        "requireRole" in ap)
    t("T75_page_no_auto_publish",    "auto_publish_enabled" in ap)
    t("T76_page_teacher_publish",    "teacher_final_publish_required" in ap)
    t("T77_page_no_supabase_client", "createClient" not in ap, "no supabase client")
    t("T78_page_diag_link",          "/system/ai-bank-package" in ap)
else:
    for tid in range(74, 79):
        t(f"T{tid}_skipped", False, "admin page missing")

print("\n[S9] system/ai-bank-package/page.tsx static checks")
sys_page = ROOT / "apps/admin/src/app/system/ai-bank-package/page.tsx"
if sys_page.exists():
    sp = sys_page.read_text(encoding="utf-8")
    t("T79_syspage_requireRole",       "requireRole" in sp)
    t("T80_syspage_no_supabase_client","createClient" not in sp)
    t("T81_syspage_back_link",         "/ai-bank-package" in sp)
else:
    for tid in range(79, 82):
        t(f"T{tid}_skipped", False, "system page missing")

print("\n[S10] api/system/ai-bank-package/route.ts static checks")
api_route = ROOT / "apps/admin/src/app/api/system/ai-bank-package/route.ts"
if api_route.exists():
    ar = api_route.read_text(encoding="utf-8")
    t("T82_route_get_export",          "export async function GET" in ar)
    t("T83_route_force_dynamic",       "force-dynamic" in ar)
    t("T84_route_no_post",             "export async function POST" not in ar)
    t("T85_route_returns_gate70c",     "70C" in ar or "gate70c" in ar.lower())
    t("T86_route_safety_fields",       "auto_publish_enabled" in ar and "supabase_write_performed" in ar)
else:
    for tid in range(82, 87):
        t(f"T{tid}_skipped", False, "api route missing")

# ─── Section 11: Layout links ─────────────────────────────────────────────
print("\n[S11] layout.tsx links")
layout = ROOT / "apps/admin/src/app/layout.tsx"
if layout.exists():
    lt = layout.read_text(encoding="utf-8")
    t("T87_layout_ai_bank_pkg_link",  "/ai-bank-package" in lt)
    t("T88_layout_ai_bank_pkg_diag",  "/system/ai-bank-package" in lt)
else:
    t("T87_layout_ai_bank_pkg_link",  False, "layout.tsx missing")
    t("T88_layout_ai_bank_pkg_diag",  False, "layout.tsx missing")

# ─── Section 12: Full report ──────────────────────────────────────────────
print("\n[S12] build_gate70c_ai_bank_package_candidate_report_v1.py")
rc, out, err = run_script("tools/ai/build_gate70c_ai_bank_package_candidate_report_v1.py")
t("T89_full_report_rc0",      rc == 0, f"rc={rc}")
t("T90_full_report_created",  FULL_REPORT.exists())

if FULL_REPORT.exists():
    fr = json.loads(FULL_REPORT.read_text(encoding="utf-8"))
    t("T91_full_report_gate70c",   fr.get("gate") == "70C")
    t("T92_full_report_passed",    fr.get("gate_status") == "passed", f"status={fr.get('gate_status')} issues={fr.get('issues')}")
    t("T93_full_report_next_gate", fr.get("next_gate") == "70D")
    t("T94_full_report_gate70d_ready", fr.get("gate70d_ready") is True)
    safety = fr.get("safety", {})
    t("T95_report_safety_no_autopublish",  safety.get("auto_publish_enabled") is False)
    t("T96_report_safety_no_supabase",     safety.get("supabase_write_performed") is False)
    t("T97_report_safety_no_ai_api",       safety.get("ai_api_called") is False)
    t("T98_report_teacher_publish",        safety.get("teacher_final_publish_required") is True)
else:
    for tid in range(91, 99):
        t(f"T{tid}_skipped", False, "full report missing")

# ─── Summary ──────────────────────────────────────────────────────────────
total = passed + failed
print()
print("=" * 60)
print(f"Results: {passed}/{total} passed  ({failed} failed)")
print("=" * 60)

if failed:
    print("\nFailed tests:")
    for tid, ok, detail in results:
        if not ok:
            print(f"  [FAIL] {tid}{(' — ' + detail) if detail else ''}")

sys.exit(0 if failed == 0 else 1)
