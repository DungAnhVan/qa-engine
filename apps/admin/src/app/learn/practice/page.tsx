import type { Metadata } from 'next'
import {
  getActiveStudentResources,
  groupResourcesByTopic,
  type StudentResource,
} from '@/lib/studentResources'
import { getActiveContentIndex } from '@/lib/activeContent'
import { getStudentAttempts, getAttemptSummary } from '@/lib/studentAttempts'
import { getResubmissionItem } from '@/lib/studentResults'
import { AttemptForm } from './AttemptForm'

export const metadata: Metadata = { title: 'Practice' }
export const dynamic = 'force-dynamic'

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

const TYPE_LABEL: Record<string, string> = {
  calculation_drill:         'Calculation Drill',
  worked_example:            'Worked Example',
  short_answer_calculation:  'Short Answer',
  diagram_or_graph_drill:    'Diagram / Graph',
  graphing_drill:            'Graphing',
  data_interpretation_drill: 'Data Interpretation',
  experiment_planning_task:  'Experiment Planning',
}

const SKILL_LABEL: Record<string, string> = {
  calculation:           'Calculation',
  equation_manipulation: 'Equation',
  graphing:              'Graphing',
  extended_planning:     'Planning',
  data_interpretation:   'Data Interpretation',
}

function typeLabel(t: string) { return TYPE_LABEL[t] ?? t.replace(/_/g, ' ') }
function skillLabel(t: string) { return SKILL_LABEL[t] ?? t.replace(/_/g, ' ') }

function DiffBadge({ d }: { d: string | null }) {
  if (!d) return null
  const cls = d === 'easy' ? 'learn-diff easy' : d === 'hard' ? 'learn-diff hard' : 'learn-diff medium'
  return <span className={cls}>{d}</span>
}

function hasRealOptions(options: Record<string, string | null> | null): boolean {
  if (!options) return false
  return Object.values(options).some((v) => v !== null && v !== '')
}

// ---------------------------------------------------------------------------
// Practice card (server content + client form)
// ---------------------------------------------------------------------------

function PracticeCard({
  resource,
  packageId,
  parentAttemptId,
  attemptType,
  mode,
}: {
  resource: StudentResource
  packageId: string
  parentAttemptId?: string
  attemptType?: 'first_attempt' | 'resubmission'
  mode?: string
}) {
  const isWorked = resource.resource_type === 'worked_example'

  return (
    <div className="learn-card">
      <div className="learn-card-header">
        <span
          className={`learn-type-badge ${isWorked ? 'worked' : ''}`}
          title={resource.resource_type}
        >
          {typeLabel(resource.resource_type)}
        </span>
        <DiffBadge d={resource.difficulty} />
        {resource.estimated_time_minutes && (
          <span className="learn-meta-chip">{resource.estimated_time_minutes} min</span>
        )}
        <span className="learn-skill-chip">{skillLabel(resource.skill_type)}</span>
      </div>

      <div className="learn-skill-name">{resource.skill_name}</div>

      {resource.student_prompt && (
        <div className="learn-prompt">{resource.student_prompt}</div>
      )}

      {hasRealOptions(resource.options) && (
        <div className="learn-options">
          {Object.entries(resource.options!).map(([key, val]) =>
            val ? (
              <div key={key} className="learn-option-row">
                <span className="learn-option-key">{key}</span>
                <span className="learn-option-val">{val}</span>
              </div>
            ) : null,
          )}
        </div>
      )}

      {isWorked && resource.worked_solution && (
        <div className="learn-solution">
          <div className="learn-solution-label">Solution</div>
          <div className="learn-solution-body">{resource.worked_solution}</div>
        </div>
      )}

      <div className="practice-form-wrapper">
        <AttemptForm
          resource={resource}
          packageId={packageId}
          parentAttemptId={parentAttemptId}
          attemptType={attemptType}
          mode={mode}
        />
      </div>
    </div>
  )
}

function PracticeTopicSection({
  topic,
  resources,
  packageId,
}: {
  topic: string
  resources: StudentResource[]
  packageId: string
}) {
  return (
    <section className="learn-topic-section">
      <div className="learn-topic-heading">
        <span className="learn-topic-name">{topic}</span>
        <span className="learn-topic-count">
          {resources.length} resource{resources.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="learn-card-list">
        {resources.map((r) => (
          <PracticeCard key={r.resource_id} resource={r} packageId={packageId} />
        ))}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function PracticePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>
}) {
  const params = await searchParams
  const mode             = params.mode
  const targetResourceId = params.resource_id
  const parentAttemptId  = params.parent_attempt_id

  const isResubmission = mode === 'resubmission' && Boolean(targetResourceId)

  const index = await getActiveContentIndex()

  if (!index) {
    return (
      <div className="learn-page">
        <h1 className="learn-page-title">Quanta Aptus Practice</h1>
        <div className="learn-empty">
          <div className="learn-empty-icon">📚</div>
          <div className="learn-empty-title">No active content available.</div>
        </div>
      </div>
    )
  }

  const { pkg, payload, resources } = await getActiveStudentResources()

  if (!pkg || !payload) {
    return (
      <div className="learn-page">
        <h1 className="learn-page-title">Quanta Aptus Practice</h1>
        <div className="learn-empty">
          <div className="learn-empty-icon">📦</div>
          <div className="learn-empty-title">No active content available.</div>
        </div>
      </div>
    )
  }

  // ── Resubmission mode ────────────────────────────────────────────────────

  if (isResubmission) {
    const targetResource = resources.find((r) => r.resource_id === targetResourceId)
    const resubItem = parentAttemptId
      ? await getResubmissionItem(parentAttemptId)
      : null

    if (!targetResource) {
      return (
        <div className="learn-page">
          <div style={{ marginBottom: 16 }}>
            <a href="/learn/results" className="action-link">← Back to Results</a>
          </div>
          <h1 className="learn-page-title">Quanta Aptus Resubmission</h1>
          <div className="learn-empty">
            <div className="learn-empty-icon">⚠️</div>
            <div className="learn-empty-title">Resource not found.</div>
            <div className="learn-empty-hint">
              Resource ID: <code>{targetResourceId}</code>
            </div>
          </div>
        </div>
      )
    }

    return (
      <div className="learn-page">
        {/* Header */}
        <div style={{ marginBottom: 8 }}>
          <a href="/learn/results" className="action-link">← Back to Results</a>
        </div>
        <h1 className="learn-page-title">Quanta Aptus Resubmission</h1>
        <p className="learn-page-sub">
          Redo this task based on teacher feedback.
        </p>

        {/* Teacher feedback context card */}
        {resubItem && (
          <div className="practice-resub-context">
            <div className="practice-resub-context-header">Teacher Feedback</div>
            {resubItem.teacher_feedback && (
              <div className="practice-resub-feedback-text">
                {resubItem.teacher_feedback}
              </div>
            )}
            {resubItem.teacher_notes && (
              <div className="practice-resub-notes-text">
                <strong>Notes:</strong> {resubItem.teacher_notes}
              </div>
            )}
            {resubItem.student_answer && (
              <div style={{ marginTop: 10 }}>
                <div className="practice-resub-context-label">Your original answer:</div>
                <div className="practice-resub-original-answer">{resubItem.student_answer}</div>
              </div>
            )}
            {resubItem.recommended_action && (
              <div className="practice-resub-action">
                {resubItem.recommended_action}
              </div>
            )}
          </div>
        )}

        {/* The resource card */}
        <div className="learn-card-list" style={{ marginTop: 16 }}>
          <PracticeCard
            resource={targetResource}
            packageId={pkg.active_package_id}
            parentAttemptId={parentAttemptId}
            attemptType="resubmission"
            mode="resubmission"
          />
        </div>
      </div>
    )
  }

  // ── Normal practice mode ─────────────────────────────────────────────────

  const attemptsFile = await getStudentAttempts()
  const summary = getAttemptSummary(attemptsFile)
  const grouped = groupResourcesByTopic(resources)

  const cards = [
    {
      label: 'Active Package',
      value:
        pkg.active_package_id.split('_resource_package_')[1]?.toUpperCase() ??
        pkg.active_package_version,
    },
    { label: 'Student Resources', value: resources.length },
    { label: 'Submitted Attempts', value: summary.submitted },
    { label: 'Unmarked Attempts', value: summary.unmarked },
    {
      label: 'Subject',
      value: `${pkg.subject.charAt(0).toUpperCase() + pkg.subject.slice(1)} ${pkg.syllabus_code}`,
    },
  ]

  return (
    <div className="learn-page">
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          marginBottom: 4,
        }}
      >
        <h1 className="learn-page-title">Quanta Aptus Practice</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <a href="/learn/results" className="action-link">View Results →</a>
          <a href="/learn" className="action-link">Back to Learn →</a>
        </div>
      </div>
      <p className="learn-page-sub">
        Submit your answers. Attempts are saved locally and can be marked later.
      </p>

      <div className="learn-card-row">
        {cards.map((c) => (
          <div key={c.label} className="learn-stat-card">
            <div className="learn-stat-val">{c.value}</div>
            <div className="learn-stat-label">{c.label}</div>
          </div>
        ))}
      </div>

      {[...grouped.entries()].map(([topic, topicResources]) => (
        <PracticeTopicSection
          key={topic}
          topic={topic}
          resources={topicResources}
          packageId={pkg.active_package_id}
        />
      ))}
    </div>
  )
}
