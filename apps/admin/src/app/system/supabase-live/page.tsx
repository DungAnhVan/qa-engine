/**
 * /system/supabase-live — Live Supabase connection diagnostic.
 *
 * Server Component. Forced dynamic so it always re-queries Supabase.
 * No secrets are rendered to the browser. Read-only — no writes.
 */
export const dynamic = 'force-dynamic'

import { getLiveSupabaseActivePackage, getLiveSupabaseEnvPresence } from '@/lib/liveSupabaseContent'
import { getContentSourceMode } from '@/lib/contentSource'

function Badge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        backgroundColor: ok ? '#d1fae5' : '#fee2e2',
        color: ok ? '#065f46' : '#991b1b',
        marginLeft: 8,
      }}
    >
      {label}
    </span>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap' }}>
        {label}
      </td>
      <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}>{value}</td>
    </tr>
  )
}

function Alert({ variant, children }: { variant: 'warn' | 'error' | 'info'; children: React.ReactNode }) {
  const colors = {
    warn:  { bg: '#fef3c7', color: '#92400e' },
    error: { bg: '#fee2e2', color: '#991b1b' },
    info:  { bg: '#dbeafe', color: '#1e40af' },
  }
  const c = colors[variant]
  return (
    <div style={{ marginTop: 12, padding: '8px 12px', background: c.bg, borderRadius: 4, fontSize: 13, color: c.color }}>
      {children}
    </div>
  )
}

export default async function SupabaseLivePage() {
  const mode    = getContentSourceMode()
  const liveEnv = getLiveSupabaseEnvPresence()
  const result  = await getLiveSupabaseActivePackage()

  return (
    <main style={{ padding: '2rem', maxWidth: 720, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Live Supabase Connection
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 28, fontSize: 14 }}>
        Tests a live server-side read from Supabase. No writes performed.
        No secret values are displayed.
      </p>

      {/* ── Write safety notice ── */}
      <Alert variant="info">
        Read-only diagnostic. No write mode enabled. SUPABASE_SERVICE_ROLE_KEY is used
        server-side only and never sent to the browser.
      </Alert>

      {/* ── Current mode ── */}
      <section style={{ marginTop: 24, marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Current App Mode</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="QA_CONTENT_SOURCE"
              value={
                <>
                  <code>{mode}</code>
                  {mode === 'live_supabase' ? (
                    <Badge label="live_supabase active" ok />
                  ) : (
                    <Badge label={`not live_supabase (${mode})`} ok={false} />
                  )}
                </>
              }
            />
          </tbody>
        </table>
        {mode !== 'live_supabase' && (
          <Alert variant="warn">
            QA_CONTENT_SOURCE is currently &quot;{mode}&quot;, not &quot;live_supabase&quot;.
            This page always tests the live connection regardless of the active mode.
          </Alert>
        )}
      </section>

      {/* ── Env status ── */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Environment</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
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

      {/* ── Connection result ── */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Connection Status
          <Badge label={result.connected ? 'Connected' : 'Failed'} ok={result.connected} />
        </h2>

        {result.error && (
          <Alert variant="error">
            <strong>Error:</strong> {result.error}
            {!liveEnv.supabase_url || !liveEnv.service_role_key ? (
              <div style={{ marginTop: 6 }}>
                Add <code>SUPABASE_URL</code> and <code>SUPABASE_SERVICE_ROLE_KEY</code> to{' '}
                <code>apps/admin/.env.local</code> and restart the server.
              </div>
            ) : null}
          </Alert>
        )}

        {result.connected && !result.error && result.package_key && (
          <table style={{ borderCollapse: 'collapse', marginTop: 8 }}>
            <tbody>
              <Row label="package_key"            value={result.package_key} />
              <Row label="version"                value={String(result.version)} />
              <Row label="status"                 value={<Badge label={result.status ?? ''} ok={result.status === 'active'} />} />
              <Row label="resource_count"         value={String(result.resource_count)} />
              <Row label="student_resource_count" value={String(result.student_resource_count)} />
              <Row label="teacher_resource_count" value={String(result.teacher_resource_count)} />
              <Row
                label="needs_human_review"
                value={
                  <Badge
                    label={`${result.needs_human_review_count} resource(s)`}
                    ok={(result.needs_human_review_count ?? 0) === 0}
                  />
                }
              />
            </tbody>
          </table>
        )}
      </section>

      {/* ── First 5 resources ── */}
      {result.connected && (result.preview_resources?.length ?? 0) > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
            First {result.preview_resources!.length} Resources
          </h2>
          <table
            style={{
              borderCollapse: 'collapse',
              width: '100%',
              fontSize: 13,
              fontFamily: 'monospace',
            }}
          >
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                <th style={{ padding: '4px 12px 4px 0', textAlign: 'left', fontWeight: 600, color: '#374151' }}>#</th>
                <th style={{ padding: '4px 12px 4px 0', textAlign: 'left', fontWeight: 600, color: '#374151' }}>Title</th>
                <th style={{ padding: '4px 12px 4px 0', textAlign: 'left', fontWeight: 600, color: '#374151' }}>Topic</th>
                <th style={{ padding: '4px 0', textAlign: 'left', fontWeight: 600, color: '#374151' }}>Visibility</th>
              </tr>
            </thead>
            <tbody>
              {result.preview_resources!.map((r, i) => (
                <tr key={r.resource_key} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '4px 12px 4px 0', color: '#9ca3af' }}>{i + 1}</td>
                  <td style={{ padding: '4px 12px 4px 0', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.title}
                  </td>
                  <td style={{ padding: '4px 12px 4px 0', color: '#6b7280' }}>{r.topic}</td>
                  <td style={{ padding: '4px 0' }}>
                    <Badge
                      label={r.visibility}
                      ok={r.visibility !== 'teacher_only'}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* ── Navigation ── */}
      <p style={{ fontSize: 13, color: '#6b7280' }}>
        <a href="/system/content-source" style={{ color: '#3b82f6' }}>
          Back to Content Source Diagnostic
        </a>
      </p>
    </main>
  )
}
