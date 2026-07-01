import { NextResponse } from 'next/server'
import { getAiBankSummary } from '@/lib/aiQuestionBank'

export const dynamic = 'force-dynamic'

export async function GET() {
  const summary = getAiBankSummary()
  return NextResponse.json({
    gate:                    '70A',
    name:                    'Live AI Question Generation to Bank v1',
    bank_exists:             summary.bank_exists,
    total_items:             summary.total_items,
    pending_review:          summary.pending_review,
    queue_count:             summary.queue_count,
    request_count:           summary.request_count,
    batches:                 summary.batches,
    teacher_review_required: summary.teacher_review_required,
    auto_publish_enabled:    summary.auto_publish_enabled,
    supabase_write_performed: summary.supabase_write_performed,
    validation_valid:        summary.validation_valid,
    updated_at:              summary.updated_at,
    safety: {
      no_raw_source_text:    true,
      no_cambridge_pdf_text: true,
      no_mark_scheme_text:   true,
      metadata_only_prompts: true,
      teacher_approval_required_before_publish: true,
    },
  })
}
