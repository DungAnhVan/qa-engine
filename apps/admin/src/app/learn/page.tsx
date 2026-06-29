import type { Metadata } from 'next'
import {
  getActiveStudentResources,
  groupResourcesByTopic,
  type StudentResource,
} from '@/lib/studentResources'
import { getActiveContentIndex } from '@/lib/activeContent'

export const metadata: Metadata = { title: 'Learn' }
export const dynamic = 'force-dynamic'

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

const RESOURCE_TYPE_LABEL: Record<string, string> = {
  calculation_drill:         'Calculation Drill',
  worked_example:            'Worked Example',
  short_answer_calculation:  'Short Answer',
  diagram_or_graph_drill:    'Diagram / Graph',
  graphing_drill:            'Graphing',
  data_interpretation_drill: 'Data Interpretation',
  experiment_planning_task:  'Experiment Planning',
}

const SKILL_TYPE_LABEL: Record<string, string> = {
  calculation:         'Calculation',
  equation_manipulation: 'Equation',
  graphing:            'Graphing',
  extended_planning:   'Planning',
  data_interpretation: 'Data Interpretation',
}

function typeLabel(t: string) {
  return RESOURCE_TYPE_LABEL[t] ?? t.replace(/_/g, ' ')
}
function skillLabel(t: string) {
  return SKILL_TYPE_LABEL[t] ?? t.replace(/_/g, ' ')
}

function DiffBadge({ d }: { d: string | null }) {
  if (!d) return null
  const cls =
    d === 'easy'   ? 'learn-diff easy'
    : d === 'hard' ? 'learn-diff hard'
    :                'learn-diff medium'
  return <span className={cls}>{d}</span>
}

function TypeBadge({ t }: { t: string }) {
  const isWorked = t === 'worked_example'
  return (
    <span className={`learn-type-badge ${isWorked ? 'worked' : ''}`}>
      {typeLabel(t)}
    </span>
  )
}

function hasRealOptions(options: Record<string, string | null> | null): boolean {
  if (!options) return false
  return Object.values(options).some((v) => v !== null && v !== '')
}

function ResourceCard({ resource }: { resource: StudentResource }) {
  const isWorked = resource.resource_type === 'worked_example'
  const showSolution = isWorked && resource.worked_solution

  return (
    <div className="learn-card">
      {/* Card header */}
      <div className="learn-card-header">
        <TypeBadge t={resource.resource_type} />
        <DiffBadge d={resource.difficulty} />
        {resource.estimated_time_minutes && (
          <span className="learn-meta-chip">
            {resource.estimated_time_minutes} min
          </span>
        )}
        <span className="learn-skill-chip">
          {skillLabel(resource.skill_type)}
        </span>
      </div>

      {/* Skill name */}
      <div className="learn-skill-name">{resource.skill_name}</div>

      {/* Prompt */}
      {resource.student_prompt && (
        <div className="learn-prompt">{resource.student_prompt}</div>
      )}

      {/* MCQ options — only when values are actually populated */}
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

      {/* Worked solution */}
      {showSolution && (
        <div className="learn-solution">
          <div className="learn-solution-label">Solution</div>
          <div className="learn-solution-body">{resource.worked_solution}</div>
        </div>
      )}
    </div>
  )
}

function TopicSection({
  topic,
  resources,
}: {
  topic: string
  resources: StudentResource[]
}) {
  return (
    <section className="learn-topic-section">
      <div className="learn-topic-heading">
        <span className="learn-topic-name">{topic}</span>
        <span className="learn-topic-count">{resources.length} resource{resources.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="learn-card-list">
        {resources.map((r) => (
          <ResourceCard key={r.resource_id} resource={r} />
        ))}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function LearnPage() {
  // Check if active index exists at all
  const index = await getActiveContentIndex()

  if (!index) {
    return (
      <div className="learn-page">
        <h1 className="learn-page-title">Quanta Aptus Learn</h1>
        <div className="learn-empty">
          <div className="learn-empty-icon">📚</div>
          <div className="learn-empty-title">No active content is available yet.</div>
          <div className="learn-empty-hint">
            The active content index has not been generated. Please contact your administrator.
          </div>
        </div>
      </div>
    )
  }

  const { pkg, payload, resources } = await getActiveStudentResources()

  if (!pkg) {
    return (
      <div className="learn-page">
        <h1 className="learn-page-title">Quanta Aptus Learn</h1>
        <div className="learn-empty">
          <div className="learn-empty-icon">📦</div>
          <div className="learn-empty-title">No active content is available yet.</div>
        </div>
      </div>
    )
  }

  if (!payload) {
    return (
      <div className="learn-page">
        <h1 className="learn-page-title">Quanta Aptus Learn</h1>
        <p className="learn-page-sub">
          Active package: <strong>{pkg.active_package_id}</strong>
        </p>
        <div className="learn-empty">
          <div className="learn-empty-icon">⚠️</div>
          <div className="learn-empty-title">Active package found, but student payload is missing.</div>
          <div className="learn-empty-hint">
            Package: <code>{pkg.active_package_id}</code>
          </div>
        </div>
      </div>
    )
  }

  const grouped = groupResourcesByTopic(resources)
  const totalTime = resources.reduce((s, r) => s + (r.estimated_time_minutes ?? 0), 0)

  const cards = [
    { label: 'Active Package',     value: pkg.active_package_id.split('_resource_package_')[1]?.toUpperCase() ?? pkg.active_package_version },
    { label: 'Student Resources',  value: resources.length },
    { label: 'Topics',             value: grouped.size },
    { label: 'Est. Time (min)',     value: totalTime },
    { label: 'Subject',            value: `${pkg.subject.charAt(0).toUpperCase() + pkg.subject.slice(1)} ${pkg.syllabus_code}` },
  ]

  return (
    <div className="learn-page">
      {/* Header */}
      <h1 className="learn-page-title">Quanta Aptus Learn</h1>
      <p className="learn-page-sub">
        Active learning resources from the current Quanta Aptus package.
      </p>

      {/* Summary cards */}
      <div className="learn-card-row">
        {cards.map((c) => (
          <div key={c.label} className="learn-stat-card">
            <div className="learn-stat-val">{c.value}</div>
            <div className="learn-stat-label">{c.label}</div>
          </div>
        ))}
      </div>

      {/* Resources grouped by topic */}
      {[...grouped.entries()].map(([topic, topicResources]) => (
        <TopicSection key={topic} topic={topic} resources={topicResources} />
      ))}
    </div>
  )
}
