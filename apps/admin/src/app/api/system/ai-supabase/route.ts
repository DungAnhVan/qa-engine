import { NextResponse } from 'next/server'
import { getAiSupabasePackageSummary, readAiSyncReport } from '@/lib/aiSupabasePackage'

export const dynamic = 'force-dynamic'

export async function GET() {
  const summary   = getAiSupabasePackageSummary()
  const syncReport = readAiSyncReport()

  return NextResponse.json({
    status:                             summary.status,
    sync_plan_exists:                   summary.sync_plan_exists,
    supabase_write_performed:           summary.supabase_write_performed,
    readback_verified:                  summary.readback_verified,
    active_switch_performed:            summary.active_switch_performed,
    existing_active_package_preserved:  summary.existing_active_package_preserved,
    secrets_exposed:                    summary.secrets_exposed,
    dry_run_default:                    summary.dry_run_default,
    active_switch_default:              summary.active_switch_default,
    resource_count:                     summary.resource_count,
    resources_upserted:                 syncReport?.resources_upserted ?? 0,
    packages_upserted:                  syncReport?.packages_upserted ?? 0,
    items_upserted:                     syncReport?.items_upserted ?? 0,
    timestamp:                          new Date().toISOString(),
  })
}
