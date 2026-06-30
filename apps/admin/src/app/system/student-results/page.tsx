/**
 * /system/student-results — Gate 59 student results diagnostic.
 *
 * Server Component — no secrets reach the browser.
 * Shows demo student result summary and readiness checks.
 */
import { getContentSourceMode } from '@/lib/contentSource'
import { getLiveSupabaseEnvPresence, isLiveSupabaseConfigured } from '@/lib/liveSupabaseContent'
import { getLiveSupabaseStudentResults } from '@/lib/liveSupabaseStudentResults'

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

export default async function StudentResultsDiagnosticPage() {
  const mode    = getContentSourceMode()
  const liveEnv = getLiveSupabaseEnvPresence()
  const envOk   = isLiveSupabaseConfigured()
  const isLive  = mode === 'live_supabase'

  const report = isLive && envOk ? await getLiveSupabaseStudentResults() : null

  const accuracyPct = report?.accuracy != null
    ? `${(report.accuracy * 100).toFixed(0)}%`
    : null

  return (
    <main style={{ padding: '2rem', maxWidth: 720, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Student Results Diagnostic
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 28, fontSize: 14 }}>
        Gate 59 status — live Supabase student result report.
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
                    ? <Badge label="live_supabase — results enabled" ok />
                    : <Badge label={`${mode} — results not available`} ok={false} />}
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
            <code>apps/admin/.env.local</code> to view results.
          </Alert>
        )}
      </section>

      {/* Demo student summary */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Demo Student Report
          <InfoBadge label={isLive ? (report ? 'loaded' : 'no data') : 'mode not live'} />
        </h2>
        {isLive && report && (
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row label="student_name"        value={report.student_name} />
              <Row label="subject_slug"        value={report.subject_slug} />
              <Row label="attempt_count"       value={<strong>{report.attempt_count}</strong>} />
              <Row label="marked_count"        value={
                <>
                  <strong>{report.marked_attempt_count}</strong>
                  <Badge label={report.marked_attempt_count > 0 ? 'OK' : 'None yet'} ok={report.marked_attempt_count > 0} />
                </>
              } />
              <Row label="correct"             value={report.correct_count} />
              <Row label="incorrect"           value={report.incorrect_count} />
              <Row label="needs_resubmission"  value={report.needs_resubmission_count} />
              <Row label="pending_review"      value={report.pending_teacher_review_count} />
              <Row label="unmarked"            value={report.unmarked_count} />
              <Row label="accuracy"            value={accuracyPct ?? '— (no resolved attempts)'} />
              <Row label="skill_gaps"          value={report.skill_gaps.length} />
              <Row label="strengths"           value={report.strengths.length} />
              <Row label="resubmission_queue"  value={report.resubmission_queue.length} />
            </tbody>
          </table>
        )}
        {isLive && !report && (
          <Alert variant="warn">
            No result data found for <code>local_demo_student</code> · <code>physics_0625</code>.
            Run attempts and marking first:
            <br />
            <code>.venv-ingest\Scripts\python.exe tools\supabase\test_gate56_attempt_write_v1.py</code>
            <br />
            <code>.venv-ingest\Scripts\python.exe tools\supabase\test_gate57_mark_latest_attempt_v1.py</code>
          </Alert>
        )}
        {!isLive && (
          <Alert variant="warn">Switch to live_supabase mode to view report.</Alert>
        )}
      </section>

      {/* Latest result */}
      {report && report.recent_attempts.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Latest Attempt</h2>
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row
                label="resource"
                value={report.recent_attempts[0].resource_title.slice(0, 60)}
              />
              <Row
                label="result"
                value={report.recent_attempts[0].result ?? '(not marked)'}
              />
              <Row
                label="submitted"
                value={new Date(report.recent_attempts[0].submitted_at).toLocaleString()}
              />
            </tbody>
          </table>
        </section>
      )}

      <Alert variant="info">
        Gate 60 will add auth so each student sees only their own results. Currently uses demo student only.
      </Alert>

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 20 }}>
        <a href="/learn/supabase-results"         style={{ color: '#3b82f6', marginRight: 16 }}>Student Results Page</a>
        <a href="/learn/supabase-attempt-review"  style={{ color: '#3b82f6', marginRight: 16 }}>Teacher Review Queue</a>
        <a href="/system/teacher-review"          style={{ color: '#3b82f6', marginRight: 16 }}>Teacher Review Diagnostic</a>
        <a href="/system/marking"                 style={{ color: '#3b82f6' }}>Marking Diagnostic</a>
      </p>
    </main>
  )
}
