'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

interface Props {
  attempt_id:     string
  resource_title: string
  resource_key:   string
  resource_type:  string | null
}

type Decision = 'correct' | 'incorrect' | 'partially_correct' | 'needs_resubmission'

interface SubmitResult {
  status?:            string
  storage?:           string
  review_id?:         string
  marked_attempt_id?: string
  decision?:          string
  success?:           boolean
  error?:             string
}

const DECISION_LABELS: Record<Decision, string> = {
  correct:            'Correct',
  incorrect:          'Incorrect',
  partially_correct:  'Partially correct',
  needs_resubmission: 'Needs resubmission',
}

const DECISION_COLORS: Record<Decision, { bg: string; fg: string }> = {
  correct:            { bg: '#d1fae5', fg: '#065f46' },
  incorrect:          { bg: '#fee2e2', fg: '#991b1b' },
  partially_correct:  { bg: '#fef3c7', fg: '#92400e' },
  needs_resubmission: { bg: '#dbeafe', fg: '#1e40af' },
}

export function TeacherReviewForm({ attempt_id, resource_title, resource_key, resource_type }: Props) {
  const router = useRouter()

  const [decision, setDecision]   = useState<Decision | ''>('')
  const [score, setScore]         = useState<string>('')
  const [feedback, setFeedback]   = useState('')
  const [notes, setNotes]         = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult]       = useState<SubmitResult | null>(null)
  const [error, setError]         = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!decision) { setError('Please select a decision.'); return }
    if (!feedback.trim()) { setError('Feedback is required.'); return }
    setSubmitting(true)
    setError(null)

    try {
      const res = await fetch('/api/supabase/teacher-attempt-review', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          attempt_id,
          decision,
          score:    score !== '' ? parseFloat(score) : null,
          feedback: feedback.trim(),
          notes:    notes.trim() || null,
        }),
      })
      const data = (await res.json()) as SubmitResult
      if (!res.ok || data.error) {
        setError(data.error ?? 'Submission failed.')
        return
      }
      setResult(data)
      // Re-fetch server component data so this item leaves the queue
      router.refresh()
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    const d = (result.decision ?? 'correct') as Decision
    const c = DECISION_COLORS[d] ?? DECISION_COLORS.correct
    return (
      <div
        style={{
          marginTop:       12,
          padding:         '10px 14px',
          borderRadius:    4,
          backgroundColor: c.bg,
          color:           c.fg,
          fontSize:        13,
          fontWeight:      600,
        }}
      >
        Review saved — {DECISION_LABELS[d] ?? d}
        {result.review_id && (
          <span style={{ fontWeight: 400, marginLeft: 10, fontFamily: 'monospace', fontSize: 12 }}>
            review: {result.review_id.slice(0, 8)}…
          </span>
        )}
      </div>
    )
  }

  const showScore =
    decision === 'correct' ||
    decision === 'incorrect' ||
    decision === 'partially_correct'

  return (
    <form onSubmit={handleSubmit} style={{ marginTop: 14 }}>
      {/* Decision */}
      <div style={{ marginBottom: 10 }}>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#374151' }}>
          Decision *
        </label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {(Object.keys(DECISION_LABELS) as Decision[]).map((d) => (
            <label
              key={d}
              style={{
                cursor:          'pointer',
                padding:         '4px 10px',
                borderRadius:    4,
                fontSize:        12,
                fontWeight:      decision === d ? 700 : 400,
                border:          `1px solid ${decision === d ? '#374151' : '#d1d5db'}`,
                backgroundColor: decision === d ? (DECISION_COLORS[d]?.bg ?? '#f3f4f6') : '#f9fafb',
                color:           decision === d ? (DECISION_COLORS[d]?.fg ?? '#374151') : '#374151',
              }}
            >
              <input
                type="radio"
                name={`decision-${attempt_id}`}
                value={d}
                checked={decision === d}
                onChange={() => setDecision(d)}
                style={{ display: 'none' }}
              />
              {DECISION_LABELS[d]}
            </label>
          ))}
        </div>
      </div>

      {/* Score (optional, only for graded decisions) */}
      {showScore && (
        <div style={{ marginBottom: 10 }}>
          <label
            htmlFor={`score-${attempt_id}`}
            style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#374151' }}
          >
            Score (0–1, optional)
          </label>
          <input
            id={`score-${attempt_id}`}
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={score}
            onChange={(e) => setScore(e.target.value)}
            style={{
              width:        80,
              padding:      '4px 8px',
              fontSize:     13,
              border:       '1px solid #d1d5db',
              borderRadius: 4,
            }}
            placeholder="e.g. 0.5"
          />
        </div>
      )}

      {/* Feedback */}
      <div style={{ marginBottom: 10 }}>
        <label
          htmlFor={`feedback-${attempt_id}`}
          style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#374151' }}
        >
          Feedback for student *
        </label>
        <textarea
          id={`feedback-${attempt_id}`}
          rows={3}
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Explain the result and what to improve…"
          style={{
            width:        '100%',
            padding:      '6px 8px',
            fontSize:     13,
            border:       '1px solid #d1d5db',
            borderRadius: 4,
            resize:       'vertical',
            boxSizing:    'border-box',
          }}
        />
      </div>

      {/* Notes (internal) */}
      <div style={{ marginBottom: 12 }}>
        <label
          htmlFor={`notes-${attempt_id}`}
          style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#9ca3af' }}
        >
          Internal notes (optional, not shown to student)
        </label>
        <textarea
          id={`notes-${attempt_id}`}
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Teacher-only notes…"
          style={{
            width:        '100%',
            padding:      '6px 8px',
            fontSize:     12,
            border:       '1px solid #e5e7eb',
            borderRadius: 4,
            resize:       'vertical',
            color:        '#6b7280',
            boxSizing:    'border-box',
          }}
        />
      </div>

      {error && (
        <div style={{ marginBottom: 10, color: '#991b1b', fontSize: 12 }}>{error}</div>
      )}

      <button
        type="submit"
        disabled={submitting}
        style={{
          padding:         '7px 18px',
          fontSize:        13,
          fontWeight:      600,
          backgroundColor: submitting ? '#9ca3af' : '#1d4ed8',
          color:           '#fff',
          border:          'none',
          borderRadius:    4,
          cursor:          submitting ? 'not-allowed' : 'pointer',
        }}
      >
        {submitting ? 'Saving…' : 'Submit review'}
      </button>
    </form>
  )
}
