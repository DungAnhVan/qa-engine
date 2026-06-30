/**
 * /system/marking — Gate 57 marking diagnostic page.
 *
 * Server Component — no secrets reach the browser.
 * Shows unmarked attempts queue and rule-based marking readiness.
 *
 * Gate 58: teacher review UI for pending_teacher_review results.
 */
import { getContentSourceMode } from '@/lib/contentSource'
import { getLiveSupabaseEnvPresence, isLiveSupabaseConfigured } from '@/lib/liveSupabaseContent'
import { getLiveSupabaseUnmarkedAttempts } from '@/lib/liveSupabaseMarking'

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
        marginTop:  10,
        padding:    '8px 12px',
        background: c.bg,
        borderRadius: 4,
        fontSize:   13,
        color:      c.color,
      }}
    >
      {children}
    </div>
  )
}

export default async function MarkingPage() {
  const mode    = getContentSourceMode()
  const liveEnv = getLiveSupabaseEnvPresence()
  const envOk   = isLiveSupabaseConfigured()
  const isLive  = mode === 'live_supabase'

  const unmarked = isLive ? await getLiveSupabaseUnmarkedAttempts(10) : []

  const AUTO_MARK_TYPES = ['calculation_drill', 'short_answer_calculation', 'algebra_drill']
  const REVIEW_TYPES    = [
    'graphing_drill', 'diagram_or_graph_drill', 'experiment_planning_task',
    'planning_marking_checklist', 'graph_marking_checklist', 'marking_checklist',
    'data_interpretation_drill', 'worked_example', 'conceptual_explanation', 'essay_planning',
  ]

  return (
    <main style={{ padding: '2rem', maxWidth: 740, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Marking Diagnostic
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 28, fontSize: 14 }}>
        Gate 57 — rule-based marking. Teacher review UI is Gate 58.
        No secrets are displayed on this page.
      </p>

      {/* ── Mode ── */}
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
                    ? <Badge label="live_supabase — marking enabled" ok />
                    : <Badge label={`${mode} — marking not available`} ok={false} />}
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
            <code>apps/admin/.env.local</code> to enable marking.
          </Alert>
        )}
      </section>

      {/* ── Rule routing ── */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>Marking Rules — Gate 57</h2>
        <div style={{ marginBottom: 10 }}>
          <strong style={{ fontSize: 13 }}>Auto-marked (numeric overlap):</strong>
          <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {AUTO_MARK_TYPES.map(t => (
              <span
                key={t}
                style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 12,
                  backgroundColor: '#d1fae5',
                  color: '#065f46',
                }}
              >
                {t}
              </span>
            ))}
          </div>
        </div>
        <div>
          <strong style={{ fontSize: 13 }}>Teacher review required:</strong>
          <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {REVIEW_TYPES.map(t => (
              <span
                key={t}
                style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 12,
                  backgroundColor: '#fef3c7',
                  color: '#92400e',
                }}
              >
                {t}
              </span>
            ))}
          </div>
        </div>
        <Alert variant="info">
          Marking endpoint: <code>POST /api/mark-attempt</code> — body:{' '}
          <code>{'{ "attempt_id": "<uuid>" }'}</code>
        </Alert>
      </section>

      {/* ── Unmarked queue ── */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
          Unmarked Attempts Queue
          <InfoBadge label={isLive ? `${unmarked.length} shown (latest 10)` : 'mode not live'} />
        </h2>
        {!isLive && (
          <Alert variant="warn">Switch to live_supabase mode to see the unmarked queue.</Alert>
        )}
        {isLive && unmarked.length === 0 && (
          <Alert variant="info">No unmarked attempts. Queue is empty.</Alert>
        )}
        {isLive && unmarked.length > 0 && (
          <table
            style={{
              width:           '100%',
              borderCollapse:  'collapse',
              fontSize:        12,
              fontFamily:      'monospace',
            }}
          >
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>
                <th style={{ padding: '4px 12px 4px 0', color: '#6b7280', fontFamily: 'system-ui' }}>Attempt ID</th>
                <th style={{ padding: '4px 12px 4px 0', color: '#6b7280', fontFamily: 'system-ui' }}>Submitted</th>
                <th style={{ padding: '4px 0',           color: '#6b7280', fontFamily: 'system-ui' }}>Answer (truncated)</th>
              </tr>
            </thead>
            <tbody>
              {unmarked.map((a) => (
                <tr key={a.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '4px 12px 4px 0', color: '#374151' }}>
                    {a.id.slice(0, 8)}…
                  </td>
                  <td style={{ padding: '4px 12px 4px 0', color: '#6b7280' }}>
                    {a.submitted_at ? new Date(a.submitted_at).toLocaleString() : '—'}
                  </td>
                  <td style={{ padding: '4px 0', color: '#374151', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {a.answer_text ? a.answer_text.slice(0, 60) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* ── Gate 58 notice ── */}
      <Alert variant="warn">
        Gate 58: teacher review UI — viewing and resolving{' '}
        <code>pending_teacher_review</code> results. Not yet implemented.
      </Alert>

      {/* ── Navigation ── */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/system/attempt-write" style={{ color: '#3b82f6', marginRight: 16 }}>
          Attempt Write Diagnostic
        </a>
        <a href="/system/content-source" style={{ color: '#3b82f6', marginRight: 16 }}>
          Content Source
        </a>
        <a href="/learn/practice" style={{ color: '#3b82f6' }}>
          Go to Practice
        </a>
      </p>
    </main>
  )
}
