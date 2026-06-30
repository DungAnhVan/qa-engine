'use client'

import { useState } from 'react'
import type { StudentResource } from '@/lib/studentResources'

interface Props {
  resource: StudentResource
  packageId: string
  parentAttemptId?: string
  attemptType?: 'first_attempt' | 'resubmission'
  mode?: string
}

type ConfidenceLevel = 'low' | 'medium' | 'high'

interface SubmitResult {
  ok?: boolean
  status?: string
  storage?: string
  attempt_id?: string
  submitted_at?: string
  marking_status?: string
  error?: string
}

interface MarkResult {
  success?: boolean
  result?: string
  score?: number | null
  max_score?: number | null
  marking_method?: string
  marking_status?: string
  feedback?: string
  resource_type?: string
  error?: string
}

function hasRealOptions(options: Record<string, string | null> | null): boolean {
  if (!options) return false
  return Object.values(options).some((v) => v !== null && v !== '')
}

export function AttemptForm({
  resource,
  packageId,
  parentAttemptId,
  attemptType,
  mode,
}: Props) {
  const [answer, setAnswer]             = useState('')
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [confidence, setConfidence]     = useState<ConfidenceLevel | ''>('')
  const [submitting, setSubmitting]     = useState(false)
  const [submitted, setSubmitted]       = useState(false)
  const [submitResult, setSubmitResult] = useState<SubmitResult | null>(null)
  const [marking, setMarking]           = useState(false)
  const [markResult, setMarkResult]     = useState<MarkResult | null>(null)
  const [error, setError]               = useState<string | null>(null)

  const showOptions   = hasRealOptions(resource.options)
  const isResubmission = mode === 'resubmission' || attemptType === 'resubmission'
  const isSupabase    = submitResult?.storage === 'supabase'

  function reset() {
    setSubmitted(false)
    setSubmitResult(null)
    setMarkResult(null)
    setMarking(false)
    setAnswer('')
    setSelectedOption(null)
    setConfidence('')
    setError(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!answer.trim() && !selectedOption) {
      setError('Please enter your answer or select an option.')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      const res = await fetch('/api/student-attempts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          package_id:       packageId,
          resource_id:      resource.resource_id,
          resource_type:    resource.resource_type,
          topic:            resource.topic,
          skill_name:       resource.skill_name,
          skill_type:       resource.skill_type,
          difficulty:       resource.difficulty,
          student_answer:   answer.trim(),
          selected_option:  selectedOption,
          self_confidence:  confidence || null,
          attempt_type:     isResubmission ? 'resubmission' : 'first_attempt',
          parent_attempt_id: parentAttemptId ?? null,
        }),
      })

      const data = (await res.json()) as SubmitResult

      if (!res.ok) {
        setError(data.error ?? 'Failed to save attempt.')
        return
      }

      setSubmitResult(data)
      setSubmitted(true)

      // Auto-mark in live_supabase mode — non-blocking, graceful on failure
      if (data.storage === 'supabase' && data.attempt_id) {
        setMarking(true)
        try {
          const markRes = await fetch('/api/mark-attempt', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ attempt_id: data.attempt_id }),
          })
          const markData = (await markRes.json()) as MarkResult
          setMarkResult(markData)
        } catch {
          // Marking failed — attempt is still saved; show no marking result
        } finally {
          setMarking(false)
        }
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Submitted: Supabase mode ────────────────────────────────────────────
  if (submitted && isSupabase) {
    const markingColor =
      markResult?.result === 'correct'
        ? { bg: '#d1fae5', fg: '#065f46' }
        : markResult?.result === 'incorrect'
          ? { bg: '#fee2e2', fg: '#991b1b' }
          : { bg: '#fef3c7', fg: '#92400e' }

    return (
      <div className="practice-submitted">
        <span className="practice-submitted-icon">✓</span>
        {isResubmission ? 'Resubmission saved.' : 'Attempt saved.'}

        <div style={{ marginTop: 8, fontSize: 13, color: '#374151' }}>
          <span
            style={{
              display: 'inline-block',
              padding: '2px 8px',
              borderRadius: 4,
              fontSize: 12,
              fontWeight: 600,
              backgroundColor: '#dbeafe',
              color: '#1e40af',
              marginBottom: 6,
            }}
          >
            Saved to: Supabase
          </span>
        </div>

        {submitResult?.attempt_id && (
          <div style={{ fontSize: 12, fontFamily: 'monospace', color: '#6b7280', marginTop: 4 }}>
            Attempt ID: {submitResult.attempt_id}
          </div>
        )}

        {/* Marking section */}
        {marking && (
          <div style={{ marginTop: 10, fontSize: 12, color: '#6b7280' }}>
            Marking…
          </div>
        )}

        {!marking && markResult && markResult.success && (
          <div
            style={{
              marginTop: 10,
              padding: '8px 12px',
              borderRadius: 4,
              backgroundColor: markingColor.bg,
              color: markingColor.fg,
              fontSize: 13,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              Result:{' '}
              {markResult.result === 'correct'
                ? 'Correct'
                : markResult.result === 'incorrect'
                  ? 'Incorrect'
                  : 'Pending teacher review'}
              {markResult.score != null && markResult.max_score != null && (
                <span style={{ marginLeft: 8, fontWeight: 400 }}>
                  ({markResult.score}/{markResult.max_score})
                </span>
              )}
            </div>
            {markResult.feedback && (
              <div style={{ fontSize: 12 }}>{markResult.feedback}</div>
            )}
          </div>
        )}

        {!marking && markResult && !markResult.success && (
          <div style={{ marginTop: 6, fontSize: 12, color: '#6b7280' }}>
            Marking status: {submitResult?.marking_status ?? 'unmarked'}
          </div>
        )}

        {!marking && !markResult && (
          <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
            Marking status: {submitResult?.marking_status ?? 'unmarked'}
          </div>
        )}

        {!isResubmission && (
          <button className="practice-try-again" type="button" onClick={reset}>
            Try again
          </button>
        )}
        {isResubmission && (
          <a
            href="/learn/results"
            className="practice-redo-link"
            style={{ marginTop: 10, display: 'inline-block' }}
          >
            ← Back to Results
          </a>
        )}
      </div>
    )
  }

  // ── Submitted: local mode — resubmission ───────────────────────────────
  if (submitted && isResubmission) {
    return (
      <div className="practice-submitted resubmission">
        <span className="practice-submitted-icon">✓</span>
        Resubmission submitted.
        <div className="practice-resub-next">
          <div className="practice-resub-next-label">Next steps — run in project root:</div>
          <code className="practice-cmd-box">
            .venv-ingest\Scripts\python.exe tools\ingest\mark_student_attempts_v1.py
          </code>
          <code className="practice-cmd-box">
            .venv-ingest\Scripts\python.exe tools\ingest\build_student_result_report_v2.py
          </code>
        </div>
        <a
          href="/learn/results"
          className="practice-redo-link"
          style={{ marginTop: 10, display: 'inline-block' }}
        >
          ← Back to Results
        </a>
      </div>
    )
  }

  // ── Submitted: local mode — first attempt ─────────────────────────────
  if (submitted) {
    return (
      <div className="practice-submitted">
        <span className="practice-submitted-icon">✓</span>
        Attempt submitted successfully.
        <button className="practice-try-again" type="button" onClick={reset}>
          Try again
        </button>
      </div>
    )
  }

  // ── Form ─────────────────────────────────────────────────────────────────
  return (
    <form className="practice-form" onSubmit={handleSubmit}>
      {/* MCQ radio options */}
      {showOptions && (
        <div className="practice-options">
          <div className="practice-label">Select answer</div>
          {Object.entries(resource.options!).map(([key, val]) =>
            val ? (
              <label key={key} className="practice-option-label">
                <input
                  type="radio"
                  name={`opt-${resource.resource_id}`}
                  value={key}
                  checked={selectedOption === key}
                  onChange={() => setSelectedOption(key)}
                />
                <span className="practice-option-key">{key}</span>
                <span className="practice-option-val">{val}</span>
              </label>
            ) : null,
          )}
        </div>
      )}

      {/* Working / explanation */}
      <div className="practice-field">
        <label
          className="practice-label"
          htmlFor={`answer-${resource.resource_id}`}
        >
          {isResubmission ? 'Your revised answer / working' : 'Your working / explanation'}
        </label>
        <textarea
          id={`answer-${resource.resource_id}`}
          className="practice-textarea"
          rows={4}
          placeholder={
            isResubmission
              ? 'Submit your full revised answer here…'
              : 'Show your working here…'
          }
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
        />
      </div>

      {/* Confidence */}
      <div className="practice-field practice-field-row">
        <label
          className="practice-label"
          htmlFor={`conf-${resource.resource_id}`}
        >
          Confidence
        </label>
        <select
          id={`conf-${resource.resource_id}`}
          className="practice-select"
          value={confidence}
          onChange={(e) => setConfidence(e.target.value as ConfidenceLevel | '')}
        >
          <option value="">— select —</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </div>

      {error && <div className="practice-error">{error}</div>}

      <button type="submit" className="practice-submit" disabled={submitting}>
        {submitting
          ? 'Saving…'
          : isResubmission
            ? 'Submit resubmission'
            : 'Submit attempt'}
      </button>
    </form>
  )
}
