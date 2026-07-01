import { requireRole } from '@/lib/serverSupabaseAuth'
import { getAiBankReviewSummary } from '@/lib/aiBankReview'
import fs from 'fs'
import path from 'path'

export const metadata = { title: 'AI Bank Review Diagnostics' }

const ROOT = path.resolve(process.cwd(), '../..')

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', marginRight: 6, marginBottom: 6,
      backgroundColor: ok ? '#1a3a1a' : '#3a1a1a',
      color: ok ? '#5aff8a' : '#ff5a5a',
      borderRadius: 4, fontSize: 11, fontFamily: 'monospace',
      border: `1px solid ${ok ? '#2d6a2d' : '#6a2d2d'}`,
    }}>
      {ok ? 'OK' : 'MISSING'} {label}
    </span>
  )
}

function BoolBadge({ val, label }: { val: boolean; label: string }) {
  const expected = !label.includes('enabled') && !label.includes('performed') && !label.includes('called')
  const ok = label.includes('required') ? val === true
    : val === false
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', marginRight: 6,
      backgroundColor: ok ? '#1a3a1a' : '#3a1a1a',
      color: ok ? '#5aff8a' : '#ff5a5a',
      borderRadius: 4, fontSize: 11, fontFamily: 'monospace',
      border: `1px solid ${ok ? '#2d6a2d' : '#6a2d2d'}`,
    }}>
      {label}={String(val)}
    </span>
  )
}

function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <tr>
      <td style={{ padding: '6px 12px', color: '#888', fontSize: 13, width: 240 }}>{label}</td>
      <td style={{ padding: '6px 12px', color: '#ccc', fontSize: 13, fontFamily: mono ? 'monospace' : undefined }}>
        {value}
      </td>
    </tr>
  )
}

function fileExists(rel: string) {
  return fs.existsSync(path.join(ROOT, rel))
}

export default async function AiBankReviewSystemPage() {
  await requireRole(['admin'])

  const summary = getAiBankReviewSummary()

  const files: [string, string][] = [
    ['tools/ai/apply_ai_bank_review_decisions_v1.py',          'Apply decisions script'],
    ['tools/ai/validate_approved_ai_bank_items_v1.py',         'Validate approved script'],
    ['apps/admin/src/lib/aiBankReview.ts',                     'aiBankReview.ts library'],
    ['apps/admin/src/app/ai-bank-review/page.tsx',             '/ai-bank-review page'],
    ['apps/admin/src/app/api/ai-bank-review/decision/route.ts', '/api/ai-bank-review/decision'],
    ['apps/admin/src/app/system/ai-bank-review/page.tsx',      '/system/ai-bank-review page'],
    ['apps/admin/src/app/api/system/ai-bank-review/route.ts',  '/api/system/ai-bank-review'],
    ['data/ai/question_bank/ai_generated_question_bank_v1.json', 'Question bank (Gate 70A)'],
    ['data/ai/teacher_review/ai_teacher_review_queue_v1.json',   'Review queue (Gate 70A)'],
    ['data/ai/review/gate70b_ai_bank_review_decisions_v1.json',  'Decisions file'],
    ['data/ai/approved/gate70b_approved_ai_bank_items_v1.json',  'Approved items'],
    ['data/ai/revision/gate70b_ai_bank_revision_items_v1.json',  'Revision items'],
    ['data/ai/rejected/gate70b_rejected_ai_bank_items_v1.json',  'Rejected items'],
    ['data/diagnostics/gate70b_ai_bank_review_apply_report_v1.json',       'Apply report'],
    ['data/diagnostics/gate70b_approved_ai_bank_items_validation_report_v1.json', 'Validation report'],
    ['data/diagnostics/gate70b_ai_bank_review_test_report_v1.json',         'Test report'],
  ]

  return (
    <main style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 24, marginBottom: 4 }}>AI Bank Review Diagnostics</h1>
      <p style={{ color: '#888', fontSize: 14, marginBottom: 24 }}>
        Gate 70B — AI Bank Review and Approval. System diagnostic view.
      </p>

      <div style={{
        backgroundColor: '#1a2a1a', border: '1px solid #2d5a2d',
        borderRadius: 6, padding: '10px 16px', marginBottom: 24, fontSize: 13,
      }}>
        <strong style={{ color: '#5aff8a' }}>Safety</strong>
        <span style={{ color: '#aaa', marginLeft: 12 }}>
          teacher_review_required=true · auto_publish=false · supabase_write=false · ai_api_called=false ·
          No AI API calls · No Supabase writes · No Cambridge raw text
        </span>
      </div>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Review Summary</h2>
        <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: '#111', borderRadius: 6 }}>
          <tbody>
            <Row label="Total queue"     value={summary.total_queue} />
            <Row label="Approved"        value={summary.approved_count} />
            <Row label="Needs revision"  value={summary.revision_count} />
            <Row label="Rejected"        value={summary.rejected_count} />
            <Row label="Pending"         value={summary.pending_count} />
            <Row label="Decisions saved" value={summary.decision_count} />
            <Row label="Apply report"    value={summary.apply_report_status ?? '—'} mono />
            <Row label="Validation"      value={
              summary.validation_passed === null ? 'not run'
                : summary.validation_passed ? 'passed' : 'failed'
            } mono />
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Policy</h2>
        <div>
          <BoolBadge val={summary.teacher_review_required} label="teacher_review_required" />
          <BoolBadge val={summary.auto_publish_enabled}    label="auto_publish_enabled" />
          <BoolBadge val={summary.supabase_write_performed} label="supabase_write_performed" />
          <BoolBadge val={summary.ai_api_called}           label="ai_api_called" />
        </div>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Files</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {files.map(([rel, label]) => (
            <Badge key={rel} ok={fileExists(rel)} label={label} />
          ))}
        </div>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Scripts</h2>
        <div style={{ backgroundColor: '#0d0d0d', border: '1px solid #222', borderRadius: 6, padding: 16 }}>
          {[
            ['A. Gate 70A tests', '.venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate70a_live_ai_generation_to_bank_v1.py'],
            ['B. Gate 70B tests', '.venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate70b_ai_bank_review_v1.py'],
            ['C. Apply decisions', '.venv-ingest\\Scripts\\python.exe tools\\ai\\apply_ai_bank_review_decisions_v1.py'],
            ['D. Validate approved', '.venv-ingest\\Scripts\\python.exe tools\\ai\\validate_approved_ai_bank_items_v1.py data\\ai\\approved\\gate70b_approved_ai_bank_items_v1.json'],
            ['E. Gate report', '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate70b_ai_bank_review_report_v1.py'],
          ].map(([label, cmd]) => (
            <div key={label} style={{ marginBottom: 10 }}>
              <div style={{ color: '#777', fontSize: 11, marginBottom: 2 }}>{label}</div>
              <code style={{
                display: 'block', backgroundColor: '#111', border: '1px solid #1a1a1a',
                padding: '6px 10px', borderRadius: 4, fontSize: 12, color: '#aaa',
              }}>
                {cmd}
              </code>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Links</h2>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {[
            ['/ai-bank-review',          'AI Bank Review'],
            ['/ai-bank',                 'AI Bank'],
            ['/api/system/ai-bank-review', 'API Status'],
            ['/system/ai-bank',          'AI Bank Diag'],
            ['/system/health',           'Health'],
          ].map(([href, label]) => (
            <a key={href} href={href} style={{
              color: '#5ab8ff', fontSize: 13, textDecoration: 'none',
              border: '1px solid #1a3a4a', padding: '4px 10px', borderRadius: 4,
            }}>
              {label}
            </a>
          ))}
        </div>
      </section>
    </main>
  )
}
