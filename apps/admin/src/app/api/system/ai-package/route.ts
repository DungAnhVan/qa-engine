import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

function dataRoot(): string {
  return path.join(process.cwd(), '..', '..', 'data')
}

export async function GET() {
  const pkgPath        = path.join(dataRoot(), 'ai', 'package_candidates',
    'ai_resource_package_candidate_v1.json')
  const validationPath = path.join(dataRoot(), 'diagnostics',
    'ai_package_candidate_validation_report_v1.json')
  const studentPath    = path.join(dataRoot(), 'ai', 'package_candidates',
    'student_ai_package_payload_v1.json')
  const teacherPath    = path.join(dataRoot(), 'ai', 'package_candidates',
    'teacher_ai_package_payload_v1.json')

  const packageExists    = fs.existsSync(pkgPath)
  const validationExists = fs.existsSync(validationPath)
  const studentExists    = fs.existsSync(studentPath)
  const teacherExists    = fs.existsSync(teacherPath)

  let resourceCount   = 0
  let validationPassed = false

  try {
    if (packageExists) {
      const p = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'))
      resourceCount = p.resource_count ?? (p.resources?.length ?? 0)
    }
    if (validationExists) {
      const v = JSON.parse(fs.readFileSync(validationPath, 'utf-8'))
      validationPassed = v.valid === true
    }
  } catch {
    // Handled gracefully
  }

  const status: 'draft_package_candidate' | 'needs_review' | 'failed' =
    !packageExists       ? 'needs_review'
    : !validationPassed  ? 'needs_review'
    : 'draft_package_candidate'

  return NextResponse.json({
    status,
    package_candidate_exists:      packageExists,
    resource_count:                resourceCount,
    validation_passed:             validationPassed,
    student_payload_exists:        studentExists,
    teacher_payload_exists:        teacherExists,
    auto_publish_enabled:          false,
    supabase_write_performed:      false,
    teacher_final_publish_required: true,
    timestamp:                     new Date().toISOString(),
  })
}
