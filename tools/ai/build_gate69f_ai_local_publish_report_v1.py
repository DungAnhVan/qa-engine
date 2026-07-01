"""
Gate 69F -- Build Gate Report v1

Checks all Gate 69F deliverables and writes a human-readable gate report.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate69f_ai_local_publish_report_v1.py

Output:
  data/diagnostics/gate69f_ai_local_publish_report_v1.json
  data/diagnostics/gate69f_ai_local_publish_report_v1.md
"""

import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Deliverable manifest
# ---------------------------------------------------------------------------

DELIVERABLES = [
    {
        "id":    "D01",
        "label": "Final approval seed file",
        "path":  ROOT / "data" / "ai" / "package_candidates" / "ai_final_publish_approval_v1.json",
        "type":  "file",
    },
    {
        "id":    "D02",
        "label": "approve_ai_package_candidate_v1.py",
        "path":  ROOT / "tools" / "ai" / "approve_ai_package_candidate_v1.py",
        "type":  "file",
    },
    {
        "id":    "D03",
        "label": "build_ai_local_published_package_v1.py",
        "path":  ROOT / "tools" / "ai" / "build_ai_local_published_package_v1.py",
        "type":  "file",
    },
    {
        "id":    "D04",
        "label": "validate_ai_local_published_package_v1.py",
        "path":  ROOT / "tools" / "ai" / "validate_ai_local_published_package_v1.py",
        "type":  "file",
    },
    {
        "id":    "D05",
        "label": "render_ai_local_published_package_preview_v1.py",
        "path":  ROOT / "tools" / "ai" / "render_ai_local_published_package_preview_v1.py",
        "type":  "file",
    },
    {
        "id":    "D06",
        "label": "build_ai_local_registry_v1.py",
        "path":  ROOT / "tools" / "ai" / "build_ai_local_registry_v1.py",
        "type":  "file",
    },
    {
        "id":    "D07",
        "label": "aiPublishedPackage.ts (server lib)",
        "path":  ROOT / "apps" / "admin" / "src" / "lib" / "aiPublishedPackage.ts",
        "type":  "file",
    },
    {
        "id":    "D08",
        "label": "ai-published/page.tsx (UI page)",
        "path":  ROOT / "apps" / "admin" / "src" / "app" / "ai-published" / "page.tsx",
        "type":  "file",
    },
    {
        "id":    "D09",
        "label": "system/ai-published/page.tsx (diagnostic page)",
        "path":  ROOT / "apps" / "admin" / "src" / "app" / "system" / "ai-published" / "page.tsx",
        "type":  "file",
    },
    {
        "id":    "D10",
        "label": "api/system/ai-published/route.ts (diagnostic API)",
        "path":  ROOT / "apps" / "admin" / "src" / "app" / "api" / "system" / "ai-published" / "route.ts",
        "type":  "file",
    },
    {
        "id":    "D11",
        "label": "test_gate69f_ai_local_publish_v1.py",
        "path":  ROOT / "tools" / "ai" / "test_gate69f_ai_local_publish_v1.py",
        "type":  "file",
    },
    {
        "id":    "D12",
        "label": "build_gate69f_ai_local_publish_report_v1.py",
        "path":  ROOT / "tools" / "ai" / "build_gate69f_ai_local_publish_report_v1.py",
        "type":  "file",
    },
]

OUTPUTS = [
    {
        "id":    "O01",
        "label": "publish_package_v1.json (published_local_not_active)",
        "path":  ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "publish_package_v1.json",
    },
    {
        "id":    "O02",
        "label": "student_resource_payload_v1.json",
        "path":  ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "student_resource_payload_v1.json",
    },
    {
        "id":    "O03",
        "label": "teacher_resource_payload_v1.json",
        "path":  ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "teacher_resource_payload_v1.json",
    },
    {
        "id":    "O04",
        "label": "ai_publish_manifest_v1.md",
        "path":  ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "ai_publish_manifest_v1.md",
    },
    {
        "id":    "O05",
        "label": "student HTML preview",
        "path":  ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "static_preview" / "student_ai_published_package_preview_v1.html",
    },
    {
        "id":    "O06",
        "label": "teacher HTML preview",
        "path":  ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "static_preview" / "teacher_ai_published_package_preview_v1.html",
    },
    {
        "id":    "O07",
        "label": "ai_content_registry_v1.json",
        "path":  ROOT / "data" / "ai" / "registry" / "ai_content_registry_v1.json",
    },
    {
        "id":    "O08",
        "label": "ai_local_published_package_validation_report_v1.json",
        "path":  ROOT / "data" / "diagnostics" / "ai_local_published_package_validation_report_v1.json",
    },
    {
        "id":    "O09",
        "label": "test_gate69f_results_v1.json",
        "path":  ROOT / "data" / "diagnostics" / "test_gate69f_results_v1.json",
    },
]

POLICY_CHECKS = [
    ("active_content == false",        "publish_package_v1.json",
     ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "publish_package_v1.json",
     "active_content", False),
    ("supabase_write_performed == false", "publish_package_v1.json",
     ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "publish_package_v1.json",
     "supabase_write_performed", False),
    ("teacher_final_approval == true", "publish_package_v1.json",
     ROOT / "data" / "ai" / "published" / "ai_resource_package_v1" / "publish_package_v1.json",
     "teacher_final_approval", True),
    ("allow_active_switch == false",   "ai_final_publish_approval_v1.json",
     ROOT / "data" / "ai" / "package_candidates" / "ai_final_publish_approval_v1.json",
     "allow_active_switch", False),
    ("allow_supabase_sync == false",   "ai_final_publish_approval_v1.json",
     ROOT / "data" / "ai" / "package_candidates" / "ai_final_publish_approval_v1.json",
     "allow_supabase_sync", False),
]


# ---------------------------------------------------------------------------
# Build report
# ---------------------------------------------------------------------------

def read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def check(items: list[dict]) -> list[dict]:
    results = []
    for item in items:
        p = item["path"]
        ok = p.exists()
        results.append({
            "id":     item["id"],
            "label":  item["label"],
            "exists": ok,
            "path":   str(p.relative_to(ROOT)),
        })
    return results


def check_policy() -> list[dict]:
    results = []
    for label, file_label, path, key, expected in POLICY_CHECKS:
        data = read_json(path)
        if data is None:
            ok = False
            got = None
        else:
            got = data.get(key)
            ok = got == expected
        results.append({
            "check":  label,
            "file":   file_label,
            "key":    key,
            "expected": expected,
            "actual": got,
            "ok":     ok,
        })
    return results


now = datetime.datetime.now(datetime.timezone.utc).isoformat()

deliverable_results = check(DELIVERABLES)
output_results      = check(OUTPUTS)
policy_results      = check_policy()

test_results_data = read_json(ROOT / "data" / "diagnostics" / "test_gate69f_results_v1.json")
test_passed   = (test_results_data or {}).get("passed", 0)
test_total    = (test_results_data or {}).get("total",  0)
test_status   = (test_results_data or {}).get("status", "not_run")

d_pass = sum(1 for r in deliverable_results if r["exists"])
o_pass = sum(1 for r in output_results      if r["exists"])
p_pass = sum(1 for r in policy_results      if r["ok"])
all_ok = (
    d_pass == len(deliverable_results) and
    o_pass == len(output_results) and
    p_pass == len(policy_results) and
    test_status == "passed"
)

report = {
    "gate":             "69F",
    "name":             "AI Package Final Approval + Local Publish v1",
    "status":           "passed" if all_ok else "incomplete",
    "generated_at":     now,
    "deliverables":     deliverable_results,
    "outputs":          output_results,
    "policy":           policy_results,
    "test_results":     {
        "status": test_status,
        "passed": test_passed,
        "total":  test_total,
    },
    "summary": {
        "deliverables": f"{d_pass}/{len(deliverable_results)}",
        "outputs":      f"{o_pass}/{len(output_results)}",
        "policy":       f"{p_pass}/{len(policy_results)}",
        "tests":        f"{test_passed}/{test_total}",
    },
}

diag_dir = ROOT / "data" / "diagnostics"
diag_dir.mkdir(parents=True, exist_ok=True)
rpt_json = diag_dir / "gate69f_ai_local_publish_report_v1.json"
rpt_md   = diag_dir / "gate69f_ai_local_publish_report_v1.md"

rpt_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

lines = [
    "# Gate 69F Report — AI Package Final Approval + Local Publish v1",
    "",
    f"Generated: {now}",
    f"Status: **{'PASSED' if all_ok else 'INCOMPLETE'}**",
    "",
    "## Summary",
    f"| Category     | Result |",
    f"|:-------------|:-------|",
    f"| Deliverables | {d_pass}/{len(deliverable_results)} |",
    f"| Outputs      | {o_pass}/{len(output_results)} |",
    f"| Policy       | {p_pass}/{len(policy_results)} |",
    f"| Tests        | {test_passed}/{test_total} ({test_status}) |",
    "",
    "## Deliverables",
]
for r in deliverable_results:
    mark = "OK" if r["exists"] else "MISSING"
    lines.append(f"- [{mark}] {r['id']}: {r['label']}")

lines += ["", "## Outputs"]
for r in output_results:
    mark = "OK" if r["exists"] else "MISSING"
    lines.append(f"- [{mark}] {r['id']}: {r['label']}")

lines += ["", "## Policy Checks"]
for r in policy_results:
    mark = "OK" if r["ok"] else "FAIL"
    lines.append(f"- [{mark}] {r['check']} (actual={r['actual']})")

lines += [
    "",
    "## Safety Guarantees",
    "- `active_content: false` — AI package is NOT active production content",
    "- `supabase_write_performed: false` — No Supabase writes in this gate",
    "- `allow_active_switch: false` — Active content switch blocked",
    "- `allow_supabase_sync: false` — Supabase sync blocked",
    "- `teacher_final_approval: true` — Teacher approved before publish",
    "",
    "## Next: Gate 69G",
    "Gate 69G will handle Supabase sync and active content switch (explicit opt-in only).",
    "This package is ready when all checks above show OK and tests pass.",
]

rpt_md.write_text("\n".join(lines), encoding="utf-8")

# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

print("Gate 69F -- Gate Report v1")
print("=" * 60)
print(f"Deliverables: {d_pass}/{len(deliverable_results)}")
print(f"Outputs:      {o_pass}/{len(output_results)}")
print(f"Policy:       {p_pass}/{len(policy_results)}")
print(f"Tests:        {test_passed}/{test_total} ({test_status})")
print(f"Status:       {'PASSED' if all_ok else 'INCOMPLETE'}")
print()
print(f"JSON report:  {rpt_json.relative_to(ROOT)}")
print(f"MD report:    {rpt_md.relative_to(ROOT)}")

if not all_ok:
    print()
    print("Missing deliverables:")
    for r in deliverable_results:
        if not r["exists"]:
            print(f"  - {r['id']}: {r['path']}")
    print("Missing outputs:")
    for r in output_results:
        if not r["exists"]:
            print(f"  - {r['id']}: {r['path']}")
    print("Failed policy checks:")
    for r in policy_results:
        if not r["ok"]:
            print(f"  - {r['check']} (got {r['actual']}, want {r['expected']})")
