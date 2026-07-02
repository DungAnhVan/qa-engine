import { NextResponse } from 'next/server'
import { getGate70eAiBankSupabaseSummary } from '@/lib/aiBankSupabasePackage'

export const dynamic = 'force-dynamic'

export async function GET() {
  const summary = getGate70eAiBankSupabaseSummary()

  const status = summary.supabaseWritePerformed
    ? (summary.readbackVerified ? 'synced_not_active' : 'needs_review')
    : summary.syncPlanExists
    ? 'not_synced'
    : 'failed'

  return NextResponse.json({
    gate:                              '70E',
    status,
    sync_plan_exists:                  summary.syncPlanExists,
    dry_run_default:                   summary.dryRunDefault,
    supabase_write_performed:          summary.supabaseWritePerformed,
    readback_verified:                 summary.readbackVerified,
    target_active:                     false,
    active_switch_performed:           false,
    existing_active_package_preserved: summary.existingActivePackagePreserved,
    ai_api_called:                     false,
    secrets_exposed:                   false,
    ready_for_gate70f:                 summary.readyForGate70F,
    timestamp:                         new Date().toISOString(),
  })
}
