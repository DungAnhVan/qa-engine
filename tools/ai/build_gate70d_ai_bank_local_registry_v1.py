"""
Gate 70D -- Build AI Bank Local Registry v1

Builds/updates:
  data/ai/registry/gate70d_ai_bank_content_registry_v1.json

Does NOT touch the main content registry or the active_content_index.
Does NOT write Supabase.

Output:
  data/diagnostics/gate70d_ai_bank_local_registry_build_report_v1.json
"""

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PKG_FILE     = ROOT / "data" / "ai" / "published" / "gate70d_ai_bank_package_v1" / "publish_package_v1.json"
REGISTRY_DIR = ROOT / "data" / "ai" / "registry"
REGISTRY_FILE = REGISTRY_DIR / "gate70d_ai_bank_content_registry_v1.json"
REPORT_FILE  = ROOT / "data" / "diagnostics" / "gate70d_ai_bank_local_registry_build_report_v1.json"

print("Gate 70D -- Build AI Bank Local Registry v1")
print("=" * 60)

if not PKG_FILE.exists():
    print("ERROR: Published package not found — run build_gate70d_ai_bank_local_published_package_v1.py first.")
    sys.exit(1)

pkg = json.loads(PKG_FILE.read_text(encoding="utf-8"))
now = datetime.datetime.now(datetime.timezone.utc).isoformat()

pkg_entry = {
    "package_id":             pkg.get("package_id"),
    "status":                 pkg.get("status"),
    "active_content":         pkg.get("active_content", False),
    "supabase_write_performed": pkg.get("supabase_write_performed", False),
    "ai_api_called":          pkg.get("ai_api_called", False),
    "teacher_final_approval": pkg.get("teacher_final_approval", True),
    "resource_count":         pkg.get("resource_count", 0),
    "published_at":           pkg.get("published_at"),
    "path":                   str(PKG_FILE.relative_to(ROOT)),
}

# Load existing registry or seed new one (upsert by package_id)
if REGISTRY_FILE.exists():
    registry = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    packages = registry.get("packages", [])
    packages = [p for p in packages if p.get("package_id") != pkg_entry["package_id"]]
    packages.append(pkg_entry)
else:
    registry = {}
    packages = [pkg_entry]

registry.update({
    "registry_id": "quanta_aptus_gate70d_ai_bank_content_registry_v1",
    "version":     "0.1.0",
    "updated_at":  now,
    "note":        "Gate 70D AI bank local registry — does not affect the main content registry or active_content_index. No Supabase write.",
    "package_count": len(packages),
    "packages":    packages,
})

REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
REGISTRY_FILE.write_text(json.dumps(registry, indent=2), encoding="utf-8")
print(f"Registry: {REGISTRY_FILE.relative_to(ROOT)}  ({len(packages)} packages)")

report = {
    "gate":          "70D",
    "status":        "passed",
    "registry_file": str(REGISTRY_FILE.relative_to(ROOT)),
    "package_count": len(packages),
    "packages":      [p.get("package_id") for p in packages],
    "active_content_touched":  False,
    "supabase_write_performed": False,
}
REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Report:   {REPORT_FILE.relative_to(ROOT)}")
print("Status: PASSED")
sys.exit(0)
