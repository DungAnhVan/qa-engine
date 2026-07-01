import { requireAppRole } from '@/lib/roleAccess'
import {
  getAiSupabasePackageSummary,
  readAiSyncPlan,
  readAiSyncReport,
  readAiVerifyReport,
  readAiActiveSwitchReport,
} from '@/lib/aiSupabasePackage'

export const dynamic = 'force-dynamic'

function Badge({ label, ok, neutral, warn }: { label: string; ok?: boolean; neutral?: boolean; warn?: boolean }) {
  const bg = warn ? '#fef3c7' : neutral ? '#dbeafe' : ok ? '#d1fae5' : '#fee2e2'
  const fg = warn ? '#92400e' : neutral ? '#1e40af' : ok ? '#065f46' : '#991b1b'
  return (
    <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 4,
      fontSize: 12, fontWeight: 600, backgroundColor: bg, color: fg, marginLeft: 8 }}>
      {label}
    </span>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <td style={{ padding: '5px 16px 5px 0', color: '#6b7280', whiteSpace: 'nowrap', verticalAlign: 'top' }}>
        {label}
      </td>
      <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}>{value}</td>
    </tr>
  )
}

export default async function AiSupabaseDiagnosticPage() {
  const { allowed, currentRole } = await requireAppRole(['admin'])
  if (!allowed) return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Access denied</h1>
      <p style={{ fontSize: 14, color: '#6b7280', marginBottom: 12 }}>
        Required: admin. Your role: <code>{currentRole ?? 'none'}</code>
      </p>
      <a href="/login" style={{ color: '#3b82f6' }}>Sign in →</a>
    </main>
  )

  const summary     = getAiSupabasePackageSummary()
  const plan        = readAiSyncPlan()
  const syncReport  = readAiSyncReport()
  const verifyReport = readAiVerifyReport()
  const activeReport = readAiActiveSwitchReport()

  return (
    <main style={{ padding: '2rem', maxWidth: 840, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        AI Supabase Sync Diagnostic
        <Badge label="Gate 69G" neutral />
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 13 }}>
        AI package Supabase sync status. No secrets displayed.
      </p>

      {/* Active switch warning */}
      {!summary.active_switch_performed && (
        <div style={{ marginBottom: 20, padding: '12px 16px', background: '#fef3c7',
          borderLeft: '4px solid #f59e0b', borderRadius: 6, fontSize: 13, color: '#92400e' }}>
          <strong>Active switch not performed.</strong> AI package is NOT active production content.
          Use <code>activate_ai_package_supabase_v1.py --execute --activate --confirm ACTIVATE_AI_PACKAGE</code> when ready.
        </div>
      )}

      {/* Status summary */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="Overall status"
              value={<Badge label={summary.status.toUpperCase()}
                ok={summary.status === 'active' || summary.status === 'synced_not_active'}
                neutral={summary.status === 'not_synced'}
                warn={summary.status === 'needs_review'} />} />
            <Row label="Sync plan exists"
              value={<Badge label={summary.sync_plan_exists ? 'YES' : 'NO'}
                ok={summary.sync_plan_exists} />} />
            <Row label="dry_run_default"
              value={<Badge label={String(summary.dry_run_default)}
                ok={summary.dry_run_default} />} />
            <Row label="active_switch_default"
              value={<Badge label={String(summary.active_switch_default)}
                ok={!summary.active_switch_default} />} />
            <Row label="supabase_write_performed"
              value={<Badge label={String(summary.supabase_write_performed)}
                ok={summary.supabase_write_performed} neutral={!summary.supabase_write_performed} />} />
            <Row label="readback_verified"
              value={<Badge label={String(summary.readback_verified)}
                ok={summary.readback_verified} neutral={!summary.readback_verified} />} />
            <Row label="active_switch_performed"
              value={<Badge label={String(summary.active_switch_performed)}
                warn={summary.active_switch_performed} neutral={!summary.active_switch_performed} />} />
            <Row label="existing_active_preserved"
              value={<Badge label={String(summary.existing_active_package_preserved)}
                ok={summary.existing_active_package_preserved} />} />
            <Row label="secrets_exposed"
              value={<Badge label={String(summary.secrets_exposed)}
                ok={!summary.secrets_exposed} />} />
          </tbody>
        </table>
      </section>

      {/* Sync plan */}
      {plan && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
            textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sync Plan</h2>
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row label="package_id"     value={<code>{plan.package_id}</code>} />
              <Row label="resource_count" value={<code>{plan.resource_count}</code>} />
              <Row label="operations"     value={<code>{plan.operation_count}</code>} />
            </tbody>
          </table>
        </section>
      )}

      {/* Sync execute report */}
      {syncReport && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
            textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sync Execute Report</h2>
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row label="dry_run"             value={<code>{String(syncReport.dry_run)}</code>} />
              <Row label="resources_upserted"  value={<code>{syncReport.resources_upserted}</code>} />
              <Row label="packages_upserted"   value={<code>{syncReport.packages_upserted}</code>} />
              <Row label="items_upserted"      value={<code>{syncReport.items_upserted}</code>} />
              {syncReport.issues.length > 0 && (
                <Row label="issues" value={
                  <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, color: '#991b1b' }}>
                    {syncReport.issues.map((iss, i) => <li key={i}>{iss}</li>)}
                  </ul>
                } />
              )}
            </tbody>
          </table>
        </section>
      )}

      {/* Verify report */}
      {verifyReport && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
            textTransform: 'uppercase', letterSpacing: '0.05em' }}>Readback Verify Report</h2>
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row label="status"              value={<Badge label={verifyReport.status.toUpperCase()}
                ok={verifyReport.status === 'passed'} warn={verifyReport.status === 'needs_review'} />} />
              <Row label="sync_executed"       value={<code>{String(verifyReport.sync_executed)}</code>} />
              <Row label="package_exists"      value={<code>{String(verifyReport.package_exists)}</code>} />
              <Row label="resources_verified"  value={<code>{verifyReport.resources_verified}</code>} />
              <Row label="resource_count_match" value={<code>{String(verifyReport.resource_count_match)}</code>} />
              <Row label="active_false"        value={<code>{String(verifyReport.active_false)}</code>} />
              <Row label="no_raw_source_text"  value={<code>{String(verifyReport.no_raw_source_text)}</code>} />
            </tbody>
          </table>
        </section>
      )}

      {/* Active switch */}
      {activeReport && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
            textTransform: 'uppercase', letterSpacing: '0.05em' }}>Active Switch Report</h2>
          <table style={{ borderCollapse: 'collapse' }}>
            <tbody>
              <Row label="dry_run"                  value={<code>{String(activeReport.dry_run)}</code>} />
              <Row label="active_switch_performed"  value={<code>{String(activeReport.active_switch_performed)}</code>} />
              <Row label="prev active package"      value={<code>{activeReport.previous_active_package_id ?? '—'}</code>} />
              <Row label="new active package"       value={<code>{activeReport.new_active_package_id}</code>} />
            </tbody>
          </table>
        </section>
      )}

      {/* Scripts */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>Gate 69G Scripts</h2>
        <pre style={{ background: '#f3f4f6', padding: '12px 16px', borderRadius: 4,
          fontSize: 12, overflowX: 'auto', lineHeight: 1.7 }}>
          {[
            '# 1. Build sync plan',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_supabase_sync_plan_v1.py',
            '',
            '# 2. Dry-run sync (default, safe)',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\sync_ai_package_to_supabase_v1.py',
            '',
            '# 3. Execute sync (writes to Supabase)',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\sync_ai_package_to_supabase_v1.py \\',
            '    --execute --confirm SYNC_AI_PACKAGE',
            '',
            '# 4. Verify readback',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\verify_ai_package_from_supabase_v1.py',
            '',
            '# 5. Export from Supabase',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_package_supabase_export_v1.py',
            '',
            '# 6. Activate (explicit opt-in only)',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\activate_ai_package_supabase_v1.py \\',
            '    --execute --activate --confirm ACTIVATE_AI_PACKAGE',
          ].join('\n')}
        </pre>
      </section>

      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/api/system/ai-supabase" style={{ color: '#3b82f6', marginRight: 16 }}>AI Supabase API</a>
        <a href="/system/ai-published"    style={{ color: '#3b82f6', marginRight: 16 }}>AI Published Diag</a>
        <a href="/system/health"          style={{ color: '#3b82f6' }}>Health</a>
      </p>
    </main>
  )
}
