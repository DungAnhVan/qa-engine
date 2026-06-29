'use client'

import { useState } from 'react'
import type { AttemptDecision, AttemptDecisionValue } from '@/lib/attemptReview'

interface Props {
  markedAttemptId: string
  attemptId: string
  studentId: string
  resourceId: string
  existingDecision: AttemptDecision | null
}

const DECISION_OPTS: { value: AttemptDecisionValue; label: string; cls: string }[] = [
  { value: 'correct',           label: '✓ Correct',           cls: 'btn-ar-correct'  },
  { value: 'partially_correct', label: '~ Partially Correct', cls: 'btn-ar-partial'  },
  { value: 'incorrect',         label: '✗ Incorrect',         cls: 'btn-ar-incorrect'},
  { value: 'needs_resubmission',label: '↺ Needs Resubmission',cls: 'btn-ar-resubmit' },
]

const SCORE_OPTS: { value: string; label: string }[] = [
  { value: '',    label: '— not scored —' },
  { value: '1',   label: '1 (full mark)'  },
  { value: '0.5', label: '0.5 (half)'     },
  { value: '0',   label: '0 (no mark)'    },
]

export function AttemptReviewForm({
  markedAttemptId,
  attemptId,
  studentId,
  resourceId,
  existingDecision,
}: Props) {
  const [decision, setDecision] = useState<AttemptDecisionValue | ''>(
    existingDecision?.decision ?? '',
  )
  const [score, setScore] = useState<string>(
    existingDecision?.score !== null && existingDecision?.score !== undefined
      ? String(existingDecision.score)
      : '',
  )
  const [feedback, setFeedback] = useState(existingDecision?.teacher_feedback ?? '')
  const [notes,    setNotes]    = useState(existingDecision?.teacher_notes    ?? '')
  const [saving,   setSaving]   = useState(false)
  const [saved,    setSaved]    = useState(!!existingDecision)
  const [error,    setError]    = useState<string | null>(null)

  async function handleSave() {
    if (!decision) { setError('Please select a decision.'); return }
    setSaving(true); setError(null)

    try {
      const res = await fetch('/api/attempt-review/decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          marked_attempt_id: markedAttemptId,
          attempt_id:        attemptId,
          student_id:        studentId,
          resource_id:       resourceId,
          decision,
          score: score !== '' ? Number(score) : null,
          teacher_feedback:  feedback,
          teacher_notes:     notes,
        }),
      })
      const data = (await res.json()) as { ok?: boolean; error?: string }
      if (!res.ok) { setError(data.error ?? 'Failed to save.'); return }
      setSaved(true)
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const decisionLabel = DECISION_OPTS.find((o) => o.value === decision)?.label ?? ''

  return (
    <div className="ar-form">
      {/* Decision buttons */}
      <div className="ar-form-label">Decision</div>
      <div className="ar-decision-btns">
        {DECISION_OPTS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            className={`btn ${opt.cls}${decision === opt.value ? ' ar-selected' : ''}`}
            onClick={() => { setDecision(opt.value); setSaved(false) }}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Score */}
      <div className="ar-form-row">
        <label className="ar-form-label" htmlFor={`score-${markedAttemptId}`}>Score</label>
        <select
          id={`score-${markedAttemptId}`}
          className="practice-select"
          value={score}
          onChange={(e) => { setScore(e.target.value); setSaved(false) }}
        >
          {SCORE_OPTS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Teacher feedback */}
      <div className="ar-form-field">
        <label className="ar-form-label" htmlFor={`fb-${markedAttemptId}`}>
          Feedback for student
        </label>
        <textarea
          id={`fb-${markedAttemptId}`}
          className="practice-textarea"
          rows={3}
          placeholder="Feedback visible to the student…"
          value={feedback}
          onChange={(e) => { setFeedback(e.target.value); setSaved(false) }}
        />
      </div>

      {/* Teacher notes */}
      <div className="ar-form-field">
        <label className="ar-form-label" htmlFor={`tn-${markedAttemptId}`}>
          Teacher notes (private)
        </label>
        <textarea
          id={`tn-${markedAttemptId}`}
          className="practice-textarea"
          rows={2}
          placeholder="Private notes…"
          value={notes}
          onChange={(e) => { setNotes(e.target.value); setSaved(false) }}
        />
      </div>

      {error && <div className="practice-error">{error}</div>}

      <div className="ar-form-actions">
        <button
          type="button"
          className="practice-submit"
          onClick={handleSave}
          disabled={saving || !decision}
        >
          {saving ? 'Saving…' : 'Save review'}
        </button>
        {saved && decision && (
          <span className={`ar-saved-badge ${decision}`}>
            Saved: {decisionLabel}
          </span>
        )}
      </div>
    </div>
  )
}
