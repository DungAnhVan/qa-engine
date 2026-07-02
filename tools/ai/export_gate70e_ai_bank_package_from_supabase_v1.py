"""
Gate 70E -- Export AI Bank Package from Supabase v1

Reads the synced AI bank package from Supabase and exports to local files.
If sync has not been executed, exports from Gate 70D local package instead
and marks as dry-run source.

Security:
  - Service role key from .env.local — NEVER written to output files.
  - No raw source text. No active switch.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\export_gate70e_ai_bank_package_from_supabase_v1.py

Output:
  data/ai/supabase_exports/gate70e_ai_bank_package_from_supabase_v1.json
  data/ai/supabase_exports/gate70e_student_ai_bank_payload_from_supabase_v1.json
  data/ai/supabase_exports/gate70e_teacher_ai_bank_payload_from_supabase_v1.json
  data/diagnostics/gate70e_ai_bank_supabase_export_report_v1.json
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
STUDENT_PAY  = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1" / "student_resource_payload_v1.json"
TEACHER_PAY  = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1" / "teacher_resource_payload_v1.json"
SYNC_REPORT  = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_sync_execute_report_v1.json"
EXPORT_DIR   = ROOT / "data" / "ai" / "supabase_exports"
REPORT_FILE  = ROOT / "data" / "diagnostics" / "gate70e_ai_bank_supabase_export_report_v1.json"

TARGET_PACKAGE_KEY = "quanta_aptus_gate70e_ai_bank_package_v1"
TIMEOUT = 20
_STUDENT_EXCLUDE = {"answer_key", "marking_rubric", "teacher_notes"}

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


def write_exports(resources: list[dict], source: str, now: str) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    student_resources = [
        {k: v for k, v in r.items() if k not in _STUDENT_EXCLUDE}
        for r in resources
    ]

    pkg_export = {
        "package_key":          TARGET_PACKAGE_KEY,
        "source":               source,
        "exported_at":          now,
        "resource_count":       len(resources),
        "active":               False,
        "supabase_write_performed": source == "supabase_readback",
        "ai_api_called":        False,
        "teacher_final_approval": True,
        "resources":            resources,
    }
    student_export = {
        "payload_type":    "student",
        "package_key":     TARGET_PACKAGE_KEY,
        "source":          source,
        "exported_at":     now,
        "resource_count":  len(student_resources),
        "active":          False,
        "resources":       student_resources,
    }
    teacher_export = {
        "payload_type":    "teacher",
        "package_key":     TARGET_PACKAGE_KEY,
        "source":          source,
        "exported_at":     now,
        "resource_count":  len(resources),
        "active":          False,
        "resources":       resources,
    }

    # Safety: no secrets in exports
    for name, data in [("pkg", pkg_export), ("student", student_export), ("teacher", teacher_export)]:
        raw = json.dumps(data)
        for pat in SECRET_PATTERNS:
            if pat in raw:
                raise ValueError(f"Secret pattern '{pat}' found in {name} export — aborting")

    (EXPORT_DIR / "gate70e_ai_bank_package_from_supabase_v1.json").write_text(
        json.dumps(pkg_export, indent=2), encoding="utf-8")
    (EXPORT_DIR / "gate70e_student_ai_bank_payload_from_supabase_v1.json").write_text(
        json.dumps(student_export, indent=2), encoding="utf-8")
    (EXPORT_DIR / "gate70e_teacher_ai_bank_payload_from_supabase_v1.json").write_text(
        json.dumps(teacher_export, indent=2), encoding="utf-8")


print("Gate 70E -- Export AI Bank Package from Supabase v1")
print("=" * 60)

now = datetime.datetime.now(datetime.timezone.utc).isoformat()
issues: list[str] = []

# ── Check whether sync was executed ────────────────────────────────────────
sync_executed = False
if SYNC_REPORT.exists():
    sr = json.loads(SYNC_REPORT.read_text(encoding="utf-8"))
    sync_executed = sr.get("supabase_write_performed", False)

if not sync_executed:
    print("  Sync not executed — exporting from Gate 70D local package (dry-run source).")
    if not PUBLISH_PKG.exists():
        issues.append("Gate 70D local package not found")
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(json.dumps({
            "gate": "70E", "status": "needs_review", "issues": issues,
            "source": "dry_run_local", "exported_at": now,
        }, indent=2), encoding="utf-8")
        sys.exit(1)

    local_pkg = json.loads(PUBLISH_PKG.read_text(encoding="utf-8"))
    resources  = local_pkg.get("resources", [])
    write_exports(resources, "dry_run_local_gate70d", now)
    source = "dry_run_local_gate70d"
    print(f"  Exported from local: {len(resources)} resource(s)")

else:
    # ── Export from Supabase ──────────────────────────────────────────────
    env_local    = load_env_local()
    supabase_url = resolve_env("NEXT_PUBLIC_SUPABASE_URL", env_local)
    service_key  = resolve_env("SUPABASE_SERVICE_ROLE_KEY", env_local)

    if not supabase_url or not service_key:
        issues.append("NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(json.dumps({
            "gate": "70E", "status": "needs_review", "issues": issues,
        }, indent=2), encoding="utf-8")
        sys.exit(1)

    print(f"Supabase URL: {supabase_url}")
    print(f"Service key:  {mask_key(service_key)}")

    enc_key = urllib.parse.quote(TARGET_PACKAGE_KEY, safe="")
    sc, pkg_rows, err = sb_get(supabase_url, service_key, "resource_packages",
                                f"package_key=eq.{enc_key}&select=id,package_key,version,status,resource_count")
    if err or not pkg_rows:
        issues.append(f"Package not found in Supabase: {err or 'empty'}")
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(json.dumps({
            "gate": "70E", "status": "needs_review", "issues": issues,
        }, indent=2), encoding="utf-8")
        sys.exit(1)

    sb_pkg   = pkg_rows[0]
    pkg_uuid = sb_pkg["id"]

    # Read package items + resources
    enc_uuid = urllib.parse.quote(str(pkg_uuid), safe="")
    sc, items, err = sb_get(supabase_url, service_key, "resource_package_items",
                             f"package_id=eq.{enc_uuid}&select=resource_id,sort_order,visibility")
    if err:
        issues.append(f"items read error: {err}")

    resources = []
    for item in sorted(items, key=lambda x: x.get("sort_order", 0)):
        enc_rid = urllib.parse.quote(str(item["resource_id"]), safe="")
        sc, rows, err = sb_get(supabase_url, service_key, "resources",
                                f"id=eq.{enc_rid}&select=resource_key,title,topic,resource_type,difficulty,student_prompt,worked_solution,marking_guidance,teacher_notes")
        if err or not rows:
            issues.append(f"resource read error: {err or 'not found'}")
            continue
        r = rows[0]
        resources.append({
            "resource_id":     r.get("resource_key"),
            "title":           r.get("title"),
            "topic":           r.get("topic"),
            "resource_type":   r.get("resource_type"),
            "difficulty":      r.get("difficulty"),
            "student_prompt":  r.get("student_prompt"),
            "answer_key":      r.get("worked_solution"),
            "marking_rubric":  json.loads(r.get("marking_guidance") or "[]"),
            "teacher_notes":   r.get("teacher_notes"),
        })

    write_exports(resources, "supabase_readback", now)
    source = "supabase_readback"
    print(f"  Exported from Supabase: {len(resources)} resource(s)")

REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
status = "passed" if not issues else "needs_review"
report = {
    "gate":                "70E",
    "status":              status,
    "source":              source,
    "exported_at":         now,
    "resource_count":      len(resources),
    "sync_executed":       sync_executed,
    "active":              False,
    "ai_api_called":       False,
    "secrets_exposed":     False,
    "student_payload_exported": True,
    "teacher_payload_exported": True,
    "issues":              issues,
}
REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report: {REPORT_FILE.relative_to(ROOT)}")
print(f"Status: {status.upper()}")
sys.exit(0 if status == "passed" else 1)
