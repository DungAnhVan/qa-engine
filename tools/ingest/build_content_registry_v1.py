"""
Build / update Quanta Aptus Content Registry v1.

Reads a publish_package_{vN}.json, extracts metadata, and upserts an entry in
data/registry/content_registry_v1.json.  Idempotent: re-running with the same
package replaces the existing entry without creating duplicates.
Version-aware: auto-detects v1/v2/... suffix from package_id or filename.

Does NOT call any AI API.  Does NOT generate content.

Usage:
    python tools/ingest/build_content_registry_v1.py \\
        data/publish/cambridge_igcse/physics_0625/resource_package_v1/publish_package_v1.json

    python tools/ingest/build_content_registry_v1.py \\
        data/publish/cambridge_igcse/physics_0625/resource_package_v2/publish_package_v2.json

Output (data/registry/):
    content_registry_v1.json
    content_registry_v1_report.json
    content_registry_v1_manifest.md
    content_registry_preview_v1.html
"""

import re
import sys
import os
import json
import html as html_module
import argparse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
REGISTRY_DIR  = PROJECT_ROOT / "data" / "registry"
REGISTRY_ID   = "quanta_aptus_content_registry_v1"

REQUIRED_FILE_KEYS = {"publish_package", "student_payload", "teacher_payload"}


def detect_suffix(pkg_path: Path, pkg_doc: dict) -> str:
    """Return version suffix (e.g. 'v1', 'v2') from package_id or filename."""
    # Prefer package_id: "...resource_package_v2" -> "v2"
    m = re.search(r"_resource_package_(v\d+)$", pkg_doc.get("package_id", ""))
    if m:
        return m.group(1)
    # Fallback: filename "publish_package_v2.json" -> "v2"
    m = re.search(r"publish_package_(v\d+)\.json$", pkg_path.name)
    if m:
        return m.group(1)
    return "v1"


def _package_file_keys(suffix: str) -> list[tuple[str, str]]:
    """Return (registry_key, relative_path) pairs for a given version suffix."""
    return [
        ("publish_package",  f"publish_package_{suffix}.json"),
        ("student_payload",  f"student_resource_payload_{suffix}.json"),
        ("teacher_payload",  f"teacher_resource_payload_{suffix}.json"),
        ("package_report",   f"resource_package_{suffix}_report.json"),
        ("package_manifest", f"resource_package_{suffix}_manifest.md"),
        ("student_preview",  f"static_preview/student_resource_preview_{suffix}.html"),
        ("teacher_preview",  f"static_preview/teacher_resource_preview_{suffix}.html"),
    ]


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def read_json_safe(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Package entry builder
# ---------------------------------------------------------------------------

def _compute_component_types(pkg_doc: dict) -> dict[str, int]:
    # v1 uses "items", v2 uses "resources"
    items = pkg_doc.get("items") or pkg_doc.get("resources") or []
    out: dict[str, int] = {}
    for item in items:
        ct = item.get("component_type")
        if ct:
            out[ct] = out.get(ct, 0) + 1
    return out


def _package_title(board: str, level: str, subject: str, syllabus_code: str, suffix: str = "v1") -> str:
    return (
        f"{board.title()} {level.upper()} {subject.title()} "
        f"{syllabus_code} Resource Package {suffix.upper()}"
    )


def build_package_entry(pkg_doc: dict, pkg_folder: Path, now_iso: str, suffix: str = "v1") -> dict:
    summary = pkg_doc.get("summary", {})
    file_keys = _package_file_keys(suffix)

    # Try to get student/teacher counts from the companion report JSON
    report = read_json_safe(pkg_folder / f"resource_package_{suffix}_report.json")
    if report:
        s_count  = report.get("student_payload_count")
        t_count  = report.get("teacher_payload_count")
        to_count = report.get("teacher_only_resource_count")
    else:
        # Fallback: read from payload JSON headers
        s_doc    = read_json_safe(pkg_folder / f"student_resource_payload_{suffix}.json")
        t_doc    = read_json_safe(pkg_folder / f"teacher_resource_payload_{suffix}.json")
        s_count  = (s_doc or {}).get("resource_count")
        t_count  = (t_doc or {}).get("resource_count")
        total    = pkg_doc.get("resource_count", 0)
        to_count = (total - s_count) if (s_count is not None) else None

    board         = pkg_doc.get("board", "")
    level         = pkg_doc.get("level", "")
    subject       = pkg_doc.get("subject", "")
    syllabus_code = pkg_doc.get("syllabus_code", "")

    # Resolve absolute paths for each versioned companion file
    paths: dict[str, str]         = {}
    availability: dict[str, bool] = {}
    for key, rel in file_keys:
        abs_path = pkg_folder / rel
        paths[key] = str(abs_path)
        availability[key] = abs_path.exists()

    app_visibility = {
        "student_visible": availability.get("student_payload", False),
        "teacher_visible": availability.get("teacher_payload", False),
        "admin_visible":   True,
    }

    return {
        "package_id":                  pkg_doc.get("package_id", ""),
        "package_version":             pkg_doc.get("version", "0.1.0"),
        "package_status":              pkg_doc.get("status", ""),
        "board":                       board,
        "level":                       level,
        "subject":                     subject,
        "syllabus_code":               syllabus_code,
        "title":                       _package_title(board, level, subject, syllabus_code, suffix),
        "content_origin":              pkg_doc.get("content_origin", ""),
        "copyright_status":            pkg_doc.get("copyright_status", ""),
        "resource_count":              pkg_doc.get("resource_count", 0),
        "student_payload_count":       s_count,
        "teacher_payload_count":       t_count,
        "teacher_only_resource_count": to_count,
        "estimated_total_time_minutes":summary.get("estimated_total_time_minutes", 0),
        "resource_types":              summary.get("resource_types", {}),
        "component_types":             _compute_component_types(pkg_doc),
        "topics":                      summary.get("topics", {}),
        "skill_types":                 summary.get("skill_types", {}),
        "difficulties":                summary.get("difficulties", {}),
        "paths":                       paths,
        "availability":                availability,
        "app_visibility":              app_visibility,
        "registered_at":               now_iso,
    }


# ---------------------------------------------------------------------------
# Registry upsert
# ---------------------------------------------------------------------------

def upsert_package(packages: list[dict], new_entry: dict) -> list[dict]:
    pid = new_entry["package_id"]
    for i, existing in enumerate(packages):
        if existing.get("package_id") == pid:
            packages[i] = new_entry
            return packages
    packages.append(new_entry)
    return packages


def build_registry_summary(packages: list[dict]) -> dict:
    boards: dict[str, int]        = {}
    levels: dict[str, int]        = {}
    subjects: dict[str, int]      = {}
    syllabus_codes: dict[str, int] = {}
    agg_topics: dict[str, int]    = {}
    agg_rtypes: dict[str, int]    = {}
    total_resources = total_student = total_teacher = total_teacher_only = total_time = 0

    def inc(d: dict, k: str | None) -> None:
        if k:
            d[k] = d.get(k, 0) + 1

    def merge(dst: dict, src: dict | None) -> None:
        if not src:
            return
        for k, v in src.items():
            dst[k] = dst.get(k, 0) + (v if isinstance(v, int) else 0)

    for p in packages:
        inc(boards,         p.get("board"))
        inc(levels,         p.get("level"))
        inc(subjects,       p.get("subject"))
        inc(syllabus_codes, p.get("syllabus_code"))
        total_resources    += p.get("resource_count")              or 0
        total_student      += p.get("student_payload_count")       or 0
        total_teacher      += p.get("teacher_payload_count")       or 0
        total_teacher_only += p.get("teacher_only_resource_count") or 0
        total_time         += p.get("estimated_total_time_minutes") or 0
        merge(agg_topics,  p.get("topics", {}))
        merge(agg_rtypes,  p.get("resource_types", {}))

    return {
        "boards":                       boards,
        "levels":                       levels,
        "subjects":                     subjects,
        "syllabus_codes":               syllabus_codes,
        "total_packages":               len(packages),
        "total_resources":              total_resources,
        "total_student_resources":      total_student,
        "total_teacher_resources":      total_teacher,
        "total_teacher_only_resources": total_teacher_only,
        "estimated_total_time_minutes": total_time,
        "topics":                       agg_topics,
        "resource_types":               agg_rtypes,
    }


def build_registry_doc(packages: list[dict], now_iso: str) -> dict:
    summary = build_registry_summary(packages)
    return {
        "registry_id":   REGISTRY_ID,
        "version":        "0.1.0",
        "status":         "internal_demo",
        "created_at":     now_iso,
        "package_count":  len(packages),
        "packages":       packages,
        "summary":        summary,
    }


# ---------------------------------------------------------------------------
# Status determination
# ---------------------------------------------------------------------------

def determine_status(entry: dict) -> tuple[str, list[str]]:
    avail = entry.get("availability", {})
    missing = [k for k, v in avail.items() if not v]
    required_missing = [k for k in missing if k in REQUIRED_FILE_KEYS]
    if required_missing:
        return "failed", missing
    if missing:
        return "needs_review", missing
    return "passed", []


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(
    reg_status: str,
    reg_doc: dict,
    updated_pkg_id: str,
    missing_files: list[str],
    out_files: dict,
) -> dict:
    sm = reg_doc.get("summary", {})
    return {
        "status":             reg_status,
        "registry_id":        REGISTRY_ID,
        "package_count":      reg_doc.get("package_count", 0),
        "updated_package_id": updated_pkg_id,
        "total_resources":    sm.get("total_resources", 0),
        "missing_file_count": len(missing_files),
        "missing_files":      missing_files,
        "output_files":       out_files,
    }


# ---------------------------------------------------------------------------
# Manifest markdown
# ---------------------------------------------------------------------------

def build_manifest_md(reg_doc: dict, report: dict) -> str:
    sm = reg_doc.get("summary", {})
    packages = reg_doc.get("packages", [])

    lines = [
        "# Quanta Aptus Content Registry v1",
        "",
        f"- **Registry ID:** `{reg_doc['registry_id']}`",
        f"- **Status:** {report['status']}",
        f"- **Created:** {reg_doc['created_at']}",
        f"- **Package Count:** {reg_doc['package_count']}",
        f"- **Total Resources:** {sm.get('total_resources', 0)}",
        "",
        "## Boards / Levels / Subjects",
        "",
    ]

    for label, key in [("Boards", "boards"), ("Levels", "levels"), ("Subjects", "subjects")]:
        lines.append(f"**{label}:** " + ", ".join(
            f"{k} ({v})" for k, v in sorted(sm.get(key, {}).items(), key=lambda x: -x[1])
        ))

    lines += ["", "## Packages", ""]

    # Markdown table
    lines.append("| Package ID | Board | Level | Subject | Syllabus | Resources | Student | Teacher | S-Preview | T-Preview |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for pkg in packages:
        av = pkg.get("availability", {})
        s_prev = "YES" if av.get("student_preview") else "—"
        t_prev = "YES" if av.get("teacher_preview") else "—"
        lines.append(
            f"| `{pkg.get('package_id', '')}` "
            f"| {pkg.get('board', '')} "
            f"| {pkg.get('level', '').upper()} "
            f"| {pkg.get('subject', '')} "
            f"| {pkg.get('syllabus_code', '')} "
            f"| {pkg.get('resource_count', '')} "
            f"| {pkg.get('student_payload_count', '')} "
            f"| {pkg.get('teacher_payload_count', '')} "
            f"| {s_prev} "
            f"| {t_prev} |"
        )

    lines += ["", "## Output Paths", ""]
    for key, path in report["output_files"].items():
        lines.append(f"- **{key}:** `{path}`")

    lines += [
        "",
        "---",
        "",
        "> Registry points only to original Quanta Aptus generated resource packages.",
        "> Cambridge source papers are internal reference only.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML preview
# ---------------------------------------------------------------------------

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f0f4f8;
    color: #1a202c;
    padding: 24px 16px;
    max-width: 1200px;
    margin: 0 auto;
}
h1 { font-size: 1.7rem; color: #1a1a2e; margin-bottom: 4px; }
.subtitle { font-size: 0.85rem; color: #666; margin-bottom: 28px; }
h2 { font-size: 1.1rem; color: #1a1a2e; margin: 28px 0 12px; border-bottom: 2px solid #1a1a2e; padding-bottom: 4px; }
.cards {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 24px;
}
.card {
    background: #fff;
    border-radius: 8px;
    padding: 18px 24px;
    flex: 1;
    min-width: 140px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
    text-align: center;
}
.card-value { font-size: 2rem; font-weight: 700; color: #1a56db; }
.card-label { font-size: 0.78rem; color: #666; margin-top: 4px; text-transform: uppercase; letter-spacing: .04em; }
.table-wrap { overflow-x: auto; }
table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
    font-size: 0.85rem;
}
th {
    background: #1a1a2e;
    color: #fff;
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 0.78rem;
    letter-spacing: .04em;
    text-transform: uppercase;
}
td {
    padding: 10px 12px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: middle;
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f7fafc; }
.pkg-id { font-family: monospace; font-size: 0.75rem; color: #444; word-break: break-all; }
a { color: #1a56db; text-decoration: none; }
a:hover { text-decoration: underline; }
.tag {
    display: inline-block;
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: 3px;
    background: #e8f0fe;
    color: #1a56db;
    margin: 1px;
}
.missing { color: #aaa; font-style: italic; }
.copyright-footer {
    margin-top: 36px;
    font-size: 0.78rem;
    color: #999;
    border-top: 1px solid #e2e8f0;
    padding-top: 12px;
}
"""


def _e(val: object) -> str:
    if val is None:
        return ""
    return html_module.escape(str(val))


def _rel(abs_path_str: str, from_dir: Path) -> str:
    """Compute a relative URL from from_dir to abs_path_str (forward slashes)."""
    if not abs_path_str:
        return "#"
    try:
        rel = os.path.relpath(abs_path_str, from_dir)
        return rel.replace("\\", "/")
    except ValueError:
        return abs_path_str.replace("\\", "/")


def build_html(reg_doc: dict, registry_dir: Path) -> str:
    sm       = reg_doc.get("summary", {})
    packages = reg_doc.get("packages", [])

    # ── Summary cards ─────────────────────────────────────────────────────
    card_data = [
        (sm.get("total_packages",        0), "Packages"),
        (sm.get("total_resources",        0), "Total Resources"),
        (sm.get("total_student_resources",0), "Student Resources"),
        (sm.get("total_teacher_resources",0), "Teacher Resources"),
    ]
    cards_html = '<div class="cards">' + "".join(
        f'<div class="card"><div class="card-value">{v}</div>'
        f'<div class="card-label">{_e(label)}</div></div>'
        for v, label in card_data
    ) + "</div>"

    # ── Packages table ────────────────────────────────────────────────────
    rows = ""
    for pkg in packages:
        avail = pkg.get("availability", {})
        paths = pkg.get("paths", {})

        def link(key: str, label: str) -> str:
            if not avail.get(key):
                return f'<span class="missing">—</span>'
            href = _rel(paths.get(key, ""), registry_dir)
            return f'<a href="{_e(href)}">{_e(label)}</a>'

        previews = (
            link("student_preview", "Student") +
            "&nbsp;" +
            link("teacher_preview", "Teacher")
        )
        payloads = (
            link("publish_package", "pkg") +
            "&nbsp;" +
            link("student_payload", "student") +
            "&nbsp;" +
            link("teacher_payload", "teacher")
        )

        rows += (
            f'<tr>'
            f'<td class="pkg-id">{_e(pkg.get("package_id", ""))}</td>'
            f'<td>{_e(pkg.get("board", ""))}</td>'
            f'<td>{_e((pkg.get("level") or "").upper())}</td>'
            f'<td>{_e(pkg.get("subject", ""))}</td>'
            f'<td>{_e(pkg.get("syllabus_code", ""))}</td>'
            f'<td>{_e(pkg.get("resource_count", ""))}</td>'
            f'<td>{_e(pkg.get("student_payload_count", ""))}</td>'
            f'<td>{_e(pkg.get("teacher_payload_count", ""))}</td>'
            f'<td>{previews}</td>'
            f'<td>{payloads}</td>'
            f'</tr>\n'
        )

    table_html = (
        '<div class="table-wrap"><table>'
        "<thead><tr>"
        "<th>Package ID</th>"
        "<th>Board</th>"
        "<th>Level</th>"
        "<th>Subject</th>"
        "<th>Syllabus</th>"
        "<th>Resources</th>"
        "<th>Student</th>"
        "<th>Teacher</th>"
        "<th>Previews</th>"
        "<th>Downloads</th>"
        "</tr></thead>"
        f"<tbody>\n{rows}</tbody>"
        "</table></div>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quanta Aptus Content Registry</title>
<style>
{_CSS}
</style>
</head>
<body>
<h1>Quanta Aptus Content Registry</h1>
<div class="subtitle">
Registry ID: {_e(reg_doc.get('registry_id', ''))} &bull;
{_e(reg_doc.get('created_at', '')[:10])} &bull;
{_e(reg_doc.get('package_count', 0))} package(s)
</div>
{cards_html}
<h2>Packages</h2>
{table_html}
<div class="copyright-footer">
Registry points only to original Quanta Aptus generated resource packages.
Cambridge source papers are internal reference only. &copy; Quanta Aptus.
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build / update the Quanta Aptus Content Registry v1."
    )
    ap.add_argument(
        "package_json",
        help="Path to publish_package_v{N}.json",
    )
    args = ap.parse_args()

    pkg_path = Path(args.package_json).resolve()
    if not pkg_path.exists():
        sys.exit(f"Error: file not found: {pkg_path}")

    pkg_doc = read_json_safe(pkg_path)
    if not pkg_doc:
        sys.exit(f"Error: could not parse JSON: {pkg_path}")

    pkg_folder = pkg_path.parent
    now_iso    = datetime.now(timezone.utc).isoformat()

    # Detect version suffix from package_id or filename
    suffix = detect_suffix(pkg_path, pkg_doc)

    # ── Build new entry ────────────────────────────────────────────────────
    entry = build_package_entry(pkg_doc, pkg_folder, now_iso, suffix)
    reg_status, missing_files = determine_status(entry)

    # ── Load existing registry and upsert ─────────────────────────────────
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    registry_path = REGISTRY_DIR / "content_registry_v1.json"
    report_path   = REGISTRY_DIR / "content_registry_v1_report.json"
    manifest_path = REGISTRY_DIR / "content_registry_v1_manifest.md"
    preview_path  = REGISTRY_DIR / "content_registry_preview_v1.html"

    existing_doc  = read_json_safe(registry_path)
    packages: list[dict] = (existing_doc or {}).get("packages", [])
    packages = upsert_package(packages, entry)
    reg_doc  = build_registry_doc(packages, now_iso)

    out_files = {
        "registry": str(registry_path),
        "report":   str(report_path),
        "manifest": str(manifest_path),
        "preview":  str(preview_path),
    }

    report   = build_report(reg_status, reg_doc, entry["package_id"], missing_files, out_files)
    manifest = build_manifest_md(reg_doc, report)
    preview  = build_html(reg_doc, REGISTRY_DIR)

    def write_json(path: Path, obj: dict) -> None:
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    write_json(registry_path, reg_doc)
    write_json(report_path,   report)
    manifest_path.write_text(manifest, encoding="utf-8")
    preview_path.write_text(preview,   encoding="utf-8")

    # ── Terminal summary ───────────────────────────────────────────────────
    sm = reg_doc["summary"]
    print(f"status                   : {reg_status}")
    print(f"registry_id              : {REGISTRY_ID}")
    print(f"package_count            : {reg_doc['package_count']}")
    print(f"total_resources          : {sm['total_resources']}")
    print(f"total_student_resources  : {sm['total_student_resources']}")
    print(f"total_teacher_resources  : {sm['total_teacher_resources']}")
    print(f"missing_file_count       : {report['missing_file_count']}")
    print(f"registry                 : {registry_path}")
    print(f"report                   : {report_path}")
    print(f"manifest                 : {manifest_path}")
    print(f"preview                  : {preview_path}")


if __name__ == "__main__":
    main()
