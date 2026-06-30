/**
 * /system/content-source — Content source diagnostic page.
 *
 * Server Component — no secrets reach the browser.
 * SUPABASE_SERVICE_ROLE_KEY presence is reported as true/false only.
 */
import { getContentSourceMode, type ContentSourceMode } from '@/lib/contentSource'
import { getExportFileStatus } from '@/lib/supabaseExportContent'
import { getActiveContentIndex } from '@/lib/activeContent'
import { getLiveSupabaseEnvPresence } from '@/lib/liveSupabaseContent'
import { existsSync } from 'fs'
import path from 'path'

// ── Small UI primitives ──────────────────────────────────────────────────────

function Badge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        backgroundColor: ok ? '#d1fae5' : '#fee2e2',
        color: ok ? '#065f46' : '#991b1b',
        marginLeft: 8,
      }}
    >
      {label}
    </span>
  )
}

function InfoBadge({ label }: { label: string }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        backgroundColor: '#dbeafe',
        color: '#1e40af',
        marginLeft: 8,
      }}
    >
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

function Section({ title, children, badge }: { title: string; children: React.ReactNode; badge?: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 4 }}>
        {title}{badge}
      </h2>
      {children}
    </section>
  )
}

function Alert({ variant, children }: { variant: 'warn' | 'error' | 'info'; children: React.ReactNode }) {
  const colors = {
    warn:  { bg: '#fef3c7', color: '#92400e' },
    error: { bg: '#fee2e2', color: '#991b1b' },
    info:  { bg: '#dbeafe', color: '#1e40af' },
  }
  const c = colors[variant]
  return (
    <p style={{ marginTop: 10, padding: '8px 12px', background: c.bg, borderRadius: 4, fontSize: 13, color: c.color }}>
      {children}
    </p>
  )
}

function modeLabel(mode: ContentSourceMode) {
  if (mode === 'live_supabase')   return 'Live Supabase (server-side, read-only)'
  if (mode === 'supabase_export') return 'Supabase Export (local JSON snapshot)'
  return 'Local JSON'
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default async function ContentSourcePage() {
  const mode       = getContentSourceMode()
  const exportSt   = getExportFileStatus()
  const liveEnv    = getLiveSupabaseEnvPresence()
  const activeIdx  = await getActiveContentIndex()

  // Local index file availability
  const repoRoot   = exportSt.export_dir.replace(/[\\/]data[\\/]supabase_exports$/, '')
  const localIndex = path.join(repoRoot, 'data', 'registry', 'active_content_index_v1.json')
  const localOk    = existsSync(localIndex)

  const allExportsOk = exportSt.active_package && exportSt.student_payload && exportSt.teacher_payload
  const liveEnvOk    = liveEnv.supabase_url && liveEnv.service_role_key

  return (
    <main style={{ padding: '2rem', maxWidth: 760, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Content Source Diagnostic</h1>
      <p style={{ color: '#6b7280', marginBottom: 28, fontSize: 14 }}>
        Shows which data source the admin app is reading from.
        No secret values are displayed on this page.
      </p>

      {/* ── Active mode ── */}
      <Section
        title="Active Mode"
        badge={<InfoBadge label={mode} />}
      >
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="QA_CONTENT_SOURCE" value={<code>{mode}</code>} />
            <Row label="Description"       value={modeLabel(mode)} />
          </tbody>
        </table>
        {mode === 'live_supabase' && (
          <Alert variant="info">
            Server-side live Supabase read. No browser Supabase client is used.
            SUPABASE_SERVICE_ROLE_KEY never leaves the server.
          </Alert>
        )}
      </Section>

      {/* ── Mode availability matrix ── */}
      <Section title="Mode Availability">
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <tbody>
            <Row
              label="local"
              value={
                <>
                  <Badge label={localOk ? 'Available' : 'Index missing'} ok={localOk} />
                  {mode === 'local' && <InfoBadge label="active" />}
                </>
              }
            />
            <Row
              label="supabase_export"
              value={
                <>
                  <Badge label={allExportsOk ? 'Available' : 'Files missing'} ok={allExportsOk} />
                  {mode === 'supabase_export' && <InfoBadge label="active" />}
                </>
              }
            />
            <Row
              label="live_supabase"
              value={
                <>
                  <Badge label={liveEnvOk ? 'Env configured' : 'Env missing'} ok={liveEnvOk} />
                  {mode === 'live_supabase' && <InfoBadge label="active" />}
                </>
              }
            />
          </tbody>
        </table>
      </Section>

      {/* ── live_supabase env ── */}
      <Section
        title="Live Supabase Environment"
        badge={liveEnvOk ? <Badge label="Configured" ok /> : <Badge label="Not configured" ok={false} />}
      >
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="SUPABASE_URL"
              value={<Badge label={liveEnv.supabase_url ? 'Present' : 'Missing'} ok={liveEnv.supabase_url} />}
            />
            <Row
              label="SUPABASE_SERVICE_ROLE_KEY"
              value={<Badge label={liveEnv.service_role_key ? 'Present' : 'Missing'} ok={liveEnv.service_role_key} />}
            />
          </tbody>
        </table>
        {!liveEnvOk && mode === 'live_supabase' && (
          <Alert variant="error">
            live_supabase mode is active but env vars are missing.
            Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to apps/admin/.env.local.
          </Alert>
        )}
        {!liveEnvOk && mode !== 'live_supabase' && (
          <Alert variant="warn">
            Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local to enable live_supabase mode.
          </Alert>
        )}
        {liveEnvOk && (
          <Alert variant="info">
            Live Supabase env configured. Visit{' '}
            <a href="/system/supabase-live" style={{ color: 'inherit' }}>/system/supabase-live</a>
            {' '}to test the live connection.
          </Alert>
        )}
      </Section>

      {/* ── Supabase export files ── */}
      <Section
        title="Supabase Export Files"
        badge={allExportsOk ? <Badge label="All present" ok /> : <Badge label="Some missing" ok={false} />}
      >
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <tbody>
            <Row
              label="active_package_from_supabase_v1.json"
              value={<Badge label={exportSt.active_package ? 'Present' : 'Missing'} ok={exportSt.active_package} />}
            />
            <Row
              label="student_resource_payload_from_supabase_v1.json"
              value={<Badge label={exportSt.student_payload ? 'Present' : 'Missing'} ok={exportSt.student_payload} />}
            />
            <Row
              label="teacher_resource_payload_from_supabase_v1.json"
              value={<Badge label={exportSt.teacher_payload ? 'Present' : 'Missing'} ok={exportSt.teacher_payload} />}
            />
          </tbody>
        </table>
        {!allExportsOk && (
          <Alert variant="warn">
            Run{' '}
            <code>.venv-ingest\Scripts\python.exe tools\supabase\read_active_package_from_supabase_v1.py</code>
            {' '}to generate the export files.
          </Alert>
        )}
      </Section>

      {/* ── Active package from current source ── */}
      <Section
        title={`Active Package (${mode})`}
        badge={activeIdx ? <Badge label="Loaded" ok /> : <Badge label="Not loaded" ok={false} />}
      >
        {activeIdx ? (
          activeIdx.active_packages.map((pkg) => (
            <table key={pkg.content_key} style={{ borderCollapse: 'collapse' }}>
              <tbody>
                <Row label="content_key"           value={pkg.content_key} />
                <Row label="package_id"            value={pkg.active_package_id} />
                <Row label="version"               value={pkg.active_package_version} />
                <Row label="status"                value={<Badge label={pkg.active_package_status} ok={pkg.active_package_status === 'active'} />} />
                <Row label="resource_count"        value={String(pkg.resource_count)} />
                <Row label="student_payload_count" value={String(pkg.student_payload_count)} />
                <Row label="teacher_payload_count" value={String(pkg.teacher_payload_count)} />
                <Row label="teacher_only_count"    value={String(pkg.teacher_only_resource_count)} />
              </tbody>
            </table>
          ))
        ) : (
          <Alert variant={mode === 'live_supabase' && !liveEnvOk ? 'error' : 'warn'}>
            {mode === 'live_supabase' && !liveEnvOk
              ? 'Cannot load: live_supabase env vars not configured.'
              : `No active package loaded from source: ${mode}.`}
          </Alert>
        )}
      </Section>

      {/* ── How to switch ── */}
      <section
        style={{ padding: '12px 16px', background: '#f3f4f6', borderRadius: 6, fontSize: 13 }}
      >
        <strong>How to switch modes</strong>
        <br />
        In <code>apps/admin/.env.local</code>:
        <pre style={{ margin: '8px 0 0', background: '#e5e7eb', padding: 8, borderRadius: 4, whiteSpace: 'pre-wrap' }}>
          {[
            '# Local JSON (default — no Supabase required):',
            'QA_CONTENT_SOURCE=local',
            '',
            '# Supabase snapshot (run Gate 53F export script first):',
            'QA_CONTENT_SOURCE=supabase_export',
            '',
            '# Live Supabase read (requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY):',
            'QA_CONTENT_SOURCE=live_supabase',
          ].join('\n')}
        </pre>
        Restart the dev server after changing this value.
      </section>
    </main>
  )
}
