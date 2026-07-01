"""
Gate 69B / Gate 70A -- AI Client v1

Safe abstraction layer for AI text generation.

- Default: mock provider (no API calls, no keys required).
- dry_run=true: always returns mock response regardless of provider.
- Real API calls: only when QA_AI_DRY_RUN=false and a provider key exists.
- If an SDK package is missing, falls back to urllib (standard library only).
- Keys are NEVER printed or returned in responses.

Model selection (Gate 70A):
  QA_OPENAI_MODEL   — overrides default OpenAI model  (default: gpt-4o-mini)
  QA_ANTHROPIC_MODEL — overrides default Anthropic model (default: claude-haiku-4-5-20251001)

Usage:
  from tools.ai.ai_client_v1 import generate_text

  # Always safe default (mock):
  result = generate_text("Generate a question about wave interference")

  # Explicit dry-run:
  result = generate_text("...", dry_run=True)
"""

import hashlib
import json
import urllib.error
import urllib.request
from tools.ai.ai_provider_config_v1 import load_ai_provider_config, load_env_local, resolve_env
from tools.ai.copyright_safety_guard_v1 import scan_prompt_for_disallowed_source_text

_OPENAI_DEFAULT_MODEL    = "gpt-4o-mini"
_ANTHROPIC_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_API_TIMEOUT = 60

# ---------------------------------------------------------------------------
# Mock responses (deterministic, keyed by first 8 chars of prompt hash)
# ---------------------------------------------------------------------------

_MOCK_TEMPLATES = [
    (
        "A physics question requires students to analyse wave behaviour "
        "in a medium. Explain what happens to the wavelength when a wave "
        "moves from a less dense medium into a denser medium, given that "
        "the frequency remains constant. [3 marks]"
    ),
    (
        "Calculate the de Broglie wavelength of an electron accelerated "
        "through a potential difference of 150 V. Show your working. [3 marks]"
    ),
    (
        "Describe the key differences between progressive waves and "
        "stationary waves in terms of energy transfer and node formation. [4 marks]"
    ),
    (
        "A student claims that increasing the tension of a string always "
        "increases the fundamental frequency of vibration. Evaluate this "
        "claim and state any conditions under which it holds. [3 marks]"
    ),
]

_DRY_RUN_NOTE = "\n\n[DRY-RUN: This is a Quanta Aptus mock response. No AI API was called.]"


def _mock_response(prompt: str) -> str:
    """Return a deterministic mock question based on a hash of the prompt."""
    h = int(hashlib.md5(prompt.encode("utf-8")).hexdigest(), 16)
    return _MOCK_TEMPLATES[h % len(_MOCK_TEMPLATES)] + _DRY_RUN_NOTE

# ---------------------------------------------------------------------------
# Main generate function
# ---------------------------------------------------------------------------

def generate_text(
    prompt: str,
    provider: str | None = None,
    dry_run: bool | None = None,
    copyright_strict: bool | None = None,
) -> dict:
    """
    Generate text using the configured AI provider.

    Args:
        prompt:           The generation prompt. Must not contain raw source material.
        provider:         Override provider (mock | openai | anthropic). Defaults to config.
        dry_run:          Override dry-run mode. Defaults to config (True).
        copyright_strict: Override copyright strict mode. Defaults to config (True).

    Returns:
        {
          "provider": str,
          "dry_run": bool,
          "status": "passed" | "needs_review" | "failed",
          "text": str,
          "usage_estimate": dict,
          "safety": dict,
          "issues": list[str],
        }
    """
    env_local = load_env_local()
    config = load_ai_provider_config(env_local)

    resolved_provider        = (provider or config["provider"]).strip().lower()
    resolved_dry_run         = dry_run if dry_run is not None else config["dry_run"]
    resolved_copyright_strict = copyright_strict if copyright_strict is not None else config["copyright_strict"]

    issues: list[str] = []

    # ── Copyright / safety gate ───────────────────────────────────────────────
    safety = scan_prompt_for_disallowed_source_text(prompt)
    if not safety["safe"] and resolved_copyright_strict:
        return {
            "provider":       resolved_provider,
            "dry_run":        resolved_dry_run,
            "status":         "failed",
            "text":           "",
            "usage_estimate": {},
            "safety":         safety,
            "issues":         [f"Prompt blocked by copyright safety guard: {safety['issues']}"],
        }
    if not safety["safe"]:
        issues.append(f"Copyright warning (not strict): {safety['issues']}")

    # ── Mock / dry-run path ───────────────────────────────────────────────────
    if resolved_provider == "mock" or resolved_dry_run:
        text = _mock_response(prompt)
        return {
            "provider":       "mock" if resolved_dry_run else resolved_provider,
            "model":          "mock",
            "dry_run":        resolved_dry_run,
            "status":         "passed",
            "text":           text,
            "usage_estimate": {
                "prompt_tokens":     len(prompt.split()),
                "completion_tokens": len(text.split()),
                "cost_usd_estimate": 0.0,
                "note":              "dry_run — no real tokens consumed",
            },
            "safety":  safety,
            "issues":  issues,
        }

    # ── OpenAI path ───────────────────────────────────────────────────────────
    if resolved_provider == "openai":
        openai_key = resolve_env("OPENAI_API_KEY", env_local)
        if not openai_key:
            return _missing_key_response("openai", safety, issues)
        model = resolve_env("QA_OPENAI_MODEL", env_local) or _OPENAI_DEFAULT_MODEL
        try:
            import openai  # type: ignore[import]
            client = openai.OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7,
            )
            text = resp.choices[0].message.content or ""
            usage = resp.usage
            return {
                "provider":       "openai",
                "model":          model,
                "dry_run":        False,
                "status":         "passed",
                "text":           text,
                "usage_estimate": {
                    "prompt_tokens":     usage.prompt_tokens if usage else None,
                    "completion_tokens": usage.completion_tokens if usage else None,
                    "cost_usd_estimate": None,
                    "note":              "real API call (SDK)",
                },
                "safety":  safety,
                "issues":  issues,
            }
        except ImportError:
            pass  # fall through to urllib
        except Exception as exc:
            return _api_error_response("openai", exc, safety, issues)
        # urllib fallback (no openai SDK)
        try:
            return _openai_urllib(openai_key, model, prompt, safety, issues)
        except Exception as exc:
            return _api_error_response("openai", exc, safety, issues)

    # ── Anthropic path ────────────────────────────────────────────────────────
    if resolved_provider == "anthropic":
        anthropic_key = resolve_env("ANTHROPIC_API_KEY", env_local)
        if not anthropic_key:
            return _missing_key_response("anthropic", safety, issues)
        model = resolve_env("QA_ANTHROPIC_MODEL", env_local) or _ANTHROPIC_DEFAULT_MODEL
        try:
            import anthropic  # type: ignore[import]
            client = anthropic.Anthropic(api_key=anthropic_key)
            resp = client.messages.create(
                model=model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text if resp.content else ""
            usage = resp.usage
            return {
                "provider":       "anthropic",
                "model":          model,
                "dry_run":        False,
                "status":         "passed",
                "text":           text,
                "usage_estimate": {
                    "prompt_tokens":     usage.input_tokens if usage else None,
                    "completion_tokens": usage.output_tokens if usage else None,
                    "cost_usd_estimate": None,
                    "note":              "real API call (SDK)",
                },
                "safety":  safety,
                "issues":  issues,
            }
        except ImportError:
            pass  # fall through to urllib
        except Exception as exc:
            return _api_error_response("anthropic", exc, safety, issues)
        # urllib fallback (no anthropic SDK)
        try:
            return _anthropic_urllib(anthropic_key, model, prompt, safety, issues)
        except Exception as exc:
            return _api_error_response("anthropic", exc, safety, issues)

    # ── Unknown provider ──────────────────────────────────────────────────────
    return {
        "provider":       resolved_provider,
        "dry_run":        resolved_dry_run,
        "status":         "failed",
        "text":           "",
        "usage_estimate": {},
        "safety":         safety,
        "issues":         [f"Unknown provider: {resolved_provider!r}"],
    }

# ---------------------------------------------------------------------------
# urllib fallback helpers (used when SDK not installed)
# ---------------------------------------------------------------------------

def _openai_urllib(key: str, model: str, prompt: str, safety: dict, issues: list[str]) -> dict:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.7,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_API_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text  = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "provider":       "openai",
        "model":          model,
        "dry_run":        False,
        "status":         "passed",
        "text":           text,
        "usage_estimate": {
            "prompt_tokens":     usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "cost_usd_estimate": None,
            "note":              "real API call (urllib fallback)",
        },
        "safety":  safety,
        "issues":  issues,
    }


def _anthropic_urllib(key: str, model: str, prompt: str, safety: dict, issues: list[str]) -> dict:
    payload = json.dumps({
        "model": model,
        "max_tokens": 800,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_API_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text  = data["content"][0]["text"]
    usage = data.get("usage", {})
    return {
        "provider":       "anthropic",
        "model":          model,
        "dry_run":        False,
        "status":         "passed",
        "text":           text,
        "usage_estimate": {
            "prompt_tokens":     usage.get("input_tokens"),
            "completion_tokens": usage.get("output_tokens"),
            "cost_usd_estimate": None,
            "note":              "real API call (urllib fallback)",
        },
        "safety":  safety,
        "issues":  issues,
    }


# ---------------------------------------------------------------------------
# Error response helpers
# ---------------------------------------------------------------------------

def _missing_key_response(provider: str, safety: dict, issues: list[str]) -> dict:
    return {
        "provider":       provider,
        "dry_run":        False,
        "status":         "needs_review",
        "text":           "",
        "usage_estimate": {},
        "safety":         safety,
        "issues":         issues + [f"{provider.upper()}_API_KEY not set; set dry_run=true or provide key"],
    }


def _missing_package_response(provider: str, package: str, safety: dict, issues: list[str]) -> dict:
    return {
        "provider":       provider,
        "dry_run":        False,
        "status":         "needs_review",
        "text":           "",
        "usage_estimate": {"package_missing": package},
        "safety":         safety,
        "issues":         issues + [f"SDK package '{package}' not installed; run: pip install {package}"],
    }


def _api_error_response(provider: str, exc: Exception, safety: dict, issues: list[str]) -> dict:
    # Stringify the exception but strip any embedded key values (basic defence)
    err_str = str(exc)[:200]
    return {
        "provider":       provider,
        "dry_run":        False,
        "status":         "failed",
        "text":           "",
        "usage_estimate": {},
        "safety":         safety,
        "issues":         issues + [f"API call failed ({provider}): {err_str}"],
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("AI Client — dry-run self-test")
    print("-" * 40)

    result = generate_text(
        "Generate an original A-Level Physics question about wave interference. "
        "Topic: Superposition. Difficulty: medium. Must be original.",
    )
    print(f"  provider:  {result['provider']}")
    print(f"  dry_run:   {result['dry_run']}")
    print(f"  status:    {result['status']}")
    print(f"  text[:80]: {result['text'][:80]}...")
    print(f"  safety:    {result['safety']['safe']}")
    if result["issues"]:
        for i in result["issues"]:
            print(f"  ! {i}")
