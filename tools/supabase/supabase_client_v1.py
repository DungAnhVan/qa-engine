"""
Supabase Client Helper v1 — Quanta Aptus Gate 53A.
Provides a service-role Supabase client loaded from .env.local.

Never prints full keys.
Does NOT connect on import — only on explicit get_supabase_service_client() call.

Usage:
    from supabase_client_v1 import get_supabase_service_client
    client = get_supabase_service_client()
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ENV_PATH = PROJECT_ROOT / ".env.local"


def mask_secret(value: str) -> str:
    """Return a masked representation. Never reveals the full key."""
    if not value:
        return "(empty)"
    if len(value) <= 12:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def load_env_file(path: str | Path | None = None) -> dict[str, str]:
    """
    Parse a .env-style file and return key/value pairs.
    Does not override existing os.environ values.
    """
    env_path = Path(path) if path else _DEFAULT_ENV_PATH
    result: dict[str, str] = {}
    if not env_path.exists():
        return result
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def _resolve(key: str, env: dict[str, str]) -> str:
    return env.get(key) or os.environ.get(key, "")


def get_supabase_service_client(env_path: str | Path | None = None):
    """
    Build and return a Supabase client authenticated with the service role key.

    Raises SystemExit with a clear message if:
    - The supabase package is not installed.
    - Required env vars are missing.
    """
    try:
        from supabase import create_client, Client  # type: ignore
    except ImportError:
        raise SystemExit(
            "\n[MISSING_DEPENDENCY] The 'supabase' Python package is not installed.\n"
            "  Install it with:\n"
            "    .venv-ingest\\Scripts\\pip.exe install supabase\n"
        )

    env = load_env_file(env_path)
    url = _resolve("SUPABASE_URL", env)
    key = _resolve("SUPABASE_SERVICE_ROLE_KEY", env)

    if not url:
        raise SystemExit(
            "\n[MISSING_ENV] SUPABASE_URL not set.\n"
            "  Copy .env.example to .env.local and fill in the values.\n"
            "  Then re-run: verify_supabase_env_v1.py\n"
        )
    if not key:
        raise SystemExit(
            "\n[MISSING_ENV] SUPABASE_SERVICE_ROLE_KEY not set.\n"
            "  Copy .env.example to .env.local and fill in the values.\n"
            "  WARNING: Never commit .env.local to git.\n"
        )

    client: Client = create_client(url, key)
    return client, url
