/**
 * /system/teacher-review — Gate 58 teacher review diagnostic.
 *
 * Server Component — no secrets reach the browser.
 * Shows teacher review queue count, review history, and mode status.
 */
import { getContentSourceMode } from '@/lib/contentSource'
import { getLiveSupabaseEnvPresence, isLiveSupabaseConfigured } from '@/lib/liveSupabaseContent'
import { getLiveSupabaseTeacherReviewStats } from '@/lib/liveSupabaseTeacherReview'

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
      <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap' }}>
        {label}
      </td>
      <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}>{value}</td>
    </tr>
  )
}

function Alert({ variant, children }: { variant: 'warn' | 'info'; children: React.ReactNode }) {
  const colors = { warn: { bg: '#fef3c7', color: '#92400e' }, info: { bg: '#dbeafe', color: '#1e40af' } }
  const c = colors[variant]
  return (
    <div
      style={{
        marginTop:    10,
        padding:      '8px 12px',
        background:   c.bg,
        borderRadius: 4,
        fontSize:     13,
        color:        c.color,
      }}
    >
      {children}
    </div>
  )
}

export default async function TeacherReviewDiagnosticPage() {
  const mode   = getContentSourceMode()
  const liveEnv = getLiveSupabaseEnvPresence()
  const envOk  = isLiveSupabaseConfigured()
  const isLive = mode === 'live_supabase'

  const stats = isLive && envOk ? await getLiveSupabaseTeacherReviewStats() : null

  return (
    <main style={{ padding: '2rem', maxWidth: 720, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Teacher Review Diagnostic
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 28, fontSize: 14 }}>
        Gate 58 status — teacher attempt review to Supabase.
        No secrets are displayed on this page.
      </p>

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
                    ? <Badge label="live_supabase — teacher review enabled" ok />
                    : <Badge label={`${mode} — teacher review not available`} ok={false} />}
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
        {!isLive && (
          <Alert variant="warn">
            Set <code>QA_CONTENT_SOURCE=live_supabase</code> in{' '}
            <code>apps/admin/.env.local</code> to enable teacher reviews.
          </Alert>
        )}
      </section>

      {/* Queue stats */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Review Queue
          <InfoBadge label={isLive && stats ? `${stats.queue_count} pending` : 'mode not live'} />
        </h2>
        {isLive && stats && (
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row
                label="teacher_review_required"
                value={
                  <>
                    <strong>{stats.queue_count}</strong>
                    <Badge
                      label={stats.queue_count === 0 ? 'Queue empty' : 'Pending'}
                      ok={stats.queue_count === 0}
                    />
                  </>
                }
              />
              <Row
                label="teacher_reviews (total)"
                value={<strong>{stats.reviews_count}</strong>}
              />
            </tbody>
          </table>
        )}
        {!isLive && (
          <Alert variant="warn">Switch to live_supabase mode to see queue stats.</Alert>
        )}
      </section>

      {/* Latest review */}
      {isLive && stats?.latest_review && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Latest Teacher Review</h2>
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row label="id (truncated)" value={`${stats.latest_review.id.slice(0, 8)}…`} />
              <Row label="decision"       value={stats.latest_review.decision} />
              <Row
                label="created_at"
                value={new Date(stats.latest_review.created_at).toLocaleString()}
              />
            </tbody>
          </table>
        </section>
      )}

      {isLive && stats && stats.reviews_count === 0 && (
        <Alert variant="info">
          No teacher reviews yet. Use the{' '}
          <a href="/learn/supabase-attempt-review" style={{ color: '#1d4ed8' }}>
            Teacher Review Queue
          </a>{' '}
          or run the test script:
          <br />
          <code>
            .venv-ingest\Scripts\python.exe tools\supabase\test_gate58_teacher_review_v1.py
          </code>
        </Alert>
      )}

      {/* Gate 59 notice */}
      <Alert variant="info">
        Gate 59 will add student results view showing marked attempt history.
      </Alert>

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 20 }}>
        <a href="/learn/supabase-attempt-review" style={{ color: '#3b82f6', marginRight: 16 }}>
          Teacher Review Queue
        </a>
        <a href="/system/marking" style={{ color: '#3b82f6', marginRight: 16 }}>
          Marking Diagnostic
        </a>
        <a href="/system/attempt-write" style={{ color: '#3b82f6', marginRight: 16 }}>
          Attempt Write Diagnostic
        </a>
        <a href="/system/content-source" style={{ color: '#3b82f6' }}>
          Content Source
        </a>
      </p>
    </main>
  )
}
