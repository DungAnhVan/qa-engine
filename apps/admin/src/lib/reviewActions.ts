'use server'

import { revalidatePath } from 'next/cache'
import { saveTeacherReviewDecision, type DecisionValue } from './teacherReview'

const VALID: DecisionValue[] = ['approved', 'revise', 'rejected']

export async function submitDecisionAction(formData: FormData) {
  const review_id    = (formData.get('review_id')    as string | null)?.trim() ?? ''
  const bank_item_id = (formData.get('bank_item_id') as string | null)?.trim() ?? ''
  const resource_id  = (formData.get('resource_id')  as string | null)?.trim() ?? ''
  const decision     = formData.get('decision') as DecisionValue
  const teacher_notes = (formData.get('teacher_notes') as string | null)?.trim() ?? ''

  if (!review_id || !bank_item_id || !resource_id) return
  if (!VALID.includes(decision)) return

  await saveTeacherReviewDecision({ review_id, bank_item_id, resource_id, decision, teacher_notes })
  revalidatePath('/content/review')
}
