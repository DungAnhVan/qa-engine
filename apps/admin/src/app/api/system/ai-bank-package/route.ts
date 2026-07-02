import { NextResponse } from 'next/server'
import {
  getPackageSummary,
  readPackageCandidate,
  readPackageValidationReport,
  readPackageBuildReport,
} from '@/lib/aiBankPackageCandidate'

export const dynamic = 'force-dynamic'

export async function GET() {
  const summary    = getPackageSummary()
  const pkg        = readPackageCandidate()
  const validation = readPackageValidationReport()
  const build      = readPackageBuildReport()

  return NextResponse.json({
    gate:    '70C',
    status:  summary.buildStatus ?? 'not_built',
    summary,
    package: pkg
      ? {
          package_candidate_id:           pkg.package_candidate_id,
          version:                         pkg.version,
          status:                          pkg.status,
          resource_count:                  pkg.resource_count,
          teacher_final_publish_required:  pkg.teacher_final_publish_required,
          auto_publish_enabled:            pkg.auto_publish_enabled,
          supabase_write_performed:        pkg.supabase_write_performed,
          ai_api_called:                   pkg.ai_api_called,
          issues:                          pkg.issues ?? [],
        }
      : null,
    validation,
    build,
    safety: {
      teacher_final_publish_required: true,
      auto_publish_enabled:           false,
      supabase_write_performed:       false,
      ai_api_called:                  false,
    },
  })
}
