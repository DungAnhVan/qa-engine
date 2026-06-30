/**
 * POST /api/supabase/teacher-attempt-review
 *
 * Gate 58 — teacher submits a review decision for a student attempt.
 * Only active in live_supabase mode. No OpenAI. No Cambridge source text.
 *
 * Body:
 *   { attempt_id, decision, score?, feedback, notes? }
 *
 * Returns:
 *   { status: "saved", storage: "supabase", review_id, marked_attempt_id, decision }
 * or
 *   { success: false, error: string }
 */
import { NextRequest, NextResponse } from 'next/server'

import { getContentSourceMode } from '@/lib/contentSource'
import { submitLiveSupabaseTeacherReview, type TeacherDecision } from '@/lib/liveSupabaseTeacherReview'

export const dynamic = 'force-dynamic'

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const VALID_DECISIONS = new Set<string>([
  'correct',
  'incorrect',
  'partially_correct',
  'needs_resubmission',
])

export async function POST(req: NextRequest) {
  const mode = getContentSourceMode()

  if (mode !== 'live_supabase') {
    return NextResponse.json(
      {
        success: false,
        error:   `Teacher review is only available in live_supabase mode. Current mode: ${mode}`,
      },
      { status: 400 },
    )
  }

  let body: Record<string, unknown>
  try {
    body = (await req.json()) as Record<string, unknown>
  } catch {
    return NextResponse.json({ success: false, error: 'Invalid JSON body.' }, { status: 400 })
  }

  const attempt_id = typeof body.attempt_id === 'string' ? body.attempt_id.trim() : ''
  if (!attempt_id) {
    return NextResponse.json({ success: false, error: 'attempt_id is required.' }, { status: 400 })
  }
  if (!UUID_REGEX.test(attempt_id)) {
    return NextResponse.json(
      { success: false, error: `attempt_id must be a valid UUID. Got: ${attempt_id}` },
      { status: 400 },
    )
  }

  const decision = typeof body.decision === 'string' ? body.decision.trim() : ''
  if (!decision) {
    return NextResponse.json({ success: false, error: 'decision is required.' }, { status: 400 })
  }
  if (!VALID_DECISIONS.has(decision)) {
    return NextResponse.json(
      {
        success: false,
        error:   `decision must be one of: ${[...VALID_DECISIONS].join(', ')}. Got: ${decision}`,
      },
      { status: 400 },
    )
  }

  const feedback = typeof body.feedback === 'string' ? body.feedback.trim() : ''
  if (!feedback) {
    return NextResponse.json({ success: false, error: 'feedback is required.' }, { status: 400 })
  }

  const score = body.score != null
    ? typeof body.score === 'number'
      ? body.score
      : typeof body.score === 'string' && body.score !== ''
        ? parseFloat(body.score as string)
        : null
    : null

  const notes = typeof body.notes === 'string' ? body.notes.trim() || null : null

  const result = await submitLiveSupabaseTeacherReview({
    attempt_id,
    decision: decision as TeacherDecision,
    score,
    feedback,
    notes: notes ?? undefined,
  })

  if (!result.success) {
    return NextResponse.json(result, { status: 422 })
  }

  return NextResponse.json({
    status:             'saved',
    storage:            'supabase',
    review_id:          result.review_id,
    marked_attempt_id:  result.marked_attempt_id,
    decision:           result.decision,
  })
}
