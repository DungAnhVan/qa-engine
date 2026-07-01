import { requireAppRole } from '@/lib/roleAccess'
import fs from 'fs'
import path from 'path'

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

export default async function AIAuthoringPage() {
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

  const provider        = process.env.QA_AI_PROVIDER        ?? 'mock'
  const dryRunRaw       = process.env.QA_AI_DRY_RUN         ?? 'true'
  const copyrightRaw    = process.env.QA_AI_COPYRIGHT_STRICT ?? 'true'
  const nodeEnv         = process.env.NODE_ENV ?? 'development'
  const isProduction    = nodeEnv === 'production'

  const dryRun          = dryRunRaw.trim().toLowerCase() !== 'false'
  const copyrightStrict = copyrightRaw.trim().toLowerCase() !== 'false'

  // Filesystem check for sample batch (server-side only)
  let sampleBatchExists = false
  let validationReportStatus = 'not_run'
  try {
    const batchPath = path.join(process.cwd(), '..', '..', 'data', 'ai',
      'generated_batches', 'gate69c_sample_generated_batch_v1.json')
    sampleBatchExists = fs.existsSync(batchPath)

    const validationPath = path.join(process.cwd(), '..', '..', 'data', 'diagnostics',
      'ai_generated_batch_validation_report_v1.json')
    if (fs.existsSync(validationPath)) {
      const raw = fs.readFileSync(validationPath, 'utf-8')
      const parsed = JSON.parse(raw)
      validationReportStatus = parsed.status ?? 'unknown'
    }
  } catch {
    // Filesystem access may fail in some deployment environments
  }

  return (
    <main style={{ padding: '2rem', maxWidth: 800, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        AI Authoring
        <Badge label="DRAFT ONLY" ok={false} neutral />
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 13 }}>
        Gate 69C — AI content factory diagnostic. No secrets displayed.
      </p>

      {/* Warning banner */}
      <div
        style={{
          marginBottom: 24,
          padding:      '12px 16px',
          background:   '#fef3c7',
          borderRadius: 6,
          borderLeft:   '4px solid #f59e0b',
          fontSize:     13,
          color:        '#92400e',
        }}
      >
        <strong>AI authoring is draft-only.</strong> All generated resources require
        teacher approval before publishing. Auto-publish is disabled.
        Generated content must not copy Cambridge source text, mark schemes, or diagrams.
      </div>

      {/* AI provider config */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          AI Provider Configuration
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="QA_AI_PROVIDER"
              value={
                <>
                  <code>{provider}</code>
                  <Badge label={provider} ok={provider !== 'mock'} neutral={provider === 'mock'} />
                </>
              }
            />
            <Row
              label="QA_AI_DRY_RUN"
              value={
                <>
                  <code>{dryRunRaw}</code>
                  <Badge
                    label={dryRun ? 'dry-run (safe)' : 'LIVE — real API calls'}
                    ok={dryRun}
                  />
                </>
              }
            />
            <Row
              label="QA_AI_COPYRIGHT_STRICT"
              value={
                <>
                  <code>{copyrightRaw}</code>
                  <Badge
                    label={copyrightStrict ? 'strict (correct)' : 'OFF — WARNING'}
                    ok={copyrightStrict}
                  />
                </>
              }
            />
            <Row
              label="NODE_ENV"
              value={
                <>
                  <code>{nodeEnv}</code>
                  <Badge label={isProduction ? 'production' : 'development'} ok={isProduction} neutral={!isProduction} />
                </>
              }
            />
          </tbody>
        </table>
      </section>

      {/* Batch status */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Sample Batch
        </h2>
        <table style={{ borderCollapse: 'collapse' }}>
          <tbody>
            <Row
              label="Sample batch exists"
              value={
                <Badge
                  label={sampleBatchExists ? 'YES' : 'NOT GENERATED'}
                  ok={sampleBatchExists}
                />
              }
            />
            <Row
              label="Validation report"
              value={
                <Badge
                  label={validationReportStatus}
                  ok={validationReportStatus === 'passed'}
                  neutral={validationReportStatus === 'not_run'}
                />
              }
            />
            <Row
              label="Teacher approval required"
              value={<Badge label="YES — always" ok={true} />}
            />
            <Row
              label="Auto-publish"
              value={<Badge label="DISABLED" ok={true} />}
            />
          </tbody>
        </table>
        {!sampleBatchExists && (
          <p style={{ fontSize: 12, color: '#6b7280', marginTop: 8 }}>
            Run{' '}
            <code>tools/ai/run_gate69c_sample_ai_authoring_v1.py</code>{' '}
            to generate the sample batch.
          </p>
        )}
      </section>

      {/* Safety rules */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Content Safety Rules
        </h2>
        <ul style={{ fontSize: 13, color: '#374151', paddingLeft: 20, lineHeight: 1.9 }}>
          <li>AI input uses safe metadata only (topic, skill, difficulty — no raw text)</li>
          <li>Raw Cambridge question text is blocked from all AI prompts</li>
          <li>Mark scheme text is blocked from all AI prompts</li>
          <li>PDF file references are blocked from all AI prompts</li>
          <li>Generated output is scanned for copyright risk patterns</li>
          <li>All drafts require teacher review before any use</li>
          <li><code>OPENAI_API_KEY</code> and <code>ANTHROPIC_API_KEY</code> are server/CLI only</li>
        </ul>
      </section>

      {/* Gate 69C flow */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Gate 69C Scripts
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
            '# Generate sample batch (mock provider)',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\run_gate69c_sample_ai_authoring_v1.py',
            '',
            '# Validate generated batch',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\validate_ai_generated_batch_v1.py \\',
            '    data\\ai\\generated_batches\\gate69c_sample_generated_batch_v1.json',
            '',
            '# Gate 69C report',
            '.venv-ingest\\Scripts\\python.exe tools\\ai\\build_gate69c_ai_authoring_report_v1.py',
          ].join('\n')}
        </pre>
      </section>

      {/* Navigation */}
      <p style={{ fontSize: 13, color: '#6b7280', marginTop: 24 }}>
        <a href="/api/system/ai-authoring"      style={{ color: '#3b82f6', marginRight: 16 }}>AI Authoring API</a>
        <a href="/system/credential-safety"     style={{ color: '#3b82f6', marginRight: 16 }}>Cred Safety</a>
        <a href="/system/health"                style={{ color: '#3b82f6', marginRight: 16 }}>Health</a>
        <a href="/system/readiness"             style={{ color: '#3b82f6' }}>Readiness</a>
      </p>
    </main>
  )
}
