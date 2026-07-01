import { requireRole } from '@/lib/serverSupabaseAuth'
import {
  readAiBankReviewQueue,
  readAiBankReviewDecisions,
  readApprovedAiBankItems,
  readPendingAiBankReviewItems,
  getAiBankReviewSummary,
} from '@/lib/aiBankReview'

export const metadata = { title: 'AI Bank Review' }

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, [string, string]> = {
    pending:                   ['#1a3a4a', '#5ab8ff'],
    approved_pending_package:  ['#1a3a1a', '#5aff8a'],
    needs_revision:            ['#3a3a1a', '#ffd05a'],
    rejected:                  ['#3a1a1a', '#ff5a5a'],
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

function SafeTag({ label }: { label: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 6px', marginRight: 4,
      backgroundColor: '#1a3a1a', color: '#5aff8a', borderRadius: 3,
      fontSize: 10, fontFamily: 'monospace', border: '1px solid #2d6a2d',
    }}>
      {label}
    </span>
  )
}

function Stat({ label, value, color }: { label: string; value: number; color?: string }) {
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

export default async function AiBankReviewPage() {
  await requireRole(['admin'])

  const summary   = getAiBankReviewSummary()
  const queue     = readAiBankReviewQueue()
  const decisions = readAiBankReviewDecisions()
  const approved  = readApprovedAiBankItems()
  const pending   = readPendingAiBankReviewItems()

  const decisionMap = new Map(decisions.map(d => [d.bank_item_id, d]))

  return (
    <main style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 24, marginBottom: 4 }}>AI Bank Review</h1>
      <p style={{ color: '#888', fontSize: 14, marginBottom: 24 }}>
        Gate 70B — Teacher review and approval of AI-generated bank items.
        No auto-publish. No Supabase sync. No AI API calls.
      </p>

      <div style={{
        backgroundColor: '#1a2a1a', border: '1px solid #2d5a2d',
        borderRadius: 6, padding: '10px 16px', marginBottom: 20, fontSize: 13,
      }}>
        <strong style={{ color: '#5aff8a' }}>Gate 70B Active</strong>
        <span style={{ color: '#aaa', marginLeft: 12 }}>
          Use <code style={{ color: '#5ab8ff' }}>/api/ai-bank-review/decision</code> to record decisions.
          Only approved items proceed to Gate 70C.
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, marginBottom: 28 }}>
        <Stat label="Total Queue"    value={summary.total_queue} />
        <Stat label="Approved"       value={summary.approved_count} color="#5aff8a" />
        <Stat label="Needs Revision" value={summary.revision_count} color="#ffd05a" />
        <Stat label="Rejected"       value={summary.rejected_count} color="#ff5a5a" />
        <Stat label="Pending"        value={summary.pending_count}  color="#5ab8ff" />
      </div>

      <div style={{
        backgroundColor: '#0d0d0d', border: '1px solid #1a3a1a',
        borderRadius: 6, padding: '14px 18px', marginBottom: 28,
      }}>
        <p style={{ margin: '0 0 8px', color: '#888', fontSize: 13 }}>
          <strong style={{ color: '#ccc' }}>How to record a decision</strong> — POST to the decision API:
        </p>
        <pre style={{ margin: 0, fontSize: 12, color: '#aaa', overflowX: 'auto' }}>{`POST /api/ai-bank-review/decision
Content-Type: application/json

{
  "bank_item_id": "<bank_id>",
  "review_item_id": "review_<bank_id>",
  "resource_id": "ai_res_70b_<hash>",
  "decision": "approve",
  "review_notes": "Content is accurate and original."
}`}</pre>
        <p style={{ margin: '8px 0 0', color: '#555', fontSize: 11 }}>
          Then run <code style={{ color: '#888' }}>apply_ai_bank_review_decisions_v1.py</code> to apply all decisions.
        </p>
      </div>

      {approved.length > 0 && (
        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 18, marginBottom: 12, color: '#5aff8a' }}>
            Approved Items ({approved.length})
          </h2>
          {approved.map((item) => (
            <div key={item.bank_id} style={{
              border: '1px solid #2d5a2d', borderRadius: 6, padding: '16px 20px',
              marginBottom: 12, backgroundColor: '#0d1a0d',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <StatusBadge status={item.status} />
                <span style={{ fontFamily: 'monospace', color: '#666', fontSize: 11 }}>{item.bank_id}</span>
                <span style={{ fontSize: 12, color: '#888' }}>{item.difficulty} · {item.resource_type}</span>
              </div>
              <div style={{ marginBottom: 4 }}>
                <strong style={{ color: '#ddd' }}>{item.topic}</strong>
                {item.subtopic && <span style={{ color: '#777', marginLeft: 8, fontSize: 13 }}>{item.subtopic}</span>}
              </div>
              {item.skill_name && <div style={{ color: '#999', fontSize: 12, marginBottom: 8 }}>Skill: {item.skill_name}</div>}
              <div style={{ marginBottom: 10 }}>
                <div style={{ color: '#888', fontSize: 11, marginBottom: 4 }}>Student Prompt</div>
                <div style={{
                  backgroundColor: '#111', border: '1px solid #1a1a1a', borderRadius: 4,
                  padding: '10px 14px', fontSize: 13, color: '#ccc', lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                }}>
                  {item.student_prompt}
                </div>
              </div>
              <div style={{ marginBottom: 8 }}>
                <div style={{ color: '#888', fontSize: 11, marginBottom: 4 }}>Answer Key (Teacher Only)</div>
                <div style={{
                  backgroundColor: '#111', border: '1px dashed #2a2a1a', borderRadius: 4,
                  padding: '8px 12px', fontSize: 12, color: '#aaa',
                }}>
                  {item.answer_key}
                </div>
              </div>
              {item.review_notes && (
                <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                  Review notes: {item.review_notes}
                </div>
              )}
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                <SafeTag label="teacher-review=true" />
                <SafeTag label="auto-publish=false" />
                <SafeTag label="supabase=false" />
              </div>
            </div>
          ))}
        </section>
      )}

      <section>
        <h2 style={{ fontSize: 18, marginBottom: 12 }}>
          Review Queue ({queue.length} items)
        </h2>
        {queue.length === 0 && (
          <p style={{ color: '#666', fontSize: 13 }}>
            No items in review queue. Run the Gate 70A generation pipeline first.
          </p>
        )}
        {queue.map((item) => {
          const dec = decisionMap.get(item.bank_id)
          const currentStatus = dec?.decision ?? 'pending'
          return (
            <div key={item.bank_id} style={{
              border: '1px solid #2a2a2a', borderRadius: 6, padding: '14px 18px',
              marginBottom: 12, backgroundColor: '#111',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <StatusBadge status={currentStatus === 'approve' ? 'approved_pending_package' : currentStatus} />
                <span style={{ fontFamily: 'monospace', color: '#666', fontSize: 11 }}>{item.bank_id}</span>
                <span style={{ fontSize: 12, color: '#888' }}>{item.difficulty} · {item.resource_type}</span>
                {item.dry_run && (
                  <span style={{
                    backgroundColor: '#1a2a3a', color: '#5ab8ff',
                    padding: '1px 5px', borderRadius: 3, fontSize: 10,
                  }}>DRY-RUN</span>
                )}
              </div>
              <div style={{ marginBottom: 4 }}>
                <strong style={{ color: '#ddd' }}>{item.topic}</strong>
              </div>
              {item.skill_name && (
                <div style={{ color: '#999', fontSize: 12, marginBottom: 8 }}>Skill: {item.skill_name}</div>
              )}
              <div style={{
                backgroundColor: '#0d0d0d', border: '1px solid #1a1a1a', borderRadius: 4,
                padding: '10px 14px', fontSize: 13, color: '#ccc', lineHeight: 1.6,
                whiteSpace: 'pre-wrap', marginBottom: 8,
              }}>
                {item.generated_text}
              </div>
              <div style={{ fontSize: 11, color: '#555', fontFamily: 'monospace' }}>
                provider={item.provider} · model={item.model} · generated={item.generated_at?.slice(0, 10)}
              </div>
              {dec && (
                <div style={{ marginTop: 8, fontSize: 12, color: '#888' }}>
                  Decision: <strong style={{ color: '#ccc' }}>{dec.decision}</strong>
                  {dec.review_notes && <span style={{ marginLeft: 8, color: '#666' }}>{dec.review_notes}</span>}
                </div>
              )}
            </div>
          )
        })}
      </section>

      <div style={{
        marginTop: 32, padding: '10px 14px', border: '1px solid #1a1a1a',
        borderRadius: 6, backgroundColor: '#0d0d0d', fontSize: 12, color: '#555',
      }}>
        Diagnostic: <a href="/system/ai-bank-review" style={{ color: '#5ab8ff' }}>/system/ai-bank-review</a>
        {' · '}API status: <a href="/api/system/ai-bank-review" style={{ color: '#5ab8ff' }}>/api/system/ai-bank-review</a>
        {' · '}No publish · No Supabase sync · No AI API
      </div>
    </main>
  )
}
