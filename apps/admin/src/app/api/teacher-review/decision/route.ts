import { NextRequest, NextResponse } from 'next/server'
import { saveTeacherReviewDecision, type DecisionValue } from '@/lib/teacherReview'

const VALID: DecisionValue[] = ['approved', 'revise', 'rejected']

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as Record<string, unknown>
    const { review_id, bank_item_id, resource_id, decision, teacher_notes } = body

    if (
      typeof review_id !== 'string' || !review_id ||
      typeof bank_item_id !== 'string' || !bank_item_id ||
      typeof resource_id !== 'string' || !resource_id ||
      !VALID.includes(decision as DecisionValue)
    ) {
      return NextResponse.json({ error: 'Missing or invalid fields' }, { status: 400 })
    }

    await saveTeacherReviewDecision({
      review_id,
      bank_item_id,
      resource_id,
      decision: decision as DecisionValue,
      teacher_notes: typeof teacher_notes === 'string' ? teacher_notes : '',
    })

    return NextResponse.json({ ok: true })
  } catch {
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
