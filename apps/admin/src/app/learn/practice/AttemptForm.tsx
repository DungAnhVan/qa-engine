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
  const [answer, setAnswer] = useState('')
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [confidence, setConfidence] = useState<ConfidenceLevel | ''>('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const showOptions = hasRealOptions(resource.options)
  const isResubmission = mode === 'resubmission' || attemptType === 'resubmission'

  function reset() {
    setSubmitted(false)
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
          package_id: packageId,
          resource_id: resource.resource_id,
          resource_type: resource.resource_type,
          topic: resource.topic,
          skill_name: resource.skill_name,
          skill_type: resource.skill_type,
          difficulty: resource.difficulty,
          student_answer: answer.trim(),
          selected_option: selectedOption,
          self_confidence: confidence || null,
          attempt_type: isResubmission ? 'resubmission' : 'first_attempt',
          parent_attempt_id: parentAttemptId ?? null,
        }),
      })

      const data = (await res.json()) as { ok?: boolean; error?: string }

      if (!res.ok) {
        setError(data.error ?? 'Failed to save attempt.')
        return
      }

      setSubmitted(true)
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    if (isResubmission) {
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
          <a href="/learn/results" className="practice-redo-link" style={{ marginTop: 10, display: 'inline-block' }}>
            ← Back to Results
          </a>
        </div>
      )
    }

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
          placeholder={isResubmission ? 'Submit your full revised answer here…' : 'Show your working here…'}
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
