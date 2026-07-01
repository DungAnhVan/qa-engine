# Gate 67 -- Custom Domain Prep DONE

Generated: 2026-07-01T06:22:57.724470+00:00

## Status: NEEDS_REVIEW

## Summary

- Custom domain plan created: admin.quantaaptus.com recommended for admin app.
- quantaaptus.com landing page is preserved — no changes to @ or www DNS records.
- DNS record template created with fillable table.
- Custom domain smoke test script ready.
- Service role not exposed to client: True
- Secrets in responses: False

## DNS Status

DNS not configured yet. Run after Vercel + DNS setup:
.venv-ingest\Scripts\python.exe tools\deploy\test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com

## Gate 67 Deliverables

- Domain guide:         `deployment/CUSTOM_DOMAIN_GATE67.md`
- DNS template:         `deployment/DNS_RECORDS_GATE67_TEMPLATE.md`
- Custom domain smoke:  `tools/deploy/test_gate67_custom_domain_smoke_v1.py`
- Report builder:       `tools/deploy/build_gate67_custom_domain_report_v1.py`

## Steps Still Required (if DNS not yet configured)

1. Open Vercel → project qa-engine-admin → Settings → Domains
2. Add: admin.quantaaptus.com
3. Copy the CNAME value Vercel shows
4. Add CNAME record at your DNS provider (name: admin, value: <from Vercel>)
5. Wait for DNS propagation (5–30 min on Cloudflare, up to 48h elsewhere)
6. Verify: https://admin.quantaaptus.com/system/health
7. Add Supabase Auth redirect URL: https://admin.quantaaptus.com/**
8. Run smoke test and report builder:
   .venv-ingest\Scripts\python.exe tools\deploy\test_gate67_custom_domain_smoke_v1.py https://admin.quantaaptus.com
   .venv-ingest\Scripts\python.exe tools\deploy\build_gate67_custom_domain_report_v1.py

## Issues

None reported from smoke test.

## Ready for Gate 68

Gate 68 -- Production MVP Freeze + Handoff:
- Final production checklist
- Demo accounts rotated or removed
- Custom domain live and verified
- Service role confirmed server-only
- RLS active
- MVP handoff documentation
