import { requireRole } from '@/lib/serverSupabaseAuth'
import {
  readGate70dAiBankPublishedPackage,
  readGate70dAiBankValidationReport,
  getGate70dAiBankPublishedSummary,
} from '@/lib/aiBankPublishedPackage'

export const metadata = { title: 'AI Bank Published' }

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, [string, string]> = {
    published_local_not_active: ['#1a2a3a', '#5ab8ff'],
    passed:                     ['#1a3a1a', '#5aff8a'],
    valid:                      ['#1a3a1a', '#5aff8a'],
    approved:                   ['#1a3a1a', '#5aff8a'],
    not_built:                  ['#2a2a2a', '#888'],
    pending:                    ['#2a2a2a', '#aaa'],
  }
  const [bg, color] = map[status] ?? ['#2a2a2a', '#aaa']
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 3,
      backgroundColor: bg, color, fontSize: 11, fontFamily: 'monospace',
    }}>
      {status}
    </span>
  )
}

function SafeTag({ label, ok = true }: { label: string; ok?: boolean }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 6px', marginRight: 4,
      backgroundColor: ok ? '#1a3a1a' : '#3a1a1a',
      color: ok ? '#5aff8a' : '#ff5a5a',
      borderRadius: 3, fontSize: 10, fontFamily: 'monospace',
      border: `1px solid ${ok ? '#2d6a2d' : '#6a2d2d'}`,
    }}>
      {label}
    </span>
  )
}

function Stat({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div style={{
      backgroundColor: '#0d0d0d', border: '1px solid #222', borderRadius: 6,
      padding: '12px 16px', textAlign: 'center',
    }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: color ?? '#eee' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#555', marginTop: 2 }}>{label}</div>
    </div>
  )
}

export default async function AiBankPublishedPage() {
  await requireRole(['admin'])

  const summary    = getGate70dAiBankPublishedSummary()
  const pkg        = readGate70dAiBankPublishedPackage()
  const validation = readGate70dAiBankValidationReport() as Record<string, unknown> | null

  return (
    <main style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 24, marginBottom: 4 }}>AI Bank Published Package</h1>
      <p style={{ color: '#888', fontSize: 14, marginBottom: 24 }}>
        Gate 70D — Final approval and local publish of AI bank package.
        Not active production content. No Supabase write. Gate 70E required for Supabase sync.
      </p>

      <div style={{
        backgroundColor: '#1a2a1a', border: '1px solid #2d5a2d',
        borderRadius: 6, padding: '10px 16px', marginBottom: 12, fontSize: 13,
      }}>
        <strong style={{ color: '#5aff8a' }}>Gate 70D — Locally Published</strong>
        <span style={{ color: '#aaa', marginLeft: 12 }}>
          Teacher final approval applied. Package is locally published and ready for Gate 70E Supabase sync.
        </span>
      </div>

      <div style={{
        backgroundColor: '#1a1a0d', border: '1px solid #3a3a1a',
        borderRadius: 6, padding: '10px 16px', marginBottom: 20, fontSize: 13,
      }}>
        <strong style={{ color: '#ffd05a' }}>Not Active Production Content</strong>
        <span style={{ color: '#aaa', marginLeft: 12 }}>
          This AI bank package is locally published but not synced to Supabase and not active
          production content. Gate 70E required for Supabase sync.
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 28 }}>
        <Stat label="Resources"      value={summary.resourceCount} />
        <Stat label="Status"         value={summary.status === 'published_local_not_active' ? 'local only' : summary.status} color="#5ab8ff" />
        <Stat label="Validation"     value={summary.validationPassed === true ? 'valid' : 'pending'} color={summary.validationPassed === true ? '#5aff8a' : '#ffd05a'} />
        <Stat label="Gate 70E Ready" value={summary.readyForGate70E ? 'yes' : 'no'} color={summary.readyForGate70E ? '#5aff8a' : '#ffd05a'} />
      </div>

      {pkg && (
        <div style={{
          marginBottom: 24, padding: '14px 18px', border: '1px solid #1a3a4a',
          borderRadius: 6, backgroundColor: '#0d1a2a', fontSize: 13,
        }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
            <SafeTag label={`active_content=${pkg.active_content}`} ok={!pkg.active_content} />
            <SafeTag label={`supabase_write=${pkg.supabase_write_performed}`} ok={!pkg.supabase_write_performed} />
            <SafeTag label={`ai_api=${pkg.ai_api_called}`} ok={!pkg.ai_api_called} />
            <SafeTag label={`teacher_approved=${pkg.teacher_final_approval}`} ok={pkg.teacher_final_approval} />
          </div>
          <div style={{ fontSize: 11, color: '#555', fontFamily: 'monospace' }}>
            id={pkg.package_id} · v={pkg.version} · published={pkg.published_at?.slice(0, 10)}
            {pkg.approved_by && ` · approved_by=${pkg.approved_by}`}
          </div>
          {pkg.approval_notes && (
            <div style={{ fontSize: 12, color: '#777', marginTop: 6 }}>
              Approval notes: {pkg.approval_notes}
            </div>
          )}
        </div>
      )}

      {validation && (validation as { valid?: boolean }).valid !== undefined && (
        <div style={{
          marginBottom: 24, padding: '12px 16px',
          border: `1px solid ${(validation as { valid?: boolean }).valid ? '#2d5a2d' : '#5a2d2d'}`,
          borderRadius: 6,
          backgroundColor: (validation as { valid?: boolean }).valid ? '#0d1a0d' : '#1a0d0d',
          fontSize: 13,
        }}>
          <strong style={{ color: (validation as { valid?: boolean }).valid ? '#5aff8a' : '#ff5a5a' }}>
            Validation: {(validation as { valid?: boolean }).valid ? 'PASSED' : 'ISSUES FOUND'}
          </strong>
          {Array.isArray((validation as { issues?: string[] }).issues) &&
            (validation as { issues: string[] }).issues.length > 0 && (
              <ul style={{ margin: '8px 0 0', paddingLeft: 18, color: '#ff5a5a', fontSize: 12 }}>
                {(validation as { issues: string[] }).issues.map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            )}
        </div>
      )}

      {pkg && pkg.resources.length > 0 ? (
        <section>
          <h2 style={{ fontSize: 18, marginBottom: 12 }}>
            Published Resources ({pkg.resources.length})
          </h2>
          {pkg.resources.map((res) => (
            <div key={res.resource_id} style={{
              border: '1px solid #1a3a4a', borderRadius: 6,
              padding: '16px 20px', marginBottom: 14, backgroundColor: '#0d1a2a',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <StatusBadge status="published_local_not_active" />
                <span style={{ fontFamily: 'monospace', color: '#666', fontSize: 11 }}>{res.resource_id}</span>
                <span style={{ fontSize: 12, color: '#888' }}>
                  {res.difficulty} · {res.resource_type} · {res.estimated_time_minutes}min
                </span>
              </div>
              <div style={{ marginBottom: 4 }}>
                <strong style={{ color: '#ddd', fontSize: 15 }}>{res.title}</strong>
              </div>
              <div style={{ color: '#888', fontSize: 12, marginBottom: 6 }}>Topic: {res.topic}</div>
              {res.skill_name && (
                <div style={{ color: '#777', fontSize: 12, marginBottom: 8 }}>Skill: {res.skill_name}</div>
              )}
              <div style={{ marginBottom: 10 }}>
                <div style={{ color: '#555', fontSize: 11, marginBottom: 4 }}>Student Prompt</div>
                <div style={{
                  backgroundColor: '#111', border: '1px solid #1a1a1a', borderRadius: 4,
                  padding: '10px 14px', fontSize: 13, color: '#ccc', lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                }}>
                  {res.student_prompt}
                </div>
              </div>
              {res.answer_key && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ color: '#555', fontSize: 11, marginBottom: 4 }}>Answer Key (Teacher Only)</div>
                  <div style={{
                    backgroundColor: '#111', border: '1px dashed #2a2a1a', borderRadius: 4,
                    padding: '8px 12px', fontSize: 12, color: '#aaa',
                  }}>
                    {res.answer_key}
                  </div>
                </div>
              )}
              {res.marking_rubric && res.marking_rubric.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ color: '#555', fontSize: 11, marginBottom: 4 }}>Marking Rubric (Teacher Only)</div>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: '#aaa' }}>
                    {res.marking_rubric.map((r, i) => (
                      <li key={i}>[{r.marks}m] {r.criterion} — <em>{r.guidance}</em></li>
                    ))}
                  </ul>
                </div>
              )}
              {res.provenance && (
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 8 }}>
                  <SafeTag label="gate70b_approved" ok={(res.provenance as { gate70b_approved?: boolean }).gate70b_approved === true} />
                  <SafeTag label="no_raw_source" ok={(res.provenance as { no_raw_source_text_used?: boolean }).no_raw_source_text_used === true} />
                  <SafeTag label="teacher_review" ok={(res.provenance as { teacher_review_required?: boolean }).teacher_review_required === true} />
                </div>
              )}
            </div>
          ))}
        </section>
      ) : (
        <div style={{
          padding: '24px', border: '1px solid #2a2a2a', borderRadius: 6,
          textAlign: 'center', color: '#666', fontSize: 14,
        }}>
          No published resources yet.
          Run Gate 70D scripts to approve and publish the AI bank package.
        </div>
      )}

      <div style={{
        marginTop: 32, padding: '10px 14px', border: '1px solid #1a1a1a',
        borderRadius: 6, backgroundColor: '#0d0d0d', fontSize: 12, color: '#555',
      }}>
        Diagnostic: <a href="/system/ai-bank-published" style={{ color: '#5ab8ff' }}>/system/ai-bank-published</a>
        {' · '}API: <a href="/api/system/ai-bank-published" style={{ color: '#5ab8ff' }}>/api/system/ai-bank-published</a>
        {' · '}No publish button · No active switch · No Supabase sync
      </div>
    </main>
  )
}
