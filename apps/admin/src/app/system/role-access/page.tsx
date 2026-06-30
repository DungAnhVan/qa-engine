/**
 * /system/role-access — Gate 62 role access matrix diagnostic.
 *
 * Server Component — shows current user, their role, and the full
 * route access matrix without exposing any secrets.
 */
import {
  getServerAuthSession,
  getCurrentProfile,
  getAuthMode,
} from '@/lib/serverSupabaseAuth'
import { ROUTE_ACCESS_MATRIX, canAccessRoute } from '@/lib/roleAccess'
import { getContentSourceMode } from '@/lib/contentSource'

export const dynamic = 'force-dynamic'

function CheckMark({ ok }: { ok: boolean }) {
  return (
    <span
      style={{
        display:    'inline-block',
        width:      18,
        textAlign:  'center',
        fontWeight: 700,
        fontSize:   13,
        color:      ok ? '#065f46' : '#9ca3af',
      }}
    >
      {ok ? '✓' : '—'}
    </span>
  )
}

function Badge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '2px 8px',
        borderRadius:    4,
        fontSize:        12,
        fontWeight:      600,
        backgroundColor: ok ? '#d1fae5' : '#fee2e2',
        color:           ok ? '#065f46' : '#991b1b',
        marginLeft:      8,
      }}
    >
      {label}
    </span>
  )
}

function InfoBadge({ label }: { label: string }) {
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '2px 8px',
        borderRadius:    4,
        fontSize:        12,
        fontWeight:      600,
        backgroundColor: '#dbeafe',
        color:           '#1e40af',
        marginLeft:      8,
      }}
    >
      {label}
    </span>
  )
}

function Alert({ variant, children }: { variant: 'warn' | 'info'; children: React.ReactNode }) {
  const c = { warn: { bg: '#fef3c7', color: '#92400e' }, info: { bg: '#dbeafe', color: '#1e40af' } }[variant]
  return (
    <div style={{ marginTop: 10, padding: '8px 12px', background: c.bg, borderRadius: 4, fontSize: 13, color: c.color }}>
      {children}
    </div>
  )
}

const COL_STYLE: React.CSSProperties = {
  padding:   '6px 10px',
  textAlign: 'center',
  fontSize:  13,
  borderBottom: '1px solid #f3f4f6',
}

const LABEL_STYLE: React.CSSProperties = {
  padding:      '6px 12px 6px 0',
  fontSize:     13,
  borderBottom: '1px solid #f3f4f6',
  whiteSpace:   'nowrap',
}

const PATH_STYLE: React.CSSProperties = {
  padding:      '6px 12px',
  fontSize:     12,
  fontFamily:   'monospace',
  color:        '#6b7280',
  borderBottom: '1px solid #f3f4f6',
  whiteSpace:   'nowrap',
}

const TH_STYLE: React.CSSProperties = {
  padding:    '6px 10px',
  fontSize:   12,
  fontWeight: 700,
  color:      '#374151',
  textAlign:  'center',
  borderBottom: '2px solid #e5e7eb',
}

export default async function RoleAccessPage() {
  const contentMode = getContentSourceMode()
  const authMode    = getAuthMode()
  const session     = await getServerAuthSession()
  const profile     = await getCurrentProfile()

  const currentRole  = profile?.role  ?? null
  const currentEmail = profile?.email ?? session?.email ?? null
  const isDemo       = session?.is_demo ?? false

  return (
    <main style={{ padding: '2rem', maxWidth: 900, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Role Access Matrix
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 28, fontSize: 14 }}>
        Gate 62 — RLS Hardening + Role-Based App Access. No secrets displayed.
      </p>

      {/* Current user */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Current User
          {currentRole && <InfoBadge label={currentRole} />}
          {isDemo && <InfoBadge label="demo fallback" />}
          {!session && <Badge label="not signed in" ok={false} />}
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <tr>
              <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap' }}>QA_CONTENT_SOURCE</td>
              <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}><code>{contentMode}</code></td>
            </tr>
            <tr>
              <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap' }}>auth mode</td>
              <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}><code>{authMode}</code></td>
            </tr>
            <tr>
              <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap' }}>email</td>
              <td style={{ padding: '5px 0', fontSize: 13 }}>{currentEmail ?? <span style={{ color: '#9ca3af' }}>—</span>}</td>
            </tr>
            <tr>
              <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap' }}>role</td>
              <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}>
                <code>{currentRole ?? '—'}</code>
                {currentRole && (
                  <Badge label={`can access ${ROUTE_ACCESS_MATRIX.filter(r => canAccessRoute(currentRole, r.path)).length}/${ROUTE_ACCESS_MATRIX.length} routes`} ok />
                )}
              </td>
            </tr>
          </tbody>
        </table>
        {!session && (
          <Alert variant="warn">
            Not signed in. <a href="/login" style={{ color: '#92400e' }}>Sign in</a> to see your effective access.
          </Alert>
        )}
        {isDemo && (
          <Alert variant="info">
            Demo fallback active (QA_AUTH_DEMO_FALLBACK=true). Role shown is demo admin.
          </Alert>
        )}
      </section>

      {/* Route access matrix */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Route Access Matrix
        </h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', minWidth: 600 }}>
            <thead>
              <tr>
                <th style={{ ...TH_STYLE, textAlign: 'left', paddingLeft: 0 }}>Page</th>
                <th style={{ ...TH_STYLE, width: 80, color: '#1d4ed8' }}>Path</th>
                <th style={{ ...TH_STYLE, width: 70 }}>Admin</th>
                <th style={{ ...TH_STYLE, width: 70 }}>Teacher</th>
                <th style={{ ...TH_STYLE, width: 70 }}>Student</th>
                <th style={{ ...TH_STYLE, width: 70 }}>Parent</th>
                {currentRole && (
                  <th style={{ ...TH_STYLE, width: 80, backgroundColor: '#eff6ff' }}>
                    You ({currentRole})
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {ROUTE_ACCESS_MATRIX.map((row) => (
                <tr key={row.path}>
                  <td style={LABEL_STYLE}>{row.label}</td>
                  <td style={PATH_STYLE}><code>{row.path}</code></td>
                  <td style={COL_STYLE}><CheckMark ok={row.admin} /></td>
                  <td style={COL_STYLE}><CheckMark ok={row.teacher} /></td>
                  <td style={COL_STYLE}><CheckMark ok={row.student} /></td>
                  <td style={COL_STYLE}><CheckMark ok={row.parent} /></td>
                  {currentRole && (
                    <td style={{ ...COL_STYLE, backgroundColor: '#eff6ff' }}>
                      <CheckMark ok={canAccessRoute(currentRole, row.path)} />
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={{ marginTop: 8, fontSize: 12, color: '#9ca3af' }}>
          ✓ = allowed, — = denied. Guards applied server-side via requireAppRole() in each page.
        </p>
      </section>

      {/* RLS info */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>RLS Hardening Status</h2>
        <Alert variant="info">
          Migration <code>000004_rls_role_hardening.sql</code> must be applied in the Supabase SQL Editor
          to activate row-level security policies. See <code>tools/supabase/apply_gate62_rls_migration_checklist_v1.md</code>.
        </Alert>
      </section>

      {/* Nav */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 12 }}>
        <a href="/system/auth-session" style={{ color: '#3b82f6', marginRight: 16 }}>Auth Session</a>
        <a href="/system/auth-roles"   style={{ color: '#3b82f6', marginRight: 16 }}>Auth Roles</a>
        <a href="/login"               style={{ color: '#3b82f6', marginRight: 16 }}>Login</a>
        <a href="/system/marking"      style={{ color: '#3b82f6' }}>Marking</a>
      </p>
    </main>
  )
}
