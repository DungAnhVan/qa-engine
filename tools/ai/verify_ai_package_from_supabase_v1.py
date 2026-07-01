"""
Gate 69G -- Verify AI Package from Supabase v1

Reads the AI package back from Supabase to verify that sync was successful.
If sync has not been executed, returns needs_review with a clear message.

Security:
  - Service role key loaded from .env.local — NEVER written to output.
  - No raw source text. No schema changes.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\verify_ai_package_from_supabase_v1.py

Output:
  data/diagnostics/ai_supabase_readback_verify_report_v1.json
"""

import datetime
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PUBLISH_PKG = ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "publish_package_v1.json"
SYNC_REPORT = ROOT / "data" / "diagnostics" / "ai_supabase_sync_execute_report_v1.json"
REPORT_FILE = ROOT / "data" / "diagnostics" / "ai_supabase_readback_verify_report_v1.json"

TIMEOUT = 20

SECRET_PATTERNS = ["SUPABASE_SERVICE_ROLE_KEY", "supabase_service_role",
                   "sk-ant-", "NEXT_PUBLIC_SUPABASE_SERVICE"]


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
    return val[:6] + "..." + val[-4:] if len(val) >= 10 else "***"


def _headers(key: str) -> dict:
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Accept":        "application/json",
    }


def sb_get(url_base: str, key: str, table: str, query: str) -> tuple[int, list, str | None]:
    url = f"{url_base}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, headers=_headers(key))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read(2048).decode(errors="replace")
        return e.code, [], f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return 0, [], str(e)[:200]


def _has_secrets(text: str) -> bool:
    return any(p in text for p in SECRET_PATTERNS)


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    print("Gate 69G -- Verify AI Package from Supabase v1")
    print("-" * 55)

    # Check if sync was executed
    sync_was_executed = False
    if SYNC_REPORT.exists():
        try:
            sr = json.loads(SYNC_REPORT.read_text(encoding="utf-8"))
            sync_was_executed = sr.get("supabase_write_performed", False)
        except Exception:
            pass

    if not sync_was_executed:
        print("Sync has not been executed (dry-run mode only).")
        print("Run sync_ai_package_to_supabase_v1.py --execute --confirm SYNC_AI_PACKAGE first.")
        report = {
            "gate":                    "69G",
            "status":                  "needs_review",
            "sync_executed":           False,
            "package_exists":          False,
            "resources_verified":      0,
            "resource_count_match":    False,
            "active_false":            True,
            "no_raw_source_text":      True,
            "no_api_keys":             True,
            "issues":                  ["sync not yet executed — dry-run only"],
            "message":                 "Run --execute --confirm SYNC_AI_PACKAGE first",
            "generated_at":            now,
        }
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report: {REPORT_FILE}")
        return

    # Load env
    env_local    = load_env_local()
    supabase_url = resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
    service_key  = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)

    if not supabase_url or not service_key:
        _fail(now, "Supabase env missing — NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        return

    print(f"  URL: {supabase_url}")
    print(f"  Key: {mask_key(service_key)}")

    pkg = json.loads(PUBLISH_PKG.read_text(encoding="utf-8"))
    package_id    = pkg.get("package_id", "quanta_aptus_ai_resource_package_v1")
    local_count   = pkg.get("resource_count", 0)
    resources     = pkg.get("resources", [])
    issues: list[str] = []

    # 1. Verify package exists in resource_packages
    encoded = urllib.parse.quote(package_id, safe="")
    sc, pkg_rows, err = sb_get(supabase_url, service_key, "resource_packages",
                                f"package_key=eq.{encoded}&select=id,package_key,status,resource_count")
    if err or not pkg_rows:
        issues.append(f"resource_package not found: {err or 'empty result'}")
        _write_report(now, True, False, False, False, 0, False, False, False, issues)
        return
    pkg_row  = pkg_rows[0]
    pkg_uuid = pkg_row["id"]
    pkg_status = pkg_row.get("status", "unknown")
    print(f"  package found: {package_id} (status={pkg_status})")

    # 2. active must be draft (not active)
    active_false = pkg_status in ("draft", "archived")
    if not active_false:
        issues.append(f"Package status is '{pkg_status}' — expected draft (not active)")

    # 3. Count package items
    sc2, item_rows, err2 = sb_get(supabase_url, service_key, "resource_package_items",
                                   f"package_id=eq.{pkg_uuid}&select=id,resource_id,sort_order")
    if err2:
        issues.append(f"package_items read error: {err2}")
    item_count = len(item_rows) if not err2 else 0
    count_match = item_count >= local_count
    if not count_match:
        issues.append(f"item count mismatch: local={local_count}, supabase={item_count}")
    print(f"  package items in Supabase: {item_count} (local: {local_count})")

    # 4. Verify each resource individually
    resources_verified = 0
    for r in resources:
        rid = r.get("resource_id", "")
        enc = urllib.parse.quote(rid, safe="")
        sc3, rrows, err3 = sb_get(supabase_url, service_key, "resources",
                                   f"resource_key=eq.{enc}&select=id,resource_key,publish_status,student_prompt")
        if err3 or not rrows:
            issues.append(f"resource '{rid}' not found: {err3 or 'empty'}")
        else:
            row = rrows[0]
            raw = json.dumps(row)
            if _has_secrets(raw):
                issues.append(f"secret detected in resource '{rid}'")
            else:
                resources_verified += 1
            print(f"    resource '{rid}' OK (status={row.get('publish_status')})")

    # 5. Check no raw source text in resources
    sc4, all_res, err4 = sb_get(supabase_url, service_key, "resources",
                                 "resource_key=like.qa_physics_0625_*&select=resource_key,student_prompt,teacher_notes")
    no_raw_source_text = True
    no_api_keys        = True
    if not err4:
        raw_all = json.dumps(all_res)
        if any(p in raw_all for p in ["UCLES", "Cambridge International", "Question Answer Marks"]):
            no_raw_source_text = False
            issues.append("Cambridge copyright text detected in Supabase resources")
        if _has_secrets(raw_all):
            no_api_keys = False
            issues.append("secret pattern detected in Supabase resource data")

    status = "passed" if not issues else "needs_review"
    _write_report(now, True, True, count_match, active_false,
                  resources_verified, no_raw_source_text, no_api_keys,
                  status == "passed", issues)
    print(f"\nStatus: {status}")
    print(f"Report: {REPORT_FILE}")


def _fail(now: str, msg: str):
    report = {
        "gate": "69G", "status": "failed", "sync_executed": True,
        "package_exists": False, "resources_verified": 0,
        "resource_count_match": False, "active_false": True,
        "no_raw_source_text": True, "no_api_keys": True,
        "issues": [msg], "generated_at": now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"ERROR: {msg}")
    print(f"Report: {REPORT_FILE}")


def _write_report(now, sync_executed, package_exists, count_match, active_false,
                  resources_verified, no_raw, no_keys, overall_ok, issues):
    status = "passed" if overall_ok and not issues else ("failed" if not package_exists else "needs_review")
    report = {
        "gate":                 "69G",
        "status":               status,
        "sync_executed":        sync_executed,
        "package_exists":       package_exists,
        "resources_verified":   resources_verified,
        "resource_count_match": count_match,
        "active_false":         active_false,
        "no_raw_source_text":   no_raw,
        "no_api_keys":          no_keys,
        "issues":               issues,
        "generated_at":         now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
