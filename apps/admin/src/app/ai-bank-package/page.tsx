import { requireRole } from '@/lib/serverSupabaseAuth'
import {
  readPackageCandidate,
  readPackageValidationReport,
  getPackageSummary,
} from '@/lib/aiBankPackageCandidate'

export const metadata = { title: 'AI Bank Package' }

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, [string, string]> = {
    draft_package_candidate: ['#1a2a3a', '#5ab8ff'],
    passed:    ['#1a3a1a', '#5aff8a'],
    valid:     ['#1a3a1a', '#5aff8a'],
    not_built: ['#2a2a2a', '#888'],
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
      <div style={{ fontSize: 26, fontWeight: 700, color: color ?? '#eee' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#555', marginTop: 2 }}>{label}</div>
    </div>
  )
}

export default async function AiBankPackagePage() {
  await requireRole(['admin'])

  const summary    = getPackageSummary()
  const pkg        = readPackageCandidate()
  const validation = readPackageValidationReport() as Record<string, unknown> | null

  return (
    <main style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 24, marginBottom: 4 }}>AI Bank Package Candidate</h1>
      <p style={{ color: '#888', fontSize: 14, marginBottom: 24 }}>
        Gate 70C — Package candidate built from Gate 70B approved items.
        No auto-publish. No Supabase write. Teacher final publish required.
      </p>

      <div style={{
        backgroundColor: '#1a2a1a', border: '1px solid #2d5a2d',
        borderRadius: 6, padding: '10px 16px', marginBottom: 20, fontSize: 13,
      }}>
        <strong style={{ color: '#5aff8a' }}>Gate 70C — Draft Package Candidate</strong>
        <span style={{ color: '#aaa', marginLeft: 12 }}>
          Only Gate 70B approved items are included. Ready for Gate 70D teacher publish.
        </span>
      </div>

      <div style={{
        backgroundColor: '#1a1a0d', border: '1px solid #3a3a1a',
        borderRadius: 6, padding: '10px 16px', marginBottom: 20, fontSize: 13,
      }}>
        <strong style={{ color: '#ffd05a' }}>Teacher Action Required</strong>
        <span style={{ color: '#aaa', marginLeft: 12 }}>
          <code>teacher_final_publish_required = true</code>. This package is NOT published.
          A teacher must explicitly approve each resource before it reaches students.
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 28 }}>
        <Stat label="Resources"  value={summary.resourceCount} />
        <Stat label="Status"     value={pkg?.status ?? 'not_built'} />
        <Stat label="Validation" value={summary.validationPassed === true ? 'valid' : summary.validationPassed === false ? 'issues' : 'pending'} color={summary.validationPassed === true ? '#5aff8a' : '#ffd05a'} />
        <Stat label="Build"      value={summary.buildStatus ?? 'pending'} color={summary.buildStatus === 'passed' ? '#5aff8a' : '#ffd05a'} />
      </div>

      {pkg && (
        <div style={{
          marginBottom: 24, padding: '14px 18px', border: '1px solid #1a3a4a',
          borderRadius: 6, backgroundColor: '#0d1a2a', fontSize: 13,
        }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
            <SafeTag label={`teacher_final_publish_required=${pkg.teacher_final_publish_required}`} ok={pkg.teacher_final_publish_required} />
            <SafeTag label={`auto_publish_enabled=${pkg.auto_publish_enabled}`} ok={!pkg.auto_publish_enabled} />
            <SafeTag label={`supabase_write_performed=${pkg.supabase_write_performed}`} ok={!pkg.supabase_write_performed} />
            <SafeTag label={`ai_api_called=${pkg.ai_api_called}`} ok={!pkg.ai_api_called} />
          </div>
          <div style={{ fontSize: 11, color: '#555', fontFamily: 'monospace' }}>
            id={pkg.package_candidate_id} · v={pkg.version} · created={pkg.created_at?.slice(0, 10)}
          </div>
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
          {Array.isArray((validation as { issues?: string[] }).issues) && (validation as { issues: string[] }).issues.length > 0 && (
            <ul style={{ margin: '8px 0 0', paddingLeft: 18, color: '#ff5a5a', fontSize: 12 }}>
              {(validation as { issues: string[] }).issues.map((issue: string, i: number) => (
                <li key={i}>{issue}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {pkg && pkg.resources.length > 0 && (
        <section>
          <h2 style={{ fontSize: 18, marginBottom: 12 }}>
            Package Resources ({pkg.resources.length})
          </h2>
          {pkg.resources.map((res) => (
            <div key={res.resource_id} style={{
              border: '1px solid #1a3a4a', borderRadius: 6,
              padding: '16px 20px', marginBottom: 14, backgroundColor: '#0d1a2a',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <StatusBadge status="draft_package_candidate" />
                <span style={{ fontFamily: 'monospace', color: '#666', fontSize: 11 }}>{res.resource_id}</span>
                <span style={{ fontSize: 12, color: '#888' }}>{res.difficulty} · {res.resource_type} · {res.estimated_time_minutes}min</span>
              </div>
              <div style={{ marginBottom: 4 }}>
                <strong style={{ color: '#ddd', fontSize: 15 }}>{res.title}</strong>
              </div>
              <div style={{ color: '#888', fontSize: 12, marginBottom: 10 }}>
                Topic: {res.topic}
              </div>
              <div style={{ marginBottom: 10 }}>
                <div style={{ color: '#555', fontSize: 11, marginBottom: 4 }}>Instructions</div>
                <div style={{ fontSize: 13, color: '#aaa' }}>{res.student_instructions}</div>
              </div>
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
              {res.provenance && (
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 8 }}>
                  <SafeTag label="gate70b_approved" ok={(res.provenance as { gate70b_approved?: boolean }).gate70b_approved === true} />
                  <SafeTag label="no_raw_source_text" ok={(res.provenance as { no_raw_source_text_used?: boolean }).no_raw_source_text_used === true} />
                  <SafeTag label="teacher_review_required" ok={(res.provenance as { teacher_review_required?: boolean }).teacher_review_required === true} />
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {!pkg && (
        <div style={{
          padding: '24px', border: '1px solid #2a2a2a', borderRadius: 6,
          textAlign: 'center', color: '#666', fontSize: 14,
        }}>
          Package candidate not yet built.
          Run <code style={{ color: '#888' }}>build_gate70c_ai_bank_package_candidate_v1.py</code> to create it.
        </div>
      )}

      <div style={{
        marginTop: 32, padding: '10px 14px', border: '1px solid #1a1a1a',
        borderRadius: 6, backgroundColor: '#0d0d0d', fontSize: 12, color: '#555',
      }}>
        Diagnostic: <a href="/system/ai-bank-package" style={{ color: '#5ab8ff' }}>/system/ai-bank-package</a>
        {' · '}API: <a href="/api/system/ai-bank-package" style={{ color: '#5ab8ff' }}>/api/system/ai-bank-package</a>
        {' · '}No publish · No Supabase · No AI API
      </div>
    </main>
  )
}
