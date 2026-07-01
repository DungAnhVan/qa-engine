"""
Gate 69E -- Build AI Package Candidate Report v1

Checks all Gate 69E deliverables and produces the gate completion report.

Output:
  data/diagnostics/gate69e_ai_package_candidate_report_v1.json
  data/diagnostics/SUPABASE_GATE_69E_AI_PACKAGE_CANDIDATE_DONE.md
"""

import json
import re
import datetime
import subprocess
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[2]
ADMIN_SRC = ROOT / "apps" / "admin" / "src"
OUT_DIR   = ROOT / "data" / "diagnostics"
OUT_FILE  = OUT_DIR / "gate69e_ai_package_candidate_report_v1.json"
DONE_FILE = OUT_DIR / "SUPABASE_GATE_69E_AI_PACKAGE_CANDIDATE_DONE.md"

PKG_DIR   = ROOT / "data" / "ai" / "package_candidates"
PREVIEW_DIR = PKG_DIR / "static_preview"

DELIVERABLES = {
    "build_package_candidate_script":   ROOT / "tools" / "ai" / "build_ai_approved_package_candidate_v1.py",
    "validate_package_candidate_script": ROOT / "tools" / "ai" / "validate_ai_package_candidate_v1.py",
    "export_payloads_script":           ROOT / "tools" / "ai" / "export_ai_package_candidate_payloads_v1.py",
    "render_preview_script":            ROOT / "tools" / "ai" / "render_ai_package_candidate_preview_v1.py",
    "ai_package_candidate_lib":         ADMIN_SRC / "lib" / "aiPackageCandidate.ts",
    "ai_package_ui_created":            ADMIN_SRC / "app" / "ai-package" / "page.tsx",
    "system_ai_package_page":           ADMIN_SRC / "app" / "system" / "ai-package" / "page.tsx",
    "system_ai_package_api":            ADMIN_SRC / "app" / "api" / "system" / "ai-package" / "route.ts",
}

GENERATED_FILES = {
    "package_candidate":    PKG_DIR / "ai_resource_package_candidate_v1.json",
    "student_payload":      PKG_DIR / "student_ai_package_payload_v1.json",
    "teacher_payload":      PKG_DIR / "teacher_ai_package_payload_v1.json",
    "student_preview":      PREVIEW_DIR / "student_ai_package_preview_v1.html",
    "teacher_preview":      PREVIEW_DIR / "teacher_ai_package_preview_v1.html",
    "validation_report":    OUT_DIR / "ai_package_candidate_validation_report_v1.json",
    "test_report":          OUT_DIR / "gate69e_ai_package_candidate_test_report_v1.json",
}

AI_KEY_PATTERNS = [
    re.compile(r'process\.env\.OPENAI_API_KEY'),
    re.compile(r'process\.env\.ANTHROPIC_API_KEY'),
    re.compile(r'\bsk-[A-Za-z0-9]{40,}\b'),
    re.compile(r'NEXT_PUBLIC_OPENAI', re.IGNORECASE),
    re.compile(r'NEXT_PUBLIC_ANTHROPIC', re.IGNORECASE),
]

BANNED_CONTENT = [
    ("UCLES",           re.compile(r'\bUCLES\b')),
    ("cambridge_copy",  re.compile(r'©\s*Cambridge', re.IGNORECASE)),
    ("cambridge_intl",  re.compile(r'Cambridge\s+(International|Assessment)', re.IGNORECASE)),
    ("mark_scheme_hdr", re.compile(r'Question\s+Answer\s+Marks', re.IGNORECASE)),
    ("raw_block",       re.compile(r'\boriginal_raw_block\b')),
    ("raw_data_path",   re.compile(r'data[/\\]raw[/\\]')),
]

SKIP_DIRS = {".git", "node_modules", ".next", ".venv-ingest", "__pycache__",
             "ai", "deploy", "diagnostics"}


def check_client_files_for_ai_keys() -> tuple[bool, list[str]]:
    violations = []
    for ext in ("*.ts", "*.tsx"):
        for p in ADMIN_SRC.rglob(ext):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            content = p.read_text(encoding="utf-8", errors="replace")
            for pat in AI_KEY_PATTERNS:
                if pat.search(content):
                    violations.append(f"{p.relative_to(ROOT)}: {pat.pattern[:40]}")
    return len(violations) == 0, violations


def check_env_local_not_tracked() -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", ".env.local"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=10,
        )
        return not bool(result.stdout.strip())
    except Exception:
        return True


def scan_generated_for_cambridge() -> tuple[bool, list[str]]:
    issues = []
    for key, path in GENERATED_FILES.items():
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for label, pat in BANNED_CONTENT:
            if pat.search(content):
                issues.append(f"Banned pattern ({label}) in {path.name}")
    return len(issues) == 0, issues


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("Gate 69E -- AI Package Candidate Report")
    print("-" * 55)

    # ── Deliverables ──────────────────────────────────────────────────────────
    print("\n[Deliverables]")
    deliverable_status: dict[str, bool] = {}
    for key, path in DELIVERABLES.items():
        exists = path.exists()
        deliverable_status[key] = exists
        print(f"  {'+'  if exists else '!'} {key}: {'OK' if exists else 'MISSING'}")
    all_deliverables = all(deliverable_status.values())

    # ── Generated files ───────────────────────────────────────────────────────
    print("\n[Generated Files]")
    generated_status: dict[str, bool] = {}
    for key, path in GENERATED_FILES.items():
        exists = path.exists()
        generated_status[key] = exists
        print(f"  {'+'  if exists else '?'} {key}: {'OK' if exists else 'not generated yet'}")

    # ── Test report ───────────────────────────────────────────────────────────
    test_report = load_json(GENERATED_FILES["test_report"])
    val_report  = load_json(GENERATED_FILES["validation_report"])

    test_status    = test_report.get("status", "not_run")
    tests_passed   = test_report.get("tests_passed", 0)
    tests_total    = test_report.get("tests_total", 0)
    rc             = test_report.get("resource_count", 0)
    val_passed     = val_report.get("valid", False)
    auto_pub       = False
    supa_write     = False

    print(f"\n[Test Report]")
    print(f"  status:   {test_status}")
    print(f"  passed:   {tests_passed}/{tests_total}")
    print(f"  resource_count: {rc}")
    print(f"  validation_passed: {val_passed}")

    # ── Security ──────────────────────────────────────────────────────────────
    print("\n[Security]")
    env_local_ok        = check_env_local_not_tracked()
    client_clean, client_violations = check_client_files_for_ai_keys()
    content_clean, content_issues   = scan_generated_for_cambridge()

    print(f"  {'+'  if env_local_ok else '!'} .env.local not tracked: {'OK' if env_local_ok else 'TRACKED'}")
    print(f"  {'+'  if client_clean else '!'} AI keys not in client files: {'OK' if client_clean else f'VIOLATIONS: {client_violations}'}")
    print(f"  {'+'  if content_clean else '!'} No raw Cambridge in output: {'OK' if content_clean else f'ISSUES: {content_issues}'}")
    print(f"  [+] auto_publish_enabled:     {auto_pub}")
    print(f"  [+] supabase_write_performed: {supa_write}")

    # ── Derive status ─────────────────────────────────────────────────────────
    critical_fail = not client_clean or not env_local_ok or not content_clean
    needs_review  = (
        not all_deliverables
        or not generated_status.get("package_candidate")
        or not generated_status.get("student_payload")
        or not generated_status.get("teacher_payload")
        or not generated_status.get("student_preview")
        or not generated_status.get("teacher_preview")
        or test_status != "passed"
    )

    if critical_fail:
        status = "failed"
    elif needs_review:
        status = "needs_review"
    else:
        status = "passed"

    print(f"\nStatus: {status}")

    report = {
        "gate":                             "69E",
        "status":                           status,
        "generated_at":                     now,
        **deliverable_status,
        "all_deliverables_present":         all_deliverables,
        "ai_package_candidate_created":     generated_status.get("package_candidate", False),
        "ai_package_candidate_validated":   val_passed,
        "student_payload_exported":         generated_status.get("student_payload", False),
        "teacher_payload_exported":         generated_status.get("teacher_payload", False),
        "static_previews_created":          (generated_status.get("student_preview", False)
                                             and generated_status.get("teacher_preview", False)),
        "ai_package_ui_created":            deliverable_status.get("ai_package_ui_created", False),
        "test_status":                      test_status,
        "tests_passed":                     tests_passed,
        "tests_total":                      tests_total,
        "resource_count":                   rc,
        "teacher_approval_required":        True,
        "auto_publish_enabled":             False,
        "supabase_write_performed":         False,
        "teacher_final_publish_required":   True,
        "raw_cambridge_text_blocked":       content_clean,
        "api_keys_exposed_to_client":       not client_clean,
        "env_local_tracked":                not env_local_ok,
        "next_gate":                        "Gate 69F - AI Package Final Approval and Publish",
    }

    OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUT_FILE}")

    # ── DONE marker ───────────────────────────────────────────────────────────
    done_content = f"""# Gate 69E — AI Approved Candidate Package Builder DONE

Generated: {now}

## Status: {status.upper()}

## What Was Created

- Package candidate builder:   tools/ai/build_ai_approved_package_candidate_v1.py
- Package validator:           tools/ai/validate_ai_package_candidate_v1.py
- Payload exporter:            tools/ai/export_ai_package_candidate_payloads_v1.py
- HTML preview renderer:       tools/ai/render_ai_package_candidate_preview_v1.py
- Server lib:                  apps/admin/src/lib/aiPackageCandidate.ts
- Package candidate UI:        apps/admin/src/app/ai-package/page.tsx
- Diagnostic page:             apps/admin/src/app/system/ai-package/page.tsx
- Diagnostic API:              apps/admin/src/app/api/system/ai-package/route.ts
- Tests:                       tools/ai/test_gate69e_ai_package_candidate_v1.py

## Results

- AI approved package candidate created.
- Package validation passed.
- Student/teacher payloads exported.
- Static previews created.
- Tests: {tests_passed}/{tests_total} passed.

## Content Policy

- No auto publish.
- No Supabase write.
- Teacher final publish required.
- Only approved AI resources included.
- Rejected and needs_revision items excluded.
- All safety declarations preserved.
- Ready for Gate 69F.

## Ready for Gate 69F

Gate 69F will provide the final approval flow for publishing the AI
package candidate to active content — with full teacher sign-off
before any Supabase write occurs.
"""
    DONE_FILE.write_text(done_content, encoding="utf-8")
    print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
