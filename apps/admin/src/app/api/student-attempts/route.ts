import { NextRequest, NextResponse } from 'next/server'
import { saveStudentAttempt, type AttemptInput } from '@/lib/studentAttempts'

export async function POST(req: NextRequest) {
  let body: Record<string, unknown>
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const { package_id, resource_id, resource_type } = body

  if (!package_id || !resource_id || !resource_type) {
    return NextResponse.json(
      { error: 'Missing required fields: package_id, resource_id, resource_type' },
      { status: 400 },
    )
  }

  const student_answer = (body.student_answer as string | null) ?? ''
  const selected_option = (body.selected_option as string | null) ?? null

  if (!student_answer.trim() && !selected_option) {
    return NextResponse.json(
      { error: 'Either student_answer or selected_option is required' },
      { status: 400 },
    )
  }

  const validConfidence = ['low', 'medium', 'high'] as const
  type Confidence = (typeof validConfidence)[number]
  const rawConf = body.self_confidence as string | null
  const self_confidence: Confidence | null =
    rawConf && (validConfidence as readonly string[]).includes(rawConf)
      ? (rawConf as Confidence)
      : null

  const attempt_type =
    body.attempt_type === 'resubmission' ? 'resubmission' : 'first_attempt'
  const parent_attempt_id =
    body.parent_attempt_id ? String(body.parent_attempt_id) : null

  const input: AttemptInput = {
    package_id: String(package_id),
    resource_id: String(resource_id),
    resource_type: String(resource_type),
    topic: String(body.topic ?? ''),
    skill_name: String(body.skill_name ?? ''),
    skill_type: String(body.skill_type ?? ''),
    difficulty: body.difficulty ? String(body.difficulty) : null,
    student_answer: student_answer.trim(),
    selected_option,
    self_confidence,
    attempt_type,
    parent_attempt_id,
    resubmission_of: parent_attempt_id,
  }

  try {
    const attempt = await saveStudentAttempt(input)
    return NextResponse.json({ ok: true, attempt_id: attempt.attempt_id })
  } catch (err) {
    console.error('[student-attempts] POST error:', err)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
