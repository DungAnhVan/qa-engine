import { requireRole } from '@/lib/serverSupabaseAuth'
import { getAiBankSummary } from '@/lib/aiQuestionBank'
import fs from 'fs'
import path from 'path'

export const metadata = { title: 'AI Bank Diagnostics' }

const ROOT = path.resolve(process.cwd(), '../..')

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px',
      backgroundColor: ok ? '#1a3a1a' : '#3a1a1a',
      color: ok ? '#5aff8a' : '#ff5a5a',
      borderRadius: 4, fontSize: 11, fontFamily: 'monospace',
      border: `1px solid ${ok ? '#2d6a2d' : '#6a2d2d'}`,
    }}>
      {ok ? 'OK' : 'MISSING'} {label}
    </span>
  )
}

function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <tr>
      <td style={{ padding: '6px 12px', color: '#888', fontSize: 13, width: 200 }}>{label}</td>
      <td style={{
        padding: '6px 12px', color: '#ccc', fontSize: 13,
        fontFamily: mono ? 'monospace' : undefined,
      }}>{value}</td>
    </tr>
  )
}

function fileExists(rel: string) {
  return fs.existsSync(path.join(ROOT, rel))
}

export default async function AiBankSystemPage() {
  await requireRole(['admin'])

  const summary = getAiBankSummary()

  const files = [
    ['tools/ai/build_safe_generation_requests_from_targets_v1.py', 'Build requests script'],
    ['tools/ai/run_live_ai_generation_to_bank_v1.py',              'Run generation script'],
    ['tools/ai/validate_ai_question_bank_v1.py',                   'Validate bank script'],
    ['tools/ai/build_teacher_review_queue_from_ai_bank_v1.py',     'Build review queue script'],
    ['tools/ai/test_gate70a_live_ai_generation_to_bank_v1.py',     'Test suite'],
    ['tools/ai/build_gate70a_live_ai_generation_to_bank_report_v1.py', 'Gate report builder'],
    ['data/ai/generation_requests/ai_safe_generation_requests_v1.json', 'Generation requests'],
    ['data/ai/question_bank/ai_generated_question_bank_v1.json',   'Question bank'],
    ['data/ai/teacher_review/ai_teacher_review_queue_v1.json',     'Teacher review queue'],
    ['data/diagnostics/ai_question_bank_validation_v1.json',       'Validation report'],
    ['data/diagnostics/gate70a_live_ai_generation_to_bank_report_v1.json', 'Gate 70A report'],
  ]

  return (
    <main style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 24, marginBottom: 4 }}>AI Bank Diagnostics</h1>
      <p style={{ color: '#888', marginBottom: 24, fontSize: 14 }}>
        Gate 70A — Live AI Question Generation to Bank v1. System diagnostic view.
      </p>

      <div style={{
        backgroundColor: '#1a2a1a', border: '1px solid #2d5a2d',
        borderRadius: 6, padding: '12px 16px', marginBottom: 24, fontSize: 13,
      }}>
        <strong style={{ color: '#5aff8a' }}>Safety</strong>
        <span style={{ color: '#aaa', marginLeft: 12 }}>
          teacher_review_required=true · auto_publish=false · supabase_write=false ·
          metadata-only prompts · no raw Cambridge text · no API keys in bank
        </span>
      </div>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Bank Status</h2>
        <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: '#111', borderRadius: 6 }}>
          <tbody>
            <Row label="Bank exists"             value={summary.bank_exists ? 'Yes' : 'No'} />
            <Row label="Total items"             value={summary.total_items} />
            <Row label="Pending review"          value={summary.pending_review} />
            <Row label="Queue count"             value={summary.queue_count} />
            <Row label="Requests built"          value={summary.request_count} />
            <Row label="teacher_review_required" value={String(summary.teacher_review_required)} mono />
            <Row label="auto_publish_enabled"    value={String(summary.auto_publish_enabled)} mono />
            <Row label="supabase_write_performed" value={String(summary.supabase_write_performed)} mono />
            <Row label="validation_valid"        value={summary.validation_valid === null ? 'not_run' : String(summary.validation_valid)} mono />
            <Row label="updated_at"              value={summary.updated_at ?? '—'} mono />
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Files</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {files.map(([rel, label]) => (
            <Badge key={rel} ok={fileExists(rel)} label={label} />
          ))}
        </div>
      </section>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Scripts</h2>
        <div style={{ backgroundColor: '#0d0d0d', border: '1px solid #222', borderRadius: 6, padding: 16 }}>
          <p style={{ color: '#888', fontSize: 12, margin: '0 0 12px' }}>Run in order:</p>
          {[
            ['A. Verify AI env', '.venv-ingest\\Scripts\\python.exe tools\\ai\\verify_ai_env_v1.py'],
            ['B. Build safe requests', '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_safe_generation_requests_from_targets_v1.py --subject physics_0625 --limit 3'],
            ['C. Dry-run generation', '.venv-ingest\\Scripts\\python.exe tools\\ai\\run_live_ai_generation_to_bank_v1.py --requests data\\ai\\generation_requests\\ai_safe_generation_requests_v1.json --batch-id gate70a_live_ai_batch_v1 --limit 3'],
            ['D. Validate bank', '.venv-ingest\\Scripts\\python.exe tools\\ai\\validate_ai_question_bank_v1.py'],
            ['E. Build review queue', '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_teacher_review_queue_from_ai_bank_v1.py'],
            ['F. Run tests', '.venv-ingest\\Scripts\\python.exe tools\\ai\\test_gate70a_live_ai_generation_to_bank_v1.py'],
            ['G. Gate report', '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate70a_live_ai_generation_to_bank_report_v1.py'],
            ['H. Build admin', 'cd apps/admin && npm run build'],
          ].map(([label, cmd]) => (
            <div key={label} style={{ marginBottom: 10 }}>
              <div style={{ color: '#888', fontSize: 11, marginBottom: 2 }}>{label}</div>
              <code style={{
                display: 'block', backgroundColor: '#111', border: '1px solid #1a1a1a',
                padding: '6px 10px', borderRadius: 4, fontSize: 12, color: '#aaa',
                overflowX: 'auto',
              }}>
                {cmd}
              </code>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Links</h2>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {[
            ['/ai-bank', 'AI Bank'],
            ['/api/system/ai-bank', 'API'],
            ['/system/ai-published', 'AI Published Diag'],
            ['/system/ai-supabase', 'AI Supabase Diag'],
            ['/system/health', 'Health'],
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
