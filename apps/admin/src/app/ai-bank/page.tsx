import { requireRole } from '@/lib/serverSupabaseAuth'
import { readAiBankItems, readAiReviewQueue, getAiBankSummary } from '@/lib/aiQuestionBank'

export const metadata = { title: 'AI Question Bank' }

function SafetyTag({ label }: { label: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', marginRight: 4,
      backgroundColor: '#1a3a1a', color: '#5aff8a', borderRadius: 4,
      fontSize: 11, fontFamily: 'monospace', border: '1px solid #2d6a2d',
    }}>
      {label}
    </span>
  )
}

function DifficultyBadge({ difficulty }: { difficulty?: string }) {
  const colors: Record<string, string> = {
    easy: '#2d5a2d', medium: '#4a4a1a', hard: '#5a2d1a', very_hard: '#5a1a1a',
  }
  const bg = colors[difficulty ?? ''] ?? '#333'
  return (
    <span style={{
      display: 'inline-block', padding: '2px 6px',
      backgroundColor: bg, color: '#eee', borderRadius: 3, fontSize: 11,
    }}>
      {difficulty ?? 'unknown'}
    </span>
  )
}

function BankCard({ item }: { item: ReturnType<typeof readAiBankItems>[number] }) {
  return (
    <div style={{
      border: '1px solid #2a2a2a', borderRadius: 6, padding: '16px 20px',
      marginBottom: 16, backgroundColor: '#111',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <span style={{ fontFamily: 'monospace', color: '#888', fontSize: 12 }}>{item.bank_id}</span>
        <DifficultyBadge difficulty={item.difficulty} />
        <span style={{ fontSize: 12, color: '#aaa' }}>{item.resource_type}</span>
        {item.dry_run && (
          <span style={{
            backgroundColor: '#1a3a4a', color: '#5ab8ff',
            padding: '1px 6px', borderRadius: 3, fontSize: 11,
          }}>DRY-RUN</span>
        )}
      </div>
      <div style={{ marginBottom: 6 }}>
        <strong style={{ color: '#ddd' }}>{item.topic}</strong>
        {item.subtopic && <span style={{ color: '#888', marginLeft: 8 }}>{item.subtopic}</span>}
      </div>
      {item.skill_name && (
        <div style={{ color: '#aaa', fontSize: 13, marginBottom: 6 }}>
          Skill: {item.skill_name}
        </div>
      )}
      {item.learning_objective && (
        <div style={{ color: '#888', fontSize: 12, marginBottom: 8 }}>
          Objective: {item.learning_objective}
        </div>
      )}
      <div style={{
        backgroundColor: '#0d0d0d', border: '1px solid #222', borderRadius: 4,
        padding: '12px 16px', marginBottom: 10,
        fontFamily: 'Georgia, serif', lineHeight: 1.7, color: '#ccc', fontSize: 14,
        whiteSpace: 'pre-wrap',
      }}>
        {item.generated_text}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
        <SafetyTag label="teacher-review-required" />
        <SafetyTag label="auto-publish=false" />
        <SafetyTag label="supabase-write=false" />
        <SafetyTag label="metadata-only-prompt" />
      </div>
      <div style={{ fontSize: 11, color: '#555', fontFamily: 'monospace' }}>
        provider={item.provider}  model={item.model ?? 'n/a'}  generated={item.generated_at?.slice(0, 10)}
      </div>
    </div>
  )
}

export default async function AiBankPage() {
  await requireRole(['admin'])

  const summary = getAiBankSummary()
  const items   = readAiBankItems()
  const queue   = readAiReviewQueue()

  return (
    <main style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 24, marginBottom: 4 }}>AI Question Bank</h1>
      <p style={{ color: '#888', marginBottom: 24, fontSize: 14 }}>
        Gate 70A — Locally generated AI questions awaiting teacher review.
        No auto-publish. No Supabase sync. Teacher approval required.
      </p>

      <div style={{
        backgroundColor: '#1a2a1a', border: '1px solid #2d5a2d',
        borderRadius: 6, padding: '12px 16px', marginBottom: 24,
      }}>
        <strong style={{ color: '#5aff8a' }}>Gate 70A Active</strong>
        <span style={{ color: '#aaa', marginLeft: 12, fontSize: 13 }}>
          All items have status: generated_needs_teacher_review.
          Teachers must review and approve before any content is published.
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 32 }}>
        {[
          ['Total Items', summary.total_items],
          ['Pending Review', summary.pending_review],
          ['Review Queue', summary.queue_count],
          ['Requests Built', summary.request_count],
        ].map(([label, value]) => (
          <div key={String(label)} style={{
            backgroundColor: '#0d0d0d', border: '1px solid #222',
            borderRadius: 6, padding: '12px 16px', textAlign: 'center',
          }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#eee' }}>{value}</div>
            <div style={{ fontSize: 12, color: '#666' }}>{label}</div>
          </div>
        ))}
      </div>

      {!summary.bank_exists && (
        <div style={{
          border: '1px solid #444', borderRadius: 6, padding: 20,
          backgroundColor: '#111', color: '#aaa', marginBottom: 24,
        }}>
          <strong>No bank items yet.</strong> Run the generation pipeline first:
          <pre style={{ marginTop: 10, fontSize: 12, color: '#888' }}>
            {`.venv-ingest\\Scripts\\python.exe tools\\ai\\build_safe_generation_requests_from_targets_v1.py --subject physics_0625 --limit 3\n.venv-ingest\\Scripts\\python.exe tools\\ai\\run_live_ai_generation_to_bank_v1.py --requests data\\ai\\generation_requests\\ai_safe_generation_requests_v1.json`}
          </pre>
        </div>
      )}

      {queue.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 18, marginBottom: 4 }}>Teacher Review Queue ({queue.length})</h2>
          <p style={{ color: '#888', fontSize: 13, marginBottom: 16 }}>
            Items pending teacher decision. All require explicit approval before publication.
          </p>
          <div style={{
            border: '1px solid #2a2a2a', borderRadius: 6, overflow: 'hidden',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ backgroundColor: '#0d0d0d', color: '#888' }}>
                  <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 500 }}>Bank ID</th>
                  <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 500 }}>Topic</th>
                  <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 500 }}>Difficulty</th>
                  <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 500 }}>Provider</th>
                  <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 500 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((q, i) => (
                  <tr key={q.bank_id} style={{
                    borderTop: '1px solid #1a1a1a',
                    backgroundColor: i % 2 === 0 ? '#111' : '#0d0d0d',
                  }}>
                    <td style={{ padding: '8px 14px', fontFamily: 'monospace', color: '#888', fontSize: 11 }}>
                      {q.bank_id}
                    </td>
                    <td style={{ padding: '8px 14px', color: '#ccc' }}>{q.topic}</td>
                    <td style={{ padding: '8px 14px' }}>
                      <DifficultyBadge difficulty={q.difficulty} />
                    </td>
                    <td style={{ padding: '8px 14px', color: '#888', fontFamily: 'monospace', fontSize: 11 }}>
                      {q.provider}{q.dry_run ? ' (mock)' : ''}
                    </td>
                    <td style={{ padding: '8px 14px' }}>
                      <span style={{
                        backgroundColor: '#1a3a4a', color: '#5ab8ff',
                        padding: '2px 6px', borderRadius: 3, fontSize: 11,
                      }}>
                        {q.review_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {items.length > 0 && (
        <div>
          <h2 style={{ fontSize: 18, marginBottom: 4 }}>Bank Items ({items.length})</h2>
          <p style={{ color: '#888', fontSize: 13, marginBottom: 16 }}>
            All AI-generated content. Status: generated_needs_teacher_review.
          </p>
          {items.map((item) => <BankCard key={item.bank_id} item={item} />)}
        </div>
      )}

      <div style={{
        marginTop: 32, padding: '12px 16px', border: '1px solid #2a2a2a',
        borderRadius: 6, backgroundColor: '#0d0d0d',
      }}>
        <p style={{ margin: 0, color: '#555', fontSize: 12 }}>
          Diagnostic: <a href="/system/ai-bank" style={{ color: '#5ab8ff' }}>/system/ai-bank</a>
          {' · '}API: <a href="/api/system/ai-bank" style={{ color: '#5ab8ff' }}>/api/system/ai-bank</a>
        </p>
      </div>
    </main>
  )
}
