"""
Gate 69G -- Build AI Package Supabase Export v1

Reads AI package data back from Supabase and exports to local JSON.
If sync has not been executed, exports are empty stubs with a clear message.

Security:
  - Service role key loaded from .env.local — NEVER written to any export file.
  - No raw Cambridge source text.
  - No schema changes.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_package_supabase_export_v1.py

Output:
  data/ai/supabase_exports/ai_package_from_supabase_v1.json
  data/ai/supabase_exports/student_ai_payload_from_supabase_v1.json
  data/ai/supabase_exports/teacher_ai_payload_from_supabase_v1.json
  data/diagnostics/ai_supabase_export_report_v1.json
"""

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
EXPORT_DIR   = ROOT / "data" / "ai" / "supabase_exports"
REPORT_FILE  = ROOT / "data" / "diagnostics" / "ai_supabase_export_report_v1.json"

AI_PKG_ID   = "quanta_aptus_ai_resource_package_v1"
TIMEOUT = 20

STUDENT_FIELDS = ["resource_key", "title", "topic", "resource_type", "difficulty",
                  "estimated_time_minutes", "student_prompt"]
TEACHER_FIELDS = STUDENT_FIELDS + ["worked_solution", "marking_guidance",
                                   "teacher_notes", "publish_status",
                                   "copyright_status", "originality_statement"]


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


def _strip_secrets(obj: dict) -> dict:
    """Remove any field that might hold secret-like values."""
    bad_keys = {"service_role_key", "supabase_key", "api_key",
                "SUPABASE_SERVICE_ROLE_KEY", "auth_token"}
    return {k: v for k, v in obj.items() if k not in bad_keys}


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    print("Gate 69G -- Build AI Package Supabase Export v1")
    print("-" * 55)

    # Check sync executed
    sync_was_executed = False
    if SYNC_REPORT.exists():
        try:
            sr = json.loads(SYNC_REPORT.read_text(encoding="utf-8"))
            sync_was_executed = sr.get("supabase_write_performed", False)
        except Exception:
            pass

    if not sync_was_executed:
        print("Sync not executed. Exporting empty stubs.")
        stub = {"exported_at": now, "sync_executed": False, "resources": [],
                "message": "Sync not yet executed. Run --execute --confirm SYNC_AI_PACKAGE first."}
        _write_exports(stub, stub, stub)
        _write_report(now, False, False, 0, 0, 0, "sync not yet executed")
        return

    env_local    = load_env_local()
    supabase_url = resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
    service_key  = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)

    if not supabase_url or not service_key:
        _write_exports({"error": "env missing"}, {"error": "env missing"}, {"error": "env missing"})
        _write_report(now, True, False, 0, 0, 0, "Supabase env missing")
        return

    issues: list[str] = []

    # Find package
    encoded = urllib.parse.quote(AI_PKG_ID, safe="")
    sc, pkg_rows, err = sb_get(supabase_url, service_key, "resource_packages",
                                f"package_key=eq.{encoded}&select=id,package_key,status,resource_count,published_at")
    if err or not pkg_rows:
        _write_exports({"error": "package not found"}, {"error": "not found"}, {"error": "not found"})
        _write_report(now, True, False, 0, 0, 0, f"package not found: {err}")
        return

    pkg_row  = pkg_rows[0]
    pkg_uuid = pkg_row["id"]

    # Get package items → resource UUIDs
    sc2, item_rows, err2 = sb_get(supabase_url, service_key, "resource_package_items",
                                   f"package_id=eq.{pkg_uuid}&select=resource_id,sort_order,visibility")
    if err2:
        issues.append(f"package items error: {err2}")
        item_rows = []

    resource_uuids = [r["resource_id"] for r in item_rows]

    # Fetch each resource
    all_resources: list[dict] = []
    for r_uuid in resource_uuids:
        enc = urllib.parse.quote(r_uuid, safe="")
        sc3, rrows, err3 = sb_get(supabase_url, service_key, "resources",
                                   f"id=eq.{enc}&select=*")
        if err3 or not rrows:
            issues.append(f"resource {r_uuid} fetch error: {err3}")
        else:
            all_resources.append(_strip_secrets(rrows[0]))

    # Build payloads
    student_resources = [{k: r.get(k) for k in STUDENT_FIELDS} for r in all_resources]
    teacher_resources = [{k: r.get(k) for k in TEACHER_FIELDS} for r in all_resources]

    pkg_export = {
        "exported_at":    now,
        "sync_executed":  True,
        "package_id":     AI_PKG_ID,
        "source_table":   "resource_packages",
        "status":         pkg_row.get("status"),
        "resource_count": len(all_resources),
        "package_uuid":   pkg_uuid,
        "resources":      all_resources,
        "issues":         issues,
    }
    student_export = {
        "exported_at":  now,
        "payload_type": "student",
        "package_id":   AI_PKG_ID,
        "resources":    student_resources,
    }
    teacher_export = {
        "exported_at":  now,
        "payload_type": "teacher",
        "package_id":   AI_PKG_ID,
        "resources":    teacher_resources,
    }

    _write_exports(pkg_export, student_export, teacher_export)
    _write_report(now, True, True, len(all_resources), len(student_resources),
                  len(teacher_resources), "; ".join(issues) if issues else "")

    print(f"  package exported: {len(all_resources)} resources")
    print(f"  status: {'passed' if not issues else 'needs_review'}")
    print(f"  export dir: {EXPORT_DIR}")
    print(f"  report: {REPORT_FILE}")


def _write_exports(pkg_export: dict, student_export: dict, teacher_export: dict):
    (EXPORT_DIR / "ai_package_from_supabase_v1.json").write_text(
        json.dumps(pkg_export, indent=2), encoding="utf-8")
    (EXPORT_DIR / "student_ai_payload_from_supabase_v1.json").write_text(
        json.dumps(student_export, indent=2), encoding="utf-8")
    (EXPORT_DIR / "teacher_ai_payload_from_supabase_v1.json").write_text(
        json.dumps(teacher_export, indent=2), encoding="utf-8")


def _write_report(now, sync_executed, export_ok, count, s_count, t_count, issues_str):
    status = "passed" if export_ok and not issues_str else ("needs_review" if sync_executed else "not_synced")
    report = {
        "gate":           "69G",
        "status":         status,
        "sync_executed":  sync_executed,
        "export_ok":      export_ok,
        "resource_count": count,
        "student_count":  s_count,
        "teacher_count":  t_count,
        "issues":         issues_str,
        "generated_at":   now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
