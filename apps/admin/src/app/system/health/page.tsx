/**
 * /system/health — Gate 63 production health page.
 *
 * Server Component — no secrets reach the browser.
 * Shows app status, build mode, and env presence (true/false only).
 */
import { getLiveSupabaseEnvPresence, isLiveSupabaseConfigured } from '@/lib/liveSupabaseContent'
import { getContentSourceMode } from '@/lib/contentSource'

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

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap', fontFamily: 'system-ui' }}>
        {label}
      </td>
      <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}>{value}</td>
    </tr>
  )
}

export default async function SystemHealthPage() {
  const mode    = getContentSourceMode()
  const liveEnv = getLiveSupabaseEnvPresence()
  const isLive  = mode === 'live_supabase'
  const envOk   = isLiveSupabaseConfigured()

  const anonKeyPresent    = Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY
  )
  const serviceRolePresent = Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY)
  const demoFallback       = process.env.QA_AUTH_DEMO_FALLBACK ?? 'not_set'
  const nodeEnv            = process.env.NODE_ENV ?? 'development'
  const timestamp          = new Date().toISOString()

  const overallOk = isLive ? envOk : true

  return (
    <main style={{ padding: '2rem', maxWidth: 640, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        System Health
        <span
          style={{
            marginLeft:      12,
            padding:         '3px 10px',
            borderRadius:    4,
            fontSize:        13,
            fontWeight:      600,
            backgroundColor: overallOk ? '#d1fae5' : '#fef3c7',
            color:           overallOk ? '#065f46' : '#92400e',
          }}
        >
          {overallOk ? 'OK' : 'NEEDS ATTENTION'}
        </span>
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 13 }}>
        Gate 63 — production readiness. No secrets displayed.
      </p>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          App
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="status"           value={<Badge label="ok" ok />} />
            <Row label="app"              value="quanta-aptus-admin" />
            <Row label="NODE_ENV"         value={<code>{nodeEnv}</code>} />
            <Row label="timestamp"        value={<code style={{ fontSize: 12 }}>{timestamp}</code>} />
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Content Mode
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="QA_CONTENT_SOURCE"
              value={
                <>
                  <code>{mode}</code>
                  {isLive
                    ? <Badge label="live_supabase" ok />
                    : <Badge label={mode} ok={false} />}
                </>
              }
            />
            <Row
              label="QA_AUTH_DEMO_FALLBACK"
              value={
                <>
                  <code>{demoFallback}</code>
                  {demoFallback === 'false'
                    ? <Badge label="off (production)" ok />
                    : <Badge label={demoFallback === 'true' ? 'on (dev mode)' : 'not set'} ok={false} />}
                </>
              }
            />
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Environment Variables
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="SUPABASE_URL (server)"
              value={<Badge label={liveEnv.supabase_url ? 'Present' : 'Missing'} ok={liveEnv.supabase_url} />}
            />
            <Row
              label="NEXT_PUBLIC_SUPABASE_URL"
              value={<Badge label={Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL) ? 'Present' : 'Missing'} ok={Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL)} />}
            />
            <Row
              label="NEXT_PUBLIC_SUPABASE_ANON_KEY"
              value={<Badge label={anonKeyPresent ? 'Present' : 'Missing'} ok={anonKeyPresent} />}
            />
            <Row
              label="SUPABASE_SERVICE_ROLE_KEY"
              value={
                <>
                  <Badge label={serviceRolePresent ? 'Present (server-only)' : 'Missing'} ok={serviceRolePresent} />
                  {serviceRolePresent && (
                    <span style={{ marginLeft: 8, fontSize: 11, color: '#6b7280' }}>
                      value never displayed
                    </span>
                  )}
                </>
              }
            />
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Quick Links
        </h2>
        <p style={{ fontSize: 13, color: '#6b7280' }}>
          <a href="/system/readiness" style={{ color: '#3b82f6', marginRight: 16 }}>Readiness</a>
          <a href="/api/system/health" style={{ color: '#3b82f6', marginRight: 16 }}>Health API</a>
          <a href="/api/system/readiness" style={{ color: '#3b82f6', marginRight: 16 }}>Readiness API</a>
          <a href="/system/auth-session" style={{ color: '#3b82f6', marginRight: 16 }}>Auth Session</a>
          <a href="/system/role-access" style={{ color: '#3b82f6' }}>Role Access</a>
        </p>
      </section>
    </main>
  )
}
