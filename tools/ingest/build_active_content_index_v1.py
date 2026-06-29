"""
Gate 37 — Build Active Content Index v1
Reads content_registry_v1.json, selects the active package for each
board/level/subject/syllabus_code group (highest _vN suffix wins),
and writes 4 output files to data/registry/.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _pkg_suffix_num(package_id: str) -> int:
    """Return the integer N from '..._resource_package_vN', or 0 if not found."""
    m = re.search(r"_resource_package_v(\d+)$", package_id)
    return int(m.group(1)) if m else 0


def _semver_tuple(version_str: str) -> tuple[int, ...]:
    """Parse '0.2.0' -> (0, 2, 0). Returns (0,) on failure."""
    try:
        return tuple(int(x) for x in version_str.split("."))
    except Exception:
        return (0,)


def _created_at_ts(pkg: dict) -> float:
    """Parse registered_at or created_at to float epoch, fallback 0."""
    for key in ("registered_at", "created_at"):
        val = pkg.get(key)
        if val:
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp()
            except Exception:
                pass
    return 0.0


def select_active(pkgs: list[dict]) -> dict:
    """
    From a group of packages, return the one that should be active.
    Priority:
      1. Highest _vN integer in package_id (primary)
      2. Highest semantic package_version (secondary)
      3. Latest registered_at / created_at (tiebreaker)
    """
    return max(
        pkgs,
        key=lambda p: (
            _pkg_suffix_num(p["package_id"]),
            _semver_tuple(p.get("package_version", "0")),
            _created_at_ts(p),
        ),
    )


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

HTML_STYLE = """
body{font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:0;background:#f8f9fa;color:#2d3748}
h1{margin:0;font-size:1.5rem;color:#fff}
.topbar{background:#2b6cb0;padding:1rem 2rem;display:flex;align-items:center;gap:1rem}
.badge{background:#ebf8ff;color:#2b6cb0;font-size:.75rem;padding:.2rem .6rem;border-radius:999px;font-weight:600}
.container{max-width:1100px;margin:2rem auto;padding:0 1rem}
.summary-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1rem;margin-bottom:2rem}
.stat-card{background:#fff;border:1px solid #e2e8f0;border-radius:.5rem;padding:1rem;text-align:center}
.stat-val{font-size:2rem;font-weight:700;color:#2b6cb0}
.stat-label{font-size:.8rem;color:#718096;margin-top:.25rem}
.section-title{font-size:1.1rem;font-weight:600;margin:1.5rem 0 .75rem;color:#2d3748;border-bottom:2px solid #bee3f8;padding-bottom:.3rem}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;border-radius:.5rem;overflow:hidden}
th{background:#ebf8ff;color:#2b6cb0;padding:.6rem .8rem;text-align:left;font-size:.82rem;font-weight:600}
td{padding:.55rem .8rem;border-top:1px solid #e2e8f0;font-size:.85rem;vertical-align:top}
tr:hover td{background:#f7fafc}
.pkg-id{font-family:monospace;font-size:.78rem;color:#4a5568}
.status-badge{display:inline-block;font-size:.72rem;padding:.1rem .5rem;border-radius:999px;font-weight:600}
.status-publish_ready{background:#c6f6d5;color:#276749}
.status-internal_demo{background:#ebf8ff;color:#2b6cb0}
.prev-ver{font-family:monospace;font-size:.76rem;color:#718096}
a{color:#2b6cb0;text-decoration:none}
a:hover{text-decoration:underline}
.footer{text-align:center;color:#a0aec0;font-size:.8rem;margin:3rem 0 1rem}
"""


def _status_badge(status: str) -> str:
    cls = f"status-{status}" if status in ("publish_ready", "internal_demo") else "status-internal_demo"
    return f'<span class="status-badge {cls}">{status}</span>'


def _prev_versions_html(prevs: list[dict]) -> str:
    if not prevs:
        return '<span style="color:#a0aec0">—</span>'
    lines = []
    for p in prevs:
        lines.append(f'<span class="prev-ver">{p["package_id"]}</span> ({p["resource_count"]} res)')
    return "<br>".join(lines)


def build_html(index: dict, now_iso: str) -> str:
    s = index["summary"]
    active = index["active_packages"]

    rows = []
    for pkg in active:
        student_link = f'<a href="{pkg["paths"]["student_preview"]}" target="_blank">Student</a>' if pkg["paths"].get("student_preview") else "—"
        teacher_link = f'<a href="{pkg["paths"]["teacher_preview"]}" target="_blank">Teacher</a>' if pkg["paths"].get("teacher_preview") else "—"
        pkg_link = f'<a href="{pkg["paths"]["publish_package"]}" target="_blank">JSON</a>' if pkg["paths"].get("publish_package") else "—"
        rows.append(f"""
        <tr>
          <td><span class="pkg-id">{pkg['active_package_id']}</span></td>
          <td>{pkg['board'].title()}</td>
          <td>{pkg['level'].upper()}</td>
          <td>{pkg['subject'].title()}</td>
          <td>{pkg['syllabus_code']}</td>
          <td>{_status_badge(pkg['active_package_status'])}</td>
          <td style="text-align:center">{pkg['resource_count']}</td>
          <td style="text-align:center">{pkg['student_payload_count']}</td>
          <td style="text-align:center">{pkg['teacher_payload_count']}</td>
          <td style="text-align:center">{pkg['teacher_only_resource_count']}</td>
          <td>{_prev_versions_html(pkg['previous_versions'])}</td>
          <td>{student_link} &nbsp; {teacher_link} &nbsp; {pkg_link}</td>
        </tr>""")

    rows_html = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quanta Aptus Active Content Index</title>
<style>{HTML_STYLE}</style>
</head>
<body>
<div class="topbar">
  <h1>Quanta Aptus Active Content Index</h1>
  <span class="badge">{index['index_id']}</span>
  <span class="badge">{index['status']}</span>
</div>
<div class="container">
  <div class="summary-grid">
    <div class="stat-card"><div class="stat-val">{s['active_package_count']}</div><div class="stat-label">Active Packages</div></div>
    <div class="stat-card"><div class="stat-val">{s['archived_package_count']}</div><div class="stat-label">Archived Packages</div></div>
    <div class="stat-card"><div class="stat-val">{s['active_total_resources']}</div><div class="stat-label">Total Resources</div></div>
    <div class="stat-card"><div class="stat-val">{s['active_student_resources']}</div><div class="stat-label">Student Resources</div></div>
    <div class="stat-card"><div class="stat-val">{s['active_teacher_resources']}</div><div class="stat-label">Teacher Resources</div></div>
    <div class="stat-card"><div class="stat-val">{s['active_teacher_only_resources']}</div><div class="stat-label">Teacher-Only</div></div>
    <div class="stat-card"><div class="stat-val">{s['all_registry_package_count']}</div><div class="stat-label">Registry Total</div></div>
  </div>

  <div class="section-title">Active Packages</div>
  <table>
    <thead>
      <tr>
        <th>Package ID</th>
        <th>Board</th>
        <th>Level</th>
        <th>Subject</th>
        <th>Syllabus</th>
        <th>Status</th>
        <th>Resources</th>
        <th>Student</th>
        <th>Teacher</th>
        <th>Teacher-Only</th>
        <th>Previous Versions</th>
        <th>Links</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>

  <p class="footer">Generated {now_iso} &middot; Source: {index['source_registry_id']}</p>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------

def build_manifest(index: dict, output_paths: dict, now_iso: str) -> str:
    s = index["summary"]
    lines = [
        "# Quanta Aptus Active Content Index v1",
        "",
        f"**Index ID:** `{index['index_id']}`  ",
        f"**Version:** {index['version']}  ",
        f"**Status:** {index['status']}  ",
        f"**Generated:** {now_iso}  ",
        f"**Source Registry:** `{index['source_registry_id']}`  ",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Active Packages | {s['active_package_count']} |",
        f"| Archived Packages | {s['archived_package_count']} |",
        f"| All Registry Packages | {s['all_registry_package_count']} |",
        f"| Active Total Resources | {s['active_total_resources']} |",
        f"| Active Student Resources | {s['active_student_resources']} |",
        f"| Active Teacher Resources | {s['active_teacher_resources']} |",
        f"| Active Teacher-Only Resources | {s['active_teacher_only_resources']} |",
        "",
        "## Active Packages",
        "",
        "| Content Key | Active Package ID | Status | Resources | Student | Teacher | Teacher-Only |",
        "|-------------|-------------------|--------|-----------|---------|---------|--------------|",
    ]
    for pkg in index["active_packages"]:
        lines.append(
            f"| `{pkg['content_key']}` "
            f"| `{pkg['active_package_id']}` "
            f"| {pkg['active_package_status']} "
            f"| {pkg['resource_count']} "
            f"| {pkg['student_payload_count']} "
            f"| {pkg['teacher_payload_count']} "
            f"| {pkg['teacher_only_resource_count']} |"
        )

    lines += ["", "## Previous Versions", ""]
    has_prev = False
    for pkg in index["active_packages"]:
        if pkg["previous_versions"]:
            has_prev = True
            lines.append(f"### {pkg['content_key']}")
            lines.append("")
            lines.append("| Package ID | Resources | Student | Teacher |")
            lines.append("|------------|-----------|---------|---------|")
            for pv in pkg["previous_versions"]:
                lines.append(
                    f"| `{pv['package_id']}` "
                    f"| {pv['resource_count']} "
                    f"| {pv['student_payload_count']} "
                    f"| {pv['teacher_payload_count']} |"
                )
            lines.append("")
    if not has_prev:
        lines.append("_No previous versions archived._")
        lines.append("")

    lines += [
        "## Output Files",
        "",
        f"- **Index:** `{output_paths['index']}`",
        f"- **Report:** `{output_paths['report']}`",
        f"- **Manifest:** `{output_paths['manifest']}`",
        f"- **Preview:** `{output_paths['preview']}`",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python build_active_content_index_v1.py <path/to/content_registry_v1.json>")
        sys.exit(1)

    registry_path = Path(sys.argv[1]).resolve()
    if not registry_path.exists():
        print(f"[FAILED] Registry not found: {registry_path}")
        sys.exit(1)

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAILED] Cannot load registry: {exc}")
        sys.exit(1)

    packages: list[dict] = registry.get("packages", [])
    if not packages:
        print("[FAILED] No packages found in registry.")
        sys.exit(1)

    # Output folder = same dir as registry
    out_dir = registry_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).isoformat()

    # Group by (board, level, subject, syllabus_code)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for pkg in packages:
        key = (
            pkg.get("board", ""),
            pkg.get("level", ""),
            pkg.get("subject", ""),
            pkg.get("syllabus_code", ""),
        )
        groups[key].append(pkg)

    active_packages = []
    archived_count = 0

    for (board, level, subject, syllabus_code), grp in sorted(groups.items()):
        active_pkg = select_active(grp)
        prev_vers = [p for p in grp if p["package_id"] != active_pkg["package_id"]]
        archived_count += len(prev_vers)

        content_key = f"{board}_{level}_{subject}_{syllabus_code}"

        entry = {
            "content_key": content_key,
            "board": board,
            "level": level,
            "subject": subject,
            "syllabus_code": syllabus_code,
            "active_package_id": active_pkg["package_id"],
            "active_package_version": active_pkg.get("package_version", ""),
            "active_package_status": active_pkg.get("package_status", ""),
            "resource_count": active_pkg.get("resource_count", 0),
            "student_payload_count": active_pkg.get("student_payload_count", 0),
            "teacher_payload_count": active_pkg.get("teacher_payload_count", 0),
            "teacher_only_resource_count": active_pkg.get("teacher_only_resource_count", 0),
            "estimated_total_time_minutes": active_pkg.get("estimated_total_time_minutes", 0),
            "paths": {
                "publish_package": active_pkg.get("paths", {}).get("publish_package", ""),
                "student_payload": active_pkg.get("paths", {}).get("student_payload", ""),
                "teacher_payload": active_pkg.get("paths", {}).get("teacher_payload", ""),
                "student_preview": active_pkg.get("paths", {}).get("student_preview", ""),
                "teacher_preview": active_pkg.get("paths", {}).get("teacher_preview", ""),
            },
            "previous_versions": [
                {
                    "package_id": p["package_id"],
                    "resource_count": p.get("resource_count", 0),
                    "student_payload_count": p.get("student_payload_count", 0),
                    "teacher_payload_count": p.get("teacher_payload_count", 0),
                }
                for p in sorted(prev_vers, key=lambda x: _pkg_suffix_num(x["package_id"]))
            ],
        }
        active_packages.append(entry)

    # Aggregate summary over active packages only
    active_total_resources = sum(p["resource_count"] for p in active_packages)
    active_student_resources = sum(p["student_payload_count"] for p in active_packages)
    active_teacher_resources = sum(p["teacher_payload_count"] for p in active_packages)
    active_teacher_only_resources = sum(p["teacher_only_resource_count"] for p in active_packages)

    index_doc = {
        "index_id": "quanta_aptus_active_content_index_v1",
        "version": "0.1.0",
        "status": registry.get("status", "internal_demo"),
        "created_at": now_iso,
        "source_registry_id": registry.get("registry_id", "quanta_aptus_content_registry_v1"),
        "active_package_count": len(active_packages),
        "active_packages": active_packages,
        "summary": {
            "active_package_count": len(active_packages),
            "active_total_resources": active_total_resources,
            "active_student_resources": active_student_resources,
            "active_teacher_resources": active_teacher_resources,
            "active_teacher_only_resources": active_teacher_only_resources,
            "archived_package_count": archived_count,
            "all_registry_package_count": len(packages),
        },
    }

    # Output paths
    index_path    = out_dir / "active_content_index_v1.json"
    report_path   = out_dir / "active_content_index_v1_report.json"
    manifest_path = out_dir / "active_content_index_v1_manifest.md"
    preview_path  = out_dir / "active_content_index_preview_v1.html"

    output_paths = {
        "index":    str(index_path),
        "report":   str(report_path),
        "manifest": str(manifest_path),
        "preview":  str(preview_path),
    }

    # Write index
    index_path.write_text(json.dumps(index_doc, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write report
    report = {
        "status": "passed",
        "index_id": index_doc["index_id"],
        "source_registry_id": index_doc["source_registry_id"],
        "active_package_count": len(active_packages),
        "archived_package_count": archived_count,
        "active_total_resources": active_total_resources,
        "active_student_resources": active_student_resources,
        "active_teacher_resources": active_teacher_resources,
        "active_teacher_only_resources": active_teacher_only_resources,
        "output_files": output_paths,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write manifest
    manifest_path.write_text(
        build_manifest(index_doc, output_paths, now_iso), encoding="utf-8"
    )

    # Write HTML preview
    preview_path.write_text(
        build_html(index_doc, now_iso), encoding="utf-8"
    )

    # Terminal summary
    print(f"[PASSED] Active Content Index built successfully")
    print(f"  status                      : passed")
    print(f"  active_package_count        : {len(active_packages)}")
    print(f"  archived_package_count      : {archived_count}")
    print(f"  active_total_resources      : {active_total_resources}")
    print(f"  active_student_resources    : {active_student_resources}")
    print(f"  active_teacher_resources    : {active_teacher_resources}")
    print(f"  active_teacher_only_resources: {active_teacher_only_resources}")
    print(f"  index    -> {index_path}")
    print(f"  report   -> {report_path}")
    print(f"  manifest -> {manifest_path}")
    print(f"  preview  -> {preview_path}")


if __name__ == "__main__":
    main()
