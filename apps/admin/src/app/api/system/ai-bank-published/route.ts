import { NextResponse } from 'next/server'
import { getGate70dAiBankPublishedSummary } from '@/lib/aiBankPublishedPackage'
import fs from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

const ROOT = path.resolve(process.cwd(), '../..')
const PKG_DIR = path.join(ROOT, 'data/ai/published/gate70d_ai_bank_package_v1')

export async function GET() {
  const summary = getGate70dAiBankPublishedSummary()

  const staticPreviewsExist =
    fs.existsSync(path.join(PKG_DIR, 'static_preview/gate70d_student_ai_bank_published_preview_v1.html')) &&
    fs.existsSync(path.join(PKG_DIR, 'static_preview/gate70d_teacher_ai_bank_published_preview_v1.html'))

  const status = summary.packageExists && summary.validationPassed === true
    ? 'published_local_not_active'
    : summary.packageExists
    ? 'needs_review'
    : 'not_built'

  return NextResponse.json({
    gate:                           '70D',
    status,
    final_approval_exists:          summary.finalApprovalExists,
    approval_status:                summary.approvalStatus,
    local_published_package_exists: summary.packageExists,
    resource_count:                 summary.resourceCount,
    validation_passed:              summary.validationPassed,
    student_payload_exists:         summary.studentPayloadExists,
    teacher_payload_exists:         summary.teacherPayloadExists,
    static_previews_exist:          staticPreviewsExist,
    local_registry_exists:          summary.registryExists,
    active_content:                 false,
    supabase_write_performed:       false,
    ai_api_called:                  false,
    teacher_final_approval:         summary.teacherFinalApproval,
    ready_for_gate70e:              summary.readyForGate70E,
    secrets_exposed:                false,
    timestamp:                      new Date().toISOString(),
  })
}
