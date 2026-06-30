/**
 * /system/readiness — Gate 63 production readiness page.
 *
 * Server Component — all checks run server-side, no secrets shown.
 * Displays READY / NEEDS_REVIEW / FAILED based on env + file checks.
 */
import { existsSync } from 'fs'
import path from 'path'
import { getContentSourceMode } from '@/lib/contentSource'
import { isLiveSupabaseConfigured } from '@/lib/liveSupabaseContent'

export const dynamic = 'force-dynamic'

// ---------------------------------------------------------------------------
// File checks
// ---------------------------------------------------------------------------

function fileExists(relFromAdminRoot: string): boolean {
  return existsSync(path.join(process.cwd(), relFromAdminRoot))
}

function repoFileExists(relFromRoot: string): boolean {
  return existsSync(path.join(process.cwd(), '../..', relFromRoot))
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type CheckStatus = 'PASS' | 'FAIL' | 'WARN' | 'SKIP'

interface ReadinessCheck {
  label:    string
  status:   CheckStatus
  detail?:  string
  critical: boolean
}

// ---------------------------------------------------------------------------
// Checks
// ---------------------------------------------------------------------------

function buildChecks(mode: string, isLive: boolean): ReadinessCheck[] {
  const anonKeyPresent     = Boolean(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY)
  const supabaseUrlPresent = Boolean(process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL)
  const serviceRolePresent = Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY)
  const demoFallback       = process.env.QA_AUTH_DEMO_FALLBACK

  return [
    // ── Content source ────────────────────────────────────────────────
    {
      label:    'QA_CONTENT_SOURCE is valid',
      status:   (mode === 'local' || mode === 'live_supabase') ? 'PASS' : 'FAIL',
      detail:   `current value: ${mode}`,
      critical: true,
    },
    {
      label:    'QA_CONTENT_SOURCE is live_supabase (production requirement)',
      status:   isLive ? 'PASS' : 'WARN',
      detail:   isLive ? 'live_supabase mode active' : 'currently local mode — change for production',
      critical: false,
    },
    {
      label:    'QA_AUTH_DEMO_FALLBACK is off',
      status:   demoFallback === 'false' ? 'PASS' : 'WARN',
      detail:   demoFallback === 'false'
        ? 'demo fallback disabled (correct for production)'
        : `current: ${demoFallback ?? 'not_set'} — set to false for production`,
      critical: false,
    },

    // ── Supabase env ──────────────────────────────────────────────────
    {
      label:    'SUPABASE_URL present (server)',
      status:   supabaseUrlPresent ? 'PASS' : (isLive ? 'FAIL' : 'WARN'),
      detail:   supabaseUrlPresent ? 'present' : 'missing — required for live_supabase mode',
      critical: isLive,
    },
    {
      label:    'NEXT_PUBLIC_SUPABASE_URL present (browser)',
      status:   Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL) ? 'PASS' : (isLive ? 'FAIL' : 'WARN'),
      detail:   Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL) ? 'present' : 'missing — required for browser auth',
      critical: isLive,
    },
    {
      label:    'NEXT_PUBLIC_SUPABASE_ANON_KEY present',
      status:   anonKeyPresent ? 'PASS' : (isLive ? 'FAIL' : 'WARN'),
      detail:   anonKeyPresent ? 'present' : 'missing — required for browser auth',
      critical: isLive,
    },
    {
      label:    'SUPABASE_SERVICE_ROLE_KEY present (server-only)',
      status:   serviceRolePresent ? 'PASS' : (isLive ? 'FAIL' : 'WARN'),
      detail:   serviceRolePresent ? 'present (value never shown)' : 'missing — required for live data reads',
      critical: isLive,
    },

    // ── App modules ───────────────────────────────────────────────────
    {
      label:    'Login UI exists (apps/admin/src/app/login/page.tsx)',
      status:   fileExists('src/app/login/page.tsx') ? 'PASS' : 'FAIL',
      critical: true,
    },
    {
      label:    'Logout page exists',
      status:   fileExists('src/app/logout/page.tsx') ? 'PASS' : 'FAIL',
      critical: true,
    },
    {
      label:    'roleAccess.ts exists',
      status:   fileExists('src/lib/roleAccess.ts') ? 'PASS' : 'FAIL',
      critical: true,
    },
    {
      label:    'serverSupabaseAuth.ts exists',
      status:   fileExists('src/lib/serverSupabaseAuth.ts') ? 'PASS' : 'FAIL',
      critical: true,
    },
    {
      label:    'browserSupabaseClient.ts exists',
      status:   fileExists('src/lib/browserSupabaseClient.ts') ? 'PASS' : 'FAIL',
      critical: true,
    },
    {
      label:    'RoleGate.tsx server component exists',
      status:   fileExists('src/components/RoleGate.tsx') ? 'PASS' : 'FAIL',
      critical: false,
    },

    // ── RLS / migrations ──────────────────────────────────────────────
    {
      label:    'RLS migration file exists (000004_rls_role_hardening.sql)',
      status:   repoFileExists('supabase/migrations/000004_rls_role_hardening.sql') ? 'PASS' : 'WARN',
      detail:   'migration must also be applied in Supabase SQL Editor',
      critical: false,
    },
    {
      label:    'Gate 62 RLS done marker exists',
      status:   repoFileExists('data/diagnostics/SUPABASE_GATE_62_RLS_ROLE_ACCESS_DONE.md') ? 'PASS' : 'WARN',
      detail:   'run build_gate62_rls_role_access_report_v1.py to generate',
      critical: false,
    },

    // ── Gate 63 files ─────────────────────────────────────────────────
    {
      label:    'Production env template (.env.production.example)',
      status:   repoFileExists('.env.production.example') ? 'PASS' : 'WARN',
      critical: false,
    },
    {
      label:    'Deployment checklist exists',
      status:   repoFileExists('deployment/VERCEL_DEPLOYMENT_CHECKLIST.md') ? 'PASS' : 'WARN',
      critical: false,
    },
    {
      label:    'Security pre-deploy checklist exists',
      status:   repoFileExists('deployment/SECURITY_PREDEPLOY_CHECKLIST.md') ? 'PASS' : 'WARN',
      critical: false,
    },
  ]
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: CheckStatus }) {
  const config = {
    PASS: { bg: '#d1fae5', fg: '#065f46', label: 'PASS' },
    FAIL: { bg: '#fee2e2', fg: '#991b1b', label: 'FAIL' },
    WARN: { bg: '#fef3c7', fg: '#92400e', label: 'WARN' },
    SKIP: { bg: '#f3f4f6', fg: '#6b7280', label: 'SKIP' },
  }[status]
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '1px 7px',
        borderRadius:    4,
        fontSize:        11,
        fontWeight:      700,
        backgroundColor: config.bg,
        color:           config.fg,
        fontFamily:      'monospace',
      }}
    >
      {config.label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function ReadinessPage() {
  const mode   = getContentSourceMode()
  const isLive = mode === 'live_supabase'
  const envOk  = isLiveSupabaseConfigured()

  const checks = buildChecks(mode, isLive)

  const hasCriticalFail = checks.some(c => c.critical && c.status === 'FAIL')
  const hasWarn         = checks.some(c => c.status === 'WARN')
  const hasFail         = checks.some(c => c.status === 'FAIL')

  const overallStatus = hasCriticalFail || hasFail ? 'FAILED' : hasWarn ? 'NEEDS_REVIEW' : 'READY'

  const statusStyle = {
    READY:        { bg: '#d1fae5', fg: '#065f46' },
    NEEDS_REVIEW: { bg: '#fef3c7', fg: '#92400e' },
    FAILED:       { bg: '#fee2e2', fg: '#991b1b' },
  }[overallStatus]

  const passCount = checks.filter(c => c.status === 'PASS').length
  const failCount = checks.filter(c => c.status === 'FAIL').length
  const warnCount = checks.filter(c => c.status === 'WARN').length

  return (
    <main style={{ padding: '2rem', maxWidth: 800, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Production Readiness
        <span
          style={{
            marginLeft:      12,
            padding:         '3px 10px',
            borderRadius:    4,
            fontSize:        13,
            fontWeight:      700,
            backgroundColor: statusStyle.bg,
            color:           statusStyle.fg,
          }}
        >
          {overallStatus}
        </span>
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 8, fontSize: 13 }}>
        Gate 63 — production readiness checks. No secrets displayed.
      </p>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 13 }}>
        {passCount} PASS · {warnCount} WARN · {failCount} FAIL · {checks.length} total
      </p>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
            <th style={{ textAlign: 'left', padding: '6px 12px 6px 0', color: '#374151', fontWeight: 600 }}>Check</th>
            <th style={{ textAlign: 'center', padding: '6px 12px', color: '#374151', fontWeight: 600, width: 90 }}>Status</th>
            <th style={{ textAlign: 'left', padding: '6px 0', color: '#374151', fontWeight: 600 }}>Detail</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((check, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '6px 12px 6px 0', color: check.critical && check.status === 'FAIL' ? '#991b1b' : '#374151' }}>
                {check.label}
                {check.critical && <span style={{ marginLeft: 6, fontSize: 10, color: '#ef4444' }}>critical</span>}
              </td>
              <td style={{ padding: '6px 12px', textAlign: 'center' }}>
                <StatusBadge status={check.status} />
              </td>
              <td style={{ padding: '6px 0', color: '#6b7280', fontSize: 12 }}>
                {check.detail ?? ''}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {overallStatus === 'FAILED' && (
        <div style={{ marginTop: 20, padding: '10px 14px', background: '#fee2e2', borderRadius: 4, fontSize: 13, color: '#991b1b' }}>
          Critical checks failed. Fix the FAIL items above before deploying to production.
        </div>
      )}
      {overallStatus === 'NEEDS_REVIEW' && (
        <div style={{ marginTop: 20, padding: '10px 14px', background: '#fef3c7', borderRadius: 4, fontSize: 13, color: '#92400e' }}>
          All critical checks pass. Review WARN items — some may be required for production.
        </div>
      )}
      {overallStatus === 'READY' && (
        <div style={{ marginTop: 20, padding: '10px 14px', background: '#d1fae5', borderRadius: 4, fontSize: 13, color: '#065f46' }}>
          All checks pass. Ready to proceed with Gate 64 Vercel deployment.
        </div>
      )}

      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/system/health"           style={{ color: '#3b82f6', marginRight: 16 }}>Health</a>
        <a href="/api/system/readiness"    style={{ color: '#3b82f6', marginRight: 16 }}>Readiness API</a>
        <a href="/api/system/health"       style={{ color: '#3b82f6', marginRight: 16 }}>Health API</a>
        <a href="/system/auth-session"     style={{ color: '#3b82f6', marginRight: 16 }}>Auth Session</a>
        <a href="/system/role-access"      style={{ color: '#3b82f6' }}>Role Access</a>
      </p>
    </main>
  )
}
