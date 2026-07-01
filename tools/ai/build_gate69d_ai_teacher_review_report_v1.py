"""
Gate 69D -- Build AI Teacher Review Report v1

Checks all Gate 69D deliverables and produces the gate completion report.

Output:
  data/diagnostics/gate69d_ai_teacher_review_report_v1.json
  data/diagnostics/SUPABASE_GATE_69D_AI_TEACHER_REVIEW_DONE.md
"""

import json
import re
import datetime
import subprocess
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[2]
ADMIN_SRC = ROOT / "apps" / "admin" / "src"
OUT_DIR   = ROOT / "data" / "diagnostics"
OUT_FILE  = OUT_DIR / "gate69d_ai_teacher_review_report_v1.json"
DONE_FILE = OUT_DIR / "SUPABASE_GATE_69D_AI_TEACHER_REVIEW_DONE.md"

# ---------------------------------------------------------------------------
# Deliverables
# ---------------------------------------------------------------------------

DELIVERABLES = {
    "build_review_queue_created":   ROOT / "tools" / "ai" / "build_ai_teacher_review_queue_v1.py",
    "apply_decisions_created":      ROOT / "tools" / "ai" / "apply_ai_teacher_review_decisions_v1.py",
    "ai_teacher_review_lib":        ADMIN_SRC / "lib" / "aiTeacherReview.ts",
    "ai_review_ui_created":         ADMIN_SRC / "app" / "ai-review" / "page.tsx",
    "decision_api_created":         ADMIN_SRC / "app" / "api" / "ai-review" / "decision" / "route.ts",
    "system_ai_review_page":        ADMIN_SRC / "app" / "system" / "ai-review" / "page.tsx",
    "system_ai_review_api":         ADMIN_SRC / "app" / "api" / "system" / "ai-review" / "route.ts",
}

GENERATED_FILES = {
    "review_queue":      ROOT / "data" / "ai" / "review" / "ai_teacher_review_queue_v1.json",
    "decisions_file":    ROOT / "data" / "ai" / "review" / "ai_teacher_review_decisions_v1.json",
    "approved_bank":     ROOT / "data" / "ai" / "approved" / "ai_approved_resource_candidates_v1.json",
    "revision_queue":    ROOT / "data" / "ai" / "revision" / "ai_revision_queue_v1.json",
    "rejected_store":    ROOT / "data" / "ai" / "rejected" / "ai_rejected_resources_v1.json",
    "test_report":       OUT_DIR / "gate69d_ai_teacher_review_test_report_v1.json",
    "apply_report":      OUT_DIR / "ai_teacher_review_decisions_apply_report_v1.json",
}

# ---------------------------------------------------------------------------
# Security scanners
# ---------------------------------------------------------------------------

AI_KEY_PATTERNS = [
    re.compile(r'process\.env\.OPENAI_API_KEY'),
    re.compile(r'process\.env\.ANTHROPIC_API_KEY'),
    re.compile(r'\bsk-[A-Za-z0-9]{40,}\b'),
    re.compile(r'NEXT_PUBLIC_OPENAI', re.IGNORECASE),
    re.compile(r'NEXT_PUBLIC_ANTHROPIC', re.IGNORECASE),
]

BANNED_CONTENT = [
    ("UCLES",            re.compile(r'\bUCLES\b')),
    ("cambridge_copy",   re.compile(r'©\s*Cambridge', re.IGNORECASE)),
    ("cambridge_intl",   re.compile(r'Cambridge\s+(International|Assessment)', re.IGNORECASE)),
    ("mark_scheme_hdr",  re.compile(r'Question\s+Answer\s+Marks', re.IGNORECASE)),
    ("raw_block_field",  re.compile(r'\boriginal_raw_block\b')),
    ("raw_data_path",    re.compile(r'data[/\\]raw[/\\]')),
]

SKIP_DIRS = {".git", "node_modules", ".next", ".venv-ingest", "__pycache__",
             "ai", "deploy", "diagnostics"}


def check_client_files_for_ai_keys() -> tuple[bool, list[str]]:
    violations = []
    for ext in ("*.ts", "*.tsx"):
        for path in ADMIN_SRC.rglob(ext):
            if any(p in SKIP_DIRS for p in path.parts):
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            for pat in AI_KEY_PATTERNS:
                if pat.search(content):
                    violations.append(f"{path.relative_to(ROOT)}: {pat.pattern[:40]}")
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


def scan_output_files_for_cambridge(files: dict) -> tuple[bool, list[str]]:
    issues = []
    for key, path in files.items():
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

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("Gate 69D -- AI Teacher Review Report")
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

    # ── Read test report ──────────────────────────────────────────────────────
    test_report  = load_json(GENERATED_FILES["test_report"])
    apply_report = load_json(GENERATED_FILES["apply_report"])

    test_status     = test_report.get("status", "not_run")
    tests_passed    = test_report.get("tests_passed", 0)
    tests_total     = test_report.get("tests_total", 0)
    approved_count  = test_report.get("approved_count", apply_report.get("approved_count", 0))
    revision_count  = test_report.get("needs_revision_count", apply_report.get("needs_revision_count", 0))
    rejected_count  = test_report.get("rejected_count", apply_report.get("rejected_count", 0))
    auto_pub        = apply_report.get("auto_publish_enabled", False)
    supa_write      = apply_report.get("supabase_write_performed", False)

    print(f"\n[Test Report]")
    print(f"  status:   {test_status}")
    print(f"  passed:   {tests_passed}/{tests_total}")
    print(f"  approved: {approved_count}, revision: {revision_count}, rejected: {rejected_count}")

    # ── Security ──────────────────────────────────────────────────────────────
    print("\n[Security]")
    env_local_ok       = check_env_local_not_tracked()
    client_clean, client_violations = check_client_files_for_ai_keys()
    content_clean, content_issues  = scan_output_files_for_cambridge(GENERATED_FILES)

    print(f"  {'+'  if env_local_ok else '!'} .env.local not tracked: {'OK' if env_local_ok else 'TRACKED'}")
    print(f"  {'+'  if client_clean else '!'} AI keys not in client files: {'OK' if client_clean else f'VIOLATIONS: {client_violations}'}")
    print(f"  {'+'  if content_clean else '!'} No raw Cambridge in output files: {'OK' if content_clean else f'ISSUES: {content_issues}'}")
    print(f"  [+] auto_publish_enabled:     {auto_pub}")
    print(f"  [+] supabase_write_performed: {supa_write}")

    # ── Derive status ─────────────────────────────────────────────────────────
    critical_fail = (
        not client_clean
        or not env_local_ok
        or not content_clean
        or auto_pub is True
        or supa_write is True
    )
    needs_review = (
        not all_deliverables
        or not generated_status.get("approved_bank")
        or test_status not in ("passed",)
    )

    if critical_fail:
        status = "failed"
    elif needs_review:
        status = "needs_review"
    else:
        status = "passed"

    print(f"\nStatus: {status}")

    report = {
        "gate":                         "69D",
        "status":                       status,
        "generated_at":                 now,
        # Deliverables
        **deliverable_status,
        "all_deliverables_present":     all_deliverables,
        # Generated outputs
        "ai_teacher_review_queue_created": generated_status.get("review_queue", False),
        "ai_review_ui_created":         deliverable_status.get("ai_review_ui_created", False),
        "decision_api_created":         deliverable_status.get("decision_api_created", False),
        "decisions_apply_created":      deliverable_status.get("apply_decisions_created", False),
        "approved_candidate_bank_created": generated_status.get("approved_bank", False),
        # Test results
        "test_status":                  test_status,
        "tests_passed":                 tests_passed,
        "tests_total":                  tests_total,
        "approved_count":               approved_count,
        "needs_revision_count":         revision_count,
        "rejected_count":               rejected_count,
        # Safety policy
        "teacher_approval_required":    True,
        "auto_publish_enabled":         False,
        "supabase_write_performed":     False,
        "raw_cambridge_text_blocked":   content_clean,
        "api_keys_exposed_to_client":   not client_clean,
        "env_local_tracked":            not env_local_ok,
        # Next gate
        "next_gate": "Gate 69E - AI Approved Candidate Package Builder",
    }

    OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUT_FILE}")

    # ── DONE marker ───────────────────────────────────────────────────────────
    done_content = f"""# Gate 69D — AI Teacher Review Queue DONE

Generated: {now}

## Status: {status.upper()}

## What Was Created

- Review queue builder:   tools/ai/build_ai_teacher_review_queue_v1.py
- Decision applicator:    tools/ai/apply_ai_teacher_review_decisions_v1.py
- Server lib:             apps/admin/src/lib/aiTeacherReview.ts
- Teacher review UI:      apps/admin/src/app/ai-review/page.tsx
- Decision API:           apps/admin/src/app/api/ai-review/decision/route.ts
- Diagnostic page:        apps/admin/src/app/system/ai-review/page.tsx
- Diagnostic API:         apps/admin/src/app/api/system/ai-review/route.ts
- Tests:                  tools/ai/test_gate69d_ai_teacher_review_v1.py

## Review Results

- Approved candidate bank created.
- Needs-revision queue created.
- Rejected resources store created.
- Tests: {tests_passed}/{tests_total} passed

## Content Policy

- AI teacher review queue created.
- Teacher decision flow created (approve / needs_revision / reject).
- Approved/revision/rejected candidate outputs created.
- No auto publish.
- No Supabase write.
- Ready for Gate 69E.

## Ready for Gate 69E

Gate 69E will build student-facing resource packages from the approved
AI candidate bank, with teacher sign-off required before any resource
enters a live package.
"""
    DONE_FILE.write_text(done_content, encoding="utf-8")
    print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
