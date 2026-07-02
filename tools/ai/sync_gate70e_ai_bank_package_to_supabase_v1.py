"""
Gate 70E -- Sync AI Bank Package to Supabase v1

Dry-run by default. Execute only with explicit flags + env.

Security:
  - Service role key from .env.local only — NEVER written to output.
  - Key masked as first6...last4 in all console output.
  - No AI API calls. No schema changes. No deletes.
  - Package status=draft (active=false) — no active switch in this gate.

Usage:
  Dry-run (default, safe):
    .venv-ingest\\Scripts\\python.exe tools\\ai\\sync_gate70e_ai_bank_package_to_supabase_v1.py

  Execute (writes to Supabase):
    .venv-ingest\\Scripts\\python.exe tools\\ai\\sync_gate70e_ai_bank_package_to_supabase_v1.py
        --execute --confirm SYNC_GATE70E_AI_BANK_PACKAGE

Output:
  data/diagnostics/gate70e_ai_bank_supabase_sync_execute_report_v1.json
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

PLAN_FILE   = ROOT / "data" / "ai" / "supabase_sync" / "gate70e_ai_bank_supabase_sync_plan_v1.json"
PUBLISH_PKG = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1" / "publish_package_v1.json"
REPORT_FILE = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_sync_execute_report_v1.json"
TIMEOUT     = 20
CONFIRM_TOKEN = "SYNC_GATE70E_AI_BANK_PACKAGE"

COPYRIGHT_PATTERNS = ["UCLES", "Cambridge International", "Cambridge Assessment",
                      "Question Answer Marks", "original_raw_block", "data/raw/"]


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


def resolve_env(key: str, env_local: dict) -> str | None:
    return os.environ.get(key) or env_local.get(key) or None


def mask_key(val: str | None) -> str:
    if not val:
        return "(not set)"
    return val[:6] + "..." + val[-4:] if len(val) >= 10 else "***"


def _headers(key: str, prefer: str = "") -> dict:
    h = {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def sb_get(url_base: str, key: str, table: str, query: str) -> tuple[int, list, str | None]:
    url = f"{url_base}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, headers=_headers(key))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read(2048).decode(errors="replace")
        return e.code, [], f"HTTP {e.code}: {body[:300]}"
    except Exception as e:
        return 0, [], str(e)[:200]


def sb_upsert(url_base: str, key: str, table: str, payload: dict,
              on_conflict: str) -> tuple[int, list, str | None]:
    url  = f"{url_base}/rest/v1/{table}"
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data, method="POST",
        headers=_headers(key, f"resolution=merge-duplicates,return=representation,on_conflict={on_conflict}"),
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read(2048).decode(errors="replace")
        return e.code, [], f"HTTP {e.code}: {body[:300]}"
    except Exception as e:
        return 0, [], str(e)[:200]


def _check_payload_safety(payload: dict) -> list[str]:
    raw    = json.dumps(payload)
    issues = []
    if any(p in raw for p in COPYRIGHT_PATTERNS):
        issues.append("copyright pattern in payload")
    for bad in ["service_role", "SUPABASE_SERVICE_ROLE", "NEXT_PUBLIC_SUPABASE_SERVICE"]:
        if bad in raw:
            issues.append(f"secret pattern '{bad}' in payload")
    return issues


def execute_sync(plan: dict, supabase_url: str, key: str) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    issues: list[str] = []
    resources_upserted = packages_upserted = items_upserted = 0
    subject_id: str | None = None

    pkg = json.loads(PUBLISH_PKG.read_text(encoding="utf-8"))
    res_map = {r["resource_id"]: r for r in pkg.get("resources", [])}

    for op in plan.get("operations", []):
        op_type = op.get("op")

        if op_type == "upsert_subject_if_needed":
            slug = op["subject_slug"]
            enc  = urllib.parse.quote(slug, safe="")
            sc, rows, err = sb_get(supabase_url, key, "subjects",
                                   f"subject_slug=eq.{enc}&select=id,subject_slug")
            if err:
                issues.append(f"subject lookup: {err}")
                continue
            if rows:
                subject_id = rows[0]["id"]
                print(f"  subject '{slug}' exists id={str(subject_id)[:8]}...")
            else:
                sc, result, err = sb_upsert(supabase_url, key, "subjects", op["fields"], "subject_slug")
                if err:
                    issues.append(f"subject upsert: {err}")
                else:
                    subject_id = result[0]["id"] if result else None
                    print(f"  upserted subject '{slug}'")

        elif op_type == "upsert_resource":
            rid = op["resource_key"]
            row = op["fields"].copy()
            if subject_id:
                row["subject_id"] = subject_id
            safety_issues = _check_payload_safety(row)
            if safety_issues:
                issues.extend(safety_issues)
                print(f"  [SKIP] resource '{rid}': safety issues")
                continue
            sc, result, err = sb_upsert(supabase_url, key, "resources", row, "resource_key")
            if err:
                issues.append(f"resource upsert ({rid}): {err}")
                print(f"  [ERROR] resource '{rid}': {err[:100]}")
            else:
                resources_upserted += 1
                print(f"  upserted resource '{rid}'")

        elif op_type == "upsert_resource_package":
            pkg_key = op["package_key"]
            row     = op["fields"].copy()
            if subject_id:
                row["subject_id"] = subject_id
            row["status"] = "draft"  # NEVER set active here
            sc, result, err = sb_upsert(supabase_url, key, "resource_packages", row, "package_key")
            if err:
                issues.append(f"package upsert: {err}")
                print(f"  [ERROR] package '{pkg_key}': {err[:100]}")
            else:
                packages_upserted += 1
                print(f"  upserted package '{pkg_key}' (status=draft, active=false)")

        elif op_type == "upsert_resource_package_item":
            res_key = op["resource_key"]
            pkg_key = op["package_key"]

            enc_r = urllib.parse.quote(res_key, safe="")
            sc, rows, err = sb_get(supabase_url, key, "resources",
                                   f"resource_key=eq.{enc_r}&select=id")
            if err or not rows:
                issues.append(f"resource lookup failed '{res_key}': {err or 'not found'}")
                continue
            res_uuid = rows[0]["id"]

            enc_p = urllib.parse.quote(pkg_key, safe="")
            sc, rows, err = sb_get(supabase_url, key, "resource_packages",
                                   f"package_key=eq.{enc_p}&select=id")
            if err or not rows:
                issues.append(f"package lookup failed '{pkg_key}': {err or 'not found'}")
                continue
            pkg_uuid = rows[0]["id"]

            row = {
                "package_id":  pkg_uuid,
                "resource_id": res_uuid,
                "sort_order":  op["fields"]["sort_order"],
                "visibility":  op["fields"]["visibility"],
            }
            sc, result, err = sb_upsert(supabase_url, key, "resource_package_items",
                                        row, "package_id,resource_id")
            if err:
                issues.append(f"package_item upsert ({res_key}): {err}")
                print(f"  [ERROR] item '{res_key}': {err[:100]}")
            else:
                items_upserted += 1
                print(f"  upserted package_item '{res_key}'")

    return {
        "resources_upserted": resources_upserted,
        "packages_upserted":  packages_upserted,
        "items_upserted":     items_upserted,
        "issues":             issues,
        "executed_at":        now,
    }


def write_report(now, dry_run, execute, confirm_ok, supabase_write,
                 res_up, pkg_up, items_up, issues):
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    status = "passed" if not issues else "needs_review"
    report = {
        "gate":                              "70E",
        "status":                            status,
        "dry_run":                           dry_run,
        "execute":                           execute,
        "confirm_ok":                        confirm_ok,
        "supabase_write_performed":          supabase_write,
        "resources_upserted":                res_up,
        "packages_upserted":                 pkg_up,
        "items_upserted":                    items_up,
        "target_active":                     False,
        "active_switch_performed":           False,
        "existing_active_package_preserved": True,
        "ai_api_called":                     False,
        "secrets_exposed":                   False,
        "issues":                            issues,
        "generated_at":                      now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Gate 70E — Sync AI Bank Package to Supabase v1")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()

    dry_run    = not args.execute
    confirm_ok = args.confirm == CONFIRM_TOKEN
    execute    = args.execute and confirm_ok
    now        = datetime.datetime.now(datetime.timezone.utc).isoformat()

    print("Gate 70E -- Sync AI Bank Package to Supabase v1")
    print("=" * 60)
    print(f"dry_run: {dry_run}")
    print(f"execute: {execute}")
    if args.execute and not confirm_ok:
        print(f"ERROR: --execute requires --confirm {CONFIRM_TOKEN}")

    if not PLAN_FILE.exists():
        print("ERROR: sync plan not found. Run build_gate70e_ai_bank_supabase_sync_plan_v1.py first.")
        write_report(now, dry_run, execute, confirm_ok, False, 0, 0, 0,
                     ["sync plan not found"])
        sys.exit(1)

    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    print(f"\nSync plan:      {plan.get('sync_plan_id')}")
    print(f"Target package: {plan.get('target_package_key')}")
    print(f"Resources:      {plan.get('resource_count')}")
    print(f"Operations:     {plan.get('operation_count')}")
    print(f"dry_run_default: {plan.get('dry_run_default')}")
    print(f"active_switch_allowed: {plan.get('active_switch_allowed')}")

    print("\nPlanned operations:")
    for op in plan.get("operations", []):
        marker = op.get("resource_key") or op.get("package_key") or op.get("subject_slug", "")
        print(f"  [{op['op']}] {marker}")

    res_up = pkg_up = items_up = 0
    issues: list[str] = []

    if execute:
        print("\n[EXECUTE MODE]")
        env_local    = load_env_local()
        supabase_url = resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
        service_key  = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)

        if not supabase_url:
            issues.append("NEXT_PUBLIC_SUPABASE_URL not set")
        if not service_key:
            issues.append("SUPABASE_SERVICE_ROLE_KEY not set")

        if issues:
            print(f"  ERROR: missing env: {issues}")
            write_report(now, dry_run, execute, confirm_ok, False,
                         0, 0, 0, issues)
            sys.exit(1)

        print(f"  Supabase URL: {supabase_url}")
        print(f"  Service key:  {mask_key(service_key)}")

        result  = execute_sync(plan, supabase_url, service_key)
        res_up  = result["resources_upserted"]
        pkg_up  = result["packages_upserted"]
        items_up = result["items_upserted"]
        issues.extend(result["issues"])
        supabase_write = (res_up + pkg_up + items_up) > 0
    else:
        print("\n[DRY-RUN MODE] — No Supabase writes performed.")
        supabase_write = False

    write_report(now, dry_run, execute, confirm_ok, supabase_write,
                 res_up, pkg_up, items_up, issues)

    status = "passed" if not issues else "needs_review"
    print(f"\nStatus:                    {status}")
    print(f"supabase_write_performed:  {supabase_write}")
    print(f"resources_upserted:        {res_up}")
    print(f"packages_upserted:         {pkg_up}")
    print(f"items_upserted:            {items_up}")
    print(f"active_switch_performed:   false")
    print(f"target_active:             false")
    print(f"Report: {REPORT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
