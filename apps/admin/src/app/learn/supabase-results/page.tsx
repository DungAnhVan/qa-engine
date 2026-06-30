/**
 * /learn/supabase-results — Gate 59 student result report from Supabase.
 *
 * Server Component — all data fetched server-side, no secrets reach the browser.
 * Default: local_demo_student + physics_0625.
 *
 * Gate 60 will add auth so each student sees only their own results.
 */
import { getContentSourceMode } from '@/lib/contentSource'
import { getLiveSupabaseEnvPresence, isLiveSupabaseConfigured } from '@/lib/liveSupabaseContent'
import {
  getLiveSupabaseStudentResults,
  type StudentResultReport,
  type SkillGapItem,
  type ResubmissionItem,
  type RecentAttemptItem,
} from '@/lib/liveSupabaseStudentResults'

export const dynamic = 'force-dynamic'

// ---------------------------------------------------------------------------
// Primitive UI helpers
// ---------------------------------------------------------------------------

function Alert({ variant, children }: { variant: 'warn' | 'info' | 'ok'; children: React.ReactNode }) {
  const c = {
    warn: { bg: '#fef3c7', color: '#92400e' },
    info: { bg: '#dbeafe', color: '#1e40af' },
    ok:   { bg: '#d1fae5', color: '#065f46' },
  }[variant]
  return (
    <div style={{ padding: '10px 14px', background: c.bg, borderRadius: 4, fontSize: 13, color: c.color, marginBottom: 16 }}>
      {children}
    </div>
  )
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div
      style={{
        border:       '1px solid #e5e7eb',
        borderRadius: 6,
        padding:      '14px 18px',
        background:   '#fff',
        minWidth:     110,
      }}
    >
      <div style={{ fontSize: 24, fontWeight: 700, color: '#111827' }}>{value}</div>
      <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function ResultBadge({ result }: { result: string | null }) {
  const MAP: Record<string, { bg: string; fg: string; label: string }> = {
    correct:               { bg: '#d1fae5', fg: '#065f46', label: 'Correct' },
    incorrect:             { bg: '#fee2e2', fg: '#991b1b', label: 'Incorrect' },
    partially_correct:     { bg: '#fef3c7', fg: '#92400e', label: 'Partial' },
    needs_resubmission:    { bg: '#dbeafe', fg: '#1e40af', label: 'Resubmit' },
    pending_teacher_review:{ bg: '#f3e8ff', fg: '#6d28d9', label: 'Pending review' },
  }
  const style = result ? (MAP[result] ?? null) : null
  if (!style) {
    return <span style={{ fontSize: 12, color: '#9ca3af' }}>—</span>
  }
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '1px 7px',
        borderRadius:    4,
        fontSize:        11,
        fontWeight:      600,
        backgroundColor: style.bg,
        color:           style.fg,
      }}
    >
      {style.label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Section components
// ---------------------------------------------------------------------------

function StrengthsSection({ report }: { report: StudentResultReport }) {
  if (!report.strengths.length) {
    return (
      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Strengths</h2>
        <p style={{ fontSize: 13, color: '#9ca3af' }}>No correct answers yet.</p>
      </section>
    )
  }
  return (
    <section style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Strengths</h2>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {report.strengths.map((s, i) => (
          <div
            key={i}
            style={{
              padding:         '6px 14px',
              borderRadius:    4,
              fontSize:        12,
              backgroundColor: '#d1fae5',
              color:           '#065f46',
              fontWeight:      600,
            }}
          >
            {s.topic ?? 'Unknown topic'}
            {s.skill_type && <span style={{ fontWeight: 400, marginLeft: 6 }}>· {s.skill_type}</span>}
            <span style={{ marginLeft: 8, fontWeight: 400 }}>×{s.count}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

function SkillGapsSection({ gaps }: { gaps: SkillGapItem[] }) {
  if (!gaps.length) {
    return (
      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Skill Gaps</h2>
        <p style={{ fontSize: 13, color: '#9ca3af' }}>No skill gaps identified.</p>
      </section>
    )
  }
  return (
    <section style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Skill Gaps</h2>
      <div>
        {gaps.map((g) => (
          <div
            key={g.attempt_id}
            style={{
              borderLeft:  '3px solid #f87171',
              paddingLeft: 12,
              marginBottom: 12,
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 13 }}>{g.resource_title}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
              {g.topic && <span>{g.topic}</span>}
              {g.skill_type && <span style={{ marginLeft: 8 }}>· {g.skill_type}</span>}
              <span style={{ marginLeft: 8 }}><ResultBadge result={g.result} /></span>
            </div>
            {g.feedback && (
              <div style={{ fontSize: 12, color: '#374151', marginTop: 4, fontStyle: 'italic' }}>
                {g.feedback}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

function ResubmissionSection({ queue }: { queue: ResubmissionItem[] }) {
  if (!queue.length) {
    return (
      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Resubmission Queue</h2>
        <p style={{ fontSize: 13, color: '#9ca3af' }}>No items to resubmit.</p>
      </section>
    )
  }
  return (
    <section style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
        Resubmission Queue
        <span
          style={{
            marginLeft:      8,
            padding:         '2px 8px',
            borderRadius:    4,
            fontSize:        12,
            fontWeight:      600,
            backgroundColor: '#dbeafe',
            color:           '#1e40af',
          }}
        >
          {queue.length}
        </span>
      </h2>
      {queue.map((item) => (
        <div
          key={item.attempt_id}
          style={{
            border:       '1px solid #bfdbfe',
            borderRadius: 6,
            padding:      '10px 14px',
            marginBottom: 10,
            background:   '#eff6ff',
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 13 }}>{item.resource_title}</div>
          <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
            {item.topic ?? '—'}
            <span style={{ marginLeft: 16, fontFamily: 'monospace' }}>{item.resource_key}</span>
          </div>
          {item.feedback && (
            <div style={{ fontSize: 12, color: '#1e40af', marginTop: 6 }}>
              Teacher: {item.feedback}
            </div>
          )}
        </div>
      ))}
    </section>
  )
}

function RecentAttemptsSection({ attempts }: { attempts: RecentAttemptItem[] }) {
  if (!attempts.length) {
    return (
      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Recent Attempts</h2>
        <p style={{ fontSize: 13, color: '#9ca3af' }}>No attempts yet.</p>
      </section>
    )
  }
  return (
    <section style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Recent Attempts</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
            <th style={{ textAlign: 'left', padding: '4px 12px 4px 0', color: '#6b7280', fontWeight: 600, fontFamily: 'system-ui' }}>Resource</th>
            <th style={{ textAlign: 'left', padding: '4px 12px 4px 0', color: '#6b7280', fontWeight: 600, fontFamily: 'system-ui' }}>Topic</th>
            <th style={{ textAlign: 'left', padding: '4px 12px 4px 0', color: '#6b7280', fontWeight: 600, fontFamily: 'system-ui' }}>Result</th>
            <th style={{ textAlign: 'left', padding: '4px 0',           color: '#6b7280', fontWeight: 600, fontFamily: 'system-ui' }}>Submitted</th>
          </tr>
        </thead>
        <tbody>
          {attempts.map((a) => (
            <tr key={a.attempt_id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '5px 12px 5px 0', color: '#111827', fontWeight: 500 }}>
                {a.resource_title.length > 50 ? `${a.resource_title.slice(0, 50)}…` : a.resource_title}
                {a.attempt_type === 'resubmission' && (
                  <span style={{ marginLeft: 6, fontSize: 10, color: '#6b7280' }}>(resubmission)</span>
                )}
              </td>
              <td style={{ padding: '5px 12px 5px 0', color: '#6b7280' }}>{a.topic ?? '—'}</td>
              <td style={{ padding: '5px 12px 5px 0' }}><ResultBadge result={a.result} /></td>
              <td style={{ padding: '5px 0', color: '#6b7280', whiteSpace: 'nowrap' }}>
                {new Date(a.submitted_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function SupabaseResultsPage() {
  const mode   = getContentSourceMode()
  const liveEnv = getLiveSupabaseEnvPresence()
  const envOk  = isLiveSupabaseConfigured()
  const isLive = mode === 'live_supabase'

  const report = isLive && envOk ? await getLiveSupabaseStudentResults() : null

  const accuracyPct = report?.accuracy != null
    ? `${(report.accuracy * 100).toFixed(0)}%`
    : '—'

  return (
    <main style={{ padding: '2rem', maxWidth: 860, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Student Results
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 20, fontSize: 14 }}>
        Gate 59 — Supabase student result report. Default student: <code>local_demo_student</code> · <code>physics_0625</code>.
      </p>

      <Alert variant="warn">
        Gate 59 reads Supabase results. Auth is Gate 60 — currently shows demo student only.
      </Alert>

      {!isLive && (
        <Alert variant="warn">
          Mode: <strong>{mode}</strong>. Set{' '}
          <code>QA_CONTENT_SOURCE=live_supabase</code> in <code>apps/admin/.env.local</code> to view results.
        </Alert>
      )}

      {isLive && !envOk && (
        <Alert variant="warn">
          Live Supabase env vars missing ({liveEnv.supabase_url ? '✓' : '✗'} URL,{' '}
          {liveEnv.service_role_key ? '✓' : '✗'} key).
        </Alert>
      )}

      {isLive && envOk && !report && (
        <Alert variant="info">
          No data found for <code>local_demo_student</code> · <code>physics_0625</code>.
          Run a test attempt first.
        </Alert>
      )}

      {report && (
        <>
          {/* Student meta */}
          <section style={{ marginBottom: 24 }}>
            <table style={{ borderCollapse: 'collapse', fontSize: 13 }}>
              <tbody>
                <tr>
                  <td style={{ color: '#9ca3af', paddingRight: 16, paddingBottom: 4 }}>Student</td>
                  <td style={{ fontWeight: 600 }}>{report.student_name}</td>
                </tr>
                <tr>
                  <td style={{ color: '#9ca3af', paddingRight: 16 }}>Subject</td>
                  <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{report.subject_slug}</td>
                </tr>
              </tbody>
            </table>
          </section>

          {/* Stat cards */}
          <section style={{ marginBottom: 28 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
              <StatCard label="Attempts"           value={report.attempt_count} />
              <StatCard label="Marked"             value={report.marked_attempt_count} />
              <StatCard label="Correct"            value={report.correct_count} />
              <StatCard label="Incorrect"          value={report.incorrect_count} />
              <StatCard label="Resubmit"           value={report.needs_resubmission_count} />
              <StatCard label="Pending review"     value={report.pending_teacher_review_count} />
              <StatCard
                label="Accuracy"
                value={accuracyPct}
                sub={report.accuracy != null
                  ? `${report.correct_count}/${report.correct_count + report.incorrect_count + report.partially_correct_count} resolved`
                  : 'no resolved attempts'}
              />
            </div>
          </section>

          {/* Status breakdown */}
          {(report.unmarked_count > 0 || report.teacher_review_required_count > 0) && (
            <Alert variant="info">
              {report.unmarked_count > 0 && (
                <span>{report.unmarked_count} unmarked attempt{report.unmarked_count > 1 ? 's' : ''}. </span>
              )}
              {report.teacher_review_required_count > 0 && (
                <span>{report.teacher_review_required_count} awaiting teacher review.</span>
              )}
            </Alert>
          )}

          <StrengthsSection report={report} />
          <SkillGapsSection gaps={report.skill_gaps} />
          <ResubmissionSection queue={report.resubmission_queue} />
          <RecentAttemptsSection attempts={report.recent_attempts} />
        </>
      )}

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 8 }}>
        <a href="/learn/supabase-attempt-review" style={{ color: '#3b82f6', marginRight: 16 }}>
          Teacher Review Queue
        </a>
        <a href="/system/student-results" style={{ color: '#3b82f6', marginRight: 16 }}>
          Student Results Diagnostic
        </a>
        <a href="/learn/practice" style={{ color: '#3b82f6' }}>
          Go to Practice
        </a>
      </p>
    </main>
  )
}
