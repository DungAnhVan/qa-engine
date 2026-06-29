import { NextRequest, NextResponse } from 'next/server'
import {
  saveTeacherAttemptReviewDecision,
  type AttemptDecisionInput,
  type AttemptDecisionValue,
} from '@/lib/attemptReview'

const VALID_DECISIONS: AttemptDecisionValue[] = [
  'correct',
  'partially_correct',
  'incorrect',
  'needs_resubmission',
]

export async function POST(req: NextRequest) {
  let body: Record<string, unknown>
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const { marked_attempt_id, attempt_id, student_id, resource_id, decision } = body

  if (!marked_attempt_id || !attempt_id || !student_id || !resource_id) {
    return NextResponse.json(
      { error: 'Missing required fields: marked_attempt_id, attempt_id, student_id, resource_id' },
      { status: 400 },
    )
  }

  if (!decision || !VALID_DECISIONS.includes(decision as AttemptDecisionValue)) {
    return NextResponse.json(
      { error: `Invalid decision. Must be one of: ${VALID_DECISIONS.join(', ')}` },
      { status: 400 },
    )
  }

  const rawScore = body.score
  const score: number | null =
    rawScore === null || rawScore === undefined
      ? null
      : typeof rawScore === 'number'
      ? rawScore
      : null

  const input: AttemptDecisionInput = {
    marked_attempt_id: String(marked_attempt_id),
    attempt_id:        String(attempt_id),
    student_id:        String(student_id),
    resource_id:       String(resource_id),
    decision:          decision as AttemptDecisionValue,
    score,
    max_score:         1,
    teacher_feedback:  String(body.teacher_feedback ?? '').trim(),
    teacher_notes:     String(body.teacher_notes ?? '').trim(),
  }

  try {
    const saved = await saveTeacherAttemptReviewDecision(input)
    return NextResponse.json({ ok: true, decision_id: saved.decision_id })
  } catch (err) {
    console.error('[attempt-review] POST error:', err)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
