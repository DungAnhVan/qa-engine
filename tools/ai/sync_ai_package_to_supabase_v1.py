"""
Gate 69G -- Sync AI Package to Supabase v1

Reads the sync plan produced by build_ai_supabase_sync_plan_v1.py and either:
  - (default) dry-runs: prints planned operations, writes report, NO Supabase writes
  - (--execute --confirm SYNC_AI_PACKAGE) executes upserts via Supabase REST API

Security:
  - Service role key loaded from .env.local — NEVER written to any output file.
  - Key masked as first6...last4 in all console output.
  - No AI API calls. No schema changes. No deletes.
  - active=false (draft) by default; active switch requires separate tool.

Usage:
  Dry run (default, safe):
    .venv-ingest\\Scripts\\python.exe tools\\ai\\sync_ai_package_to_supabase_v1.py

  Execute (writes to Supabase):
    .venv-ingest\\Scripts\\python.exe tools\\ai\\sync_ai_package_to_supabase_v1.py \\
        --execute --confirm SYNC_AI_PACKAGE

Output:
  data/diagnostics/ai_supabase_sync_execute_report_v1.json
"""

import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PLAN_FILE   = ROOT / "data" / "ai" / "supabase_sync" / "ai_supabase_sync_plan_v1.json"
PUBLISH_PKG = ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "publish_package_v1.json"
REPORT_FILE = ROOT / "data" / "diagnostics" / "ai_supabase_sync_execute_report_v1.json"

TIMEOUT = 20

COPYRIGHT_PATTERNS = ["UCLES", "Cambridge International", "Cambridge Assessment",
                      "Question Answer Marks", "original_raw_block", "data/raw/"]


# ---------------------------------------------------------------------------
# Env helpers
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


def mask_key(val: str | None) -> str:
    if not val:
        return "(not set)"
    if len(val) < 10:
        return "***"
    return val[:6] + "..." + val[-4:]


# ---------------------------------------------------------------------------
# HTTP helpers (Supabase REST API via service role — server-side only)
# ---------------------------------------------------------------------------

def _headers(service_role_key: str, prefer: str = "") -> dict:
    h = {
        "apikey":        service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def sb_get(supabase_url: str, key: str, table: str, query: str) -> tuple[int, list, str | None]:
    url = f"{supabase_url}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, headers=_headers(key))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read(2048).decode(errors="replace")
        return e.code, [], f"HTTP {e.code}: {body[:300]}"
    except Exception as e:
        return 0, [], str(e)[:200]


def sb_upsert(supabase_url: str, key: str, table: str, payload: dict | list,
              on_conflict: str) -> tuple[int, list, str | None]:
    url  = f"{supabase_url}/rest/v1/{table}"
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data, method="POST",
        headers=_headers(key, prefer=f"resolution=merge-duplicates,return=representation,on_conflict={on_conflict}"),
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read(2048).decode(errors="replace")
        return e.code, [], f"HTTP {e.code}: {body[:300]}"
    except Exception as e:
        return 0, [], str(e)[:200]


# ---------------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------------

def _has_copyright(text: str) -> bool:
    return any(p in text for p in COPYRIGHT_PATTERNS)


def _check_payload_safety(payload: dict) -> list[str]:
    raw = json.dumps(payload)
    issues: list[str] = []
    if _has_copyright(raw):
        issues.append("copyright pattern detected in payload")
    # Service role key should never appear in payload
    for bad in ["service_role", "SUPABASE_SERVICE_ROLE", "NEXT_PUBLIC_SUPABASE_SERVICE"]:
        if bad in raw:
            issues.append(f"potential secret pattern '{bad}' in payload")
    return issues


# ---------------------------------------------------------------------------
# Sync executor
# ---------------------------------------------------------------------------

def execute_sync(plan: dict, supabase_url: str, key: str) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    issues: list[str] = []
    resources_upserted = 0
    packages_upserted  = 0
    items_upserted     = 0
    subject_id: str | None = None

    # Load full published package for resource details
    pkg = json.loads(PUBLISH_PKG.read_text(encoding="utf-8"))
    resources = pkg.get("resources", [])

    # Resource map by resource_key for quick lookup
    res_map = {r["resource_id"]: r for r in resources}

    for op in plan.get("operations", []):
        op_type = op.get("op")

        # ── upsert_subject_if_needed ─────────────────────────────────────
        if op_type == "upsert_subject_if_needed":
            slug = op["subject_slug"]
            encoded = urllib.parse.quote(slug, safe="")
            sc, rows, err = sb_get(supabase_url, key, "subjects",
                                   f"subject_slug=eq.{encoded}&select=id,subject_slug")
            if err:
                issues.append(f"subject lookup error: {err}")
                continue
            if rows:
                subject_id = rows[0]["id"]
                print(f"    subject '{slug}' already exists (id={subject_id[:8]}...)")
            else:
                row = op["fields"].copy()
                sc, result, err = sb_upsert(supabase_url, key, "subjects", row, "subject_slug")
                if err:
                    issues.append(f"subject upsert error: {err}")
                else:
                    subject_id = result[0]["id"] if result else None
                    print(f"    upserted subject '{slug}' id={str(subject_id)[:8] if subject_id else '?'}...")

        # ── upsert_resource ──────────────────────────────────────────────
        elif op_type == "upsert_resource":
            rid = op["resource_key"]
            r   = res_map.get(rid, {})
            row = op["fields"].copy()
            if subject_id:
                row["subject_id"] = subject_id

            safety_issues = _check_payload_safety(row)
            if safety_issues:
                issues.extend(safety_issues)
                print(f"    [SKIP] resource '{rid}': safety issues")
                continue

            sc, result, err = sb_upsert(supabase_url, key, "resources", row, "resource_key")
            if err:
                issues.append(f"resource upsert error ({rid}): {err}")
                print(f"    [ERROR] resource '{rid}': {err[:100]}")
            else:
                resources_upserted += 1
                print(f"    upserted resource '{rid}'")

        # ── upsert_resource_package ──────────────────────────────────────
        elif op_type == "upsert_resource_package":
            pkg_key = op["package_key"]
            row     = op["fields"].copy()
            if subject_id:
                row["subject_id"] = subject_id
            # NEVER set status=active here
            row["status"] = "draft"

            sc, result, err = sb_upsert(supabase_url, key, "resource_packages", row, "package_key")
            if err:
                issues.append(f"package upsert error: {err}")
                print(f"    [ERROR] package '{pkg_key}': {err[:100]}")
            else:
                packages_upserted += 1
                print(f"    upserted package '{pkg_key}' (status=draft)")

        # ── upsert_resource_package_item ─────────────────────────────────
        elif op_type == "upsert_resource_package_item":
            res_key = op["resource_key"]
            pkg_key = op["package_key"]

            # Look up resource UUID
            encoded_r = urllib.parse.quote(res_key, safe="")
            sc, res_rows, err = sb_get(supabase_url, key, "resources",
                                       f"resource_key=eq.{encoded_r}&select=id")
            if err or not res_rows:
                issues.append(f"resource_id lookup failed for '{res_key}': {err or 'not found'}")
                continue
            res_uuid = res_rows[0]["id"]

            # Look up package UUID
            encoded_p = urllib.parse.quote(pkg_key, safe="")
            sc, pkg_rows, err = sb_get(supabase_url, key, "resource_packages",
                                       f"package_key=eq.{encoded_p}&select=id")
            if err or not pkg_rows:
                issues.append(f"package_id lookup failed for '{pkg_key}': {err or 'not found'}")
                continue
            pkg_uuid = pkg_rows[0]["id"]

            row = {
                "package_id":  pkg_uuid,
                "resource_id": res_uuid,
                "sort_order":  op["fields"]["sort_order"],
                "visibility":  op["fields"]["visibility"],
            }
            sc, result, err = sb_upsert(supabase_url, key, "resource_package_items",
                                         row, "package_id,resource_id")
            if err:
                issues.append(f"package_item upsert error ({res_key}): {err}")
                print(f"    [ERROR] package_item '{res_key}': {err[:100]}")
            else:
                items_upserted += 1
                print(f"    upserted package_item '{res_key}'")

    return {
        "resources_upserted": resources_upserted,
        "packages_upserted":  packages_upserted,
        "items_upserted":     items_upserted,
        "issues":             issues,
        "executed_at":        now,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Gate 69G — Sync AI Package to Supabase v1")
    parser.add_argument("--execute", action="store_true",
                        help="Execute upserts (default: dry-run)")
    parser.add_argument("--confirm", default="",
                        help="Required: SYNC_AI_PACKAGE (when --execute)")
    args = parser.parse_args()

    dry_run    = not args.execute
    confirm_ok = args.confirm == "SYNC_AI_PACKAGE"
    execute    = args.execute and confirm_ok

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print("Gate 69G -- Sync AI Package to Supabase v1")
    print("=" * 55)
    print(f"  dry_run: {dry_run}")
    print(f"  execute: {execute}")
    if args.execute and not confirm_ok:
        print("  ERROR: --execute requires --confirm SYNC_AI_PACKAGE")

    # Load plan
    if not PLAN_FILE.exists():
        print("ERROR: sync plan not found. Run build_ai_supabase_sync_plan_v1.py first.")
        _write_report(now, dry_run, execute, confirm_ok, False,
                      0, 0, 0, ["sync plan not found"])
        raise SystemExit(1)

    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))

    print(f"\nSync plan: {plan['sync_plan_id']}")
    print(f"  package_id:     {plan['package_id']}")
    print(f"  resource_count: {plan['resource_count']}")
    print(f"  operations:     {plan['operation_count']}")
    print(f"  dry_run_default: {plan['dry_run_default']}")
    print(f"  active_switch:  {plan['active_switch_default']}")

    print("\nPlanned operations:")
    for op in plan.get("operations", []):
        marker = op.get("resource_key") or op.get("package_key") or op.get("subject_slug", "")
        print(f"  [{op['op']}] {marker}")

    resources_upserted = 0
    packages_upserted  = 0
    items_upserted     = 0
    issues: list[str]  = []

    if execute:
        print("\n[EXECUTE MODE]")
        env_local = load_env_local()
        supabase_url = resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
        service_key  = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)

        if not supabase_url:
            issues.append("NEXT_PUBLIC_SUPABASE_URL not set")
        if not service_key:
            issues.append("SUPABASE_SERVICE_ROLE_KEY not set")

        if issues:
            print(f"  ERROR: missing env: {issues}")
            _write_report(now, dry_run, execute, confirm_ok, False,
                          0, 0, 0, issues)
            raise SystemExit(1)

        print(f"  Supabase URL: {supabase_url}")
        print(f"  Service key:  {mask_key(service_key)}")

        result = execute_sync(plan, supabase_url, service_key)
        resources_upserted = result["resources_upserted"]
        packages_upserted  = result["packages_upserted"]
        items_upserted     = result["items_upserted"]
        issues.extend(result["issues"])

        supabase_write_performed = (resources_upserted + packages_upserted + items_upserted) > 0
    else:
        print("\n[DRY-RUN MODE] — No Supabase writes.")
        supabase_write_performed = False

    status = "passed" if not issues else "needs_review"
    _write_report(now, dry_run, execute, confirm_ok, supabase_write_performed,
                  resources_upserted, packages_upserted, items_upserted, issues)

    print(f"\nStatus:                    {status}")
    print(f"dry_run:                   {dry_run}")
    print(f"supabase_write_performed:  {supabase_write_performed}")
    print(f"resources_upserted:        {resources_upserted}")
    print(f"packages_upserted:         {packages_upserted}")
    print(f"items_upserted:            {items_upserted}")
    print(f"active_switch_performed:   false")
    print(f"Report: {REPORT_FILE}")


def _write_report(now, dry_run, execute, confirm_ok, supabase_write_performed,
                  res_up, pkg_up, items_up, issues):
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)
    status = "passed" if not issues else "needs_review"
    report = {
        "gate":                             "69G",
        "status":                           status,
        "dry_run":                          dry_run,
        "execute":                          execute,
        "confirm_ok":                       confirm_ok,
        "supabase_write_performed":         supabase_write_performed,
        "resources_upserted":               res_up,
        "packages_upserted":                pkg_up,
        "items_upserted":                   items_up,
        "active_switch_performed":          False,
        "existing_active_package_preserved": True,
        "secrets_exposed":                  False,
        "issues":                           issues,
        "generated_at":                     now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
