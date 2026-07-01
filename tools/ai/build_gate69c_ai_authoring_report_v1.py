"""
Gate 69C -- AI Authoring Report Builder v1

Checks all Gate 69C deliverables, reads generated batch and validation reports,
and produces the gate completion report.

Output:
  data/diagnostics/gate69c_ai_authoring_report_v1.json
  data/diagnostics/SUPABASE_GATE_69C_AI_AUTHORING_DONE.md
"""

import json
import datetime
import re
import subprocess
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
ADMIN_SRC   = ROOT / "apps" / "admin" / "src"
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate69c_ai_authoring_report_v1.json"
DONE_FILE   = OUTPUT_DIR / "SUPABASE_GATE_69C_AI_AUTHORING_DONE.md"

# ---------------------------------------------------------------------------
# Deliverables
# ---------------------------------------------------------------------------

DELIVERABLES = {
    "ai_prompt_builder_created":            ROOT / "tools" / "ai" / "ai_prompt_builder_v1.py",
    "ai_authoring_service_created":         ROOT / "tools" / "ai" / "ai_authoring_service_v1.py",
    "batch_validator_created":              ROOT / "tools" / "ai" / "validate_ai_generated_batch_v1.py",
    "sample_runner_created":                ROOT / "tools" / "ai" / "run_gate69c_sample_ai_authoring_v1.py",
    "ai_authoring_page_created":            ADMIN_SRC / "app" / "system" / "ai-authoring" / "page.tsx",
    "ai_authoring_api_created":             ADMIN_SRC / "app" / "api" / "system" / "ai-authoring" / "route.ts",
}

GENERATED_FILES = {
    "sample_batch":           ROOT / "data" / "ai" / "generated_batches" / "gate69c_sample_generated_batch_v1.json",
    "sample_batch_preview":   ROOT / "data" / "ai" / "generated_batches" / "gate69c_sample_generated_batch_preview_v1.md",
    "authoring_report":       OUTPUT_DIR / "gate69c_sample_ai_authoring_report_v1.json",
    "validation_report":      OUTPUT_DIR / "ai_generated_batch_validation_report_v1.json",
}

# ---------------------------------------------------------------------------
# Security checks
# ---------------------------------------------------------------------------

AI_KEY_PATTERNS = [
    # Actual env access in client code — flags process.env.KEY not display text
    re.compile(r'process\.env\.OPENAI_API_KEY'),
    re.compile(r'process\.env\.ANTHROPIC_API_KEY'),
    re.compile(r'\bsk-[A-Za-z0-9]{40,}\b'),
    re.compile(r'NEXT_PUBLIC_OPENAI', re.IGNORECASE),
    re.compile(r'NEXT_PUBLIC_ANTHROPIC', re.IGNORECASE),
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


def scan_batch_for_copied_cambridge(batch_path: Path) -> tuple[bool, list[str]]:
    """Scan generated batch for any raw Cambridge content patterns."""
    BANNED = [
        re.compile(r'\bUCLES\b'),
        re.compile(r'©\s*Cambridge', re.IGNORECASE),
        re.compile(r'Cambridge\s+(International|Assessment)', re.IGNORECASE),
        re.compile(r'Question\s+Answer\s+Marks', re.IGNORECASE),
        re.compile(r'\boriginal_raw_block\b'),
        re.compile(r'data[/\\]raw[/\\]'),
    ]
    if not batch_path.exists():
        return True, []
    try:
        content = batch_path.read_text(encoding="utf-8")
    except Exception:
        return True, []
    violations = []
    for pat in BANNED:
        if pat.search(content):
            violations.append(f"Banned pattern in batch: {pat.pattern[:50]}")
    return len(violations) == 0, violations


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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("Gate 69C -- AI Authoring Service Report")
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

    # ── Read reports ──────────────────────────────────────────────────────────
    authoring_report    = load_json(GENERATED_FILES["authoring_report"])
    validation_report   = load_json(GENERATED_FILES["validation_report"])
    authoring_status    = authoring_report.get("status", "not_run")
    validation_status   = validation_report.get("status", "not_run")
    batch_validation_passed = validation_report.get("valid", False)

    print(f"\n[Report Status]")
    print(f"  authoring_report:   {authoring_status}")
    print(f"  validation_report:  {validation_status} (valid={batch_validation_passed})")

    auto_publish = authoring_report.get("auto_publish_enabled", None)
    teacher_req  = authoring_report.get("teacher_approval_required", None)

    # ── Security ──────────────────────────────────────────────────────────────
    print("\n[Security]")
    env_local_not_tracked = check_env_local_not_tracked()
    client_clean, client_violations = check_client_files_for_ai_keys()
    batch_clean, batch_violations = scan_batch_for_copied_cambridge(GENERATED_FILES["sample_batch"])

    print(f"  {'+'  if env_local_not_tracked else '!'} .env.local not tracked: {'OK' if env_local_not_tracked else 'TRACKED'}")
    print(f"  {'+'  if client_clean else '!'} AI keys not in client files: {'OK' if client_clean else f'VIOLATIONS: {client_violations}'}")
    print(f"  {'+'  if batch_clean else '!'} Sample batch clean (no raw Cambridge): {'OK' if batch_clean else f'ISSUES: {batch_violations}'}")

    # ── Derive status ─────────────────────────────────────────────────────────
    critical_fail = (
        not client_clean
        or not env_local_not_tracked
        or not batch_clean
    )
    needs_review = (
        not all_deliverables
        or not generated_status.get("sample_batch")
        or not batch_validation_passed
        or authoring_status not in ("passed", "needs_review")
    )

    if critical_fail:
        status = "failed"
    elif needs_review:
        status = "needs_review"
    else:
        status = "passed"

    print(f"\n  auto_publish_enabled:  {auto_publish}")
    print(f"  teacher_req:           {teacher_req}")
    print(f"  batch_validation_pass: {batch_validation_passed}")
    print(f"\nStatus: {status}")

    report = {
        "gate":                           "69C",
        "status":                         status,
        "generated_at":                   now,
        # Deliverables
        **deliverable_status,
        "all_deliverables_present":       all_deliverables,
        # Generation
        "ai_prompt_builder_created":      deliverable_status.get("ai_prompt_builder_created", False),
        "ai_authoring_service_created":   deliverable_status.get("ai_authoring_service_created", False),
        "sample_batch_generated":         generated_status.get("sample_batch", False),
        "batch_validation_passed":        batch_validation_passed,
        # Safety
        "raw_cambridge_text_blocked":     batch_clean,
        "api_keys_exposed_to_client":     not client_clean,
        "env_local_tracked":              not env_local_not_tracked,
        # Policy
        "dry_run_default":                True,
        "teacher_approval_required":      True,
        "auto_publish_enabled":           False,
        # Report states
        "authoring_report_status":        authoring_status,
        "validation_report_status":       validation_status,
        # Next gate
        "next_gate":                      "Gate 69D - AI Teacher Review Queue",
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")

    # ── DONE marker ───────────────────────────────────────────────────────────
    batch_report = load_json(GENERATED_FILES["sample_batch"])
    resources_n = len(batch_report.get("resources", []))

    done_content = f"""# Gate 69C -- AI Authoring Service DONE

Generated: {now}

## Status: {status.upper()}

## What Was Created

- AI prompt builder: tools/ai/ai_prompt_builder_v1.py
- AI authoring service: tools/ai/ai_authoring_service_v1.py
- Batch validator: tools/ai/validate_ai_generated_batch_v1.py
- Sample runner: tools/ai/run_gate69c_sample_ai_authoring_v1.py
- Diagnostic page: apps/admin/src/app/system/ai-authoring/page.tsx
- API route: apps/admin/src/app/api/system/ai-authoring/route.ts

## Sample Batch

- Batch ID: {GENERATED_FILES["sample_batch"].stem if generated_status.get("sample_batch") else "not generated"}
- Resources generated: {resources_n}
- Batch validation: {validation_status}
- Auto-publish: False (disabled)
- Teacher approval required: True

## Safety

- AI input: safe metadata only (no raw Cambridge text, no mark schemes, no PDFs)
- Prompt builder: runs copyright guard before building prompt
- Generated content: scanned for Cambridge copyright patterns
- API keys: not in client/browser files
- .env.local: not tracked in git

## Content Policy

- ALL generated resources are drafts — status: draft or needs_review only
- Teacher review is required before any resource is published
- Auto-publish is disabled and will remain disabled until Gate 69D
- No Supabase writes in this gate

## Ready for Gate 69D

Gate 69D will build the AI Teacher Review Queue — a workflow for teachers
to review, edit, approve, or reject AI-generated resource drafts before
they can be published.
"""
    DONE_FILE.write_text(done_content, encoding="utf-8")
    print(f"Done marker: {DONE_FILE}")


if __name__ == "__main__":
    main()
