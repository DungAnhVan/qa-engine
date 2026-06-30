"""
Gate 53E — Sync Resource Packages and Resources to Supabase v1.

Reads resource_package_v* folders from data/publish/cambridge_igcse/<subject_slug>/
and syncs:
  - resource_packages  (one row per package)
  - resources          (one row per generated resource)
  - resource_package_items  (join: package <-> resource with visibility)

COPYRIGHT SAFETY:
  - All synced resources are Quanta Aptus original_generated content.
  - Cambridge source question text is never synced.
  - skill_name (contains partial Cambridge text) is NOT stored; title is derived instead.

CLI:
  # Single subject (preferred for first run):
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\sync_resources_packages_to_supabase_v1.py physics_0625

  # All subjects with resource packages:
  .venv-ingest\\Scripts\\python.exe tools\\supabase\\sync_resources_packages_to_supabase_v1.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
SUPABASE_TOOL = Path(__file__).parent
PUBLISH_ROOT  = PROJECT_ROOT / "data" / "publish" / "cambridge_igcse"
DIAG_DIR      = PROJECT_ROOT / "data" / "diagnostics"

if str(SUPABASE_TOOL) not in sys.path:
    sys.path.insert(0, str(SUPABASE_TOOL))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _resource_title(resource_type: str, topic: str) -> str:
    """Construct a safe title from derived metadata only — no Cambridge source text."""
    rt = resource_type.replace("_", " ").title()
    return f"{rt} — {topic}" if topic else rt


def _version_from_folder(name: str) -> int:
    """'resource_package_v2' -> 2"""
    m = re.search(r"v(\d+)$", name)
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------------------
# Supabase pre-fetch helpers
# ---------------------------------------------------------------------------

def _fetch_org_id(client, slug: str = "quanta-aptus-local-demo") -> Optional[str]:
    r = client.table("organizations").select("id").eq("slug", slug).execute()
    return r.data[0]["id"] if r.data else None


def _fetch_subject_row(client, subject_slug: str) -> Optional[dict]:
    r = (
        client.table("subjects")
        .select("id, adapter_status")
        .eq("subject_slug", subject_slug)
        .execute()
    )
    return r.data[0] if r.data else None


def _fetch_skill_unit_index(client, subject_id: str) -> dict[tuple, str]:
    """(topic, skill_type) -> first matching skill_unit id"""
    r = (
        client.table("skill_units")
        .select("id, topic, skill_type")
        .eq("subject_id", subject_id)
        .execute()
    )
    index: dict[tuple, str] = {}
    for row in (r.data or []):
        k = (row["topic"], row["skill_type"])
        if k not in index:
            index[k] = row["id"]
    return index


def _fetch_existing_packages(client, subject_id: str) -> dict[str, str]:
    """package_key -> row id"""
    r = (
        client.table("resource_packages")
        .select("id, package_key")
        .eq("subject_id", subject_id)
        .execute()
    )
    return {row["package_key"]: row["id"] for row in (r.data or [])}


def _fetch_existing_resources(client, subject_id: str) -> dict[str, str]:
    """resource_key -> row id"""
    r = (
        client.table("resources")
        .select("id, resource_key")
        .eq("subject_id", subject_id)
        .execute()
    )
    return {row["resource_key"]: row["id"] for row in (r.data or [])}


def _fetch_existing_pkg_items(client, package_id: str) -> dict[str, str]:
    """resource_id -> row id"""
    r = (
        client.table("resource_package_items")
        .select("id, resource_id")
        .eq("package_id", package_id)
        .execute()
    )
    return {row["resource_id"]: row["id"] for row in (r.data or [])}


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------

def _upsert_package(client, row: dict, existing: dict[str, str]) -> Optional[str]:
    pk = row["package_key"]
    if pk in existing:
        row_id = existing[pk]
        client.table("resource_packages").update(row).eq("id", row_id).execute()
        return row_id
    resp = client.table("resource_packages").insert(row).execute()
    if resp.data:
        new_id = resp.data[0]["id"]
        existing[pk] = new_id
        return new_id
    return None


def _upsert_resource(client, row: dict, existing: dict[str, str]) -> Optional[str]:
    rk = row["resource_key"]
    if rk in existing:
        row_id = existing[rk]
        client.table("resources").update(row).eq("id", row_id).execute()
        return row_id
    resp = client.table("resources").insert(row).execute()
    if resp.data:
        new_id = resp.data[0]["id"]
        existing[rk] = new_id
        return new_id
    return None


def _upsert_pkg_item(
    client,
    package_id: str,
    resource_id: str,
    sort_order: int,
    visibility: str,
    existing: dict[str, str],
) -> Optional[str]:
    if resource_id in existing:
        row_id = existing[resource_id]
        client.table("resource_package_items").update({
            "sort_order": sort_order, "visibility": visibility,
        }).eq("id", row_id).execute()
        return row_id
    resp = client.table("resource_package_items").insert({
        "package_id":  package_id,
        "resource_id": resource_id,
        "sort_order":  sort_order,
        "visibility":  visibility,
    }).execute()
    if resp.data:
        new_id = resp.data[0]["id"]
        existing[resource_id] = new_id
        return new_id
    return None


# ---------------------------------------------------------------------------
# Discover packages for a subject
# ---------------------------------------------------------------------------

def _discover_packages(subject_path: Path) -> list[Path]:
    """Return resource_package_v* folders sorted by version ascending."""
    folders = [
        p for p in subject_path.iterdir()
        if p.is_dir() and re.match(r"resource_package_v\d+$", p.name)
    ]
    return sorted(folders, key=lambda p: _version_from_folder(p.name))


# ---------------------------------------------------------------------------
# Build resource row from publish_package entry + teacher payload entry
# ---------------------------------------------------------------------------

def _build_resource_row(
    res: dict,
    teacher_map: dict[str, dict],
    subject_id: str,
    org_id: str,
    adapter_status: str,
    skill_unit_index: dict[tuple, str],
    package_active: bool,
) -> dict:
    resource_id  = res["resource_id"]
    resource_type= res.get("resource_type", "unknown")
    topic        = res.get("topic", "")
    skill_type   = res.get("skill_type", "unknown")
    difficulty   = res.get("difficulty", "unknown")

    # Best-effort skill_unit link
    su_id = skill_unit_index.get((topic, skill_type))

    # Teacher-enriched fields
    teacher_res  = teacher_map.get(resource_id, res)
    worked_sol   = teacher_res.get("worked_solution") or res.get("worked_solution")
    marking_guid = teacher_res.get("marking_guidance") or res.get("marking_guidance")
    teacher_note = teacher_res.get("teacher_note") or res.get("teacher_note")
    common_misc  = teacher_res.get("common_misconception") or res.get("common_misconception")
    common_misc_list = [common_misc] if common_misc else []

    orig_stmt    = res.get("originality_statement", "Original Quanta Aptus content.")
    val_status   = res.get("validation_status", teacher_res.get("validation_status", ""))
    bank_status  = res.get("bank_status", teacher_res.get("bank_status", ""))

    needs_review = not (val_status == "passed" and bank_status == "publish_ready")
    pub_status   = "published" if (package_active and not needs_review) else (
                   "teacher_review" if needs_review else "approved"
    )

    return {
        "subject_id":             subject_id,
        "organization_id":        org_id,
        "source_skill_unit_id":   su_id,
        "resource_key":           resource_id,
        "title":                  _resource_title(resource_type, topic),
        "topic":                  topic,
        "subtopic":               "",
        "skill_type":             skill_type,
        "resource_type":          resource_type,
        "difficulty":             difficulty if difficulty in ("easy","medium","hard") else "unknown",
        "estimated_time_minutes": res.get("estimated_time_minutes"),
        "student_prompt":         res.get("student_prompt"),
        "worked_solution":        worked_sol,
        "marking_guidance":       marking_guid,
        "common_misconceptions":  json.dumps(common_misc_list),
        "teacher_notes":          teacher_note,
        "originality_statement":  orig_stmt,
        "copyright_status":       "original_generated",
        "adapter_status":         adapter_status,
        "confidence":             None,
        "needs_human_review":     needs_review,
        "publish_status":         pub_status,
    }


# ---------------------------------------------------------------------------
# Per-subject sync
# ---------------------------------------------------------------------------

def sync_subject(
    client,
    subject_slug: str,
    subject_row: dict,
    org_id: str,
) -> dict:
    subject_id     = subject_row["id"]
    adapter_status = subject_row.get("adapter_status", "basic_adapter")

    result = {
        "subject_slug":            subject_slug,
        "packages_found":          0,
        "packages_upserted":       0,
        "resources_found":         0,
        "resources_upserted":      0,
        "package_items_upserted":  0,
        "teacher_only_count":      0,
        "needs_human_review_count":0,
        "failed_packages":         0,
        "failed_resources":        0,
        "failed_items":            0,
        "warnings":                [],
        "errors":                  [],
    }

    subject_path = PUBLISH_ROOT / subject_slug
    packages     = _discover_packages(subject_path)

    if not packages:
        result["warnings"].append(f"No resource_package_v* folders found for {subject_slug}.")
        return result

    result["packages_found"] = len(packages)
    max_version = _version_from_folder(packages[-1].name)

    # Pre-fetch caches
    skill_unit_index = _fetch_skill_unit_index(client, subject_id)
    existing_pkgs    = _fetch_existing_packages(client, subject_id)
    existing_res     = _fetch_existing_resources(client, subject_id)

    for pkg_folder in packages:
        version = _version_from_folder(pkg_folder.name)
        is_latest = (version == max_version)

        # ── Load package files ─────────────────────────────────────────────
        # Find the highest-versioned files in the folder
        pub_files = sorted(pkg_folder.glob("publish_package_v*.json"),
                           key=lambda p: _version_from_folder(p.stem))
        teacher_files = sorted(pkg_folder.glob("teacher_resource_payload_v*.json"),
                               key=lambda p: _version_from_folder(p.stem))
        student_files = sorted(pkg_folder.glob("student_resource_payload_v*.json"),
                               key=lambda p: _version_from_folder(p.stem))
        report_files  = sorted(pkg_folder.glob("resource_package_v*_report.json"),
                               key=lambda p: _version_from_folder(p.stem))

        pub_doc     = _load(pub_files[-1])     if pub_files     else None
        teacher_doc = _load(teacher_files[-1]) if teacher_files else None
        student_doc = _load(student_files[-1]) if student_files else None
        report_doc  = _load(report_files[-1])  if report_files  else None

        if pub_doc is None and teacher_doc is None:
            result["warnings"].append(f"{pkg_folder.name}: no publish_package or teacher payload found.")
            continue

        master_doc   = pub_doc or teacher_doc
        package_key  = master_doc.get("package_id", f"{subject_slug}_resource_package_v{version}")
        resource_count         = master_doc.get("resource_count", 0)
        student_resource_count = (student_doc or {}).get("resource_count", 0)
        teacher_resource_count = (teacher_doc or {}).get("resource_count", resource_count)
        pkg_status   = "active" if is_latest else "archived"
        published_at = datetime.now(timezone.utc).isoformat() if pkg_status == "active" else None

        # ── Upsert resource_packages ──────────────────────────────────────
        pkg_row = {
            "subject_id":              subject_id,
            "package_key":             package_key,
            "version":                 version,
            "title":                   f"Cambridge IGCSE {subject_slug.replace('_',' ').title()} Resource Package v{version}",
            "status":                  pkg_status,
            "resource_count":          resource_count,
            "student_resource_count":  student_resource_count,
            "teacher_resource_count":  teacher_resource_count,
            "published_at":            published_at,
        }
        try:
            package_db_id = _upsert_package(client, pkg_row, existing_pkgs)
            if package_db_id:
                result["packages_upserted"] += 1
            else:
                result["failed_packages"] += 1
                result["errors"].append(f"No id returned for package {package_key}")
                continue
        except Exception as exc:
            result["failed_packages"] += 1
            result["errors"].append(f"Package {package_key}: {str(exc)[:120]}")
            continue

        # ── Build lookup maps ─────────────────────────────────────────────
        resources_list = master_doc.get("resources", [])
        result["resources_found"] += len(resources_list)

        teacher_map: dict[str, dict] = {}
        for r in (teacher_doc or {}).get("resources", []):
            teacher_map[r["resource_id"]] = r

        student_ids: set[str] = {
            r["resource_id"]
            for r in (student_doc or {}).get("resources", [])
        }

        existing_items = _fetch_existing_pkg_items(client, package_db_id)

        # ── Upsert resources + package items ──────────────────────────────
        for sort_order, res in enumerate(resources_list):
            resource_id = res.get("resource_id", "")
            if not resource_id:
                result["warnings"].append("Resource with no resource_id — skipped.")
                continue

            # Determine visibility
            visibility = "student" if resource_id in student_ids else "teacher_only"
            if visibility == "teacher_only":
                result["teacher_only_count"] += 1

            # Build resource row
            try:
                res_row = _build_resource_row(
                    res, teacher_map, subject_id, org_id,
                    adapter_status, skill_unit_index, is_latest,
                )
            except Exception as exc:
                result["failed_resources"] += 1
                result["errors"].append(f"Build resource {resource_id[:60]}: {str(exc)[:100]}")
                continue

            if res_row.get("needs_human_review"):
                result["needs_human_review_count"] += 1

            # Upsert resource
            try:
                res_db_id = _upsert_resource(client, res_row, existing_res)
                if res_db_id:
                    result["resources_upserted"] += 1
                else:
                    result["failed_resources"] += 1
                    result["errors"].append(f"No id returned for resource {resource_id[:60]}")
                    continue
            except Exception as exc:
                result["failed_resources"] += 1
                result["errors"].append(f"Resource {resource_id[:60]}: {str(exc)[:120]}")
                continue

            # Upsert package item
            try:
                item_id = _upsert_pkg_item(
                    client, package_db_id, res_db_id,
                    sort_order, visibility, existing_items,
                )
                if item_id:
                    result["package_items_upserted"] += 1
                else:
                    result["failed_items"] += 1
                    result["errors"].append(f"No id returned for pkg_item {resource_id[:60]}")
            except Exception as exc:
                result["failed_items"] += 1
                result["errors"].append(f"PkgItem {resource_id[:60]}: {str(exc)[:120]}")

    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(
    now_iso: str,
    subject_results: list[dict],
    top_errors: list[str],
) -> Path:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DIAG_DIR / "supabase_resources_packages_sync_report_v1.json"

    total_pkgs   = sum(r["packages_upserted"]      for r in subject_results)
    total_res    = sum(r["resources_upserted"]      for r in subject_results)
    total_items  = sum(r["package_items_upserted"]  for r in subject_results)
    total_to     = sum(r["teacher_only_count"]      for r in subject_results)
    total_nhr    = sum(r["needs_human_review_count"]for r in subject_results)
    total_failed = sum(
        r["failed_packages"] + r["failed_resources"] + r["failed_items"]
        for r in subject_results
    )
    all_errs     = top_errors + [e for r in subject_results for e in r["errors"]]
    all_warns    = [w for r in subject_results for w in r["warnings"]]

    status = (
        "passed"       if total_failed == 0 and not top_errors
        else "needs_review" if total_res > 0
        else "failed"
    )

    clean = [{k: v for k, v in r.items() if k != "warnings"} for r in subject_results]

    report = {
        "report_id":                         "quanta_aptus_supabase_resources_packages_sync_v1",
        "gate":                              "53E",
        "created_at":                        now_iso,
        "status":                            status,
        "synced_subjects":                   [r["subject_slug"] for r in subject_results],
        "packages_found":                    sum(r["packages_found"] for r in subject_results),
        "packages_upserted":                 total_pkgs,
        "resources_found":                   sum(r["resources_found"] for r in subject_results),
        "resources_upserted":                total_res,
        "package_items_upserted":            total_items,
        "teacher_only_resource_count":       total_to,
        "needs_human_review_count":          total_nhr,
        "failed_count":                      total_failed,
        "warnings":                          all_warns,
        "errors":                            all_errs,
        "copyright_safety": {
            "uploaded_raw_pdfs":                  False,
            "uploaded_extracted_text":            False,
            "synced_generated_resources_only":    True,
            "source_text_copied_to_resources":    False,
        },
        "subjects":                          clean,
        "next_gate":                         "Gate 53F - Read Active Package from Supabase",
    }

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()

    from supabase_client_v1 import get_supabase_service_client, mask_secret

    print("=" * 60)
    print("Quanta Aptus - Sync Resources + Packages v1")
    print("=" * 60)

    client, url = get_supabase_service_client()
    print(f"  connected  : {mask_secret(url)}")

    org_id = _fetch_org_id(client)
    if not org_id:
        print("[ERROR] Organization 'quanta-aptus-local-demo' not found. Run seed first.")
        sys.exit(1)

    # ── Determine subjects ─────────────────────────────────────────────────
    if len(sys.argv) > 1:
        slugs = [sys.argv[1]]
    else:
        slugs = sorted(
            p.name for p in PUBLISH_ROOT.iterdir()
            if p.is_dir() and any(_discover_packages(p))
        )

    print(f"  subjects   : {slugs}")

    subject_results: list[dict] = []
    top_errors: list[str] = []

    for slug in slugs:
        print(f"\n  [{slug}]")

        subject_row = _fetch_subject_row(client, slug)
        if not subject_row:
            msg = f"Subject '{slug}' not found in Supabase subjects table. Skipping."
            print(f"    SKIP: {msg}")
            top_errors.append(msg)
            subject_results.append({
                "subject_slug": slug, "packages_found": 0, "packages_upserted": 0,
                "resources_found": 0, "resources_upserted": 0,
                "package_items_upserted": 0, "teacher_only_count": 0,
                "needs_human_review_count": 0, "failed_packages": 0,
                "failed_resources": 0, "failed_items": 0,
                "warnings": [], "errors": [msg],
            })
            continue

        result = sync_subject(client, slug, subject_row, org_id)
        subject_results.append(result)

        for pkg_f in _discover_packages(PUBLISH_ROOT / slug):
            v = _version_from_folder(pkg_f.name)
            print(f"    package v{v}  : {pkg_f.name}")

        print(f"    packages_up    : {result['packages_upserted']}")
        print(f"    resources_found: {result['resources_found']}")
        print(f"    resources_up   : {result['resources_upserted']}")
        print(f"    items_up       : {result['package_items_upserted']}")
        print(f"    teacher_only   : {result['teacher_only_count']}")
        if result["needs_human_review_count"]:
            print(f"    needs_review   : {result['needs_human_review_count']}")
        if result["warnings"]:
            for w in result["warnings"]:
                print(f"    WARN: {w[:90]}")
        if result["errors"]:
            for e in result["errors"]:
                print(f"    ERROR: {e[:90]}")

    # ── Totals ────────────────────────────────────────────────────────────
    total_pkgs   = sum(r["packages_upserted"]     for r in subject_results)
    total_res    = sum(r["resources_upserted"]     for r in subject_results)
    total_items  = sum(r["package_items_upserted"] for r in subject_results)
    total_failed = sum(
        r["failed_packages"] + r["failed_resources"] + r["failed_items"]
        for r in subject_results
    )
    status = (
        "passed"       if total_failed == 0 and not top_errors
        else "needs_review" if total_res > 0
        else "failed"
    )

    print(f"\n  packages_upserted  : {total_pkgs}")
    print(f"  resources_upserted : {total_res}")
    print(f"  items_upserted     : {total_items}")
    print(f"  failed_count       : {total_failed}")
    print(f"  status             : {status.upper()}")

    report_path = write_report(now_iso, subject_results, top_errors)
    print(f"  report             -> {report_path}")

    sys.exit(0 if status in ("passed", "needs_review") else 1)


if __name__ == "__main__":
    main()
