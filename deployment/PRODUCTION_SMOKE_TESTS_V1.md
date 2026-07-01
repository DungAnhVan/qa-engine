# Production Smoke Tests v1

Run these scripts after any deployment, environment change, or DNS update to
verify the production app is healthy.

---

## Gate 65 — Full Route Smoke Test (Vercel URL)

Tests all 8 key routes on the Vercel default URL.

```powershell
.\.venv-ingest\Scripts\python.exe tools\deploy\test_gate65_post_deploy_smoke_v1.py https://qa-engine-admin.vercel.app
```

Then build the report:

```powershell
.\.venv-ingest\Scripts\python.exe tools\deploy\build_gate65_post_deploy_report_v1.py
```

Output: `data/diagnostics/gate65_post_deploy_smoke_test_report_v1.json`

---

## Gate 66 — Demo User Safety Check

Verifies demo accounts exist (expected before cleanup) and production env is safe.

```powershell
.\.venv-ingest\Scripts\python.exe tools\deploy\check_gate66_demo_user_safety_v1.py https://qa-engine-admin.vercel.app
```

Then build the report:

```powershell
.\.venv-ingest\Scripts\python.exe tools\deploy\build_gate66_demo_safety_report_v1.py
```

Output: `data/diagnostics/gate66_demo_user_safety_check_v1.json`

---

## Gate 67 — Custom Domain Smoke Test

Verifies the custom domain `admin.quantaaptus.com` is live and healthy.
Run only after DNS is configured and Vercel domain is verified.

```powershell
.\.venv-ingest\Scripts\python.exe tools\deploy\test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com
```

Then build the report:

```powershell
.\.venv-ingest\Scripts\python.exe tools\deploy\build_gate67_custom_domain_report_v1.py
```

Output: `data/diagnostics/gate67_custom_domain_smoke_test_report_v1.json`

---

## Expected Results

| Check | Expected Value |
|---|---|
| Health API status | `ok` |
| Readiness API status | `ready` or `needs_review` |
| Login page | HTTP 200, "Sign in" text present |
| Secrets in responses | `false` |
| `content_source` | `live_supabase` |
| `demo_fallback` | `false` |
| `demo_safety.public_launch_safe` | `false` — correct until demo passwords rotated |
| `demo_safety.internal_testing_safe` | `true` |
| Gate 67 `custom_domain_used` | `true` |
| Gate 67 `routes_passed` | `8/8` |

---

## Security Patterns Checked

All smoke tests scan response bodies for:

| Pattern | Description |
|---|---|
| `eyJ...` (300+ chars) | JWT-format key value leaked into response |
| `sb_sec_...` (20+ chars) | Supabase new key format value |
| `sk-...` (40+ chars) | OpenAI API key value |
| `sk-ant-...` (50+ chars) | Anthropic API key value |
| `SUPABASE_SERVICE_ROLE_KEY=...` | Key assignment in response |
| `data/raw/` | Raw Cambridge material path |
| `original_raw_block` | Raw source field exposed |
| `normalized_raw_block` | Normalized source field exposed |

> Diagnostic pages display `SUPABASE_SERVICE_ROLE_KEY` as a **label** (not value) — this
> is expected and not flagged. Only actual key values and assignments are flagged.

---

## Running All Smoke Tests

```powershell
# Full sequence (replace URLs as needed)
.\.venv-ingest\Scripts\python.exe tools\deploy\test_gate65_post_deploy_smoke_v1.py https://qa-engine-admin.vercel.app
.\.venv-ingest\Scripts\python.exe tools\deploy\check_gate66_demo_user_safety_v1.py https://qa-engine-admin.vercel.app
.\.venv-ingest\Scripts\python.exe tools\deploy\test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com

# Report builders
.\.venv-ingest\Scripts\python.exe tools\deploy\build_gate65_post_deploy_report_v1.py
.\.venv-ingest\Scripts\python.exe tools\deploy\build_gate66_demo_safety_report_v1.py
.\.venv-ingest\Scripts\python.exe tools\deploy\build_gate67_custom_domain_report_v1.py
.\.venv-ingest\Scripts\python.exe tools\deploy\build_gate68_mvp_freeze_report_v1.py
```

---

## Report Files

| File | Description |
|---|---|
| `data/diagnostics/gate65_post_deploy_smoke_test_report_v1.json` | Route smoke test results |
| `data/diagnostics/gate65_post_deploy_report_v1.json` | Gate 65 summary report |
| `data/diagnostics/gate66_demo_user_safety_check_v1.json` | Demo safety raw check |
| `data/diagnostics/gate66_demo_safety_report_v1.json` | Gate 66 summary report |
| `data/diagnostics/gate67_custom_domain_smoke_test_report_v1.json` | Custom domain smoke results |
| `data/diagnostics/gate67_custom_domain_report_v1.json` | Gate 67 summary report |
| `data/diagnostics/gate68_mvp_freeze_report_v1.json` | Gate 68 MVP freeze report |
