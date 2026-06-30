/**
 * POST /api/mark-attempt
 *
 * Gate 57 — marks a single attempt using rule-based logic.
 * Only active in live_supabase mode. No OpenAI. No Cambridge source text.
 *
 * Body: { attempt_id: string }
 *
 * Returns:
 *   { success, attempt_id, result, score, max_score, marking_method,
 *     marking_status, feedback, resource_type, marked_attempt_id }
 * or
 *   { success: false, error: string }
 */
import { NextRequest, NextResponse } from 'next/server'

import { getContentSourceMode } from '@/lib/contentSource'
import { markLiveSupabaseAttempt } from '@/lib/liveSupabaseMarking'

export const dynamic = 'force-dynamic'

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export async function POST(req: NextRequest) {
  const mode = getContentSourceMode()

  if (mode !== 'live_supabase') {
    return NextResponse.json(
      {
        success: false,
        error:   `Marking is only available in live_supabase mode. Current mode: ${mode}`,
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

  const result = await markLiveSupabaseAttempt(attempt_id)

  if (!result.success) {
    return NextResponse.json(result, { status: 422 })
  }

  return NextResponse.json(result)
}
