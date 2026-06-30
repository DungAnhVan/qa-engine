/**
 * /learn/supabase-attempt-review — Gate 58 teacher review queue.
 *
 * Server Component — queue data is server-fetched, no secrets reach the browser.
 * TeacherReviewForm is a client component (decision + submit only).
 *
 * Only meaningful when QA_CONTENT_SOURCE = live_supabase.
 */
import { getContentSourceMode } from '@/lib/contentSource'
import { isLiveSupabaseConfigured, getLiveSupabaseTeacherReviewQueue } from '@/lib/liveSupabaseTeacherReview'
import { getLiveSupabaseEnvPresence } from '@/lib/liveSupabaseContent'
import { TeacherReviewForm } from './TeacherReviewForm'
import { requireAppRole } from '@/lib/roleAccess'

export const dynamic = 'force-dynamic'

function Alert({ variant, children }: { variant: 'warn' | 'info' | 'ok'; children: React.ReactNode }) {
  const colors = {
    warn: { bg: '#fef3c7', color: '#92400e' },
    info: { bg: '#dbeafe', color: '#1e40af' },
    ok:   { bg: '#d1fae5', color: '#065f46' },
  }
  const c = colors[variant]
  return (
    <div
      style={{
        padding:      '10px 14px',
        background:   c.bg,
        borderRadius: 4,
        fontSize:     13,
        color:        c.color,
        marginBottom: 16,
      }}
    >
      {children}
    </div>
  )
}

function Tag({ label }: { label: string }) {
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '1px 7px',
        borderRadius:    4,
        fontSize:        11,
        fontWeight:      600,
        backgroundColor: '#f3f4f6',
        color:           '#374151',
        marginRight:     6,
      }}
    >
      {label}
    </span>
  )
}

export default async function SupabaseAttemptReviewPage() {
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
  const mode  = getContentSourceMode()
  const envOk = isLiveSupabaseConfigured()
  const isLive = mode === 'live_supabase'

  const queue = isLive && envOk ? await getLiveSupabaseTeacherReviewQueue(20) : []

  return (
    <main style={{ padding: '2rem', maxWidth: 800, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Teacher Review Queue
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 20, fontSize: 14 }}>
        Gate 58 — Supabase student attempt review.
        Attempts with <code>marking_status = teacher_review_required</code>.
      </p>

      {!isLive && (
        <Alert variant="warn">
          Mode: <strong>{mode}</strong>. Set{' '}
          <code>QA_CONTENT_SOURCE=live_supabase</code> in{' '}
          <code>apps/admin/.env.local</code> to use this queue.
        </Alert>
      )}

      {isLive && !envOk && (
        <Alert variant="warn">
          Live Supabase environment variables missing. Check{' '}
          <code>SUPABASE_URL</code> and <code>SUPABASE_SERVICE_ROLE_KEY</code> in{' '}
          <code>apps/admin/.env.local</code>.
        </Alert>
      )}

      {isLive && envOk && queue.length === 0 && (
        <Alert variant="ok">
          No Supabase teacher review items. Queue is empty.
        </Alert>
      )}

      {isLive && envOk && queue.length > 0 && (
        <Alert variant="info">
          {queue.length} attempt{queue.length !== 1 ? 's' : ''} pending review.
          Reviews are saved immediately to Supabase. The item disappears from the
          queue once reviewed.
        </Alert>
      )}

      {/* Queue items */}
      <div>
        {queue.map((item) => (
          <div
            key={item.attempt_id}
            style={{
              border:       '1px solid #e5e7eb',
              borderRadius: 6,
              padding:      '16px 20px',
              marginBottom: 20,
              background:   '#fff',
            }}
          >
            {/* Header */}
            <div style={{ marginBottom: 10 }}>
              <span style={{ fontWeight: 700, fontSize: 15 }}>{item.resource_title}</span>
              <div style={{ marginTop: 4 }}>
                {item.resource_type && <Tag label={item.resource_type} />}
                {item.skill_type && <Tag label={item.skill_type} />}
                {item.subject_slug && <Tag label={item.subject_slug} />}
              </div>
            </div>

            {/* Meta */}
            <table style={{ borderCollapse: 'collapse', fontSize: 12, marginBottom: 12 }}>
              <tbody>
                <tr>
                  <td style={{ color: '#9ca3af', paddingRight: 14, whiteSpace: 'nowrap' }}>Student</td>
                  <td style={{ color: '#374151' }}>{item.student_name}</td>
                </tr>
                <tr>
                  <td style={{ color: '#9ca3af', paddingRight: 14 }}>Topic</td>
                  <td style={{ color: '#374151' }}>{item.topic ?? '—'}</td>
                </tr>
                <tr>
                  <td style={{ color: '#9ca3af', paddingRight: 14 }}>Resource key</td>
                  <td style={{ color: '#374151', fontFamily: 'monospace' }}>{item.resource_key}</td>
                </tr>
                <tr>
                  <td style={{ color: '#9ca3af', paddingRight: 14 }}>Submitted</td>
                  <td style={{ color: '#374151' }}>
                    {item.submitted_at ? new Date(item.submitted_at).toLocaleString() : '—'}
                  </td>
                </tr>
              </tbody>
            </table>

            {/* Student answer */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 4 }}>
                Student answer
              </div>
              <div
                style={{
                  padding:         '8px 12px',
                  backgroundColor: '#f9fafb',
                  borderRadius:    4,
                  fontSize:        13,
                  color:           '#111827',
                  whiteSpace:      'pre-wrap',
                  minHeight:       40,
                  border:          '1px solid #e5e7eb',
                }}
              >
                {item.answer_text || <span style={{ color: '#9ca3af' }}>No answer text provided.</span>}
              </div>
            </div>

            {/* Current auto-marking result (if any) */}
            {item.current_result && (
              <div style={{ marginBottom: 10, fontSize: 12, color: '#6b7280' }}>
                Current auto-mark result:{' '}
                <strong>{item.current_result}</strong>
                {item.current_feedback && (
                  <span style={{ marginLeft: 8 }}>— {item.current_feedback}</span>
                )}
              </div>
            )}

            {/* Review form (client component) */}
            <TeacherReviewForm
              attempt_id={item.attempt_id}
              resource_title={item.resource_title}
              resource_key={item.resource_key}
              resource_type={item.resource_type}
            />
          </div>
        ))}
      </div>

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 16 }}>
        <a href="/system/teacher-review" style={{ color: '#3b82f6', marginRight: 16 }}>
          Teacher Review Diagnostic
        </a>
        <a href="/system/marking" style={{ color: '#3b82f6', marginRight: 16 }}>
          Marking Diagnostic
        </a>
        <a href="/learn/practice" style={{ color: '#3b82f6' }}>
          Go to Practice
        </a>
      </p>
    </main>
  )
}
