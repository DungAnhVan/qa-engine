import { requireRole } from '@/lib/serverSupabaseAuth'
import {
  readPackageCandidate,
  readStudentPayload,
  readTeacherPayload,
  readPackageValidationReport,
  readPackageBuildReport,
  getPackageSummary,
} from '@/lib/aiBankPackageCandidate'

export const metadata = { title: 'AI Bank Package Diagnostic' }

export default async function AiBankPackageDiagPage() {
  await requireRole(['admin'])

  const summary    = getPackageSummary()
  const pkg        = readPackageCandidate()
  const student    = readStudentPayload() as Record<string, unknown> | null
  const teacher    = readTeacherPayload() as Record<string, unknown> | null
  const validation = readPackageValidationReport() as Record<string, unknown> | null
  const build      = readPackageBuildReport() as Record<string, unknown> | null

  function Row({ label, value, ok }: { label: string; value: string | boolean | number | null; ok?: boolean }) {
    const color = ok === true ? '#5aff8a' : ok === false ? '#ff5a5a' : '#ccc'
    return (
      <tr>
        <td style={{ padding: '6px 12px', fontFamily: 'monospace', fontSize: 12, color: '#888', width: 280 }}>{label}</td>
        <td style={{ padding: '6px 12px', fontFamily: 'monospace', fontSize: 12, color }}>{String(value ?? '—')}</td>
      </tr>
    )
  }

  return (
    <main style={{ maxWidth: 860, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 22, marginBottom: 4 }}>AI Bank Package — Diagnostic</h1>
      <p style={{ color: '#888', fontSize: 13, marginBottom: 24 }}>Gate 70C system view</p>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Summary</h2>
        <table style={{ borderCollapse: 'collapse', width: '100%', border: '1px solid #222', borderRadius: 6 }}>
          <tbody>
            <Row label="packageExists"             value={summary.packageExists}           ok={summary.packageExists} />
            <Row label="resourceCount"             value={summary.resourceCount} />
            <Row label="status"                    value={summary.status} />
            <Row label="validationPassed"          value={summary.validationPassed}        ok={summary.validationPassed === true} />
            <Row label="buildStatus"               value={summary.buildStatus}             ok={summary.buildStatus === 'passed'} />
            <Row label="teacherFinalPublishRequired" value={summary.teacherFinalPublishRequired} ok={summary.teacherFinalPublishRequired} />
            <Row label="autoPublishEnabled"        value={summary.autoPublishEnabled}      ok={!summary.autoPublishEnabled} />
            <Row label="supabaseWritePerformed"    value={summary.supabaseWritePerformed}  ok={!summary.supabaseWritePerformed} />
            <Row label="aiApiCalled"               value={summary.aiApiCalled}             ok={!summary.aiApiCalled} />
            <Row label="studentPayloadExists"      value={summary.studentPayloadExists}    ok={summary.studentPayloadExists} />
            <Row label="teacherPayloadExists"      value={summary.teacherPayloadExists}    ok={summary.teacherPayloadExists} />
            <Row label="validationReportExists"    value={summary.validationReportExists}  ok={summary.validationReportExists} />
          </tbody>
        </table>
      </section>

      {pkg && (
        <section style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 16, marginBottom: 10 }}>Package Candidate</h2>
          <table style={{ borderCollapse: 'collapse', width: '100%', border: '1px solid #222' }}>
            <tbody>
              <Row label="package_candidate_id"    value={pkg.package_candidate_id} />
              <Row label="version"                 value={pkg.version} />
              <Row label="status"                  value={pkg.status} />
              <Row label="resource_count"          value={pkg.resource_count} />
              <Row label="created_at"              value={pkg.created_at?.slice(0, 19) ?? null} />
              <Row label="teacher_final_publish_required" value={pkg.teacher_final_publish_required} ok={pkg.teacher_final_publish_required} />
              <Row label="auto_publish_enabled"    value={pkg.auto_publish_enabled}    ok={!pkg.auto_publish_enabled} />
              <Row label="supabase_write_performed" value={pkg.supabase_write_performed} ok={!pkg.supabase_write_performed} />
              <Row label="ai_api_called"           value={pkg.ai_api_called}            ok={!pkg.ai_api_called} />
              {pkg.issues && pkg.issues.length > 0 && (
                <Row label="issues" value={pkg.issues.join('; ')} ok={false} />
              )}
            </tbody>
          </table>
        </section>
      )}

      {validation && (
        <section style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 16, marginBottom: 10 }}>Validation Report</h2>
          <pre style={{
            backgroundColor: '#0d0d0d', border: '1px solid #222', borderRadius: 4,
            padding: '12px 16px', fontSize: 11, color: '#aaa',
            overflowX: 'auto', maxHeight: 300, overflowY: 'auto',
          }}>
            {JSON.stringify(validation, null, 2)}
          </pre>
        </section>
      )}

      {build && (
        <section style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 16, marginBottom: 10 }}>Build Report</h2>
          <pre style={{
            backgroundColor: '#0d0d0d', border: '1px solid #222', borderRadius: 4,
            padding: '12px 16px', fontSize: 11, color: '#aaa',
            overflowX: 'auto', maxHeight: 300, overflowY: 'auto',
          }}>
            {JSON.stringify(build, null, 2)}
          </pre>
        </section>
      )}

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Payload Counts</h2>
        <table style={{ borderCollapse: 'collapse', width: '100%', border: '1px solid #222' }}>
          <tbody>
            <Row label="student_payload.resource_count" value={student ? (student as { resource_count?: number }).resource_count ?? 0 : null} />
            <Row label="teacher_payload.resource_count" value={teacher ? (teacher as { resource_count?: number }).resource_count ?? 0 : null} />
          </tbody>
        </table>
      </section>

      <div style={{
        marginTop: 24, padding: '10px 14px', border: '1px solid #1a1a1a',
        borderRadius: 6, backgroundColor: '#0d0d0d', fontSize: 12, color: '#555',
      }}>
        <a href="/ai-bank-package" style={{ color: '#5ab8ff' }}>← Admin View</a>
        {' · '}API: <a href="/api/system/ai-bank-package" style={{ color: '#5ab8ff' }}>/api/system/ai-bank-package</a>
        {' · '}Gate 70C · No publish · No Supabase · No AI API
      </div>
    </main>
  )
}
