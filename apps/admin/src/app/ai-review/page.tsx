import { requireAppRole } from '@/lib/roleAccess'
import {
  readAiTeacherReviewQueue,
  readAiTeacherReviewDecisions,
  getAiReviewSummary,
  type ReviewItem,
} from '@/lib/aiTeacherReview'

export const dynamic = 'force-dynamic'

function Badge({ label, ok, neutral }: { label: string; ok?: boolean; neutral?: boolean }) {
  const bg = neutral ? '#dbeafe' : ok ? '#d1fae5' : '#fee2e2'
  const fg = neutral ? '#1e40af' : ok ? '#065f46' : '#991b1b'
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '2px 8px',
        borderRadius:    4,
        fontSize:        12,
        fontWeight:      600,
        backgroundColor: bg,
        color:           fg,
        marginLeft:      6,
      }}
    >
      {label}
    </span>
  )
}

function RubricEntry({ criterion, marks, guidance }: { criterion: string; marks: number; guidance?: string }) {
  return (
    <li style={{ marginBottom: 4 }}>
      <strong>{criterion}</strong>{' '}
      <span style={{ color: '#6b7280', fontSize: 12 }}>[{marks} mark{marks !== 1 ? 's' : ''}]</span>
      {guidance && <span style={{ color: '#6b7280', fontSize: 12 }}> — {guidance}</span>}
    </li>
  )
}

function SafetyTag({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '1px 6px',
        borderRadius:    3,
        fontSize:        11,
        fontWeight:      600,
        marginRight:     6,
        backgroundColor: ok ? '#d1fae5' : '#fee2e2',
        color:           ok ? '#065f46' : '#991b1b',
      }}
    >
      {label}: {ok ? 'YES' : 'NO'}
    </span>
  )
}

function DecisionStatusBadge({ decision }: { decision: string | null }) {
  if (decision === 'approve')           return <Badge label="APPROVED" ok={true} />
  if (decision === 'needs_revision')    return <Badge label="NEEDS REVISION" />
  if (decision === 'reject')            return <Badge label="REJECTED" ok={false} />
  return <Badge label="PENDING" neutral />
}

function ResourceCard({ item, currentDecision }: { item: ReviewItem; currentDecision: string | null }) {
  const cardBorder = currentDecision === 'approve'        ? '#6ee7b7'
                   : currentDecision === 'needs_revision' ? '#fcd34d'
                   : currentDecision === 'reject'         ? '#fca5a5'
                   : '#e5e7eb'

  return (
    <article
      style={{
        border:       `2px solid ${cardBorder}`,
        borderRadius: 8,
        padding:      '20px 24px',
        marginBottom: 24,
        background:   '#fff',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', marginBottom: 12 }}>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>
            {item.title || item.resource_id}
            <DecisionStatusBadge decision={currentDecision} />
          </h2>
          <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0 0' }}>
            <code>{item.resource_id}</code>
          </p>
        </div>
        <div style={{ fontSize: 12, color: '#6b7280', textAlign: 'right' }}>
          <div><strong>Type:</strong> {item.resource_type}</div>
          <div><strong>Topic:</strong> {item.topic}</div>
          <div><strong>Skill:</strong> {item.skill_name} ({item.skill_type})</div>
          <div><strong>Difficulty:</strong> {item.difficulty}</div>
        </div>
      </div>

      {/* Student prompt */}
      <section style={{ marginBottom: 12 }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 4 }}>Student Prompt</h3>
        <p style={{ fontSize: 13, background: '#f9fafb', padding: '10px 12px', borderRadius: 4, margin: 0, lineHeight: 1.6 }}>
          {item.student_prompt}
        </p>
      </section>

      {/* Answer key */}
      <section style={{ marginBottom: 12 }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 4 }}>Answer Key</h3>
        <p style={{ fontSize: 13, background: '#f0fdf4', padding: '10px 12px', borderRadius: 4, margin: 0, lineHeight: 1.6, fontFamily: 'monospace' }}>
          {item.answer_key}
        </p>
      </section>

      {/* Marking rubric */}
      {item.marking_rubric && item.marking_rubric.length > 0 && (
        <section style={{ marginBottom: 12 }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 4 }}>Marking Rubric</h3>
          <ul style={{ fontSize: 13, paddingLeft: 20, margin: 0, lineHeight: 1.7 }}>
            {item.marking_rubric.map((r, i) => (
              <RubricEntry key={i} criterion={r.criterion} marks={r.marks} guidance={r.guidance} />
            ))}
          </ul>
        </section>
      )}

      {/* Teacher notes */}
      {item.teacher_notes && (
        <section style={{ marginBottom: 12 }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 4 }}>Teacher Notes</h3>
          <p style={{ fontSize: 13, color: '#4b5563', margin: 0, padding: '8px 12px', background: '#fffbeb', borderRadius: 4, lineHeight: 1.6 }}>
            {item.teacher_notes}
          </p>
        </section>
      )}

      {/* Safety declaration */}
      <section style={{ marginBottom: 12 }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Safety Declaration</h3>
        <div>
          <SafetyTag ok={item.safety_declaration?.original_content}        label="original_content" />
          <SafetyTag ok={item.safety_declaration?.no_raw_source_text_used} label="no_raw_source" />
          <SafetyTag ok={item.safety_declaration?.no_mark_scheme_copied}   label="no_mark_scheme" />
        </div>
      </section>

      {/* Decision instructions */}
      <section
        style={{
          marginTop:    12,
          padding:      '10px 14px',
          background:   '#f3f4f6',
          borderRadius: 4,
          fontSize:     12,
          color:        '#374151',
        }}
      >
        <strong>Make a decision:</strong> POST to <code>/api/ai-review/decision</code> with:
        <pre style={{ margin: '6px 0 0', fontSize: 11, color: '#6b7280', whiteSpace: 'pre-wrap' }}>
{`{
  "review_item_id": "${item.review_item_id}",
  "resource_id":    "${item.resource_id}",
  "decision":       "approve" | "needs_revision" | "reject",
  "review_notes":   "optional notes"
}`}
        </pre>
        <p style={{ margin: '6px 0 0', color: '#6b7280' }}>
          Or edit <code>data/ai/review/ai_teacher_review_decisions_v1.json</code> directly during local MVP.
        </p>
      </section>
    </article>
  )
}

export default async function AiReviewPage() {
  const { allowed, currentRole } = await requireAppRole(['admin'])
  if (!allowed) return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Access denied</h1>
      <p style={{ color: '#6b7280', fontSize: 14, marginBottom: 12 }}>
        Required: admin. Your role: <code>{currentRole ?? 'none'}</code>
      </p>
      <a href="/login" style={{ color: '#3b82f6' }}>Sign in →</a>
    </main>
  )

  const queue     = readAiTeacherReviewQueue()
  const decisions = readAiTeacherReviewDecisions()
  const summary   = getAiReviewSummary()

  // Build decision map for display
  const decisionMap = new Map<string, string>()
  for (const d of decisions?.decisions ?? []) {
    decisionMap.set(d.review_item_id, d.decision)
  }

  const items = queue?.items ?? []

  return (
    <main style={{ padding: '2rem', maxWidth: 900, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        AI Teacher Review Queue
        <Badge label="DRAFT ONLY — no auto-publish" neutral />
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
        Gate 69D — review AI-generated resource drafts. Teacher approval required before any use.
        No raw Cambridge text. No API keys. No Supabase writes.
      </p>

      {/* Warning */}
      <div style={{ marginBottom: 24, padding: '12px 16px', background: '#fef3c7', borderRadius: 6, borderLeft: '4px solid #f59e0b', fontSize: 13, color: '#92400e' }}>
        <strong>All resources are AI-generated drafts.</strong> Review each item carefully before approving.
        Approved resources will go to the candidate bank — they are NOT published automatically.
        Gate 69E will handle package building from approved candidates.
      </div>

      {/* Summary */}
      <section style={{ marginBottom: 24, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {[
          { label: 'Total',         value: summary.total_items,         color: '#374151' },
          { label: 'Pending',       value: summary.pending_count,       color: '#92400e' },
          { label: 'Approved',      value: summary.approved_count,      color: '#065f46' },
          { label: 'Needs revision',value: summary.needs_revision_count,color: '#78350f' },
          { label: 'Rejected',      value: summary.rejected_count,      color: '#991b1b' },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            style={{ padding: '10px 18px', background: '#f9fafb', borderRadius: 6, border: '1px solid #e5e7eb', minWidth: 90 }}
          >
            <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>{label}</div>
          </div>
        ))}
      </section>

      {/* No queue */}
      {!queue && (
        <div style={{ padding: '20px', background: '#fee2e2', borderRadius: 6, fontSize: 13, color: '#991b1b' }}>
          <strong>Review queue not found.</strong> Run the queue builder first:
          <pre style={{ margin: '8px 0 0', fontSize: 12 }}>
            .venv-ingest\Scripts\python.exe tools\ai\build_ai_teacher_review_queue_v1.py data\ai\generated_batches\gate69c_sample_generated_batch_v1.json
          </pre>
        </div>
      )}

      {/* Resource cards */}
      {items.map(item => (
        <ResourceCard
          key={item.review_item_id}
          item={item}
          currentDecision={decisionMap.get(item.review_item_id) ?? item.review_decision ?? null}
        />
      ))}

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/system/ai-review"    style={{ color: '#3b82f6', marginRight: 16 }}>AI Review Diagnostic</a>
        <a href="/api/system/ai-review" style={{ color: '#3b82f6', marginRight: 16 }}>AI Review API</a>
        <a href="/system/ai-authoring" style={{ color: '#3b82f6', marginRight: 16 }}>AI Authoring</a>
        <a href="/system/health"       style={{ color: '#3b82f6' }}>Health</a>
      </p>
    </main>
  )
}
