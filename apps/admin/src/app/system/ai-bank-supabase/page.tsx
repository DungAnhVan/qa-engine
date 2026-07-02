import { requireRole } from '@/lib/serverSupabaseAuth'
import {
  getGate70eAiBankSupabaseSummary,
  readGate70eAiBankSupabaseSyncPlan,
  readGate70eAiBankSupabaseSyncReport,
  readGate70eAiBankSupabaseVerifyReport,
} from '@/lib/aiBankSupabasePackage'

export const metadata = { title: 'AI Bank Supabase Diagnostic' }

export default async function AiBankSupabaseDiagPage() {
  await requireRole(['admin'])

  const summary    = getGate70eAiBankSupabaseSummary()
  const plan       = readGate70eAiBankSupabaseSyncPlan() as Record<string, unknown> | null
  const syncReport = readGate70eAiBankSupabaseSyncReport() as Record<string, unknown> | null
  const verify     = readGate70eAiBankSupabaseVerifyReport() as Record<string, unknown> | null

  function Row({ label, value, ok }: { label: string; value: string | boolean | number | null; ok?: boolean }) {
    const color = ok === true ? '#5aff8a' : ok === false ? '#ff5a5a' : '#ccc'
    return (
      <tr>
        <td style={{ padding: '6px 12px', fontFamily: 'monospace', fontSize: 12, color: '#888', width: 340 }}>{label}</td>
        <td style={{ padding: '6px 12px', fontFamily: 'monospace', fontSize: 12, color }}>{String(value ?? '—')}</td>
      </tr>
    )
  }

  const syncStatus = summary.supabaseWritePerformed
    ? (summary.readbackVerified ? 'synced_not_active' : 'synced_unverified')
    : 'not_synced'

  return (
    <main style={{ maxWidth: 860, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 22, marginBottom: 4 }}>AI Bank Supabase — Diagnostic</h1>
      <p style={{ color: '#888', fontSize: 13, marginBottom: 24 }}>Gate 70E — Supabase sync for AI bank package, not active</p>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Summary</h2>
        <table style={{ borderCollapse: 'collapse', width: '100%', border: '1px solid #222' }}>
          <tbody>
            <Row label="syncPlanExists"                  value={summary.syncPlanExists}                  ok={summary.syncPlanExists} />
            <Row label="dryRunDefault"                   value={summary.dryRunDefault}                   ok={summary.dryRunDefault} />
            <Row label="activeSwitchAllowed"             value={summary.activeSwitchAllowed}             ok={!summary.activeSwitchAllowed} />
            <Row label="supabaseWritePerformed"          value={summary.supabaseWritePerformed} />
            <Row label="resourcesUpserted"               value={summary.resourcesUpserted} />
            <Row label="packagesUpserted"                value={summary.packagesUpserted} />
            <Row label="itemsUpserted"                   value={summary.itemsUpserted} />
            <Row label="readbackVerified"                value={summary.readbackVerified}                ok={summary.readbackVerified || !summary.supabaseWritePerformed} />
            <Row label="targetActive"                    value={summary.targetActive}                    ok={!summary.targetActive} />
            <Row label="activeSwitchPerformed"           value={summary.activeSwitchPerformed}           ok={!summary.activeSwitchPerformed} />
            <Row label="existingActivePackagePreserved"  value={summary.existingActivePackagePreserved}  ok={summary.existingActivePackagePreserved} />
            <Row label="aiApiCalled"                     value={summary.aiApiCalled}                     ok={!summary.aiApiCalled} />
            <Row label="secretsExposed"                  value={summary.secretsExposed}                  ok={!summary.secretsExposed} />
            <Row label="readyForGate70F"                 value={summary.readyForGate70F}                 ok={summary.readyForGate70F} />
            <Row label="syncStatus"                      value={syncStatus} />
          </tbody>
        </table>
      </section>

      {plan && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, marginBottom: 10 }}>Sync Plan</h2>
          <table style={{ borderCollapse: 'collapse', width: '100%', border: '1px solid #222' }}>
            <tbody>
              <Row label="sync_plan_id"         value={String(plan.sync_plan_id ?? '—')} />
              <Row label="target_package_key"   value={String(plan.target_package_key ?? '—')} />
              <Row label="resource_count"        value={Number(plan.resource_count ?? 0)} />
              <Row label="operation_count"       value={Number(plan.operation_count ?? 0)} />
              <Row label="dry_run_default"       value={Boolean(plan.dry_run_default)}   ok={Boolean(plan.dry_run_default)} />
              <Row label="active_switch_allowed" value={Boolean(plan.active_switch_allowed)} ok={!plan.active_switch_allowed} />
              <Row label="target_active"         value={Boolean(plan.target_active)}     ok={!plan.target_active} />
            </tbody>
          </table>
          <div style={{ marginTop: 10 }}>
            <div style={{ color: '#555', fontSize: 11, marginBottom: 6 }}>Execute command:</div>
            <pre style={{
              backgroundColor: '#0d0d0d', border: '1px solid #222', borderRadius: 4,
              padding: '10px 14px', fontSize: 11, color: '#aaa', overflowX: 'auto',
            }}>
              {`.venv-ingest\\Scripts\\python.exe tools\\ai\\sync_gate70e_ai_bank_package_to_supabase_v1.py --execute --confirm SYNC_GATE70E_AI_BANK_PACKAGE`}
            </pre>
          </div>
        </section>
      )}

      {syncReport && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, marginBottom: 10 }}>Sync Report</h2>
          <pre style={{
            backgroundColor: '#0d0d0d', border: '1px solid #222', borderRadius: 4,
            padding: '12px 16px', fontSize: 11, color: '#aaa',
            overflowX: 'auto', maxHeight: 260, overflowY: 'auto',
          }}>
            {JSON.stringify(syncReport, null, 2)}
          </pre>
        </section>
      )}

      {verify && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, marginBottom: 10 }}>Read-back Verify Report</h2>
          <pre style={{
            backgroundColor: '#0d0d0d', border: '1px solid #222', borderRadius: 4,
            padding: '12px 16px', fontSize: 11, color: '#aaa',
            overflowX: 'auto', maxHeight: 260, overflowY: 'auto',
          }}>
            {JSON.stringify(verify, null, 2)}
          </pre>
        </section>
      )}

      <div style={{
        marginTop: 24, padding: '10px 14px', border: '1px solid #1a1a1a',
        borderRadius: 6, backgroundColor: '#0d0d0d', fontSize: 12, color: '#555',
      }}>
        <a href="/ai-bank-published" style={{ color: '#5ab8ff' }}>← AI Bank Published</a>
        {' · '}API: <a href="/api/system/ai-bank-supabase" style={{ color: '#5ab8ff' }}>/api/system/ai-bank-supabase</a>
        {' · '}Gate 70E · active=false · No active switch · No schema change
      </div>
    </main>
  )
}
