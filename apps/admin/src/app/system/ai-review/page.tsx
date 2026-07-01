import { requireAppRole } from '@/lib/roleAccess'
import { getAiReviewSummary } from '@/lib/aiTeacherReview'

export const dynamic = 'force-dynamic'

function Badge({ label, ok, neutral }: { label: string; ok?: boolean; neutral?: boolean }) {
  const bg = neutral ? '#dbeafe' : ok ? '#d1fae5' : '#fee2e2'
  const fg = neutral ? '#1e40af' : ok ? '#065f46' : '#991b1b'
  return (
    <span
      style={{
        display:         'inline-block',
        padding:         '2px 8px',
        borderRadius:    4,
        fontSize:        12,
        fontWeight:      600,
        backgroundColor: bg,
        color:           fg,
        marginLeft:      8,
      }}
    >
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
      <td style={{ padding: '5px 0', fontFamily: 'monospace', fontSize: 13 }}>
        {value}
      </td>
    </tr>
  )
}

export default async function AiReviewDiagnosticPage() {
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

  const summary = getAiReviewSummary()

  return (
    <main style={{ padding: '2rem', maxWidth: 800, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        AI Review Diagnostic
        <Badge label="Gate 69D" neutral />
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 13 }}>
        AI teacher review queue status. No secrets displayed.
      </p>

      {/* Files */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          File Status
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="Review queue"
              value={<Badge label={summary.queue_exists ? 'EXISTS' : 'MISSING'} ok={summary.queue_exists} />}
            />
            <Row
              label="Decisions file"
              value={<Badge label={summary.decision_file_exists ? 'EXISTS' : 'MISSING'} ok={summary.decision_file_exists} />}
            />
            <Row
              label="Approved candidate bank"
              value={<Badge label={summary.approved_candidates_exists ? 'EXISTS' : 'NOT GENERATED'} ok={summary.approved_candidates_exists} neutral={!summary.approved_candidates_exists} />}
            />
          </tbody>
        </table>
      </section>

      {/* Counts */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Queue Counts
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row label="Total items"      value={<code>{summary.total_items}</code>} />
            <Row label="Pending"          value={<code>{summary.pending_count}</code>} />
            <Row label="Approved"         value={<code>{summary.approved_count}</code>} />
            <Row label="Needs revision"   value={<code>{summary.needs_revision_count}</code>} />
            <Row label="Rejected"         value={<code>{summary.rejected_count}</code>} />
          </tbody>
        </table>
      </section>

      {/* Policy */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Policy
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="auto_publish_enabled"
              value={<Badge label="FALSE — disabled" ok={true} />}
            />
            <Row
              label="supabase_write_performed"
              value={<Badge label="FALSE" ok={true} />}
            />
            <Row
              label="teacher_approval_required"
              value={<Badge label="TRUE — always" ok={true} />}
            />
          </tbody>
        </table>
      </section>

      {/* Scripts */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Gate 69D Scripts
        </h2>
        <pre
          style={{
            background:   '#f3f4f6',
            padding:      '12px 16px',
            borderRadius: 4,
            fontSize:     12,
            overflowX:    'auto',
            lineHeight:   1.7,
          }}
        >
          {[
            '# Build review queue from Gate 69C batch',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_ai_teacher_review_queue_v1.py \\',
            '    data\\ai\\generated_batches\\gate69c_sample_generated_batch_v1.json',
            '',
            '# Apply decisions (approve / needs_revision / reject)',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\apply_ai_teacher_review_decisions_v1.py',
            '',
            '# Run end-to-end test',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate69d_ai_teacher_review_v1.py',
            '',
            '# Build Gate 69D report',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate69d_ai_teacher_review_report_v1.py',
          ].join('\n')}
        </pre>
      </section>

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/api/system/ai-review"     style={{ color: '#3b82f6', marginRight: 16 }}>AI Review API</a>
        <a href="/ai-review"                style={{ color: '#3b82f6', marginRight: 16 }}>Teacher Review UI</a>
        <a href="/system/ai-authoring"      style={{ color: '#3b82f6', marginRight: 16 }}>AI Authoring</a>
        <a href="/system/health"            style={{ color: '#3b82f6' }}>Health</a>
      </p>
    </main>
  )
}
