"""
Gate 67 -- Custom Domain Smoke Test v1

Verifies the admin app is reachable and healthy at a custom domain
(expected: admin.quantaaptus.com). Must be run AFTER DNS is configured
and Vercel verifies the domain.

Usage:
  .venv-ingest\\Scripts\\python.exe tools\\deploy\\test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com

Output: data/diagnostics/gate67_custom_domain_smoke_test_report_v1.json
"""

import sys
import json
import re
import time
import datetime
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "gate67_custom_domain_smoke_test_report_v1.json"

VERCEL_DEFAULT_HOSTNAME = "qa-engine-admin.vercel.app"

REQUEST_TIMEOUT = 20

# Routes to test: (path, expect_json, expected_status_codes, html_marker)
ROUTES = [
    ("/",                         False, [200, 301, 302, 307, 308], None),
    ("/login",                    False, [200],                     "Sign in"),
    ("/system/health",            False, [200],                     None),
    ("/system/readiness",         False, [200],                     None),
    ("/api/system/health",        True,  [200],                     None),
    ("/api/system/readiness",     True,  [200],                     None),
    ("/system/auth-session",      False, [200],                     None),
    ("/system/demo-safety",       False, [200],                     None),
]

# Security patterns — scan response bodies for actual SECRET VALUES or paths.
# Patterns deliberately avoid flagging diagnostic variable-name labels
# (e.g. "SUPABASE_SERVICE_ROLE_KEY present") — only actual exposures are flagged.
SECURITY_PATTERNS = [
    # JWT-format key values (300+ chars): service role key, JWT sessions
    ("Supabase key value (JWT 300+ chars)",
        re.compile(r'eyJ[A-Za-z0-9+/=_-]{300,}')),
    # New Supabase key format (sb_sec_ prefix + value)
    ("Supabase service key value (sb_sec_ prefix)",
        re.compile(r'sb_sec_[A-Za-z0-9]{20,}')),
    # OpenAI API key value
    ("OpenAI API key value (sk-...)",
        re.compile(r'sk-[A-Za-z0-9]{40,}')),
    # Anthropic API key value
    ("Anthropic API key value (sk-ant-...)",
        re.compile(r'sk-ant-[A-Za-z0-9\-_]{50,}')),
    # Service role key in an ASSIGNMENT context (not a label)
    ("SUPABASE_SERVICE_ROLE_KEY assignment",
        re.compile(r'SUPABASE_SERVICE_ROLE_KEY\s*[=:]\s*["\']?[A-Za-z0-9+/=_\-]{20,}')),
    # Other API key assignments
    ("OPENAI_API_KEY assignment",
        re.compile(r'OPENAI_API_KEY\s*=\s*["\'][^\s"\']{10,}')),
    ("ANTHROPIC_API_KEY assignment",
        re.compile(r'ANTHROPIC_API_KEY\s*=\s*["\'][^\s"\']{10,}')),
    # Raw Cambridge content paths and fields
    ("data/raw path in response",
        re.compile(r'data[/\\]raw[/\\]')),
    ("original_raw_block field",
        re.compile(r'original_raw_block')),
    ("normalized_raw_block field",
        re.compile(r'normalized_raw_block')),
]

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def fetch(url: str) -> dict:
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "QA-Gate67-DomainSmoke/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read(256 * 1024)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            return {
                "status_code": resp.status,
                "final_url":   resp.url,
                "body_text":   body.decode("utf-8", errors="replace"),
                "elapsed_ms":  elapsed_ms,
                "error":       None,
            }
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        try:
            body = exc.read(32 * 1024).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return {
            "status_code": exc.code,
            "final_url":   url,
            "body_text":   body,
            "elapsed_ms":  elapsed_ms,
            "error":       f"HTTP {exc.code}: {exc.reason}",
        }
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return {
            "status_code": 0,
            "final_url":   url,
            "body_text":   "",
            "elapsed_ms":  elapsed_ms,
            "error":       str(exc)[:200],
        }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def scan_for_secrets(body: str) -> list[str]:
    findings = []
    for label, pattern in SECURITY_PATTERNS:
        if pattern.search(body):
            findings.append(label)
    return findings


def test_route(base_url: str, path: str, expect_json: bool,
               expected_codes: list[int], html_marker: str | None) -> dict:
    url = base_url.rstrip("/") + path
    result = fetch(url)

    status_ok = result["status_code"] in expected_codes
    body      = result["body_text"]
    secrets   = scan_for_secrets(body)

    json_data  = None
    json_error = None
    if expect_json and result["status_code"] == 200:
        try:
            json_data = json.loads(body)
        except Exception as exc:
            json_error = str(exc)[:100]

    marker_found = True
    if html_marker and result["status_code"] == 200 and not expect_json:
        marker_found = html_marker in body

    overall_ok = status_ok and not secrets and json_error is None and marker_found

    return {
        "path":          path,
        "url":           url,
        "status_code":   result["status_code"],
        "elapsed_ms":    result["elapsed_ms"],
        "status_ok":     status_ok,
        "secrets_found": secrets,
        "json_data":     json_data,
        "json_error":    json_error,
        "marker_found":  marker_found,
        "error":         result["error"],
        "pass":          overall_ok,
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    if not base_url.startswith("http"):
        print(f"ERROR: base_url must start with http(s): {base_url}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    hostname = urllib.parse.urlparse(base_url).hostname or ""
    custom_domain_used = hostname.lower() != VERCEL_DEFAULT_HOSTNAME.lower()

    print("Gate 67 -- Custom Domain Smoke Test")
    print(f"Base URL: {base_url}")
    print(f"Hostname: {hostname}")
    if not custom_domain_used:
        print(f"  WARNING: hostname is the Vercel default ({VERCEL_DEFAULT_HOSTNAME})")
        print(f"  This test is intended for a custom domain — configure DNS first")
    else:
        print(f"  + Custom domain confirmed (not Vercel default)")
    print("-" * 60)

    route_results  = []
    all_secrets: list[str] = []

    for path, expect_json, expected_codes, html_marker in ROUTES:
        r = test_route(base_url, path, expect_json, expected_codes, html_marker)
        route_results.append(r)
        all_secrets.extend(r["secrets_found"])
        icon = "+" if r["pass"] else "!"
        print(f"  {icon} [{r['status_code']:3}] {path:<38} {r['elapsed_ms']:>5}ms", end="")
        if r["secrets_found"]:
            print(f"  SECRETS: {r['secrets_found'][:2]}", end="")
        if r["error"] and r["status_code"] == 0:
            print(f"  ERR: {r['error'][:50]}", end="")
        if not r["marker_found"]:
            print(f"  marker '{html_marker}' not found", end="")
        print()

    print("-" * 60)

    # ── Summary ───────────────────────────────────────────────────────────────
    health_api    = next((r for r in route_results if r["path"] == "/api/system/health"), None)
    readiness_api = next((r for r in route_results if r["path"] == "/api/system/readiness"), None)
    login_result  = next((r for r in route_results if r["path"] == "/login"), None)

    health_ok = (
        health_api is not None
        and health_api["status_code"] == 200
        and isinstance(health_api.get("json_data"), dict)
        and health_api["json_data"].get("status") == "ok"
    )
    readiness_ok = (
        readiness_api is not None
        and readiness_api["status_code"] == 200
        and isinstance(readiness_api.get("json_data"), dict)
        and readiness_api["json_data"].get("status") in ("ready", "needs_review")
    )
    login_reachable = login_result is not None and login_result["status_code"] == 200

    content_source_live = (
        health_api is not None
        and isinstance(health_api.get("json_data"), dict)
        and health_api["json_data"].get("content_source") == "live_supabase"
    )
    demo_fallback_off = (
        health_api is not None
        and isinstance(health_api.get("json_data"), dict)
        and health_api["json_data"].get("demo_fallback") == "false"
    )

    secrets_exposed  = bool(all_secrets)
    routes_passed    = sum(1 for r in route_results if r["pass"])
    routes_total     = len(route_results)

    # Collect issues
    issues: list[str] = []
    if not custom_domain_used:
        issues.append(f"Hostname is Vercel default ({VERCEL_DEFAULT_HOSTNAME}) — configure custom domain first")
    if not health_ok:
        issues.append("Health API not returning status:ok")
    if not readiness_ok:
        val = readiness_api["json_data"].get("status") if readiness_api and readiness_api.get("json_data") else "unknown"
        issues.append(f"Readiness API status is '{val}' (expected ready or needs_review)")
    if not login_reachable:
        issues.append("Login page not reachable (HTTP 200)")
    if secrets_exposed:
        issues.append(f"Secrets found in responses: {list(set(all_secrets))}")
    if not content_source_live:
        src = health_api["json_data"].get("content_source") if health_api and health_api.get("json_data") else "unknown"
        issues.append(f"content_source is '{src}', expected live_supabase")
    if not demo_fallback_off:
        issues.append("QA_AUTH_DEMO_FALLBACK is not false in production")
    for r in route_results:
        if not r["pass"] and r["status_code"] == 0:
            issues.append(f"Connection error on {r['path']}: {r['error']}")

    # Overall status
    critical_ok = health_ok and login_reachable and not secrets_exposed and custom_domain_used
    if not critical_ok:
        overall_status = "failed"
    elif not readiness_ok or not content_source_live or not demo_fallback_off or routes_passed < routes_total:
        overall_status = "needs_review"
    else:
        overall_status = "passed"

    print(f"Custom domain used  : {custom_domain_used}")
    print(f"Routes passed       : {routes_passed}/{routes_total}")
    print(f"Health API          : {'OK' if health_ok else 'FAIL'}")
    print(f"Readiness API       : {'OK' if readiness_ok else 'FAIL'}")
    print(f"Login               : {'reachable' if login_reachable else 'FAIL'}")
    print(f"Content source      : {'live_supabase' if content_source_live else 'NOT live'}")
    print(f"Demo fallback off   : {demo_fallback_off}")
    print(f"Secrets exposed     : {secrets_exposed}")
    print(f"Status              : {overall_status}")
    if issues:
        print("Issues:")
        for i in issues:
            print(f"  - {i}")

    report = {
        "gate":                       "67",
        "title":                      "Custom Domain Smoke Test v1",
        "generated_at":               datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "base_url":                   base_url,
        "hostname":                   hostname,
        "status":                     overall_status,
        "custom_domain_used":         custom_domain_used,
        "routes_tested":              routes_total,
        "routes_passed":              routes_passed,
        "health_ok":                  health_ok,
        "readiness_ok":               readiness_ok,
        "login_reachable":            login_reachable,
        "content_source_live_supabase": content_source_live,
        "demo_fallback_off":          demo_fallback_off,
        "secrets_exposed":            secrets_exposed,
        "issues":                     issues,
        "routes":                     route_results,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
