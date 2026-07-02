"""
Gate 70E -- Verify AI Bank Package from Supabase v1

Reads the AI bank package back from Supabase to verify sync was successful.
If sync has not been executed, returns needs_review with a clear message.

Security:
  - Service role key from .env.local — NEVER written to output.
  - No raw source text. No schema changes. No active switch.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\verify_gate70e_ai_bank_package_from_supabase_v1.py

Output:
  data/diagnostics/gate70e_ai_bank_supabase_readback_verify_report_v1.json
"""

import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PUBLISH_PKG  = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1" / "publish_package_v1.json"
SYNC_REPORT  = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_sync_execute_report_v1.json"
REPORT_FILE  = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_readback_verify_report_v1.json"

TARGET_PACKAGE_KEY = "quanta_aptus_gate70e_ai_bank_package_v1"
TIMEOUT = 20

SECRET_PATTERNS = ["SUPABASE_SERVICE_ROLE_KEY", "supabase_service_role",
                   "sk-ant-", "NEXT_PUBLIC_SUPABASE_SERVICE"]
COPYRIGHT_PATTERNS = ["UCLES", "Cambridge International", "original_raw_block"]


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


def write_report(report: dict) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")


print("Gate 70E -- Verify AI Bank Package from Supabase v1")
print("=" * 60)

now = datetime.datetime.now(datetime.timezone.utc).isoformat()

# ── Check if sync has been executed ────────────────────────────────────────
sync_executed = False
if SYNC_REPORT.exists():
    sr = json.loads(SYNC_REPORT.read_text(encoding="utf-8"))
    sync_executed = sr.get("supabase_write_performed", False)

if not sync_executed:
    msg = "Sync not executed yet. Dry-run plan exists. Run sync with --execute --confirm SYNC_GATE70E_AI_BANK_PACKAGE to write to Supabase."
    print(f"  Status: needs_review\n  {msg}")
    write_report({
        "gate":              "70E",
        "status":            "needs_review",
        "sync_executed":     False,
        "message":           msg,
        "package_verified":  False,
        "resource_count":    0,
        "target_active":     False,
        "active_switch_performed": False,
        "existing_active_package_preserved": True,
        "ai_api_called":     False,
        "secrets_exposed":   False,
        "issues":            [msg],
        "verified_at":       now,
    })
    sys.exit(0)

# ── Load env ────────────────────────────────────────────────────────────────
env_local    = load_env_local()
supabase_url = resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
service_key  = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)

issues: list[str] = []
if not supabase_url:
    issues.append("NEXT_PUBLIC_SUPABASE_URL not set")
if not service_key:
    issues.append("SUPABASE_SERVICE_ROLE_KEY not set")

if issues:
    write_report({"gate": "70E", "status": "needs_review", "issues": issues})
    print(f"Missing env: {issues}")
    sys.exit(1)

print(f"Supabase URL: {supabase_url}")
print(f"Service key:  {mask_key(service_key)}")
print(f"Target:       {TARGET_PACKAGE_KEY}")

# ── Read local package for expected counts ──────────────────────────────────
local_pkg = json.loads(PUBLISH_PKG.read_text(encoding="utf-8")) if PUBLISH_PKG.exists() else {}
local_resource_count = local_pkg.get("resource_count", 0)

# ── Read package from Supabase ──────────────────────────────────────────────
enc_key = urllib.parse.quote(TARGET_PACKAGE_KEY, safe="")
sc, pkg_rows, err = sb_get(supabase_url, service_key, "resource_packages",
                            f"package_key=eq.{enc_key}&select=id,package_key,version,status,resource_count")
if err or not pkg_rows:
    issues.append(f"Package not found in Supabase: {err or 'empty result'}")
    write_report({
        "gate": "70E", "status": "needs_review",
        "sync_executed": True, "package_verified": False,
        "issues": issues, "verified_at": now,
    })
    sys.exit(1)

sb_pkg = pkg_rows[0]
pkg_uuid = sb_pkg["id"]
print(f"\nPackage found: {sb_pkg['package_key']} (id={str(pkg_uuid)[:8]}...)")
print(f"  status:         {sb_pkg.get('status')}")
print(f"  resource_count: {sb_pkg.get('resource_count')}")

if sb_pkg.get("status") == "active":
    issues.append("CRITICAL: package is active — should be draft only in Gate 70E")

# ── Read package items ──────────────────────────────────────────────────────
enc_uuid = urllib.parse.quote(str(pkg_uuid), safe="")
sc, items, err = sb_get(supabase_url, service_key, "resource_package_items",
                         f"package_id=eq.{enc_uuid}&select=id,resource_id,sort_order")
if err:
    issues.append(f"package_items read error: {err}")

print(f"  items_in_supabase: {len(items)}")
if len(items) != local_resource_count and local_resource_count > 0:
    issues.append(f"item count mismatch: local={local_resource_count} supabase={len(items)}")

# ── Verify existing active package preserved ────────────────────────────────
sc, active_pkgs, err = sb_get(supabase_url, service_key, "resource_packages",
                               f"status=eq.active&select=id,package_key,status")
if err:
    issues.append(f"active package check error: {err}")
    existing_active_preserved = True  # assume ok on error
else:
    # Our new package should NOT be in the active list
    our_pkg_active = any(p.get("package_key") == TARGET_PACKAGE_KEY for p in active_pkgs)
    existing_active_preserved = not our_pkg_active
    if our_pkg_active:
        issues.append(f"CRITICAL: {TARGET_PACKAGE_KEY} is in active packages — should be draft")
    print(f"  active_packages_in_db: {len(active_pkgs)} (ours active: {our_pkg_active})")

# ── Safety check: no secrets in output ────────────────────────────────────
output_text = json.dumps({"pkg": sb_pkg, "items_count": len(items)})
secrets_ok = not any(p in output_text for p in SECRET_PATTERNS)
copyright_ok = not any(p in output_text for p in COPYRIGHT_PATTERNS)

status = "passed" if not issues else "needs_review"
valid  = len(issues) == 0

report = {
    "gate":                              "70E",
    "status":                            status,
    "sync_executed":                     True,
    "package_verified":                  valid,
    "package_key":                       sb_pkg.get("package_key"),
    "package_status_in_supabase":        sb_pkg.get("status"),
    "resource_count_local":              local_resource_count,
    "resource_count_supabase":           sb_pkg.get("resource_count"),
    "items_in_supabase":                 len(items),
    "target_active":                     False,
    "active_switch_performed":           False,
    "existing_active_package_preserved": existing_active_preserved,
    "ai_api_called":                     False,
    "secrets_exposed":                   not secrets_ok,
    "copyright_clean":                   copyright_ok,
    "issues":                            issues,
    "verified_at":                       now,
}
write_report(report)
print(f"\nStatus: {status}")
print(f"Verified: {valid}")
print(f"Report: {REPORT_FILE.relative_to(ROOT)}")
sys.exit(0 if status == "passed" else 1)
