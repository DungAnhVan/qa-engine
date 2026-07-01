"""
Gate 69B -- AI Provider Config v1

Loads and validates AI provider configuration from environment variables.
No API keys are printed. Keys are masked as first6...last4.

Environment variables:
  QA_AI_PROVIDER       = mock | openai | anthropic  (default: mock)
  QA_AI_DRY_RUN        = true | false               (default: true)
  QA_AI_COPYRIGHT_STRICT = true | false             (default: true)
  OPENAI_API_KEY       = <key>                      (required only when provider=openai, dry_run=false)
  ANTHROPIC_API_KEY    = <key>                      (required only when provider=anthropic, dry_run=false)

Security:
  - Keys are never printed or written to any file.
  - Keys are masked (first6...last4) in log output only.
  - This module does NOT make any API calls.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

VALID_PROVIDERS = {"mock", "openai", "anthropic"}

# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------

def load_env_local() -> dict[str, str]:
    env_path = ROOT / ".env.local"
    result: dict[str, str] = {}
    if not env_path.exists():
        return result
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def resolve_env(key: str, env_local: dict[str, str]) -> str | None:
    return os.environ.get(key) or env_local.get(key) or None


def mask_key(value: str | None) -> str:
    """Mask an API key for safe log output. Never exposes real values."""
    if not value:
        return "(not set)"
    if len(value) < 10:
        return "***"
    return value[:6] + "..." + value[-4:]

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_ai_provider_config(env_local: dict[str, str] | None = None) -> dict:
    """
    Load and return AI provider configuration.

    Returns a config dict — never includes key values, only presence flags.
    """
    if env_local is None:
        env_local = load_env_local()

    provider_raw   = resolve_env("QA_AI_PROVIDER", env_local) or "mock"
    dry_run_raw    = resolve_env("QA_AI_DRY_RUN", env_local) or "true"
    strict_raw     = resolve_env("QA_AI_COPYRIGHT_STRICT", env_local) or "true"
    openai_key     = resolve_env("OPENAI_API_KEY", env_local)
    anthropic_key  = resolve_env("ANTHROPIC_API_KEY", env_local)

    provider  = provider_raw.strip().lower() if provider_raw.strip().lower() in VALID_PROVIDERS else "mock"
    dry_run   = dry_run_raw.strip().lower() != "false"
    copyright_strict = strict_raw.strip().lower() != "false"

    issues: list[str] = []

    if provider_raw.strip().lower() not in VALID_PROVIDERS:
        issues.append(
            f"QA_AI_PROVIDER={provider_raw!r} is not valid; "
            f"must be one of {sorted(VALID_PROVIDERS)}. Defaulting to 'mock'."
        )

    # Key requirements: only when dry_run=false
    if not dry_run:
        if provider == "openai" and not openai_key:
            issues.append("provider=openai with dry_run=false requires OPENAI_API_KEY to be set")
        if provider == "anthropic" and not anthropic_key:
            issues.append("provider=anthropic with dry_run=false requires ANTHROPIC_API_KEY to be set")

    selected_provider_ready = (
        provider == "mock"
        or dry_run
        or (provider == "openai"    and bool(openai_key))
        or (provider == "anthropic" and bool(anthropic_key))
    )

    return {
        "provider":                provider,
        "dry_run":                 dry_run,
        "copyright_strict":        copyright_strict,
        "openai_key_present":      bool(openai_key),
        "anthropic_key_present":   bool(anthropic_key),
        "selected_provider_ready": selected_provider_ready,
        "issues":                  issues,
        # Internal only — masked representations for logging
        "_openai_key_masked":      mask_key(openai_key),
        "_anthropic_key_masked":   mask_key(anthropic_key),
    }

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_ai_env(config: dict | None = None) -> dict:
    """
    Validate the AI provider environment.
    Returns validation result dict with issues list.
    """
    if config is None:
        config = load_ai_provider_config()

    ok = config["selected_provider_ready"] and not config["issues"]
    return {
        "valid":    ok,
        "provider": config["provider"],
        "dry_run":  config["dry_run"],
        "issues":   config["issues"],
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    config = load_ai_provider_config()
    print("AI Provider Config")
    print("-" * 40)
    print(f"  provider:                {config['provider']}")
    print(f"  dry_run:                 {config['dry_run']}")
    print(f"  copyright_strict:        {config['copyright_strict']}")
    print(f"  openai_key_present:      {config['openai_key_present']}  ({config['_openai_key_masked']})")
    print(f"  anthropic_key_present:   {config['anthropic_key_present']}  ({config['_anthropic_key_masked']})")
    print(f"  selected_provider_ready: {config['selected_provider_ready']}")
    if config["issues"]:
        print("Issues:")
        for i in config["issues"]:
            print(f"  ! {i}")
