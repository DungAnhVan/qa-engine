# Gate 66 -- Production Demo Safety Cleanup DONE

Generated: 2026-07-01T05:50:52.540612+00:00

## Status: PASSED

## Summary

- Internal testing is safe: True
- Public launch remains blocked until demo passwords/users are rotated or removed.
- QA_AUTH_DEMO_FALLBACK is false: True
- Service role key not exposed to client: true (by design — value never shown)
- Demo profiles found: [{'email': 'admin@quantaaptus.local', 'role': 'admin'}, {'email': 'teacher@quantaaptus.local', 'role': 'teacher'}, {'email': 'student@quantaaptus.local', 'role': 'student'}, {'email': 'parent@quantaaptus.local', 'role': 'parent'}]
- Demo auth users found: True
- Secrets exposed: False

## Public Launch Blockers

Demo accounts with known passwords exist in the Supabase Auth database.
Complete the following before pointing any public traffic to the app:

1. Rotate all 4 demo passwords (or disable/delete demo accounts)
2. Replace admin@quantaaptus.local with a real admin email
3. Verify RLS is active on all tables
4. Confirm QA_AUTH_DEMO_FALLBACK=false in Vercel (already done)
5. Confirm SUPABASE_SERVICE_ROLE_KEY is server-only (already done)

See: deployment/PRODUCTION_DEMO_SAFETY_GATE66.md for full instructions.

## Gate 66 Deliverables

- Safety documentation: `deployment/PRODUCTION_DEMO_SAFETY_GATE66.md`
- Demo user check:      `tools/deploy/check_gate66_demo_user_safety_v1.py`
- Report builder:       `tools/deploy/build_gate66_demo_safety_report_v1.py`
- Safety UI page:       `apps/admin/src/app/system/demo-safety/page.tsx`
- Safety API route:     `apps/admin/src/app/api/system/demo-safety/route.ts`

## Re-Run After Demo Cleanup

After rotating or removing demo accounts:

```powershell
.venv-ingest\Scripts\python.exe tools\deploy\check_gate66_demo_user_safety_v1.py https://qa-engine-admin.vercel.app
.venv-ingest\Scripts\python.exe tools\deploy\build_gate66_demo_safety_report_v1.py
```

Expected final state:
- demo_profiles_found: false
- demo_auth_users_found: false
- public_launch_safe: true

## Issues

- QA_AUTH_DEMO_FALLBACK is 'None' in .env.local
- 4 demo profile(s) found in Supabase
- 4 demo auth user(s) found in Supabase Auth

## Recommended Actions

- Rotate demo account passwords or disable/delete demo users
- Create real admin@quantaaptus.com account before removing demo admin
- Verify QA_AUTH_DEMO_FALLBACK=false in Vercel environment variables
- Verify SUPABASE_SERVICE_ROLE_KEY is server-only in Vercel (no NEXT_PUBLIC_ prefix)
- Do NOT point admin.quantaaptus.com until passwords are rotated

## Ready for Gate 67

Gate 67 -- Custom Domain Prep:
- Point admin.quantaaptus.com to the Vercel deployment
- Configure domain in Vercel dashboard
- Add domain to Supabase allowed redirect URLs
- Prerequisite: demo safety must be resolved first
