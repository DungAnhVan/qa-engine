"""
Gate 52 — Supabase Schema Verifier v1.
Connects to a live Supabase project and verifies:
  - All 19 tables exist in the public schema
  - Seed data counts (subjects >= 22, organizations >= 1, students >= 1)
  - Active Physics package present

Requires:
  .env.local with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set.
  pip install supabase

Will not connect to the network if env is missing.
Will not crash if the supabase package is not installed.

CLI:
    .venv-ingest\\Scripts\\python.exe tools\\supabase\\verify_supabase_schema_v1.py
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

EXPECTED_TABLES = [
    "organizations",
    "profiles",
    "students",
    "parent_student_links",
    "subjects",
    "source_documents",
    "source_pairs",
    "source_items",
    "skill_units",
    "generation_targets",
    "authoring_batches",
    "resources",
    "resource_packages",
    "resource_package_items",
    "attempts",
    "marked_attempts",
    "teacher_reviews",
    "student_reports",
    "audit_events",
]

ACTIVE_PACKAGE_KEY = "cambridge_igcse_physics_0625_resource_package_v2"


# ---------------------------------------------------------------------------
# .env.local parser
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
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def _get(env: dict[str, str], key: str) -> str:
    return env.get(key) or os.environ.get(key, "")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_tables(client) -> list[dict]:
    results = []
    for table in EXPECTED_TABLES:
        try:
            # Use count query — does not fetch rows
            resp = client.table(table).select("*", count="exact").limit(0).execute()
            results.append({"table": table, "exists": True, "error": None})
        except Exception as exc:
            results.append({"table": table, "exists": False, "error": str(exc)[:120]})
    return results


def check_seed_counts(client) -> dict:
    checks: dict[str, dict] = {}

    # subjects
    try:
        r = client.table("subjects").select("*", count="exact").limit(0).execute()
        count = r.count if r.count is not None else 0
        checks["subjects"] = {"count": count, "ok": count >= 22, "min": 22}
    except Exception as exc:
        checks["subjects"] = {"count": None, "ok": False, "error": str(exc)[:120]}

    # organizations
    try:
        r = client.table("organizations").select("*", count="exact").limit(0).execute()
        count = r.count if r.count is not None else 0
        checks["organizations"] = {"count": count, "ok": count >= 1, "min": 1}
    except Exception as exc:
        checks["organizations"] = {"count": None, "ok": False, "error": str(exc)[:120]}

    # students
    try:
        r = client.table("students").select("*", count="exact").limit(0).execute()
        count = r.count if r.count is not None else 0
        checks["students"] = {"count": count, "ok": count >= 1, "min": 1}
    except Exception as exc:
        checks["students"] = {"count": None, "ok": False, "error": str(exc)[:120]}

    # active physics package
    try:
        r = (
            client.table("resource_packages")
            .select("package_key, status")
            .eq("package_key", ACTIVE_PACKAGE_KEY)
            .execute()
        )
        found = len(r.data) > 0
        active = found and r.data[0].get("status") == "active"
        checks["active_physics_package"] = {
            "package_key": ACTIVE_PACKAGE_KEY,
            "found": found,
            "active": active,
            "ok": active,
        }
    except Exception as exc:
        checks["active_physics_package"] = {"ok": False, "error": str(exc)[:120]}

    return checks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print("Quanta Aptus - Supabase Schema Verifier v1")
    print("=" * 60)

    # ── Env check ─────────────────────────────────────────────────────────
    env_vars = _load_env_local(ENV_LOCAL)
    url      = _get(env_vars, "SUPABASE_URL")
    svc_key  = _get(env_vars, "SUPABASE_SERVICE_ROLE_KEY")

    if not url or not svc_key:
        print("\n[MISSING_ENV] SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        print("  1. Create .env.local from .env.example and fill in credentials.")
        print("  2. Run verify_supabase_env_v1.py first to check env vars.")
        print("  Stopping safely — no network connection attempted.")
        _write_report(now_iso, status="missing_env", table_results=[], seed_checks={},
                      url_present=bool(url), key_present=bool(svc_key))
        sys.exit(1)

    # ── Import check ──────────────────────────────────────────────────────
    try:
        from supabase import create_client, Client  # type: ignore
    except ImportError:
        print("\n[MISSING_DEPENDENCY] The 'supabase' Python package is not installed.")
        print("  Install it with:")
        print("    .venv-ingest\\Scripts\\pip.exe install supabase")
        print("  Then re-run this script.")
        _write_report(now_iso, status="missing_dependency", table_results=[], seed_checks={},
                      url_present=True, key_present=True)
        sys.exit(1)

    # ── Connect ───────────────────────────────────────────────────────────
    print(f"\n  Connecting to: {url[:40]}...")
    try:
        client: Client = create_client(url, svc_key)
    except Exception as exc:
        print(f"\n[CONNECTION_ERROR] Could not create Supabase client: {exc}")
        _write_report(now_iso, status="connection_error", table_results=[], seed_checks={},
                      url_present=True, key_present=True, error=str(exc))
        sys.exit(1)

    # ── Table checks ──────────────────────────────────────────────────────
    print("\n  Checking tables...")
    table_results = check_tables(client)
    tables_ok   = all(r["exists"] for r in table_results)
    missing_tbs = [r["table"] for r in table_results if not r["exists"]]

    for r in table_results:
        mark = "OK " if r["exists"] else "MISSING"
        print(f"    [{mark}] {r['table']}")

    # ── Seed checks ───────────────────────────────────────────────────────
    print("\n  Checking seed data...")
    seed_checks = check_seed_counts(client)
    seed_ok     = all(v.get("ok") for v in seed_checks.values())

    for name, chk in seed_checks.items():
        mark = "OK " if chk.get("ok") else "FAIL"
        detail = (
            f"count={chk['count']} (min {chk.get('min', '?')})"
            if "count" in chk
            else f"found={chk.get('found')} active={chk.get('active')}"
        )
        print(f"    [{mark}] {name}: {detail}")

    # ── Status ────────────────────────────────────────────────────────────
    if tables_ok and seed_ok:
        status = "passed"
        print("\n[PASSED] Schema and seed data verified successfully.")
        print("         Ready for Gate 53 — Connect pipeline to Supabase.")
    elif tables_ok:
        status = "seed_incomplete"
        print("\n[SEED_INCOMPLETE] Tables OK but seed data incomplete.")
        print("  Run seed_local_mvp_demo.sql in Supabase SQL Editor (service-role).")
    else:
        status = "tables_missing"
        print(f"\n[TABLES_MISSING] {len(missing_tbs)} table(s) not found: {missing_tbs}")
        print("  Apply migrations in order:")
        print("    1. supabase/migrations/000001_init_quanta_aptus_schema.sql")
        print("    2. supabase/migrations/000002_rls_policies.sql")
        print("    3. supabase/seed/seed_local_mvp_demo.sql")

    _write_report(
        now_iso, status=status,
        table_results=table_results,
        seed_checks=seed_checks,
        url_present=True, key_present=True,
    )
    sys.exit(0 if status == "passed" else 1)


def _write_report(
    now_iso: str,
    status: str,
    table_results: list[dict],
    seed_checks: dict,
    url_present: bool = False,
    key_present: bool = False,
    error: str | None = None,
) -> None:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "supabase_schema_verify_report_v1.json"

    tables_ok   = all(r.get("exists") for r in table_results) if table_results else False
    missing_tbs = [r["table"] for r in table_results if not r.get("exists")]

    report = {
        "report_id":     "quanta_aptus_supabase_schema_verify_v1",
        "gate":          "52",
        "created_at":    now_iso,
        "status":        status,
        "url_present":   url_present,
        "key_present":   key_present,
        "tables_ok":     tables_ok,
        "missing_tables": missing_tbs,
        "table_results": table_results,
        "seed_checks":   seed_checks,
        "error":         error,
    }

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  report -> {report_path}")


if __name__ == "__main__":
    main()
