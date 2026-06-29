import type { Metadata } from 'next'
import {
  getLatestStudentResultReport,
  type SkillGap,
  type Strength,
  type ReviewQueueItem,
  type ResubmissionQueueItem,
  type TopicSummary,
} from '@/lib/studentResults'

export const metadata: Metadata = { title: 'Results' }
export const dynamic = 'force-dynamic'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pctDisplay(accuracy: number | null | undefined): string {
  if (accuracy == null) return '—'
  return `${Math.round(accuracy * 100)}%`
}

function SevBadge({ sev }: { sev: string }) {
  const cls =
    sev === 'high'   ? 'result-sev-badge high'
    : sev === 'low'  ? 'result-sev-badge low'
    :                  'result-sev-badge medium'
  return <span className={cls}>{sev}</span>
}

function AccCell({ accuracy }: { accuracy: number | null | undefined }) {
  if (accuracy == null) return <span style={{ color: 'var(--text-muted)' }}>—</span>
  const pct = Math.round(accuracy * 100)
  const cls = pct >= 70 ? 'result-acc-good' : 'result-acc-bad'
  return <span className={cls}>{pct}%</span>
}

function VersionBadge({ version }: { version: string }) {
  const color = version === 'v2' ? 'var(--success)' : 'var(--text-muted)'
  return (
    <span
      style={{
        display: 'inline-block',
        fontSize: '0.7rem',
        fontWeight: 700,
        padding: '2px 9px',
        borderRadius: 999,
        background: color,
        color: '#fff',
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        verticalAlign: 'middle',
        marginLeft: 8,
      }}
    >
      {version}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Section wrapper
// ---------------------------------------------------------------------------

function ResultSection({
  title,
  count,
  children,
}: {
  title: string
  count?: number
  children: React.ReactNode
}) {
  const heading = count !== undefined ? `${title} (${count})` : title
  return (
    <div className="result-section">
      <div className="result-section-header">{heading}</div>
      <div className="result-section-body">{children}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Topic table — supports v1 + v2 schemas
// ---------------------------------------------------------------------------

function TopicTable({ topics, isV2 }: { topics: TopicSummary[]; isV2: boolean }) {
  if (topics.length === 0) {
    return <div className="learn-empty-hint" style={{ padding: '20px 0' }}>No topic data yet.</div>
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Topic</th>
            <th style={{ textAlign: 'center' }}>Attempts</th>
            <th style={{ textAlign: 'center' }}>Auto</th>
            {isV2 && <th style={{ textAlign: 'center' }}>Reviewed</th>}
            {isV2 && <th style={{ textAlign: 'center' }}>Pending</th>}
            <th style={{ textAlign: 'center' }}>Correct</th>
            <th style={{ textAlign: 'center' }}>Incorrect</th>
            {isV2 && <th style={{ textAlign: 'center' }}>Partial</th>}
            {isV2 && <th style={{ textAlign: 'center' }}>Resub</th>}
            {!isV2 && <th style={{ textAlign: 'center' }}>Review</th>}
            <th style={{ textAlign: 'center' }}>Accuracy</th>
          </tr>
        </thead>
        <tbody>
          {topics.map((t) => (
            <tr key={t.topic}>
              <td style={{ fontWeight: 500 }}>{t.topic}</td>
              <td style={{ textAlign: 'center' }}>{t.attempt_count}</td>
              <td style={{ textAlign: 'center' }}>{t.auto_marked_count}</td>
              {isV2 && (
                <td style={{ textAlign: 'center' }}>{t.teacher_reviewed_count ?? 0}</td>
              )}
              {isV2 && (
                <td style={{ textAlign: 'center' }}>
                  {(t.pending_teacher_review_count ?? 0) > 0 ? (
                    <span style={{ color: 'var(--warning, #d69e2e)', fontWeight: 600 }}>
                      {t.pending_teacher_review_count}
                    </span>
                  ) : (
                    t.pending_teacher_review_count ?? 0
                  )}
                </td>
              )}
              <td style={{ textAlign: 'center', color: 'var(--success)', fontWeight: 600 }}>
                {t.correct_count}
              </td>
              <td style={{ textAlign: 'center', color: t.incorrect_count > 0 ? 'var(--error)' : undefined }}>
                {t.incorrect_count}
              </td>
              {isV2 && (
                <td style={{ textAlign: 'center' }}>{t.partially_correct_count ?? 0}</td>
              )}
              {isV2 && (
                <td style={{ textAlign: 'center' }}>
                  {(t.needs_resubmission_count ?? 0) > 0 ? (
                    <span style={{ color: '#d97706', fontWeight: 600 }}>
                      {t.needs_resubmission_count}
                    </span>
                  ) : (
                    0
                  )}
                </td>
              )}
              {!isV2 && (
                <td style={{ textAlign: 'center' }}>{t.teacher_review_required_count ?? 0}</td>
              )}
              <td style={{ textAlign: 'center' }}>
                <AccCell accuracy={t.accuracy} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Strengths
// ---------------------------------------------------------------------------

function StrengthCards({ strengths }: { strengths: Strength[] }) {
  if (strengths.length === 0) {
    return (
      <div className="learn-empty-hint" style={{ padding: '16px 0' }}>
        No confirmed strengths yet. Complete more attempts to build your profile.
      </div>
    )
  }
  return (
    <div className="result-card-list">
      {strengths.map((s, i) => (
        <div key={i} className="result-strength-card">
          <div className="result-card-title">{s.topic}</div>
          <div className="result-card-meta">
            {s.skill_type} &middot; <em>{s.skill_name}</em>
          </div>
          <div className="result-card-body">{s.evidence}</div>
          {s.note && <div className="result-card-note">{s.note}</div>}
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Skill Gaps
// ---------------------------------------------------------------------------

function GapCards({ gaps }: { gaps: SkillGap[] }) {
  if (gaps.length === 0) {
    return (
      <div className="learn-empty-hint" style={{ padding: '16px 0', color: 'var(--success)' }}>
        No skill gaps identified. Keep practising to maintain accuracy.
      </div>
    )
  }
  return (
    <div className="result-card-list">
      {gaps.map((g) => (
        <div key={g.gap_id} className={`result-gap-card ${g.severity}`}>
          <div className="result-gap-header">
            <span className="result-card-title">{g.topic}</span>
            <SevBadge sev={g.severity} />
          </div>
          <div className="result-card-meta">
            {g.skill_type} &middot; {g.difficulty} &middot;{' '}
            <em>{g.reason.replace(/_/g, ' ')}</em>
          </div>
          <div className="result-card-body">{g.evidence}</div>
          <div className="result-gap-action">
            Recommendation: {g.recommended_action}
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Resubmission Queue (v2 only)
// ---------------------------------------------------------------------------

function ResubmissionQueueCards({ items }: { items: ResubmissionQueueItem[] }) {
  if (items.length === 0) {
    return (
      <div className="result-resolved-card">
        No items require resubmission.
      </div>
    )
  }
  return (
    <div className="result-card-list">
      {items.map((q) => {
        const redoUrl =
          `/learn/practice?resource_id=${encodeURIComponent(q.resource_id)}` +
          `&parent_attempt_id=${encodeURIComponent(q.attempt_id)}` +
          `&mode=resubmission`
        return (
          <div key={q.attempt_id} className="result-resub-card">
            <div className="result-resub-header">
              <span className="result-card-title">{q.topic}</span>
              <span className="result-resub-badge">Needs Resubmission</span>
            </div>
            <div className="result-card-meta">
              {q.resource_type.replace(/_/g, ' ')} &middot; <em>{q.skill_name}</em>
            </div>
            <div className="result-resub-answer">{q.student_answer}</div>
            {q.teacher_feedback && (
              <div className="result-resub-feedback">
                <strong>Teacher feedback:</strong> {q.teacher_feedback}
              </div>
            )}
            {q.teacher_notes && (
              <div className="result-resub-notes">
                <strong>Notes:</strong> {q.teacher_notes}
              </div>
            )}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: 8,
                flexWrap: 'wrap',
                gap: 8,
              }}
            >
              <div className="result-gap-action">{q.recommended_action}</div>
              <a href={redoUrl} className="practice-redo-link">
                Redo Task →
              </a>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Teacher Review Queue (v1 compat)
// ---------------------------------------------------------------------------

function ReviewQueueCards({
  items,
  pendingCount,
}: {
  items: ReviewQueueItem[]
  pendingCount: number
}) {
  if (pendingCount === 0) {
    return (
      <div className="result-resolved-card">
        All current teacher reviews are resolved.
      </div>
    )
  }
  if (items.length === 0) {
    return (
      <div className="learn-empty-hint" style={{ padding: '16px 0', color: 'var(--success)' }}>
        No items pending teacher review.
      </div>
    )
  }
  return (
    <div className="result-card-list">
      {items.map((q) => (
        <div key={q.attempt_id} className="result-queue-card">
          <div className="result-card-title">{q.topic}</div>
          <div className="result-card-meta">
            {q.resource_type.replace(/_/g, ' ')} &middot; <em>{q.skill_name}</em>
          </div>
          <div className="result-queue-answer">{q.student_answer}</div>
          <div className="result-card-note">{q.feedback}</div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function ActionsList({ actions }: { actions: string[] }) {
  if (actions.length === 0) {
    return <div className="learn-empty-hint">No actions yet.</div>
  }
  return (
    <ul className="result-actions-list">
      {actions.map((a, i) => (
        <li key={i}>{a}</li>
      ))}
    </ul>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function ResultsPage() {
  const report = await getLatestStudentResultReport()

  if (!report) {
    return (
      <div className="learn-page">
        <h1 className="learn-page-title">Quanta Aptus Results</h1>
        <div className="learn-empty">
          <div className="learn-empty-icon">📊</div>
          <div className="learn-empty-title">No result report found yet.</div>
          <div className="learn-empty-hint" style={{ textAlign: 'left', maxWidth: 520, margin: '0 auto' }}>
            <strong>Steps to generate your report:</strong>
            <ol style={{ marginTop: 10, paddingLeft: 20, lineHeight: 2 }}>
              <li>
                Submit at least one attempt at{' '}
                <a href="/learn/practice">Practice</a>
              </li>
              <li>
                Run marking:
                <code className="result-cmd-box">
                  .venv-ingest\Scripts\python.exe tools\ingest\mark_student_attempts_v1.py
                </code>
              </li>
              <li>
                Build report:
                <code className="result-cmd-box">
                  .venv-ingest\Scripts\python.exe tools\ingest\build_student_result_report_v2.py
                </code>
              </li>
            </ol>
          </div>
        </div>
      </div>
    )
  }

  const isV2 = report.report_version === 'v2'
  const pct  = pctDisplay(report.accuracy)

  const pendingCount =
    report.pending_teacher_review_count ??
    report.teacher_review_required_count ??
    0

  // Summary card definitions — v2 has extra fields
  const summaryCards = [
    { label: 'Attempts',          value: report.attempt_count },
    { label: 'Auto-marked',       value: report.auto_marked_count },
    ...(isV2
      ? [
          { label: 'Teacher Reviewed', value: report.teacher_reviewed_count ?? 0 },
          { label: 'Pending Review',   value: pendingCount },
        ]
      : [
          { label: 'Review Required', value: report.teacher_review_required_count ?? 0 },
        ]),
    { label: 'Correct',           value: report.correct_count },
    { label: 'Incorrect',         value: report.incorrect_count },
    ...(isV2
      ? [
          { label: 'Partially Correct',    value: report.partially_correct_count ?? 0 },
          { label: 'Needs Resubmission',   value: report.needs_resubmission_count ?? 0 },
        ]
      : []),
    { label: 'Accuracy',          value: pct },
  ]

  // Source basename for header display
  const srcBase = report.source_marked_attempts
    ? report.source_marked_attempts.split(/[\\/]/).pop()
    : 'unknown'

  return (
    <div className="learn-page">
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: 4,
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <h1 className="learn-page-title" style={{ marginBottom: 4 }}>
            Quanta Aptus Results
            <VersionBadge version={report.report_version} />
          </h1>
          <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', margin: 0 }}>
            Source: <code style={{ fontSize: '0.74rem' }}>{srcBase}</code>
            &nbsp;&middot;&nbsp;Student: <code style={{ fontSize: '0.74rem' }}>{report.student_id}</code>
            &nbsp;&middot;&nbsp;Generated: {new Date(report.created_at).toLocaleString()}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <a href="/learn/attempt-review" className="action-link">Attempt Review →</a>
          <a href="/learn/practice" className="action-link">Back to Practice →</a>
        </div>
      </div>

      {/* Rebuild hint */}
      <div className="result-rebuild-hint">
        Rebuild: <code>.venv-ingest\Scripts\python.exe tools\ingest\build_student_result_report_v2.py</code>
      </div>

      {/* Summary cards */}
      <div className="learn-card-row" style={{ flexWrap: 'wrap' }}>
        {summaryCards.map((c) => (
          <div key={c.label} className="learn-stat-card">
            <div className="learn-stat-val">{c.value}</div>
            <div className="learn-stat-label">{c.label}</div>
          </div>
        ))}
      </div>

      {/* Topic summary */}
      <ResultSection title="Topic Summary">
        <TopicTable topics={report.topics} isV2={isV2} />
      </ResultSection>

      {/* Strengths */}
      <ResultSection title="Strengths" count={report.strengths.length}>
        <StrengthCards strengths={report.strengths} />
      </ResultSection>

      {/* Skill gaps */}
      <ResultSection title="Skill Gaps" count={report.skill_gaps.length}>
        <GapCards gaps={report.skill_gaps} />
      </ResultSection>

      {/* Resubmission queue — v2 only */}
      {isV2 && (
        <ResultSection
          title="Resubmission Queue"
          count={report.resubmission_queue?.length ?? 0}
        >
          <ResubmissionQueueCards items={report.resubmission_queue ?? []} />
        </ResultSection>
      )}

      {/* Recommended actions */}
      <ResultSection title="Recommended Next Actions">
        <ActionsList actions={report.recommended_next_actions} />
      </ResultSection>

      {/* Teacher review queue — always shown (resolved state in v2) */}
      <ResultSection
        title="Teacher Review Queue"
        count={report.review_queue?.length ?? pendingCount}
      >
        <ReviewQueueCards
          items={report.review_queue ?? []}
          pendingCount={pendingCount}
        />
      </ResultSection>
    </div>
  )
}
