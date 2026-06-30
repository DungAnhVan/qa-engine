/**
 * /system/content-source — Content source diagnostic page.
 *
 * Shows the current QA_CONTENT_SOURCE mode, which export files are present,
 * and basic package metadata from whichever source is active.
 *
 * Server Component — no secrets reach the browser.
 */
import { getContentSourceMode } from '@/lib/contentSource'
import { getExportFileStatus, getSupabaseExportPackageData } from '@/lib/supabaseExportContent'
import { getActiveContentIndex } from '@/lib/activeContent'
import { existsSync } from 'fs'
import path from 'path'

function Badge({ label, ok }: { label: string; ok: boolean }) {
  const style: React.CSSProperties = {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 4,
    fontSize: 12,
    fontWeight: 600,
    backgroundColor: ok ? '#d1fae5' : '#fee2e2',
    color: ok ? '#065f46' : '#991b1b',
    marginLeft: 8,
  }
  return <span style={style}>{label}</span>
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <td style={{ padding: '6px 12px 6px 0', color: '#6b7280', whiteSpace: 'nowrap' }}>
        {label}
      </td>
      <td style={{ padding: '6px 0', fontFamily: 'monospace', fontSize: 13 }}>{value}</td>
    </tr>
  )
}

export default async function ContentSourcePage() {
  const mode = getContentSourceMode()
  const exportStatus = getExportFileStatus()
  const exportPkg = await getSupabaseExportPackageData()
  const activeIndex = await getActiveContentIndex()

  const allExportsPresent =
    exportStatus.active_package && exportStatus.student_payload && exportStatus.teacher_payload

  const localIndexPath = path.join(
    exportStatus.export_dir.replace(/[\\/]data[\\/]supabase_exports$/, ''),
    'data',
    'registry',
    'active_content_index_v1.json',
  )
  const localIndexPresent = existsSync(localIndexPath)

  return (
    <main style={{ padding: '2rem', maxWidth: 720, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Content Source Diagnostic
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 14 }}>
        Shows which data source the admin app is reading from.
        No secrets are displayed on this page.
      </p>

      {/* ── Current mode ── */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Active Mode</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="QA_CONTENT_SOURCE"
              value={
                <>
                  <code>{mode}</code>
                  <Badge label={mode === 'supabase_export' ? 'Supabase Export' : 'Local JSON'} ok />
                </>
              }
            />
            <Row
              label="Active package source"
              value={
                mode === 'supabase_export'
                  ? 'data/supabase_exports/active_package_from_supabase_v1.json'
                  : 'data/registry/active_content_index_v1.json'
              }
            />
          </tbody>
        </table>
      </section>

      {/* ── Supabase export files ── */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
          Supabase Export Files
          {allExportsPresent ? (
            <Badge label="All present" ok />
          ) : (
            <Badge label="Some missing" ok={false} />
          )}
        </h2>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <tbody>
            <Row
              label="active_package_from_supabase_v1.json"
              value={
                <Badge
                  label={exportStatus.active_package ? 'Present' : 'Missing'}
                  ok={exportStatus.active_package}
                />
              }
            />
            <Row
              label="student_resource_payload_from_supabase_v1.json"
              value={
                <Badge
                  label={exportStatus.student_payload ? 'Present' : 'Missing'}
                  ok={exportStatus.student_payload}
                />
              }
            />
            <Row
              label="teacher_resource_payload_from_supabase_v1.json"
              value={
                <Badge
                  label={exportStatus.teacher_payload ? 'Present' : 'Missing'}
                  ok={exportStatus.teacher_payload}
                />
              }
            />
          </tbody>
        </table>
        {!allExportsPresent && (
          <p
            style={{
              marginTop: 12,
              padding: '8px 12px',
              background: '#fef3c7',
              borderRadius: 4,
              fontSize: 13,
              color: '#92400e',
            }}
          >
            Run{' '}
            <code>
              .venv-ingest\Scripts\python.exe tools\supabase\read_active_package_from_supabase_v1.py
            </code>{' '}
            to generate the export files.
          </p>
        )}
      </section>

      {/* ── Package info from active source ── */}
      {activeIndex && (
        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
            Active Package (from {mode === 'supabase_export' ? 'Supabase export' : 'local index'})
          </h2>
          {activeIndex.active_packages.map((pkg) => (
            <table key={pkg.content_key} style={{ borderCollapse: 'collapse', marginBottom: 16 }}>
              <tbody>
                <Row label="content_key" value={pkg.content_key} />
                <Row label="package_id" value={pkg.active_package_id} />
                <Row label="version" value={pkg.active_package_version} />
                <Row label="status" value={<Badge label={pkg.active_package_status} ok={pkg.active_package_status === 'active'} />} />
                <Row label="resource_count" value={String(pkg.resource_count)} />
                <Row label="student_payload_count" value={String(pkg.student_payload_count)} />
                <Row label="teacher_payload_count" value={String(pkg.teacher_payload_count)} />
                <Row label="teacher_only_count" value={String(pkg.teacher_only_resource_count)} />
              </tbody>
            </table>
          ))}
          {mode === 'supabase_export' && exportPkg && (
            <table style={{ borderCollapse: 'collapse' }}>
              <tbody>
                <Row label="exported_at" value={exportPkg.exported_at} />
                <Row label="source" value={exportPkg.source} />
              </tbody>
            </table>
          )}
        </section>
      )}

      {!activeIndex && (
        <p
          style={{
            padding: '8px 12px',
            background: '#fee2e2',
            borderRadius: 4,
            fontSize: 13,
            color: '#991b1b',
          }}
        >
          No active package could be loaded from the current source ({mode}).
        </p>
      )}

      {/* ── Local index status ── */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Local Index Status</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="active_content_index_v1.json"
              value={
                <Badge
                  label={localIndexPresent ? 'Present' : 'Missing'}
                  ok={localIndexPresent}
                />
              }
            />
          </tbody>
        </table>
      </section>

      {/* ── How to switch ── */}
      <section
        style={{
          padding: '12px 16px',
          background: '#f3f4f6',
          borderRadius: 6,
          fontSize: 13,
        }}
      >
        <strong>How to switch modes</strong>
        <br />
        In <code>apps/admin/.env.local</code>:
        <pre style={{ margin: '8px 0 0', background: '#e5e7eb', padding: 8, borderRadius: 4 }}>
          {[
            '# Local JSON mode (default):',
            'QA_CONTENT_SOURCE=local',
            '',
            '# Supabase export mode:',
            'QA_CONTENT_SOURCE=supabase_export',
          ].join('\n')}
        </pre>
        Restart the dev server after changing this value.
      </section>
    </main>
  )
}
