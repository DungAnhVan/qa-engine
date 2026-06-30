/**
 * /system/attempt-write — Gate 56 attempt write diagnostic.
 *
 * Server Component — no secrets reach the browser.
 * Shows whether the live_supabase attempt write path is ready.
 */
import { getContentSourceMode } from '@/lib/contentSource'
import {
  getLiveSupabaseEnvPresence,
  isLiveSupabaseConfigured,
} from '@/lib/liveSupabaseContent'
import { getLiveSupabaseDemoStudent } from '@/lib/liveSupabaseAttempts'
import { getActiveContentIndex } from '@/lib/activeContent'

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

function Alert({ variant, children }: { variant: 'warn' | 'info'; children: React.ReactNode }) {
  const colors = {
    warn: { bg: '#fef3c7', color: '#92400e' },
    info: { bg: '#dbeafe', color: '#1e40af' },
  }
  const c = colors[variant]
  return (
    <div
      style={{
        marginTop: 10,
        padding: '8px 12px',
        background: c.bg,
        borderRadius: 4,
        fontSize: 13,
        color: c.color,
      }}
    >
      {children}
    </div>
  )
}

export default async function AttemptWritePage() {
  const mode       = getContentSourceMode()
  const liveEnv    = getLiveSupabaseEnvPresence()
  const envOk      = isLiveSupabaseConfigured()
  const activeIdx  = await getActiveContentIndex()

  // Only query demo student if env is configured — avoids a throw
  const demoStudent = envOk ? await getLiveSupabaseDemoStudent() : null

  const pkg = activeIdx?.active_packages[0] ?? null

  return (
    <main style={{ padding: '2rem', maxWidth: 720, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Attempt Write Diagnostic
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 28, fontSize: 14 }}>
        Gate 56 status — student attempt write to Supabase.
        No secrets are displayed on this page.
      </p>

      {/* ── Gate 56 notice ── */}
      <Alert variant="warn">
        Gate 56 writes attempts only. Marking is Gate 57.
        Attempts inserted here have <code>marking_status = unmarked</code>.
      </Alert>

      {/* ── Current mode ── */}
      <section style={{ marginTop: 24, marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Active Mode</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="QA_CONTENT_SOURCE"
              value={
                <>
                  <code>{mode}</code>
                  {mode === 'live_supabase' ? (
                    <Badge label="live_supabase - writes enabled" ok />
                  ) : (
                    <Badge label={`${mode} - local write only`} ok={false} />
                  )}
                </>
              }
            />
          </tbody>
        </table>
        {mode !== 'live_supabase' && (
          <Alert variant="warn">
            Set <code>QA_CONTENT_SOURCE=live_supabase</code> in{' '}
            <code>apps/admin/.env.local</code> to enable Supabase attempt writes.
          </Alert>
        )}
      </section>

      {/* ── Environment ── */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Live Supabase Environment
          <Badge label={envOk ? 'Configured' : 'Missing'} ok={envOk} />
        </h2>
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

      {/* ── Demo student ── */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Demo Student
          <Badge
            label={demoStudent ? 'Found' : envOk ? 'Not found' : 'Env not configured'}
            ok={Boolean(demoStudent)}
          />
        </h2>
        {demoStudent && (
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row label="display_name"   value={demoStudent.display_name} />
              <Row label="external_code"  value={demoStudent.external_code} />
              <Row label="id (truncated)" value={`${demoStudent.id.slice(0, 8)}…`} />
            </tbody>
          </table>
        )}
        {!demoStudent && envOk && (
          <Alert variant="warn">
            Demo student not found in Supabase. Run the seed SQL:
            <br />
            <code>supabase/seed/seed_local_mvp_demo.sql</code>
          </Alert>
        )}
      </section>

      {/* ── Active package ── */}
      {pkg && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Active Package</h2>
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row label="package_id"     value={pkg.active_package_id} />
              <Row label="resource_count" value={String(pkg.resource_count)} />
              <Row label="source"         value={mode === 'live_supabase' ? 'live Supabase' : mode} />
            </tbody>
          </table>
        </section>
      )}

      {/* ── Navigation ── */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 16 }}>
        <a href="/system/content-source" style={{ color: '#3b82f6', marginRight: 16 }}>
          Content Source Diagnostic
        </a>
        <a href="/learn/practice" style={{ color: '#3b82f6' }}>
          Go to Practice
        </a>
      </p>
    </main>
  )
}
