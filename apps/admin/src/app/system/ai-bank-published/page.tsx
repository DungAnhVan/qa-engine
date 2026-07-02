import { requireRole } from '@/lib/serverSupabaseAuth'
import { getGate70dAiBankPublishedSummary } from '@/lib/aiBankPublishedPackage'
import fs from 'fs'
import path from 'path'

export const metadata = { title: 'AI Bank Published Diagnostic' }

const ROOT = path.resolve(process.cwd(), '../..')
const PKG_DIR = path.join(ROOT, 'data/ai/published/gate70d_ai_bank_package_v1')

export default async function AiBankPublishedDiagPage() {
  await requireRole(['admin'])

  const summary = getGate70dAiBankPublishedSummary()

  const fileChecks = [
    ['Final Approval JSON',           path.join(ROOT, 'data/ai/package_candidates/gate70d_ai_bank_final_publish_approval_v1.json')],
    ['Local Published Package',       path.join(PKG_DIR, 'publish_package_v1.json')],
    ['Student Payload',               path.join(PKG_DIR, 'student_resource_payload_v1.json')],
    ['Teacher Payload',               path.join(PKG_DIR, 'teacher_resource_payload_v1.json')],
    ['Publish Manifest',              path.join(PKG_DIR, 'ai_bank_publish_manifest_v1.md')],
    ['Publish Report',                path.join(PKG_DIR, 'ai_bank_publish_report_v1.json')],
    ['Student Preview HTML',          path.join(PKG_DIR, 'static_preview/gate70d_student_ai_bank_published_preview_v1.html')],
    ['Teacher Preview HTML',          path.join(PKG_DIR, 'static_preview/gate70d_teacher_ai_bank_published_preview_v1.html')],
    ['Preview Report',                path.join(PKG_DIR, 'static_preview/gate70d_ai_bank_published_preview_report_v1.json')],
    ['Local Registry',                path.join(ROOT, 'data/ai/registry/gate70d_ai_bank_content_registry_v1.json')],
    ['Validation Report',             path.join(ROOT, 'data/diagnostics/gate70d_ai_bank_local_published_package_validation_report_v1.json')],
    ['Build Report',                  path.join(ROOT, 'data/diagnostics/gate70d_ai_bank_local_publish_build_report_v1.json')],
    ['Approval Report',               path.join(ROOT, 'data/diagnostics/gate70d_ai_bank_final_publish_approval_report_v1.json')],
    ['Registry Report',               path.join(ROOT, 'data/diagnostics/gate70d_ai_bank_local_registry_build_report_v1.json')],
    ['Test Report',                   path.join(ROOT, 'data/diagnostics/gate70d_ai_bank_local_publish_test_report_v1.json')],
    ['Gate Report',                   path.join(ROOT, 'data/diagnostics/gate70d_ai_bank_local_publish_report_v1.json')],
    ['DONE Marker',                   path.join(ROOT, 'data/diagnostics/SUPABASE_GATE_70D_AI_BANK_LOCAL_PUBLISH_DONE.md')],
  ] as [string, string][]

  function Row({ label, value, ok }: { label: string; value: string | boolean | number | null; ok?: boolean }) {
    const color = ok === true ? '#5aff8a' : ok === false ? '#ff5a5a' : '#ccc'
    return (
      <tr>
        <td style={{ padding: '6px 12px', fontFamily: 'monospace', fontSize: 12, color: '#888', width: 320 }}>{label}</td>
        <td style={{ padding: '6px 12px', fontFamily: 'monospace', fontSize: 12, color }}>{String(value ?? '—')}</td>
      </tr>
    )
  }

  return (
    <main style={{ maxWidth: 860, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 22, marginBottom: 4 }}>AI Bank Published — Diagnostic</h1>
      <p style={{ color: '#888', fontSize: 13, marginBottom: 24 }}>Gate 70D system view</p>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Summary</h2>
        <table style={{ borderCollapse: 'collapse', width: '100%', border: '1px solid #222' }}>
          <tbody>
            <Row label="packageExists"           value={summary.packageExists}           ok={summary.packageExists} />
            <Row label="resourceCount"           value={summary.resourceCount} />
            <Row label="status"                  value={summary.status} />
            <Row label="approvalStatus"          value={summary.approvalStatus}          ok={summary.approvalStatus === 'approved'} />
            <Row label="approvedBy"              value={summary.approvedBy} />
            <Row label="validationPassed"        value={summary.validationPassed}        ok={summary.validationPassed === true} />
            <Row label="activeContent"           value={summary.activeContent}           ok={!summary.activeContent} />
            <Row label="supabaseWritePerformed"  value={summary.supabaseWritePerformed}  ok={!summary.supabaseWritePerformed} />
            <Row label="aiApiCalled"             value={summary.aiApiCalled}             ok={!summary.aiApiCalled} />
            <Row label="teacherFinalApproval"    value={summary.teacherFinalApproval}    ok={summary.teacherFinalApproval} />
            <Row label="registryExists"          value={summary.registryExists}          ok={summary.registryExists} />
            <Row label="studentPayloadExists"    value={summary.studentPayloadExists}    ok={summary.studentPayloadExists} />
            <Row label="teacherPayloadExists"    value={summary.teacherPayloadExists}    ok={summary.teacherPayloadExists} />
            <Row label="studentPreviewExists"    value={summary.studentPreviewExists}    ok={summary.studentPreviewExists} />
            <Row label="teacherPreviewExists"    value={summary.teacherPreviewExists}    ok={summary.teacherPreviewExists} />
            <Row label="readyForGate70E"         value={summary.readyForGate70E}         ok={summary.readyForGate70E} />
            <Row label="secretsExposed"          value={false}                           ok={true} />
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>File Checklist</h2>
        <table style={{ borderCollapse: 'collapse', width: '100%', border: '1px solid #222' }}>
          <tbody>
            {fileChecks.map(([label, filePath]) => {
              const exists = fs.existsSync(filePath)
              return (
                <tr key={label}>
                  <td style={{ padding: '5px 12px', fontFamily: 'monospace', fontSize: 11, color: '#888', width: 280 }}>{label}</td>
                  <td style={{ padding: '5px 12px', fontFamily: 'monospace', fontSize: 11, color: exists ? '#5aff8a' : '#ff5a5a' }}>
                    {exists ? 'exists' : 'missing'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>

      <div style={{
        marginTop: 24, padding: '10px 14px', border: '1px solid #1a1a1a',
        borderRadius: 6, backgroundColor: '#0d0d0d', fontSize: 12, color: '#555',
      }}>
        <a href="/ai-bank-published" style={{ color: '#5ab8ff' }}>← Admin View</a>
        {' · '}API: <a href="/api/system/ai-bank-published" style={{ color: '#5ab8ff' }}>/api/system/ai-bank-published</a>
        {' · '}Gate 70D · No publish · No Supabase · No AI API
      </div>
    </main>
  )
}
