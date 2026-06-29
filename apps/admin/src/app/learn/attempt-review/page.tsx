import type { Metadata } from 'next'
import {
  getMarkedAttempts,
  getTeacherAttemptReviewDecisions,
  getAttemptReviewSummary,
  type MarkedAttemptItem,
  type AttemptDecision,
} from '@/lib/attemptReview'
import { AttemptReviewForm } from './AttemptReviewForm'

export const metadata: Metadata = { title: 'Attempt Review' }
export const dynamic = 'force-dynamic'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function shortId(id: string) {
  const parts = id.split('_')
  return parts.slice(-4).join('_')
}

function isPlaceholder(answer: string): boolean {
  const a = (answer ?? '').trim().toLowerCase()
  return a.length < 3 || ['test', 'abc', 'placeholder', 'none', 'n/a', 'na', 'null'].includes(a)
}

function DiffBadge({ d }: { d: string | null }) {
  const cls = !d ? 'badge-gray' : d === 'easy' ? 'badge-green' : d === 'hard' ? 'badge-red' : 'badge-blue'
  return <span className={`badge ${cls}`}>{d ?? '—'}</span>
}

function DecisionBadge({ d }: { d: AttemptDecision | null | undefined }) {
  if (!d) return <span className="badge badge-gray">pending</span>
  const cls =
    d.decision === 'correct'            ? 'badge-green'
    : d.decision === 'partially_correct'? 'badge-yellow'
    : d.decision === 'incorrect'        ? 'badge-red'
    :                                     'badge-gray'   // needs_resubmission
  return <span className={`badge ${cls}`}>{d.decision.replace(/_/g, ' ')}</span>
}

function FieldBlock({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="field-block">
      <span className="field-label">{label}</span>
      <span className="field-val">{value}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Review card (server content + client form)
// ---------------------------------------------------------------------------

function AttemptReviewCard({
  item,
  decision,
}: {
  item: MarkedAttemptItem
  decision: AttemptDecision | null
}) {
  const decisionKey = decision?.decision ?? 'pending'
  const placeholder = isPlaceholder(item.student_answer)
  const ref = item.teacher_reference

  return (
    <div className={`review-card ${decisionKey}`}>
      {/* Header */}
      <div className="review-card-header">
        <code style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          {shortId(item.attempt_id)}
        </code>
        <span className="badge badge-blue">{item.resource_type.replace(/_/g, ' ')}</span>
        <DiffBadge d={item.difficulty} />
        {item.self_confidence && (
          <span className="badge badge-gray">conf: {item.self_confidence}</span>
        )}
        <DecisionBadge d={decision} />
      </div>

      {/* Body */}
      <div className="review-card-body">
        {/* Skill info */}
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 6 }}>
          {item.topic} &middot; {item.skill_type} &middot; <em>{item.skill_name}</em>
        </div>

        {/* Student answer */}
        <div className="field-block">
          <span className="field-label">Student Answer</span>
          <div className={`ar-student-answer${placeholder ? ' placeholder' : ''}`}>
            {placeholder && (
              <span className="ar-placeholder-warn">Placeholder detected — </span>
            )}
            {item.student_answer || <em style={{ color: 'var(--text-muted)' }}>(empty)</em>}
          </div>
        </div>

        {/* Rule-based feedback */}
        <div className="field-block">
          <span className="field-label">Rule-based Feedback</span>
          <span className="field-val" style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
            {item.feedback}
          </span>
        </div>

        {/* Teacher reference */}
        {(ref.marking_guidance || ref.worked_solution || ref.common_misconception) && (
          <details className="resource-details" style={{ marginTop: 4 }}>
            <summary>Teacher Reference</summary>
            <div className="resource-expand">
              <FieldBlock label="Marking Guidance"   value={ref.marking_guidance} />
              <FieldBlock label="Worked Solution"    value={ref.worked_solution} />
              <FieldBlock label="Common Misconception" value={ref.common_misconception} />
            </div>
          </details>
        )}

        {/* Review form (client component) */}
        <AttemptReviewForm
          markedAttemptId={item.marked_attempt_id}
          attemptId={item.attempt_id}
          studentId={item.student_id}
          resourceId={item.resource_id}
          existingDecision={decision}
        />
      </div>
    </div>
  )
}

function TopicGroup({
  topic,
  items,
  decisionMap,
}: {
  topic: string
  items: MarkedAttemptItem[]
  decisionMap: Map<string, AttemptDecision>
}) {
  return (
    <section className="learn-topic-section">
      <div className="learn-topic-heading">
        <span className="learn-topic-name">{topic}</span>
        <span className="learn-topic-count">
          {items.length} item{items.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {items.map((item) => (
          <AttemptReviewCard
            key={item.marked_attempt_id}
            item={item}
            decision={decisionMap.get(item.marked_attempt_id) ?? null}
          />
        ))}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function AttemptReviewPage() {
  const markedDoc = await getMarkedAttempts()

  if (!markedDoc) {
    return (
      <div className="learn-page">
        <h1 className="learn-page-title">Quanta Aptus Attempt Review</h1>
        <div className="learn-empty">
          <div className="learn-empty-icon">📋</div>
          <div className="learn-empty-title">No marked attempts found.</div>
          <div className="learn-empty-hint">
            Run:<br />
            <code
              style={{
                display: 'inline-block',
                background: '#1a202c',
                color: '#e2e8f0',
                padding: '6px 12px',
                borderRadius: 4,
                fontSize: '0.78rem',
                marginTop: 6,
              }}
            >
              .venv-ingest\Scripts\python.exe tools\ingest\mark_student_attempts_v1.py
            </code>
          </div>
        </div>
      </div>
    )
  }

  const decisionsDoc = await getTeacherAttemptReviewDecisions()
  const decisionMap = new Map(
    decisionsDoc.decisions.map((d) => [d.marked_attempt_id, d]),
  )

  const allItems = markedDoc.items
  const reviewItems = allItems.filter(
    (i) => i.marking_status === 'teacher_review_required' || i.needs_teacher_review,
  )

  const summary = getAttemptReviewSummary(allItems, decisionsDoc.decisions)

  const cards = [
    { label: 'Total Attempts',       value: summary.total },
    { label: 'Auto-marked',          value: summary.auto_marked },
    { label: 'Review Required',      value: summary.review_required },
    { label: 'Pending Review',       value: summary.pending_review },
    { label: 'Reviewed',             value: summary.reviewed },
    { label: 'Correct After Review', value: summary.correct_after_review },
    { label: 'Needs Resubmission',   value: summary.needs_resubmission },
  ]

  // Group by topic
  const topicMap = new Map<string, MarkedAttemptItem[]>()
  for (const item of reviewItems) {
    const t = item.topic || 'Other'
    const arr = topicMap.get(t)
    if (arr) arr.push(item)
    else topicMap.set(t, [item])
  }

  return (
    <div className="learn-page">
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          marginBottom: 4,
        }}
      >
        <h1 className="learn-page-title">Quanta Aptus Attempt Review</h1>
        <a href="/learn/results" className="action-link">Results →</a>
      </div>
      <p className="learn-page-sub">
        Teacher review for student attempts that rule-based marking cannot safely mark.
      </p>

      {/* Summary cards */}
      <div className="learn-card-row">
        {cards.map((c) => (
          <div key={c.label} className="learn-stat-card">
            <div className="learn-stat-val">{c.value}</div>
            <div className="learn-stat-label">{c.label}</div>
          </div>
        ))}
      </div>

      {/* Review items */}
      {reviewItems.length === 0 ? (
        <div className="learn-empty">
          <div className="learn-empty-icon">✓</div>
          <div className="learn-empty-title">No attempts currently require teacher review.</div>
        </div>
      ) : (
        [...topicMap.entries()].map(([topic, items]) => (
          <TopicGroup
            key={topic}
            topic={topic}
            items={items}
            decisionMap={decisionMap}
          />
        ))
      )}
    </div>
  )
}
