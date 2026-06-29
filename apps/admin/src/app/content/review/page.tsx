import type { Metadata } from 'next'
import React from 'react'
import {
  getTeacherReviewQueue,
  getTeacherReviewDecisions,
  getReviewSummary,
  type ReviewItem,
  type Decision,
  type DecisionValue,
} from '@/lib/teacherReview'
import { submitDecisionAction } from '@/lib/reviewActions'

export const metadata: Metadata = { title: 'Teacher Review Queue' }
export const dynamic = 'force-dynamic'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function shortId(id: string): string {
  const parts = id.split('_')
  return parts.slice(-5).join('_')
}

function DiffBadge({ d }: { d: string | null }) {
  const cls = !d ? 'badge-gray' : d === 'easy' ? 'badge-green' : d === 'hard' ? 'badge-red' : 'badge-blue'
  return <span className={`badge ${cls}`}>{d ?? '—'}</span>
}

function DecisionBadge({ d }: { d: DecisionValue | null | undefined }) {
  if (!d) return <span className="badge badge-gray">pending</span>
  const cls = d === 'approved' ? 'badge-green' : d === 'revise' ? 'badge-yellow' : 'badge-red'
  return <span className={`badge ${cls}`}>{d}</span>
}

// ─── Resource content block ───────────────────────────────────────────────────

function FieldLine({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="field-block">
      <span className="field-label">{label}</span>
      <span className="field-val">{value}</span>
    </div>
  )
}

function ResourceContent({ item }: { item: ReviewItem }) {
  const opts: Array<[string, string]> = item.options
    ? (Object.entries(item.options) as Array<[string, string | null]>).filter(
        (e): e is [string, string] => e[1] !== null,
      )
    : []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <FieldLine label="Student Prompt" value={item.student_prompt} />
      {opts.length > 0 && (
        <div className="field-block">
          <span className="field-label">Options</span>
          {opts.map(([k, v]) => (
            <div key={k} style={{ display: 'flex', gap: 8, fontSize: '0.8rem', lineHeight: 1.5 }}>
              <span style={{ fontWeight: 700, minWidth: 20 }}>{k}.</span>
              <span>{v}</span>
            </div>
          ))}
        </div>
      )}
      <FieldLine label="Correct Answer"      value={item.correct_answer} />
      <FieldLine label="Worked Solution"     value={item.worked_solution} />
      <FieldLine label="Marking Guidance"    value={item.marking_guidance} />
      <FieldLine label="Common Misconception" value={item.common_misconception} />
      <FieldLine label="Teacher Note"        value={item.teacher_note} />
    </div>
  )
}

// ─── Single review card ───────────────────────────────────────────────────────

function ReviewCard({
  item,
  decision,
}: {
  item: ReviewItem
  decision: Decision | undefined
}) {
  const d = decision?.decision ?? null
  const cardClass = `review-card ${d ?? 'pending'}`
  const existingNotes = decision?.teacher_notes ?? ''

  return (
    <div className={cardClass}>
      {/* Header row */}
      <div className="review-card-header">
        <code className="pkg-id" title={item.resource_id}>{shortId(item.resource_id)}</code>
        <span className="badge badge-gray" style={{ fontSize: '0.7rem' }}>
          {item.resource_type.replace(/_/g, ' ')}
        </span>
        <DiffBadge d={item.difficulty} />
        <DecisionBadge d={d} />
        {item.suggested_action && (
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
            Suggested: {item.suggested_action.replace(/_/g, ' ')}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="review-card-body">
        {/* Skill + topic */}
        <div style={{ fontSize: '0.82rem' }}>
          <strong>{item.skill_name}</strong>
          <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>
            {item.skill_type}
          </span>
        </div>

        {/* Validation warnings */}
        {item.validation_warnings.map((w, i) => (
          <div key={i} className="validation-warn">⚠ {w}</div>
        ))}
        {item.validation_errors.map((e, i) => (
          <div key={i} className="validation-error">✗ {e}</div>
        ))}

        {/* Expandable resource content */}
        <details className="resource-details">
          <summary>View Resource Content</summary>
          <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
            <ResourceContent item={item} />
          </div>
        </details>

        {/* Decision form */}
        <form action={submitDecisionAction} className="review-form">
          <input type="hidden" name="review_id"    value={item.review_id} />
          <input type="hidden" name="bank_item_id" value={item.bank_item_id} />
          <input type="hidden" name="resource_id"  value={item.resource_id} />

          <label className="field-label" htmlFor={`notes-${item.review_id}`}>
            Teacher Notes
          </label>
          <textarea
            id={`notes-${item.review_id}`}
            name="teacher_notes"
            className="review-notes"
            defaultValue={existingNotes}
            placeholder="Optional notes for this decision…"
          />

          <div className="review-actions">
            <button type="submit" name="decision" value="approved" className="btn btn-approve">
              ✓ Approve
            </button>
            <button type="submit" name="decision" value="revise"   className="btn btn-revise">
              ↻ Needs Revision
            </button>
            <button type="submit" name="decision" value="rejected" className="btn btn-reject">
              ✗ Reject
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default async function TeacherReviewPage() {
  const [queue, decisionFile] = await Promise.all([
    getTeacherReviewQueue(),
    getTeacherReviewDecisions(),
  ])

  if (!queue) {
    return (
      <div className="page">
        <a href="/content" className="back-link">← Content Registry</a>
        <h1 className="page-title">Teacher Review Queue</h1>
        <div className="warn-card">Review queue file not found. Run the pipeline to generate it.</div>
      </div>
    )
  }

  const decisions = decisionFile.decisions
  const decisionMap = new Map<string, Decision>(decisions.map((d) => [d.review_id, d]))
  const summary = getReviewSummary(queue.items, decisions)

  // Group by topic preserving order
  const grouped = new Map<string, ReviewItem[]>()
  for (const item of queue.items) {
    const key = item.topic || 'Unknown Topic'
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(item)
  }

  return (
    <div className="page">
      <a href="/content" className="back-link">← Content Registry</a>

      <h1 className="page-title">Teacher Review Queue</h1>
      <p className="page-sub">
        Queue: <code>{queue.queue_id}</code> &nbsp;·&nbsp;
        Created: {queue.created_at.slice(0, 10)} &nbsp;·&nbsp;
        Status: {queue.status.replace(/_/g, ' ')}
      </p>

      {/* Summary cards */}
      <div className="card-row">
        {([
          { label: 'Total Items', value: summary.total },
          { label: 'Pending',     value: summary.pending },
          { label: 'Approved',    value: summary.approved },
          { label: 'Needs Revision', value: summary.revise },
          { label: 'Rejected',    value: summary.rejected },
        ] as const).map((c) => (
          <div key={c.label} className="stat-card">
            <div className="value">{c.value}</div>
            <div className="label">{c.label}</div>
          </div>
        ))}
      </div>

      {/* Items by topic */}
      {[...grouped.entries()].map(([topic, items]) => {
        const dm = items.map((i) => decisionMap.get(i.review_id)?.decision)
        const topicPending = dm.filter((d) => !d).length

        return (
          <div key={topic} className="section" style={{ marginBottom: 20 }}>
            <div className="section-header">
              {topic}
              <span style={{ fontWeight: 400, fontSize: '0.82rem', marginLeft: 8, color: 'rgba(255,255,255,.7)' }}>
                ({items.length} items · {topicPending} pending)
              </span>
            </div>
            <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {items.map((item) => (
                <ReviewCard
                  key={item.review_id}
                  item={item}
                  decision={decisionMap.get(item.review_id)}
                />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
