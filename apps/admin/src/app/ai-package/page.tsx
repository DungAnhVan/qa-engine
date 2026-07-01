import { requireAppRole } from '@/lib/roleAccess'
import {
  readAiPackageCandidate,
  readAiPackageValidationReport,
  getAiPackageCandidateSummary,
  type PackageResource,
} from '@/lib/aiPackageCandidate'

export const dynamic = 'force-dynamic'

function Badge({ label, ok, neutral }: { label: string; ok?: boolean; neutral?: boolean }) {
  const bg = neutral ? '#dbeafe' : ok ? '#d1fae5' : '#fee2e2'
  const fg = neutral ? '#1e40af' : ok ? '#065f46' : '#991b1b'
  return (
    <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 4,
      fontSize: 12, fontWeight: 600, backgroundColor: bg, color: fg, marginLeft: 6 }}>
      {label}
    </span>
  )
}

function SafetyTag({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span style={{ display: 'inline-block', padding: '1px 6px', borderRadius: 3,
      fontSize: 11, fontWeight: 600, marginRight: 6,
      backgroundColor: ok ? '#d1fae5' : '#fee2e2',
      color:           ok ? '#065f46' : '#991b1b' }}>
      {label}: {ok ? 'YES' : 'NO'}
    </span>
  )
}

function ResourceCard({ resource }: { resource: PackageResource }) {
  const prov = resource.provenance ?? {}
  return (
    <article style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '20px 24px', marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>
            {resource.title || resource.resource_id}
            <Badge label="AI-generated" neutral />
            <Badge label="Teacher approved" ok />
          </h2>
          <p style={{ fontSize: 11, color: '#9ca3af', margin: '3px 0 0' }}>
            <code>{resource.resource_id}</code>
          </p>
        </div>
        <div style={{ fontSize: 12, color: '#6b7280', textAlign: 'right' }}>
          <div>{resource.resource_type} · {resource.topic}</div>
          <div>{resource.skill_name} · {resource.difficulty}</div>
          {resource.estimated_time_minutes > 0 && (
            <div>{resource.estimated_time_minutes} min</div>
          )}
        </div>
      </div>

      <p style={{ fontSize: 12, fontWeight: 600, color: '#374151', textTransform: 'uppercase',
        letterSpacing: '0.05em', marginBottom: 6 }}>Student Prompt</p>
      <p style={{ fontSize: 13, background: '#f9fafb', padding: '10px 12px', borderRadius: 4,
        margin: '0 0 12px', lineHeight: 1.7 }}>
        {resource.student_prompt}
      </p>

      <p style={{ fontSize: 12, fontWeight: 600, color: '#374151', textTransform: 'uppercase',
        letterSpacing: '0.05em', marginBottom: 6 }}>Answer Key</p>
      <p style={{ fontSize: 13, background: '#f0fdf4', padding: '10px 12px', borderRadius: 4,
        margin: '0 0 12px', lineHeight: 1.7, fontFamily: 'monospace' }}>
        {resource.answer_key}
      </p>

      {resource.marking_rubric && resource.marking_rubric.length > 0 && (
        <>
          <p style={{ fontSize: 12, fontWeight: 600, color: '#374151', textTransform: 'uppercase',
            letterSpacing: '0.05em', marginBottom: 6 }}>Marking Rubric</p>
          <ul style={{ fontSize: 13, paddingLeft: 20, margin: '0 0 12px', lineHeight: 1.8 }}>
            {resource.marking_rubric.map((rb, i) => (
              <li key={i}>
                <strong>{rb.criterion}</strong>
                <span style={{ color: '#6b7280', fontSize: 12 }}> [{rb.marks} mark{rb.marks !== 1 ? 's' : ''}]</span>
                {rb.guidance && <span style={{ color: '#6b7280', fontSize: 12 }}> — {rb.guidance}</span>}
              </li>
            ))}
          </ul>
        </>
      )}

      {resource.teacher_notes && (
        <>
          <p style={{ fontSize: 12, fontWeight: 600, color: '#374151', textTransform: 'uppercase',
            letterSpacing: '0.05em', marginBottom: 6 }}>Teacher Notes</p>
          <p style={{ fontSize: 13, color: '#4b5563', background: '#fffbeb', padding: '8px 12px',
            borderRadius: 4, margin: '0 0 12px', lineHeight: 1.6 }}>
            {resource.teacher_notes}
          </p>
        </>
      )}

      <p style={{ fontSize: 12, fontWeight: 600, color: '#374151', textTransform: 'uppercase',
        letterSpacing: '0.05em', marginBottom: 6 }}>Safety Declaration</p>
      <div style={{ marginBottom: 8 }}>
        <SafetyTag ok={resource.safety_declaration?.original_content}        label="original_content" />
        <SafetyTag ok={resource.safety_declaration?.no_raw_source_text_used} label="no_raw_source" />
        <SafetyTag ok={resource.safety_declaration?.no_mark_scheme_copied}   label="no_mark_scheme" />
      </div>

      <p style={{ fontSize: 11, color: '#9ca3af', margin: 0 }}>
        Provenance: origin={prov.origin ?? '—'} · teacher_approved={String(prov.approved_by_teacher_review ?? false)}
        · no_raw_source={String(prov.no_raw_source_text_used ?? false)}
      </p>
    </article>
  )
}

export default async function AiPackagePage() {
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

  const pkg        = readAiPackageCandidate()
  const validation = readAiPackageValidationReport()
  const summary    = getAiPackageCandidateSummary()
  const resources  = pkg?.resources ?? []

  return (
    <main style={{ padding: '2rem', maxWidth: 900, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        AI Package Candidate
        <Badge label="DRAFT — NOT PUBLISHED" neutral />
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
        Gate 69E — approved AI resources assembled into package candidate.
        Gate 69F required before publishing.
      </p>

      {/* Warning */}
      <div style={{ marginBottom: 24, padding: '12px 16px', background: '#fef3c7',
        borderRadius: 6, borderLeft: '4px solid #f59e0b', fontSize: 13, color: '#92400e' }}>
        <strong>Gate 69F required before publishing AI package.</strong>{' '}
        This package candidate contains teacher-approved AI-generated resources.
        Final publish approval must go through Gate 69F. Auto-publish is disabled.
        No Supabase writes will be made without explicit Gate 69F confirmation.
      </div>

      {/* Summary */}
      <section style={{ marginBottom: 24, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {[
          { label: 'Status',         value: summary.status,                color: '#1e40af' },
          { label: 'Resources',      value: summary.resource_count,         color: '#065f46' },
          { label: 'Student payload',value: summary.student_payload_count,  color: '#374151' },
          { label: 'Teacher payload',value: summary.teacher_payload_count,  color: '#374151' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ padding: '10px 18px', background: '#f9fafb',
            borderRadius: 6, border: '1px solid #e5e7eb', minWidth: 120 }}>
            <div style={{ fontSize: typeof value === 'number' ? 22 : 13,
              fontWeight: 700, color }}>{value}</div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>{label}</div>
          </div>
        ))}
      </section>

      {/* Policy */}
      <section style={{ marginBottom: 24 }}>
        <table style={{ borderCollapse: 'collapse', fontSize: 13 }}>
          <tbody>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Validation</td>
              <td><Badge label={summary.validation_passed ? 'PASSED' : 'NOT RUN'}
                ok={summary.validation_passed} neutral={!summary.validation_report_exists} /></td>
            </tr>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Auto-publish</td>
              <td><Badge label="DISABLED" ok={true} /></td>
            </tr>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Supabase write</td>
              <td><Badge label="NOT PERFORMED" ok={true} /></td>
            </tr>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Teacher final publish</td>
              <td><Badge label="REQUIRED — Gate 69F" ok={true} /></td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* No package */}
      {!pkg && (
        <div style={{ padding: '20px', background: '#fee2e2', borderRadius: 6,
          fontSize: 13, color: '#991b1b' }}>
          <strong>Package candidate not found.</strong> Run the builder first:
          <pre style={{ margin: '8px 0 0', fontSize: 12 }}>
            .venv-ingest\Scripts\python.exe tools\ai\build_ai_approved_package_candidate_v1.py
          </pre>
        </div>
      )}

      {/* Resource cards */}
      {resources.map(r => <ResourceCard key={r.resource_id} resource={r} />)}

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/system/ai-package"   style={{ color: '#3b82f6', marginRight: 16 }}>Package Diagnostic</a>
        <a href="/api/system/ai-package" style={{ color: '#3b82f6', marginRight: 16 }}>Package API</a>
        <a href="/ai-review"           style={{ color: '#3b82f6', marginRight: 16 }}>AI Review Queue</a>
        <a href="/system/health"       style={{ color: '#3b82f6' }}>Health</a>
      </p>
    </main>
  )
}
