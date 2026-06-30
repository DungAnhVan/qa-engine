/**
 * /system/auth-roles — Gate 60 auth/roles foundation diagnostic.
 *
 * Server Component — no secrets reach the browser.
 * Shows role counts, organization status, and Gate 61 readiness.
 *
 * Gate 61 will add real login UI and per-user session scoping.
 */
import { getContentSourceMode } from '@/lib/contentSource'
import { getLiveSupabaseEnvPresence, isLiveSupabaseConfigured } from '@/lib/liveSupabaseContent'
import { getDemoAuthContext, getAuthRoleStats } from '@/lib/liveSupabaseAuthContext'
import { requireAppRole } from '@/lib/roleAccess'

export const dynamic = 'force-dynamic'

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

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap' }}>{label}</td>
      <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}>{value}</td>
    </tr>
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

const ROLE_LABELS: Record<string, string> = {
  admin:   'Admin',
  teacher: 'Teacher',
  student: 'Student',
  parent:  'Parent',
}

export default async function AuthRolesPage() {
  const { allowed, currentRole } = await requireAppRole(['admin', 'teacher'])
  if (!allowed) return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Access denied</h1>
      <p style={{ color: '#6b7280', fontSize: 14, marginBottom: 12 }}>
        Required: admin or teacher. Your role: <code>{currentRole ?? 'none'}</code>
      </p>
      <a href="/login" style={{ color: '#3b82f6' }}>Sign in →</a>
    </main>
  )
  const mode    = getContentSourceMode()
  const liveEnv = getLiveSupabaseEnvPresence()
  const envOk   = isLiveSupabaseConfigured()
  const isLive  = mode === 'live_supabase'

  const demoCtx = getDemoAuthContext()
  const stats   = isLive && envOk ? await getAuthRoleStats() : null

  return (
    <main style={{ padding: '2rem', maxWidth: 720, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Auth + Roles Diagnostic
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 28, fontSize: 14 }}>
        Gate 60 — auth/roles foundation. No login UI yet.
        No secrets are displayed on this page.
      </p>

      <Alert variant="warn">
        Gate 60 prepares auth/roles. Real login UI is Gate 61 — currently uses demo context only.
      </Alert>

      {/* Mode */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Active Mode</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="QA_CONTENT_SOURCE"
              value={
                <>
                  <code>{mode}</code>
                  {isLive
                    ? <Badge label="live_supabase — auth context available" ok />
                    : <Badge label={`${mode} — demo mode only`} ok={false} />}
                </>
              }
            />
            <Row
              label="SUPABASE_URL"
              value={<Badge label={liveEnv.supabase_url ? 'Present' : 'Missing'} ok={liveEnv.supabase_url} />}
            />
            <Row
              label="SUPABASE_SERVICE_ROLE_KEY"
              value={<Badge label={liveEnv.service_role_key ? 'Present' : 'Missing'} ok={liveEnv.service_role_key} />}
            />
          </tbody>
        </table>
      </section>

      {/* Current auth context */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Current Auth Context
          <InfoBadge label={demoCtx.mode} />
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="mode"              value={<code>{demoCtx.mode}</code>} />
            <Row label="role"              value={<code>{demoCtx.role}</code>} />
            <Row label="organization_slug" value={<code>{demoCtx.organization_slug}</code>} />
          </tbody>
        </table>
        <Alert variant="info">
          <code>getDemoAuthContext()</code> returns this static context until Gate 61 wires real Supabase Auth sessions.
        </Alert>
      </section>

      {/* Role counts */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Profiles by Role
          <InfoBadge label={isLive && stats ? `${stats.profiles_total} total` : 'mode not live'} />
        </h2>
        {stats && (
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              {stats.by_role.map((r) => (
                <Row
                  key={r.role}
                  label={ROLE_LABELS[r.role] ?? r.role}
                  value={
                    <>
                      <strong>{r.count}</strong>
                      {r.count === 0 && (
                        <span style={{ marginLeft: 8, fontSize: 12, color: '#9ca3af' }}>
                          (run seed_demo_auth_profiles.sql to add demo profiles)
                        </span>
                      )}
                    </>
                  }
                />
              ))}
            </tbody>
          </table>
        )}
        {!isLive && (
          <Alert variant="warn">Switch to live_supabase mode to see profile counts.</Alert>
        )}
      </section>

      {/* Organizations */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Organizations
          <InfoBadge label={stats ? `${stats.organizations.length} found` : 'mode not live'} />
        </h2>
        {stats && stats.organizations.length > 0 && (
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              {stats.organizations.map((org) => (
                <Row key={org.id} label={org.slug} value={org.name} />
              ))}
            </tbody>
          </table>
        )}
        {stats && stats.organizations.length === 0 && (
          <Alert variant="warn">
            No organizations found. Run <code>supabase/seed/seed_local_mvp_demo.sql</code>.
          </Alert>
        )}
      </section>

      {/* Students + parent links */}
      {stats && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Students + Links</h2>
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row
                label="students"
                value={
                  <>
                    <strong>{stats.students_count}</strong>
                    <Badge label={stats.students_count > 0 ? 'OK' : 'None'} ok={stats.students_count > 0} />
                  </>
                }
              />
              <Row label="parent_student_links" value={stats.parent_links_count} />
            </tbody>
          </table>
        </section>
      )}

      {/* Auth trigger migration status */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Auth Profile Trigger</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="migration file"
              value={<code>supabase/migrations/000003_auth_profile_trigger.sql</code>}
            />
            <Row
              label="function"
              value={<code>public.handle_new_user()</code>}
            />
            <Row
              label="trigger"
              value={<code>on_auth_user_created ON auth.users</code>}
            />
            <Row
              label="apply status"
              value={
                <span style={{ color: '#92400e', fontSize: 12 }}>
                  Apply manually in Supabase SQL Editor — not applied automatically.
                </span>
              }
            />
          </tbody>
        </table>
        <Alert variant="info">
          To apply: paste <code>supabase/migrations/000003_auth_profile_trigger.sql</code> into
          the Supabase Dashboard SQL Editor and run it.
        </Alert>
      </section>

      {/* Login UI status */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Login UI Status</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="login page"  value={<code>/login</code>} />
            <Row label="logout page" value={<code>/logout</code>} />
            <Row
              label="demo users expected"
              value={
                <span style={{ fontSize: 13, color: '#374151' }}>
                  admin@quantaaptus.local, teacher@quantaaptus.local,
                  student@quantaaptus.local, parent@quantaaptus.local
                </span>
              }
            />
            <Row
              label="demo password"
              value={
                <span style={{ fontSize: 13, color: '#374151' }}>
                  QuantaAptusDemo123! (local dev only)
                </span>
              }
            />
          </tbody>
        </table>
        <Alert variant="info">
          Run <code>tools/supabase/create_gate61_demo_auth_users_v1.py</code> to create demo Supabase Auth users.
        </Alert>
      </section>

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 12 }}>
        <a href="/system/auth-session"      style={{ color: '#3b82f6', marginRight: 16 }}>Auth Session</a>
        <a href="/login"                    style={{ color: '#3b82f6', marginRight: 16 }}>Login</a>
        <a href="/system/student-results"   style={{ color: '#3b82f6', marginRight: 16 }}>Student Results</a>
        <a href="/system/teacher-review"    style={{ color: '#3b82f6', marginRight: 16 }}>Teacher Review</a>
        <a href="/system/marking"           style={{ color: '#3b82f6', marginRight: 16 }}>Marking</a>
        <a href="/system/content-source"    style={{ color: '#3b82f6' }}>Content Source</a>
      </p>
    </main>
  )
}
