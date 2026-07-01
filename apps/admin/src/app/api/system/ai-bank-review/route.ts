import { NextResponse } from 'next/server'
import { getAiBankReviewSummary } from '@/lib/aiBankReview'

export const dynamic = 'force-dynamic'

export async function GET() {
  const s = getAiBankReviewSummary()

  const status =
    !s.bank_exists || !s.queue_exists     ? 'needs_review'
    : s.approved_count === 0              ? 'pending_review'
    : s.validation_passed === true        ? 'ready_for_package_candidate'
    : s.validation_passed === false       ? 'failed'
    : 'pending_review'

  return NextResponse.json({
    gate:                    '70B',
    name:                    'AI Bank Review and Approval v1',
    status,
    question_bank_exists:    s.bank_exists,
    review_queue_exists:     s.queue_exists,
    decisions_file_exists:   s.decisions_file_exists,
    approved_count:          s.approved_count,
    needs_revision_count:    s.revision_count,
    rejected_count:          s.rejected_count,
    pending_count:           s.pending_count,
    decision_count:          s.decision_count,
    validation_passed:       s.validation_passed,
    teacher_review_required: true,
    auto_publish_enabled:    false,
    supabase_write_performed: false,
    ai_api_called:           false,
    secrets_exposed:         false,
    timestamp:               new Date().toISOString(),
  })
}
