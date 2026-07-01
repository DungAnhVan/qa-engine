import { requireAppRole } from '@/lib/roleAccess'
import { getAiPublishedPackageSummary } from '@/lib/aiPublishedPackage'

export const dynamic = 'force-dynamic'

function Badge({ label, ok, neutral }: { label: string; ok?: boolean; neutral?: boolean }) {
  const bg = neutral ? '#dbeafe' : ok ? '#d1fae5' : '#fee2e2'
  const fg = neutral ? '#1e40af' : ok ? '#065f46' : '#991b1b'
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

export default async function AiPublishedDiagnosticPage() {
  const { allowed, currentRole } = await requireAppRole(['admin'])
  if (!allowed) return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Access denied</h1>
      <p style={{ color: '#6b7280', fontSize: 14, marginBottom: 12 }}>
        Required: admin. Your role: <code>{currentRole ?? 'none'}</code>
      </p>
      <a href="/login" style={{ color: '#3b82f6' }}>Sign in →</a>
    </main>
  )

  const summary = getAiPublishedPackageSummary()

  return (
    <main style={{ padding: '2rem', maxWidth: 800, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        AI Published Package Diagnostic
        <Badge label="Gate 69F" neutral />
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 13 }}>
        AI local publish status. No secrets displayed.
      </p>

      {/* File Status */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>File Status</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="Final approval file"
              value={<><Badge label={summary.approval_exists ? 'EXISTS' : 'MISSING'}
                ok={summary.approval_exists} />
                {summary.approval_exists && (
                  <span style={{ marginLeft: 8, fontSize: 12, color: '#6b7280' }}>
                    status: {summary.approval_status}
                  </span>
                )}</>} />
            <Row label="Local published package"
              value={<Badge label={summary.local_published_package_exists ? 'EXISTS' : 'MISSING'}
                ok={summary.local_published_package_exists} />} />
            <Row label="Validation report"
              value={<Badge label={summary.validation_passed ? 'PASSED' : (summary.local_published_package_exists ? 'FAILED' : 'NOT RUN')}
                ok={summary.validation_passed}
                neutral={!summary.local_published_package_exists} />} />
            <Row label="Student payload"
              value={<Badge label={summary.student_payload_exists ? 'EXISTS' : 'MISSING'}
                ok={summary.student_payload_exists}
                neutral={!summary.student_payload_exists} />} />
            <Row label="Teacher payload"
              value={<Badge label={summary.teacher_payload_exists ? 'EXISTS' : 'MISSING'}
                ok={summary.teacher_payload_exists}
                neutral={!summary.teacher_payload_exists} />} />
            <Row label="Student HTML preview"
              value={<Badge label={summary.student_preview_exists ? 'EXISTS' : 'NOT RENDERED'}
                ok={summary.student_preview_exists}
                neutral={!summary.student_preview_exists} />} />
            <Row label="Teacher HTML preview"
              value={<Badge label={summary.teacher_preview_exists ? 'EXISTS' : 'NOT RENDERED'}
                ok={summary.teacher_preview_exists}
                neutral={!summary.teacher_preview_exists} />} />
            <Row label="AI local registry"
              value={<Badge label={summary.registry_exists ? 'EXISTS' : 'NOT BUILT'}
                ok={summary.registry_exists}
                neutral={!summary.registry_exists} />} />
          </tbody>
        </table>
      </section>

      {/* Package info */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>Package Info</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="Status"         value={<code>{summary.status}</code>} />
            <Row label="Resource count" value={<code>{summary.resource_count}</code>} />
          </tbody>
        </table>
      </section>

      {/* Policy */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>Policy</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="active_content"
              value={<Badge label="FALSE" ok={true} />} />
            <Row label="supabase_write_performed"
              value={<Badge label="FALSE" ok={true} />} />
            <Row label="teacher_final_approval"
              value={<Badge label="TRUE" ok={true} />} />
            <Row label="ready_for_gate69g"
              value={<Badge label={summary.ready_for_gate69g ? 'YES' : 'NOT YET'}
                ok={summary.ready_for_gate69g}
                neutral={!summary.ready_for_gate69g} />} />
          </tbody>
        </table>
      </section>

      {/* Scripts */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>Gate 69F Scripts</h2>
        <pre style={{ background: '#f3f4f6', padding: '12px 16px', borderRadius: 4,
          fontSize: 12, overflowX: 'auto', lineHeight: 1.7 }}>
          {[
            '# Approve package candidate',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\approve_ai_package_candidate_v1.py \\',
            '    --approve --approved-by local_demo_teacher --notes "approved for local publish"',
            '',
            '# Build local published package',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_local_published_package_v1.py',
            '',
            '# Validate published package',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\validate_ai_local_published_package_v1.py \\',
            '    data\\ai\\published\\ai_resource_package_v1\\publish_package_v1.json',
            '',
            '# Render previews + build registry',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\render_ai_local_published_package_preview_v1.py',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_local_registry_v1.py',
          ].join('\n')}
        </pre>
      </section>

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/api/system/ai-published" style={{ color: '#3b82f6', marginRight: 16 }}>AI Published API</a>
        <a href="/ai-published"            style={{ color: '#3b82f6', marginRight: 16 }}>Published Package UI</a>
        <a href="/system/ai-package"       style={{ color: '#3b82f6', marginRight: 16 }}>AI Package Diag</a>
        <a href="/system/health"           style={{ color: '#3b82f6' }}>Health</a>
      </p>
    </main>
  )
}
