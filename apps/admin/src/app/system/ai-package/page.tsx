import { requireAppRole } from '@/lib/roleAccess'
import { getAiPackageCandidateSummary } from '@/lib/aiPackageCandidate'

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

export default async function AiPackageDiagnosticPage() {
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

  const summary = getAiPackageCandidateSummary()

  return (
    <main style={{ padding: '2rem', maxWidth: 800, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        AI Package Candidate Diagnostic
        <Badge label="Gate 69E" neutral />
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 13 }}>
        AI approved package candidate status. No secrets displayed.
      </p>

      {/* File status */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>File Status</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="Package candidate"
              value={<Badge label={summary.package_candidate_exists ? 'EXISTS' : 'MISSING'}
                ok={summary.package_candidate_exists} />} />
            <Row label="Validation report"
              value={<Badge label={summary.validation_report_exists
                ? (summary.validation_passed ? 'PASSED' : 'FAILED')
                : 'MISSING'}
                ok={summary.validation_passed}
                neutral={!summary.validation_report_exists} />} />
            <Row label="Student payload"
              value={<Badge label={summary.student_payload_exists ? 'EXISTS' : 'NOT EXPORTED'}
                ok={summary.student_payload_exists}
                neutral={!summary.student_payload_exists} />} />
            <Row label="Teacher payload"
              value={<Badge label={summary.teacher_payload_exists ? 'EXISTS' : 'NOT EXPORTED'}
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
          </tbody>
        </table>
      </section>

      {/* Counts */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>Package Contents</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="Status"                value={<code>{summary.status}</code>} />
            <Row label="Resource count"        value={<code>{summary.resource_count}</code>} />
            <Row label="Student payload count" value={<code>{summary.student_payload_count}</code>} />
            <Row label="Teacher payload count" value={<code>{summary.teacher_payload_count}</code>} />
          </tbody>
        </table>
      </section>

      {/* Policy */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>Policy</h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="auto_publish_enabled"
              value={<Badge label="FALSE — disabled" ok={true} />} />
            <Row label="supabase_write_performed"
              value={<Badge label="FALSE" ok={true} />} />
            <Row label="teacher_final_publish_required"
              value={<Badge label="TRUE — Gate 69F required" ok={true} />} />
          </tbody>
        </table>
      </section>

      {/* Scripts */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>Gate 69E Scripts</h2>
        <pre style={{ background: '#f3f4f6', padding: '12px 16px', borderRadius: 4,
          fontSize: 12, overflowX: 'auto', lineHeight: 1.7 }}>
          {[
            '# Build package candidate from approved resources',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_approved_package_candidate_v1.py',
            '',
            '# Validate package candidate',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\validate_ai_package_candidate_v1.py \\',
            '    data\\ai\\package_candidates\\ai_resource_package_candidate_v1.json',
            '',
            '# Export student/teacher payloads',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\export_ai_package_candidate_payloads_v1.py',
            '',
            '# Render HTML previews',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\render_ai_package_candidate_preview_v1.py',
            '',
            '# Run full Gate 69E test',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate69e_ai_package_candidate_v1.py',
          ].join('\n')}
        </pre>
      </section>

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/api/system/ai-package"  style={{ color: '#3b82f6', marginRight: 16 }}>AI Package API</a>
        <a href="/ai-package"             style={{ color: '#3b82f6', marginRight: 16 }}>Package Candidate UI</a>
        <a href="/system/ai-review"       style={{ color: '#3b82f6', marginRight: 16 }}>AI Review Diag</a>
        <a href="/system/ai-authoring"    style={{ color: '#3b82f6' }}>AI Authoring</a>
      </p>
    </main>
  )
}
