"""
Gate 52 — Supabase Environment Verifier v1.
Reads .env.local (if present), checks required Supabase env vars,
masks key values, and writes a report to data/diagnostics/.

Does NOT connect to the network.
Does NOT print full keys.

CLI:
    .venv-ingest\\Scripts\\python.exe tools\\supabase\\verify_supabase_env_v1.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL    = PROJECT_ROOT / ".env.local"
DIAG_DIR     = PROJECT_ROOT / "data" / "diagnostics"

REQUIRED_VARS = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
]

OPTIONAL_VARS = [
    "SUPABASE_DB_PASSWORD",
    "SUPABASE_PROJECT_REF",
]


# ---------------------------------------------------------------------------
# .env.local parser (minimal, no dependency on python-dotenv)
# ---------------------------------------------------------------------------

def _load_env_local(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key  = key.strip()
        val  = val.strip().strip('"').strip("'")
        env[key] = val
    return env


def _mask(value: str) -> str:
    """Show first 6 + ... + last 4 characters. Never show full key."""
    if len(value) <= 12:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def _check_var(name: str, env: dict[str, str]) -> dict:
    val = env.get(name) or os.environ.get(name, "")
    present = bool(val)
    return {
        "name":    name,
        "present": present,
        "masked":  _mask(val) if present else None,
        "source":  (
            "env.local" if name in env and env[name]
            else "os.environ" if os.environ.get(name)
            else "missing"
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso  = datetime.now(timezone.utc).isoformat()
    env_vars = _load_env_local(ENV_LOCAL)

    env_local_found = ENV_LOCAL.exists()

    print("=" * 60)
    print("Quanta Aptus - Supabase Env Verifier v1")
    print(f"  .env.local found: {env_local_found}")
    print("=" * 60)

    results: list[dict] = []
    all_required_present = True

    for name in REQUIRED_VARS:
        r = _check_var(name, env_vars)
        results.append({**r, "required": True})
        status_str = "OK " if r["present"] else "MISSING"
        masked_str = f" ({r['masked']})" if r["masked"] else ""
        print(f"  [{status_str}] {name}{masked_str}")
        if not r["present"]:
            all_required_present = False

    for name in OPTIONAL_VARS:
        r = _check_var(name, env_vars)
        results.append({**r, "required": False})
        status_str = "OK " if r["present"] else "not set"
        masked_str = f" ({r['masked']})" if r["masked"] else ""
        print(f"  [{status_str}] {name}{masked_str}  (optional)")

    if all_required_present:
        status = "env_ok"
        print("\n[ENV_OK] All required env vars are present.")
        print("         Run verify_supabase_schema_v1.py to check the live schema.")
    else:
        status = "missing_env"
        print("\n[MISSING_ENV] One or more required env vars are missing.")
        print("  Steps to fix:")
        print("  1. Create a Supabase project at https://supabase.com")
        print("  2. Copy .env.example to .env.local")
        print("  3. Fill in SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY")
        print("  4. Re-run this script.")
        print("  WARNING: Never commit .env.local to git.")

    # ── Write report ───────────────────────────────────────────────────────
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "supabase_env_check_report_v1.json"

    report = {
        "report_id":         "quanta_aptus_supabase_env_check_v1",
        "gate":              "52",
        "created_at":        now_iso,
        "status":            status,
        "env_local_found":   env_local_found,
        "all_required_present": all_required_present,
        "vars":              results,
        "note":              "Masked values shown only. Full keys never logged.",
    }

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  report -> {report_path}")

    sys.exit(0 if all_required_present else 1)


if __name__ == "__main__":
    main()
