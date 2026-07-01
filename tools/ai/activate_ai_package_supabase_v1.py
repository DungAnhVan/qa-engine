"""
Gate 69G -- Activate AI Package in Supabase v1

Sets the AI resource package to active in Supabase.
Default is DRY-RUN — no changes unless ALL three flags are provided.

Security:
  - Service role key loaded from .env.local — NEVER written to output.
  - Does NOT delete any package.
  - Preserves previous active package metadata in report.
  - No raw Cambridge text. No AI API calls.

Usage:
  Dry run (default, safe):
    .venv-ingest\\Scripts\\python.exe tools\\ai\\activate_ai_package_supabase_v1.py

  Execute activation (requires all three flags):
    .venv-ingest\\Scripts\\python.exe tools\\ai\\activate_ai_package_supabase_v1.py \\
        --execute --activate --confirm ACTIVATE_AI_PACKAGE

Output:
  data/diagnostics/ai_supabase_active_switch_report_v1.json
"""

import argparse
import datetime
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PUBLISH_PKG  = ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "publish_package_v1.json"
SYNC_REPORT  = ROOT / "data" / "diagnostics" / "ai_supabase_sync_execute_report_v1.json"
VERIFY_REPORT = ROOT / "data" / "diagnostics" / "ai_supabase_readback_verify_report_v1.json"
REPORT_FILE  = ROOT / "data" / "diagnostics" / "ai_supabase_active_switch_report_v1.json"

TIMEOUT = 20

AI_PACKAGE_ID = "quanta_aptus_ai_resource_package_v1"


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


def _rw_headers(key: str) -> dict:
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def sb_get(url_base: str, key: str, table: str, query: str) -> tuple[int, list, str | None]:
    url = f"{url_base}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, headers=_rw_headers(key))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read(2048).decode(errors="replace")
        return e.code, [], f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return 0, [], str(e)[:200]


def sb_patch(url_base: str, key: str, table: str, query: str, payload: dict) -> tuple[int, list, str | None]:
    url  = f"{url_base}/rest/v1/{table}?{query}"
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data, method="PATCH",
        headers={**_rw_headers(key), "Prefer": "return=representation"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read(2048).decode(errors="replace")
        return e.code, [], f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return 0, [], str(e)[:200]


def _pre_activate_checks(supabase_url: str, key: str) -> tuple[bool, list[str], str | None]:
    issues: list[str] = []
    encoded = urllib.parse.quote(AI_PACKAGE_ID, safe="")

    # 1. AI package must exist
    sc, rows, err = sb_get(supabase_url, key, "resource_packages",
                            f"package_key=eq.{encoded}&select=id,package_key,status,resource_count")
    if err or not rows:
        issues.append(f"AI package not found in Supabase: {err or 'empty result'}")
        return False, issues, None
    pkg_uuid = rows[0]["id"]

    # 2. Resource count > 0
    resource_count = rows[0].get("resource_count", 0)
    if resource_count < 1:
        issues.append(f"resource_count={resource_count} — must be > 0")

    # 3. teacher_final_approval (check local package)
    if PUBLISH_PKG.exists():
        pkg = json.loads(PUBLISH_PKG.read_text(encoding="utf-8"))
        if not pkg.get("teacher_final_approval"):
            issues.append("teacher_final_approval is not true in local package")

    # 4. No raw source text in Supabase resources
    sc2, rrows, err2 = sb_get(supabase_url, key, "resources",
                               f"resource_key=like.qa_physics_0625_*&select=student_prompt,teacher_notes")
    if not err2:
        raw = json.dumps(rrows)
        for bad in ["UCLES", "Cambridge International", "Question Answer Marks"]:
            if bad in raw:
                issues.append(f"copyright pattern '{bad}' in resource data")

    return len(issues) == 0, issues, pkg_uuid


def main():
    parser = argparse.ArgumentParser(description="Gate 69G — Activate AI Package in Supabase v1")
    parser.add_argument("--execute",  action="store_true", help="Execute (default: dry-run)")
    parser.add_argument("--activate", action="store_true", help="Confirm activation intent")
    parser.add_argument("--confirm",  default="", help="Required: ACTIVATE_AI_PACKAGE")
    args = parser.parse_args()

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    dry_run = not (args.execute and args.activate and args.confirm == "ACTIVATE_AI_PACKAGE")

    print("Gate 69G -- Activate AI Package in Supabase v1")
    print("=" * 55)
    print(f"  dry_run:  {dry_run}")
    print(f"  execute:  {args.execute}")
    print(f"  activate: {args.activate}")
    print(f"  confirm:  {'OK' if args.confirm == 'ACTIVATE_AI_PACKAGE' else 'MISSING or WRONG'}")

    if not dry_run and not (args.execute and args.activate and args.confirm == "ACTIVATE_AI_PACKAGE"):
        print("  Activation requires: --execute --activate --confirm ACTIVATE_AI_PACKAGE")

    previous_active_package_id: str | None = None
    active_switch_performed = False
    issues: list[str] = []

    if dry_run:
        print("\n[DRY-RUN] No Supabase writes. Activation NOT performed.")
        print("To activate: --execute --activate --confirm ACTIVATE_AI_PACKAGE")
        _write_report(now, dry_run, False, None, AI_PACKAGE_ID, issues, "")
        print(f"Report: {REPORT_FILE}")
        return

    # Execute path
    env_local    = load_env_local()
    supabase_url = resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
    service_key  = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)

    if not supabase_url or not service_key:
        issues.append("Missing env: NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        _write_report(now, False, False, None, AI_PACKAGE_ID, issues, "")
        raise SystemExit(1)

    print(f"\n  URL: {supabase_url}")
    print(f"  Key: {mask_key(service_key)}")

    # Pre-activation checks
    ok, pre_issues, pkg_uuid = _pre_activate_checks(supabase_url, service_key)
    issues.extend(pre_issues)
    if not ok:
        print(f"Pre-activation checks FAILED: {pre_issues}")
        _write_report(now, False, False, None, AI_PACKAGE_ID, issues, "")
        raise SystemExit(1)

    # Find current active package (to preserve its metadata in report)
    sc, active_rows, err = sb_get(supabase_url, service_key, "resource_packages",
                                   "status=eq.active&select=id,package_key")
    if not err and active_rows:
        previous_active_package_id = active_rows[0].get("package_key")
        print(f"  Current active package: {previous_active_package_id}")

    # Set AI package to active
    encoded = urllib.parse.quote(AI_PACKAGE_ID, safe="")
    sc, result, err = sb_patch(supabase_url, service_key, "resource_packages",
                                f"package_key=eq.{encoded}", {"status": "active"})
    if err:
        issues.append(f"activation PATCH failed: {err}")
        _write_report(now, False, False, previous_active_package_id, AI_PACKAGE_ID, issues, "")
        raise SystemExit(1)

    active_switch_performed = True
    print(f"  AI package '{AI_PACKAGE_ID}' set to active.")

    rollback = (
        f"To rollback: set resource_packages status='draft' where package_key='{AI_PACKAGE_ID}'"
        + (f" and set package_key='{previous_active_package_id}' back to status='active'"
           if previous_active_package_id else "")
    )

    _write_report(now, False, True, previous_active_package_id, AI_PACKAGE_ID, issues, rollback)
    print(f"\nStatus: {'passed' if not issues else 'needs_review'}")
    print(f"active_switch_performed: {active_switch_performed}")
    print(f"Rollback: {rollback}")
    print(f"Report: {REPORT_FILE}")


def _write_report(now, dry_run, active_switch_performed,
                  previous_active_package_id, new_active_package_id,
                  issues, rollback_instructions):
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)
    status = "passed" if not issues else "needs_review"
    report = {
        "gate":                      "69G",
        "status":                    status,
        "dry_run":                   dry_run,
        "active_switch_performed":   active_switch_performed,
        "previous_active_package_id": previous_active_package_id,
        "new_active_package_id":     new_active_package_id,
        "rollback_instructions":     rollback_instructions,
        "issues":                    issues,
        "generated_at":              now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
