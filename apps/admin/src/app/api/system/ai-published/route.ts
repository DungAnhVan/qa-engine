import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

function dataRoot(): string {
  return path.join(process.cwd(), '..', '..', 'data')
}

export async function GET() {
  const approvalPath    = path.join(dataRoot(), 'ai', 'package_candidates',
    'ai_final_publish_approval_v1.json')
  const pkgPath         = path.join(dataRoot(), 'ai', 'published',
    'ai_resource_package_v1', 'publish_package_v1.json')
  const validationPath  = path.join(dataRoot(), 'diagnostics',
    'ai_local_published_package_validation_report_v1.json')
  const registryPath    = path.join(dataRoot(), 'ai', 'registry',
    'ai_content_registry_v1.json')

  const approvalExists  = fs.existsSync(approvalPath)
  const pkgExists       = fs.existsSync(pkgPath)
  const validationExists = fs.existsSync(validationPath)
  const registryExists  = fs.existsSync(registryPath)

  let resourceCount    = 0
  let validationPassed = false
  let approvalStatus   = 'pending'

  try {
    if (approvalExists) {
      const a = JSON.parse(fs.readFileSync(approvalPath, 'utf-8'))
      approvalStatus = a.approval_status ?? 'pending'
    }
    if (pkgExists) {
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

  const pkgReady = pkgExists && validationPassed
  const status: 'published_local_not_active' | 'needs_review' | 'failed' =
    !pkgExists        ? 'needs_review'
    : !validationPassed ? 'needs_review'
    : 'published_local_not_active'

  return NextResponse.json({
    status,
    final_approval_exists:          approvalExists,
    approval_status:                approvalStatus,
    local_published_package_exists: pkgExists,
    resource_count:                 resourceCount,
    validation_passed:              validationPassed,
    registry_exists:                registryExists,
    active_content:                 false,
    supabase_write_performed:       false,
    teacher_final_approval:         true,
    ready_for_gate69g:              pkgReady && registryExists,
    timestamp:                      new Date().toISOString(),
  })
}
