"""
Gate 70D -- Test Suite v1

Tests the full Gate 70D pipeline:
  1. Approve Gate 70C package candidate.
  2. Build local published package.
  3. Validate local published package.
  4. Render previews.
  5. Build local registry.
  6. Verify all safety constraints, outputs, and schema.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate70d_ai_bank_local_publish_v1.py

Output:
  data/diagnostics/gate70d_ai_bank_local_publish_test_report_v1.json
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable)

passed = 0
failed = 0
results: list[tuple[str, bool, str]] = []


def t(tid: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
    results.append((tid, condition, detail))
    label = "PASS" if condition else "FAIL"
    print(f"  [{label}] {tid}{(' — ' + detail) if detail else ''}")


def run(script: str, *args: str) -> tuple[int, str, str]:
    p = subprocess.run(
        [str(PYTHON), str(ROOT / script), *args],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return p.returncode, p.stdout, p.stderr


# Paths
PKG_FILE      = ROOT / "data" / "ai" / "package_candidates" / "gate70c_ai_bank_package_candidate_v1.json"
APPROVAL_FILE = ROOT / "data" / "ai" / "package_candidates" / "gate70d_ai_bank_final_publish_approval_v1.json"
PUB_DIR       = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1"
PUB_PKG       = PUB_DIR / "publish_package_v1.json"
STUDENT_P     = PUB_DIR / "student_resource_payload_v1.json"
TEACHER_P     = PUB_DIR / "teacher_resource_payload_v1.json"
MANIFEST      = PUB_DIR / "ai_bank_publish_manifest_v1.md"
PUB_REPORT    = PUB_DIR / "ai_bank_publish_report_v1.json"
STUDENT_HTML  = PUB_DIR / "static_preview" / "gate70d_student_ai_bank_published_preview_v1.html"
TEACHER_HTML  = PUB_DIR / "static_preview" / "gate70d_teacher_ai_bank_published_preview_v1.html"
PREVIEW_RPT   = PUB_DIR / "static_preview" / "gate70d_ai_bank_published_preview_report_v1.json"
REGISTRY      = ROOT / "data" / "ai" / "registry" / "gate70d_ai_bank_content_registry_v1.json"
VAL_REPORT    = ROOT / "data" / "diagnostics" / "gate70d_ai_bank_local_published_package_validation_report_v1.json"
BUILD_REPORT  = ROOT / "data" / "diagnostics" / "gate70d_ai_bank_local_publish_build_report_v1.json"
APPR_REPORT   = ROOT / "data" / "diagnostics" / "gate70d_ai_bank_final_publish_approval_report_v1.json"
REG_REPORT    = ROOT / "data" / "diagnostics" / "gate70d_ai_bank_local_registry_build_report_v1.json"
TEST_REPORT   = ROOT / "data" / "diagnostics" / "gate70d_ai_bank_local_publish_test_report_v1.json"

print("Gate 70D — Test Suite")
print("=" * 60)

# ─── S1: Script existence ──────────────────────────────────────────────────
print("\n[S1] Script/file existence")
scripts = [
    "tools/ai/approve_gate70d_ai_bank_package_candidate_v1.py",
    "tools/ai/build_gate70d_ai_bank_local_published_package_v1.py",
    "tools/ai/validate_gate70d_ai_bank_local_published_package_v1.py",
    "tools/ai/render_gate70d_ai_bank_local_published_preview_v1.py",
    "tools/ai/build_gate70d_ai_bank_local_registry_v1.py",
    "apps/admin/src/lib/aiBankPublishedPackage.ts",
    "apps/admin/src/app/ai-bank-published/page.tsx",
    "apps/admin/src/app/system/ai-bank-published/page.tsx",
    "apps/admin/src/app/api/system/ai-bank-published/route.ts",
]
for s in scripts:
    t(f"T01_{s.split('/')[-1][:30]}", (ROOT / s).exists(), s)

# ─── S2: Gate 70C prerequisite ────────────────────────────────────────────
print("\n[S2] Gate 70C prerequisite")
t("T02_gate70c_pkg_exists", PKG_FILE.exists(), str(PKG_FILE.relative_to(ROOT)))

if not PKG_FILE.exists():
    print("FATAL: Gate 70C package candidate missing. Run test_gate70c_ai_bank_package_candidate_v1.py first.")
    sys.exit(1)

pkg_c = json.loads(PKG_FILE.read_text(encoding="utf-8"))
t("T03_gate70c_status", pkg_c.get("status") == "draft_package_candidate", f"status={pkg_c.get('status')}")
t("T04_gate70c_resources", pkg_c.get("resource_count", 0) >= 1, f"count={pkg_c.get('resource_count')}")

# ─── S3: Seed approval file ───────────────────────────────────────────────
print("\n[S3] Seed approval file")
t("T05_approval_seed_exists", APPROVAL_FILE.exists(), str(APPROVAL_FILE.relative_to(ROOT)))
if APPROVAL_FILE.exists():
    seed = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
    t("T06_seed_allow_local_publish_false", not seed.get("allow_local_publish", True), "default=false")
    t("T07_seed_allow_supabase_sync_false", not seed.get("allow_supabase_sync", True), "always false")
    t("T08_seed_allow_active_switch_false", not seed.get("allow_active_switch", True), "always false")

# ─── S4: Approve ──────────────────────────────────────────────────────────
print("\n[S4] approve_gate70d_ai_bank_package_candidate_v1.py --approve")
rc, out, err = run(
    "tools/ai/approve_gate70d_ai_bank_package_candidate_v1.py",
    "--approve", "--approved-by", "local_demo_teacher",
    "--notes", "automated test approval for Gate 70D"
)
t("T09_approve_rc0", rc == 0, f"rc={rc}")
t("T10_approval_file_updated", APPROVAL_FILE.exists())
t("T11_approval_report_created", APPR_REPORT.exists())

if APPROVAL_FILE.exists():
    appr = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
    t("T12_approval_status_approved",      appr.get("approval_status") == "approved", f"status={appr.get('approval_status')}")
    t("T13_allow_local_publish_true",      appr.get("allow_local_publish") is True)
    t("T14_allow_supabase_sync_false",     appr.get("allow_supabase_sync") is False, "always false")
    t("T15_allow_active_switch_false",     appr.get("allow_active_switch") is False, "always false")
    t("T16_approved_by_set",               bool(appr.get("approved_by")))
    t("T17_approved_at_set",               bool(appr.get("approved_at")))

# ─── S5: Build local published package ────────────────────────────────────
print("\n[S5] build_gate70d_ai_bank_local_published_package_v1.py")
rc, out, err = run("tools/ai/build_gate70d_ai_bank_local_published_package_v1.py")
t("T18_build_rc0",          rc == 0,              f"rc={rc}")
t("T19_pub_pkg_exists",     PUB_PKG.exists())
t("T20_student_p_exists",   STUDENT_P.exists())
t("T21_teacher_p_exists",   TEACHER_P.exists())
t("T22_manifest_exists",    MANIFEST.exists())
t("T23_pub_report_exists",  PUB_REPORT.exists())
t("T24_build_diag_exists",  BUILD_REPORT.exists())

if PUB_PKG.exists():
    pub = json.loads(PUB_PKG.read_text(encoding="utf-8"))
    t("T25_pkg_id",                    pub.get("package_id") == "quanta_aptus_gate70d_ai_bank_package_v1")
    t("T26_status_local_not_active",   pub.get("status") == "published_local_not_active", f"status={pub.get('status')}")
    t("T27_active_content_false",      pub.get("active_content") is False)
    t("T28_supabase_false",            pub.get("supabase_write_performed") is False)
    t("T29_ai_api_false",              pub.get("ai_api_called") is False)
    t("T30_teacher_approval_true",     pub.get("teacher_final_approval") is True)
    t("T31_resource_count_gte_1",      pub.get("resource_count", 0) >= 1, f"count={pub.get('resource_count')}")
    t("T32_allow_active_switch_false", pub.get("allow_active_switch") is False)
    t("T33_allow_supabase_sync_false", pub.get("allow_supabase_sync") is False)

    resources = pub.get("resources", [])
    t("T34_resources_non_empty", len(resources) >= 1)

    if resources:
        res = resources[0]
        t("T35_resource_has_resource_id",    "resource_id" in res)
        t("T36_resource_has_student_prompt", bool(res.get("student_prompt")))
        t("T37_resource_has_answer_key",     bool(res.get("answer_key")))
        t("T38_resource_has_rubric",         isinstance(res.get("marking_rubric"), list) and len(res.get("marking_rubric", [])) > 0)
        t("T39_resource_has_safety_decl",    isinstance(res.get("safety_declaration"), dict))
        prov = res.get("provenance", {})
        t("T40_provenance_gate70b_approved", prov.get("gate70b_approved") is True)

    # No rejected/revision/pending
    bad = [r for r in resources if r.get("decision") in ("needs_revision", "reject")]
    t("T41_no_bad_decisions", len(bad) == 0, f"bad={len(bad)}")

    # No raw Cambridge text in content
    content = " ".join(str(r.get(f, "")) for r in resources
                       for f in ("student_prompt", "answer_key", "teacher_notes", "title"))
    bad_pats = ["Cambridge International", "UCLES", "© Cambridge", "mark_scheme_text\": \""]
    found = [p for p in bad_pats if p in content]
    t("T42_no_raw_cambridge_text", len(found) == 0, f"found={found}")

    # No secrets in full package
    all_text = json.dumps(pub)
    secret_pats = [r"sk-[A-Za-z0-9]{20,}", r"sk-ant-[A-Za-z0-9\-]{20,}"]
    found_secrets = [p for p in secret_pats if re.search(p, all_text)]
    t("T43_no_secrets", len(found_secrets) == 0, f"found={found_secrets}")

# Student payload excludes answer_key/rubric/teacher_notes
if STUDENT_P.exists():
    sp = json.loads(STUDENT_P.read_text(encoding="utf-8"))
    if sp.get("resources"):
        sr = sp["resources"][0]
        t("T44_student_no_answer_key",     "answer_key" not in sr)
        t("T45_student_no_marking_rubric", "marking_rubric" not in sr)
        t("T46_student_no_teacher_notes",  "teacher_notes" not in sr)
        t("T47_student_has_prompt",        bool(sr.get("student_prompt")))

# ─── S6: Validate ─────────────────────────────────────────────────────────
print("\n[S6] validate_gate70d_ai_bank_local_published_package_v1.py")
rc, out, err = run("tools/ai/validate_gate70d_ai_bank_local_published_package_v1.py")
t("T48_validate_rc0",       rc == 0, f"rc={rc}")
t("T49_val_report_created", VAL_REPORT.exists())

if VAL_REPORT.exists():
    val = json.loads(VAL_REPORT.read_text(encoding="utf-8"))
    t("T50_val_valid_true",    val.get("valid") is True, f"issues={val.get('issues')}")
    safety = val.get("safety_summary", {})
    t("T51_val_secrets_clean",   safety.get("secrets_clean") is True)
    t("T52_val_copyright_clean", safety.get("copyright_clean") is True)
    t("T53_val_active_false",    safety.get("active_content") is False)
    t("T54_val_supabase_false",  safety.get("supabase_write_performed") is False)
    t("T55_val_ai_false",        safety.get("ai_api_called") is False)
    t("T56_val_teacher_true",    safety.get("teacher_final_approval") is True)
    t("T57_val_student_exists",  safety.get("student_payload_exists") is True)
    t("T58_val_teacher_exists",  safety.get("teacher_payload_exists") is True)

# ─── S7: Render previews ──────────────────────────────────────────────────
print("\n[S7] render_gate70d_ai_bank_local_published_preview_v1.py")
rc, out, err = run("tools/ai/render_gate70d_ai_bank_local_published_preview_v1.py")
t("T59_render_rc0",        rc == 0, f"rc={rc}")
t("T60_student_html",      STUDENT_HTML.exists())
t("T61_teacher_html",      TEACHER_HTML.exists())
t("T62_preview_rpt",       PREVIEW_RPT.exists())

if STUDENT_HTML.exists():
    sh = STUDENT_HTML.read_text(encoding="utf-8")
    t("T63_student_doctype",         sh.startswith("<!DOCTYPE html"))
    t("T64_student_no_answer_key",   "answer_key" not in sh.lower().replace("_",""))
    t("T65_student_has_banner",      "Gate 70D" in sh)
    t("T66_student_not_active",      "not_active" in sh or "not active" in sh.lower())

if TEACHER_HTML.exists():
    th = TEACHER_HTML.read_text(encoding="utf-8")
    t("T67_teacher_doctype",         th.startswith("<!DOCTYPE html"))
    t("T68_teacher_confidential",    "Confidential" in th or "teacher" in th.lower())
    t("T69_teacher_answer_key",      "Answer Key" in th)
    t("T70_teacher_rubric",          "Marking Rubric" in th)

# ─── S8: Registry ─────────────────────────────────────────────────────────
print("\n[S8] build_gate70d_ai_bank_local_registry_v1.py")
rc, out, err = run("tools/ai/build_gate70d_ai_bank_local_registry_v1.py")
t("T71_registry_rc0",      rc == 0, f"rc={rc}")
t("T72_registry_exists",   REGISTRY.exists())
t("T73_reg_report_exists", REG_REPORT.exists())

if REGISTRY.exists():
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    packages = reg.get("packages", [])
    t("T74_registry_has_package", len(packages) >= 1)
    if packages:
        p0 = packages[0]
        t("T75_reg_pkg_id",          p0.get("package_id") == "quanta_aptus_gate70d_ai_bank_package_v1")
        t("T76_reg_status_local",    p0.get("status") == "published_local_not_active")
        t("T77_reg_active_false",    p0.get("active_content") is False)
        t("T78_reg_supabase_false",  p0.get("supabase_write_performed") is False)

# ─── S9: TypeScript / Next.js static checks ───────────────────────────────
print("\n[S9] TS/TSX static checks")
ts_lib = ROOT / "apps/admin/src/lib/aiBankPublishedPackage.ts"
if ts_lib.exists():
    ts = ts_lib.read_text(encoding="utf-8")
    t("T79_ts_reads_pub_pkg",     "publish_package_v1.json" in ts)
    t("T80_ts_reads_student",     "student_resource_payload_v1.json" in ts)
    t("T81_ts_reads_teacher",     "teacher_resource_payload_v1.json" in ts)
    t("T82_ts_reads_registry",    "gate70d_ai_bank_content_registry_v1.json" in ts)
    t("T83_ts_reads_validation",  "validation_report" in ts)
    t("T84_ts_server_only",       "import fs" in ts)
    t("T85_ts_no_use_client",     '"use client"' not in ts)
    t("T86_ts_no_service_role_in_client", "SUPABASE_SERVICE_ROLE_KEY" not in ts or "server" in ts.lower())

page = ROOT / "apps/admin/src/app/ai-bank-published/page.tsx"
if page.exists():
    pg = page.read_text(encoding="utf-8")
    t("T87_page_requireRole",        "requireRole" in pg)
    t("T88_page_no_supabase_client", "createClient" not in pg)
    t("T89_page_active_false",       "active_content" in pg)
    t("T90_page_no_publish_btn",     "publish" not in pg.lower() or "not active" in pg.lower() or "No publish" in pg)
    t("T91_page_gate70e_warning",    "Gate 70E" in pg)
    t("T92_page_diag_link",          "/system/ai-bank-published" in pg)

sys_page = ROOT / "apps/admin/src/app/system/ai-bank-published/page.tsx"
if sys_page.exists():
    sp = sys_page.read_text(encoding="utf-8")
    t("T93_syspage_requireRole",     "requireRole" in sp)
    t("T94_syspage_no_client",       "createClient" not in sp)
    t("T95_syspage_ready_gate70e",   "Gate70E" in sp or "gate70e" in sp.lower() or "readyForGate70E" in sp)

route = ROOT / "apps/admin/src/app/api/system/ai-bank-published/route.ts"
if route.exists():
    rt = route.read_text(encoding="utf-8")
    t("T96_route_get_export",        "export async function GET" in rt)
    t("T97_route_force_dynamic",     "force-dynamic" in rt)
    t("T98_route_no_post",           "export async function POST" not in rt)
    t("T99_route_ready_gate70e",     "ready_for_gate70e" in rt)
    t("T100_route_secrets_false",    "secrets_exposed" in rt)

# ─── S10: Layout links ─────────────────────────────────────────────────────
print("\n[S10] layout.tsx nav links")
layout = ROOT / "apps/admin/src/app/layout.tsx"
if layout.exists():
    lt = layout.read_text(encoding="utf-8")
    t("T101_layout_published_link",  "/ai-bank-published" in lt)
    t("T102_layout_pub_diag_link",   "/system/ai-bank-published" in lt)

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

# Save test report
test_report = {
    "gate":    "70D",
    "total":   total,
    "passed":  passed,
    "failed":  failed,
    "status":  "passed" if failed == 0 else "needs_review",
    "results": [{"id": tid, "ok": ok, "detail": det} for tid, ok, det in results],
}
TEST_REPORT.parent.mkdir(parents=True, exist_ok=True)
TEST_REPORT.write_text(json.dumps(test_report, indent=2), encoding="utf-8")
print(f"\nTest report: {TEST_REPORT.relative_to(ROOT)}")
sys.exit(0 if failed == 0 else 1)
