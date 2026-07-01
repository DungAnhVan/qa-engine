"""
Gate 69F -- Build AI Local Registry v1

Scans locally published AI packages and builds/updates the AI content
registry. Does NOT touch the main content registry or active_content_index.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_local_registry_v1.py

Output:
  data/ai/registry/ai_content_registry_v1.json
  data/diagnostics/ai_local_registry_build_report_v1.json
"""

import json
import sys
import datetime
from pathlib import Path

ROOT          = Path(__file__).resolve().parents[2]
PUBLISHED_DIR = ROOT / "data" / "ai" / "published"
REGISTRY_DIR  = ROOT / "data" / "ai" / "registry"
REGISTRY_FILE = REGISTRY_DIR / "ai_content_registry_v1.json"
REPORT_FILE   = ROOT / "data" / "diagnostics" / "ai_local_registry_build_report_v1.json"


def build_local_registry() -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    packages: list[dict] = []

    # Scan data/ai/published/ for publish_package_v1.json files
    if PUBLISHED_DIR.exists():
        for pkg_json in sorted(PUBLISHED_DIR.rglob("publish_package_v1.json")):
            try:
                pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            except Exception:
                continue
            rel_path = str(pkg_json.relative_to(ROOT))
            packages.append({
                "package_id":               pkg.get("package_id", "unknown"),
                "status":                   pkg.get("status", "unknown"),
                "active_content":           pkg.get("active_content", False),
                "supabase_write_performed": pkg.get("supabase_write_performed", False),
                "teacher_final_approval":   pkg.get("teacher_final_approval", False),
                "resource_count":           pkg.get("resource_count", 0),
                "published_at":             pkg.get("published_at", now),
                "path":                     rel_path,
            })

    registry = {
        "registry_id": "quanta_aptus_ai_content_registry_v1",
        "version":     "0.1.0",
        "updated_at":  now,
        "note":        "AI local registry only — does not affect the main content registry or the active content index",
        "package_count": len(packages),
        "packages":    packages,
    }

    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    return {
        "ok":            True,
        "package_count": len(packages),
        "generated_at":  now,
    }


def main():
    (ROOT / "data" / "diagnostics").mkdir(parents=True, exist_ok=True)

    print("Gate 69F -- Build AI Local Registry v1")
    print("-" * 55)

    result = build_local_registry()
    now    = result["generated_at"]

    print(f"  + package_count: {result['package_count']}")
    print(f"  + registry:      {REGISTRY_FILE}")

    report = {
        "status":        "passed",
        "package_count": result["package_count"],
        "registry_file": str(REGISTRY_FILE.relative_to(ROOT)),
        "generated_at":  now,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nStatus: passed")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
