import { requireAppRole } from '@/lib/roleAccess'
import {
  readAiPublishedPackage,
  readAiLocalRegistry,
  getAiPublishedPackageSummary,
  type PublishedResource,
} from '@/lib/aiPublishedPackage'

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

function ResourceCard({ resource }: { resource: PublishedResource }) {
  const prov = resource.provenance ?? {}
  return (
    <article style={{ border: '1px solid #c4b5fd', borderRadius: 8, padding: '20px 24px', marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>
            {resource.title || resource.resource_id}
            <Badge label="LOCAL — NOT ACTIVE" neutral />
          </h2>
          <p style={{ fontSize: 11, color: '#9ca3af', margin: '3px 0 0' }}>
            <code>{resource.resource_id}</code>
          </p>
        </div>
        <div style={{ fontSize: 12, color: '#6b7280', textAlign: 'right' }}>
          <div>{resource.resource_type} · {resource.topic}</div>
          <div>{resource.skill_name} · {resource.difficulty}</div>
        </div>
      </div>

      <p style={{ fontSize: 12, fontWeight: 700, color: '#374151', textTransform: 'uppercase',
        letterSpacing: '0.05em', marginBottom: 6 }}>Student Prompt</p>
      <p style={{ fontSize: 13, background: '#f9fafb', padding: '10px 12px',
        borderRadius: 4, margin: '0 0 12px', lineHeight: 1.7 }}>
        {resource.student_prompt}
      </p>

      <p style={{ fontSize: 12, fontWeight: 700, color: '#374151', textTransform: 'uppercase',
        letterSpacing: '0.05em', marginBottom: 6 }}>Answer Key</p>
      <p style={{ fontSize: 13, background: '#f0fdf4', padding: '10px 12px',
        borderRadius: 4, margin: '0 0 12px', lineHeight: 1.7, fontFamily: 'monospace' }}>
        {resource.answer_key}
      </p>

      {resource.marking_rubric?.length > 0 && (
        <>
          <p style={{ fontSize: 12, fontWeight: 700, color: '#374151', textTransform: 'uppercase',
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
          <p style={{ fontSize: 12, fontWeight: 700, color: '#374151', textTransform: 'uppercase',
            letterSpacing: '0.05em', marginBottom: 6 }}>Teacher Notes</p>
          <p style={{ fontSize: 13, background: '#fffbeb', padding: '8px 12px',
            borderRadius: 4, margin: '0 0 12px', lineHeight: 1.6, color: '#4b5563' }}>
            {resource.teacher_notes}
          </p>
        </>
      )}

      <p style={{ fontSize: 12, fontWeight: 700, color: '#374151', textTransform: 'uppercase',
        letterSpacing: '0.05em', marginBottom: 6 }}>Safety Declaration</p>
      <div style={{ marginBottom: 8 }}>
        <SafetyTag ok={resource.safety_declaration?.original_content}        label="original_content" />
        <SafetyTag ok={resource.safety_declaration?.no_raw_source_text_used} label="no_raw_source" />
        <SafetyTag ok={resource.safety_declaration?.no_mark_scheme_copied}   label="no_mark_scheme" />
      </div>

      <p style={{ fontSize: 11, color: '#9ca3af', margin: 0 }}>
        Provenance: origin={prov.origin ?? '—'} · teacher_approved={String(prov.approved_by_teacher_review ?? false)}
      </p>
    </article>
  )
}

export default async function AiPublishedPage() {
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

  const pkg      = readAiPublishedPackage()
  const registry = readAiLocalRegistry()
  const summary  = getAiPublishedPackageSummary()
  const resources = pkg?.resources ?? []

  return (
    <main style={{ padding: '2rem', maxWidth: 900, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        AI Published Package
        <Badge label="LOCAL — NOT ACTIVE CONTENT" neutral />
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
        Gate 69F — AI package locally published with teacher final approval.
        Not active production content. Gate 69G required for Supabase sync.
      </p>

      {/* Warning */}
      <div style={{ marginBottom: 24, padding: '12px 16px', background: '#fef3c7',
        borderRadius: 6, borderLeft: '4px solid #f59e0b', fontSize: 13, color: '#92400e' }}>
        <strong>This AI package is locally published but not active production content.</strong>{' '}
        Gate 69G required for Supabase sync and active content switch.
        Auto-publish is disabled. No Supabase writes performed.
      </div>

      {/* Summary */}
      <section style={{ marginBottom: 24, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {[
          { label: 'Status',         value: summary.status,        color: '#4c1d95' },
          { label: 'Resources',      value: summary.resource_count, color: '#065f46' },
          { label: 'Active content', value: 'false',               color: '#374151' },
          { label: 'Supabase write', value: 'false',               color: '#374151' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ padding: '10px 18px', background: '#f9fafb',
            borderRadius: 6, border: '1px solid #e5e7eb', minWidth: 110 }}>
            <div style={{ fontSize: typeof value === 'number' ? 22 : 13,
              fontWeight: 700, color }}>{value}</div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>{label}</div>
          </div>
        ))}
      </section>

      {/* Policy badges */}
      <section style={{ marginBottom: 24 }}>
        <table style={{ borderCollapse: 'collapse', fontSize: 13 }}>
          <tbody>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Package ID</td>
              <td><code>{pkg?.package_id ?? '—'}</code></td>
            </tr>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Approved by</td>
              <td><code>{pkg?.approved_by ?? '—'}</code></td>
            </tr>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Active content</td>
              <td><Badge label="FALSE" ok={true} /></td>
            </tr>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Supabase write</td>
              <td><Badge label="NOT PERFORMED" ok={true} /></td>
            </tr>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Teacher final approval</td>
              <td><Badge label="TRUE" ok={true} /></td>
            </tr>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Validation</td>
              <td><Badge label={summary.validation_passed ? 'PASSED' : 'NOT RUN'}
                ok={summary.validation_passed} neutral={!summary.validation_passed} /></td>
            </tr>
            <tr>
              <td style={{ padding: '4px 16px 4px 0', color: '#6b7280' }}>Ready for Gate 69G</td>
              <td><Badge label={summary.ready_for_gate69g ? 'YES' : 'NOT YET'}
                ok={summary.ready_for_gate69g} neutral={!summary.ready_for_gate69g} /></td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* No package */}
      {!pkg && (
        <div style={{ padding: '20px', background: '#fee2e2', borderRadius: 6,
          fontSize: 13, color: '#991b1b' }}>
          <strong>Local published package not found.</strong> Run:
          <pre style={{ margin: '8px 0 0', fontSize: 12 }}>
            .venv-ingest\Scripts\python.exe tools\ai\test_gate69f_ai_local_publish_v1.py
          </pre>
        </div>
      )}

      {/* Resource cards */}
      {resources.map(r => <ResourceCard key={r.resource_id} resource={r} />)}

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/system/ai-published"    style={{ color: '#3b82f6', marginRight: 16 }}>Published Diagnostic</a>
        <a href="/api/system/ai-published" style={{ color: '#3b82f6', marginRight: 16 }}>Published API</a>
        <a href="/ai-package"             style={{ color: '#3b82f6', marginRight: 16 }}>Package Candidate</a>
        <a href="/system/health"          style={{ color: '#3b82f6' }}>Health</a>
      </p>
    </main>
  )
}
