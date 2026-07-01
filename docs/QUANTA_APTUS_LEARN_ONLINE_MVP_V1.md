# Quanta Aptus Learn Online MVP v1

## MVP Status

**Frozen: Gate 68 — Production MVP Freeze**

The Quanta Aptus Learn Online MVP v1 is deployed and operational for internal testing.
Public launch remains blocked until demo account credentials are rotated or removed.

---

## Production URLs

| URL | Purpose | Status |
|---|---|---|
| `https://admin.quantaaptus.com` | Admin app (custom domain) | live |
| `https://qa-engine-admin.vercel.app` | Admin app (Vercel default) | live (always available) |

---

## What Works

### Infrastructure
- Vercel deployment (GitHub auto-deploy on push to `main`)
- Custom domain `admin.quantaaptus.com` verified and SSL issued
- Supabase connection (live_supabase mode)
- Environment variables correctly set in Vercel (production)

### Authentication
- Supabase Auth login via email/password
- Session handling via server-side cookies
- Role-based access control (admin / teacher / student / parent)
- `QA_AUTH_DEMO_FALLBACK=false` in production
- Row Level Security (RLS) enabled on all tables

### Content & Data
- Live Supabase read (Gate 55) — active package `physics_0625`
- Student attempt write (Gate 56)
- AI/rule-based marking (Gate 57)
- Teacher attempt review (Gate 58)
- Student results view (Gate 59)

### System Diagnostics
- `/system/health` — app health status
- `/system/readiness` — production readiness checks
- `/system/auth-session` — current session diagnostic
- `/system/demo-safety` — demo account safety status
- `/system/role-access` — route access matrix by role
- `/api/system/health` — JSON health API
- `/api/system/readiness` — JSON readiness API
- `/api/system/demo-safety` — JSON safety status API

---

## Gate Summary Table

| Gate | Title | Status |
|---|---|---|
| 30–40 | Local MVP content pipeline | done |
| 41–50 | Local MVP app (practice, marking, results) | done |
| 51 | Supabase schema foundation | done |
| 52 | Supabase schema ready | done |
| 53A–F | Supabase sync/export/import pipeline | done |
| 54 | Export cleanup and validation | done |
| 55 | Live Supabase read | done |
| 56 | Student attempt write | done |
| 57 | Supabase marking | done |
| 58 | Teacher attempt review | done |
| 59 | Student results | done |
| 60 | Auth roles foundation | done |
| 61 | Login UI + RLS tests | done |
| 62 | RLS hardening + role-based access | done |
| 63 | Production deployment prep | done |
| 64 | Vercel deployment | done |
| 65 | Post-deploy smoke test | done |
| 65B | Production readiness runtime patch | done |
| 66 | Production demo safety cleanup | done |
| 67 | Custom domain prep | done |
| **68** | **Production MVP Freeze + Handoff** | **current** |

---

## Current Backend

| Component | Provider | Notes |
|---|---|---|
| Frontend hosting | Vercel | project: qa-engine-admin |
| Database + Auth | Supabase | live_supabase mode |
| Code repository | GitHub | DungAnhVan/qa-engine |
| Landing page DNS | Netlify DNS | quantaaptus.com apex and www unchanged |
| Admin subdomain | Vercel via CNAME | admin.quantaaptus.com → Vercel |

---

## Current Data

| Item | Value | Notes |
|---|---|---|
| Active package | `physics_0625` | Cambridge A-Level Physics, June 2025 |
| Demo admin user | `admin@quantaaptus.local` | password documented — must be rotated before public launch |
| Demo teacher | `teacher@quantaaptus.local` | password documented |
| Demo student | `student@quantaaptus.local` | password documented |
| Demo parent | `parent@quantaaptus.local` | password documented |

---

## Known Limitations

### Immediate (before public launch)
- **Demo user passwords** are documented in the repository. All 4 demo accounts
  (`@quantaaptus.local`) must have their passwords rotated or the accounts must be
  disabled/deleted before any real-user traffic.
- **`public_launch_safe: false`** — the system correctly reports this via the demo safety API.
- No real admin account (`admin@quantaaptus.com`) has been created yet.

### Content and Features
- AI content factory (automated question import from PDF) not yet enabled in production.
- Raw PDF upload UI not yet built.
- Graph/image-based questions require teacher manual review (no automated image marking).
- Only Cambridge A-Level Physics (`physics_0625`) is loaded. Additional subjects/packages
  require the content pipeline to re-run with new source material.

### Platform
- No billing or subscription management.
- Parent UX is basic (list view only, no detailed progress reports).
- Student-facing UX is admin-tool quality — not yet polished for consumer use.
- No full student-facing production app (`learn.quantaaptus.com`) yet.
- Role management UI is diagnostic only — no admin UI for assigning roles.
- No email notifications for marking completion or assignment submission.

---

## Recommended Next Phases

### Phase 3A — Production Hardening (immediate priority)
- Rotate/remove demo accounts
- Create real admin user (`admin@quantaaptus.com`)
- RLS audit confirmation
- Supabase Auth email verification enabled
- Monitoring/alerts setup (Vercel analytics, Supabase usage alerts)
- Custom domain for student app (`learn.quantaaptus.com`)

### Phase 3B — AI Content Factory
- Re-enable automated PDF → question pipeline
- Add more Cambridge subjects and years
- Tag questions by topic, difficulty, skill
- Bulk import UI

### Phase 3C — Student and Parent UX
- Polish student practice interface for consumer use
- Parent dashboard with progress over time
- Email notifications (marking complete, new assignments)
- Mobile-responsive redesign

### Phase 3D — Subscription and Growth Loop
- Billing integration (Stripe or similar)
- Free tier / paid tier distinction
- Referral / school purchase flow
- Usage analytics

---

## Security Notes (MVP)

- `SUPABASE_SERVICE_ROLE_KEY` is server-side only — never in `NEXT_PUBLIC_` vars
- RLS is enabled on all tables — profiles, attempts, markings, packages
- `QA_AUTH_DEMO_FALLBACK=false` in Vercel production env
- No secrets in git repository (`.env.local` is gitignored)
- Diagnostic pages show env var presence (true/false) only — never values
