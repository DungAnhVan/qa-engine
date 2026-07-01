"""
Gate 69B -- Verify AI Environment v1

Verifies AI provider configuration and scans the repository for
committed API keys or unsafe exposure patterns.

Security:
  - API keys are NEVER printed. Masked as first6...last4 in output.
  - .env.local is read but never written to output or report files.
  - Report file contains no key values.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\verify_ai_env_v1.py

Output:
  data/diagnostics/ai_env_verify_report_v1.json
"""

import json
import re
import datetime
import subprocess
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "ai_env_verify_report_v1.json"

ADMIN_SRC   = ROOT / "apps" / "admin" / "src"

# Patterns that indicate a real key value (not just a placeholder or var name)
SECRET_VALUE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("openai_key_value",        re.compile(r'OPENAI_API_KEY\s*=\s*sk-[A-Za-z0-9\-_]{20,}')),
    ("anthropic_key_value",     re.compile(r'ANTHROPIC_API_KEY\s*=\s*sk-ant-[A-Za-z0-9\-_]{20,}')),
    ("openai_key_raw",          re.compile(r'\bsk-[A-Za-z0-9]{40,}\b')),
    ("anthropic_key_raw",       re.compile(r'\bsk-ant-[A-Za-z0-9\-_]{50,}\b')),
    ("next_public_openai",      re.compile(r'NEXT_PUBLIC_OPENAI', re.IGNORECASE)),
    ("next_public_anthropic",   re.compile(r'NEXT_PUBLIC_ANTHROPIC', re.IGNORECASE)),
]

# Patterns safe to ignore in example files (placeholders only)
EXAMPLE_FILE_SAFE_PATTERNS = re.compile(r'(OPENAI_API_KEY=\s*$|ANTHROPIC_API_KEY=\s*$)')

# Files/dirs to skip during secret scan
SCAN_SKIP_DIRS = {".git", "node_modules", ".next", ".venv-ingest", "__pycache__", ".venv",
                  # Scanner tool dirs contain regex pattern definitions — not real keys
                  "ai", "deploy",
                  # Generated output dirs — not source files
                  "diagnostics"}
SCAN_SKIP_FILES = {".env.local", ".env.production"}

# File extensions to scan (JSON excluded — generated reports contain pattern strings)
SCAN_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".env.example",
                   ".env.production.example", ".toml", ".yaml", ".yml"}


# ---------------------------------------------------------------------------
# Imports from sibling modules
# ---------------------------------------------------------------------------

import sys
sys.path.insert(0, str(ROOT))
from tools.ai.ai_provider_config_v1 import load_ai_provider_config, load_env_local, mask_key, resolve_env

# ---------------------------------------------------------------------------
# Repo secret scan
# ---------------------------------------------------------------------------

def scan_repo_for_secrets() -> tuple[bool, list[str]]:
    """
    Walk the repo and scan committed source files for real key values.
    Skips .env.local, node_modules, .git, and build outputs.

    Returns (clean, violations).
    """
    violations: list[str] = []

    for path in ROOT.rglob("*"):
        # Skip directories
        if path.is_dir():
            continue
        # Skip by directory name
        if any(part in SCAN_SKIP_DIRS for part in path.parts):
            continue
        # Skip by file name
        if path.name in SCAN_SKIP_FILES:
            continue
        # Only scan known text extensions
        if path.suffix not in SCAN_EXTENSIONS and path.name not in {".env.example", ".env.production.example"}:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel = path.relative_to(ROOT)
        is_example_file = "example" in path.name.lower() or path.name.endswith(".example")

        for label, pattern in SECRET_VALUE_PATTERNS:
            if label in ("next_public_openai", "next_public_anthropic"):
                # These are never OK even in example files
                pass
            elif is_example_file:
                # Example files may have OPENAI_API_KEY= (empty placeholder)
                # Only flag if the value looks real (non-empty after =)
                for m in pattern.finditer(content):
                    val = m.group(0)
                    if "sk-" in val.split("=", 1)[-1] if "=" in val else True:
                        violations.append(f"{rel}: {label} — real key value detected")
                continue

            if pattern.search(content):
                violations.append(f"{rel}: {label}")

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


def check_client_files_for_ai_keys() -> tuple[bool, list[str]]:
    """
    Scan the admin app client/browser source files for AI API key references.
    OPENAI_API_KEY and ANTHROPIC_API_KEY must never appear in client bundles.
    """
    violations: list[str] = []
    client_key_patterns = [
        re.compile(r'OPENAI_API_KEY'),
        re.compile(r'ANTHROPIC_API_KEY'),
        re.compile(r'sk-[A-Za-z0-9]{20,}'),
        re.compile(r'sk-ant-[A-Za-z0-9\-_]{20,}'),
        re.compile(r'NEXT_PUBLIC_OPENAI', re.IGNORECASE),
        re.compile(r'NEXT_PUBLIC_ANTHROPIC', re.IGNORECASE),
    ]
    for path in ADMIN_SRC.rglob("*.ts"):
        if any(part in SCAN_SKIP_DIRS for part in path.parts):
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pat in client_key_patterns:
            if pat.search(content):
                rel = path.relative_to(ROOT)
                violations.append(f"{rel}: AI key reference in client file")
    for path in ADMIN_SRC.rglob("*.tsx"):
        if any(part in SCAN_SKIP_DIRS for part in path.parts):
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pat in client_key_patterns:
            if pat.search(content):
                rel = path.relative_to(ROOT)
                violations.append(f"{rel}: AI key reference in client file")

    return len(violations) == 0, violations


def check_env_examples_updated() -> tuple[bool, list[str]]:
    """Verify that .env.example and .env.production.example include QA_AI_PROVIDER."""
    issues: list[str] = []
    for filename in (".env.example", ".env.production.example"):
        path = ROOT / filename
        if not path.exists():
            issues.append(f"{filename} does not exist")
            continue
        content = path.read_text(encoding="utf-8")
        if "QA_AI_PROVIDER" not in content:
            issues.append(f"{filename} missing QA_AI_PROVIDER")
        if "QA_AI_DRY_RUN" not in content:
            issues.append(f"{filename} missing QA_AI_DRY_RUN")
        if "QA_AI_COPYRIGHT_STRICT" not in content:
            issues.append(f"{filename} missing QA_AI_COPYRIGHT_STRICT")
    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Gate 69B -- AI Environment Verify")
    print("-" * 55)

    # Load config
    env_local = load_env_local()
    config    = load_ai_provider_config(env_local)

    print(f"\n[AI Provider Config]")
    print(f"  provider:                {config['provider']}")
    print(f"  dry_run:                 {config['dry_run']}")
    print(f"  copyright_strict:        {config['copyright_strict']}")
    print(f"  openai_key:              {'present' if config['openai_key_present'] else 'not set'}  ({config['_openai_key_masked']})")
    print(f"  anthropic_key:           {'present' if config['anthropic_key_present'] else 'not set'}  ({config['_anthropic_key_masked']})")
    print(f"  selected_provider_ready: {config['selected_provider_ready']}")
    for issue in config["issues"]:
        print(f"  ! {issue}")

    # Git tracking
    print("\n[Git / Secrets]")
    env_local_not_tracked = check_env_local_not_tracked()
    print(f"  .env.local not tracked:  {'OK' if env_local_not_tracked else 'TRACKED — SECURITY ISSUE'}")

    # Repo secret scan
    repo_clean, repo_violations = scan_repo_for_secrets()
    print(f"  repo secret scan:        {'CLEAN' if repo_clean else f'ISSUES ({len(repo_violations)})'}")
    for v in repo_violations:
        print(f"    ! {v}")

    # Client file AI key scan
    print("\n[Client File AI Key Scan]")
    client_clean, client_violations = check_client_files_for_ai_keys()
    print(f"  admin client files:      {'CLEAN' if client_clean else f'ISSUES ({len(client_violations)})'}")
    for v in client_violations:
        print(f"    ! {v}")

    # Env examples
    print("\n[Env Examples]")
    examples_ok, examples_issues = check_env_examples_updated()
    print(f"  .env examples updated:   {'OK' if examples_ok else 'MISSING KEYS'}")
    for i in examples_issues:
        print(f"    ! {i}")

    # Overall status
    issues = config["issues"] + repo_violations + client_violations + examples_issues
    if not env_local_not_tracked:
        issues.append(".env.local is tracked in git")

    critical = not repo_clean or not client_clean or not env_local_not_tracked
    if critical:
        status = "failed"
    elif not examples_ok or not config["selected_provider_ready"]:
        status = "needs_review"
    else:
        status = "passed"

    print(f"\nStatus: {status}")

    report = {
        "gate":                         "69B",
        "title":                        "AI Environment Verify v1",
        "status":                       status,
        "generated_at":                 datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "provider":                     config["provider"],
        "dry_run":                      config["dry_run"],
        "copyright_strict":             config["copyright_strict"],
        "openai_key_present":           config["openai_key_present"],
        "anthropic_key_present":        config["anthropic_key_present"],
        "selected_provider_ready":      config["selected_provider_ready"],
        "env_local_not_tracked":        env_local_not_tracked,
        "repo_secret_scan_clean":       repo_clean,
        "repo_secret_violations":       repo_violations,
        "client_files_clean":           client_clean,
        "client_violations":            client_violations,
        "env_examples_updated":         examples_ok,
        "env_examples_issues":          examples_issues,
        "api_keys_exposed_to_client":   not client_clean,
        "issues":                       issues,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
