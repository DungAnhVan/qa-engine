import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import {
  getPackageDetail,
  fileApiUrl,
  type RegistryPackage,
  type ResourceItem,
} from '@/lib/contentRegistry'

export const dynamic = 'force-dynamic'

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

export async function generateMetadata({
  params,
}: {
  params: Promise<{ packageId: string }>
}): Promise<Metadata> {
  const { packageId } = await params
  return { title: decodeURIComponent(packageId) }
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

/** Keep last N underscore-segments as a readable short ID. */
function shortId(id: string): string {
  const parts = id.split('_')
  return parts.slice(-5).join('_')
}

function diffBadgeClass(difficulty: string | null): string {
  if (!difficulty) return 'badge-gray'
  if (difficulty === 'easy') return 'badge-green'
  if (difficulty === 'hard') return 'badge-red'
  return 'badge-blue'
}

/** Return MCQ option entries that have a non-null value. */
function mcqOptions(options: Record<string, string | null> | null): Array<[string, string]> {
  if (!options) return []
  return (Object.entries(options) as Array<[string, string | null]>).filter(
    (e): e is [string, string] => e[1] !== null,
  )
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="meta-row">
      <span className="meta-key">{label}</span>
      <span className="meta-val">{value}</span>
    </div>
  )
}

function AvailBadge({ ok }: { ok: boolean }) {
  return (
    <span className={`badge ${ok ? 'badge-green' : 'badge-red'}`}>
      {ok ? 'present' : 'missing'}
    </span>
  )
}

function DistBar({ label, count, max }: { label: string; count: number; max: number }) {
  const pct = max > 0 ? (count / max) * 100 : 0
  return (
    <div className="dist-row">
      <span className="dist-label" title={label}>{label}</span>
      <div className="dist-bar-bg">
        <div className="dist-bar" style={{ width: `${pct}%` }} />
      </div>
      <span className="dist-count">{count}</span>
    </div>
  )
}

function DistSection({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  const max = entries[0]?.[1] ?? 1
  return (
    <div className="section">
      <div className="section-header">{title}</div>
      <div className="dist-list">
        {entries.length === 0 ? (
          <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>—</span>
        ) : (
          entries.map(([k, v]) => <DistBar key={k} label={k} count={v} max={max} />)
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Resource detail card (expandable)
// ---------------------------------------------------------------------------

function FieldBlock({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="field-block">
      <span className="field-label">{label}</span>
      <span className="field-val">{value}</span>
    </div>
  )
}

function ResourceRow({ r }: { r: ResourceItem }) {
  const opts = mcqOptions(r.options)
  const isStudentVisible = !!r.student_prompt

  return (
    <tr>
      <td>
        <code className="pkg-id" title={r.resource_id}>{shortId(r.resource_id)}</code>
      </td>
      <td>
        <span className="badge badge-gray" style={{ fontSize: '0.7rem' }}>
          {r.resource_type.replace(/_/g, ' ')}
        </span>
      </td>
      <td style={{ maxWidth: 220, fontSize: '0.78rem' }}>{r.skill_name}</td>
      <td><span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{r.skill_type}</span></td>
      <td>
        {r.difficulty ? (
          <span className={`badge ${diffBadgeClass(r.difficulty)}`} style={{ fontSize: '0.7rem' }}>
            {r.difficulty}
          </span>
        ) : '—'}
      </td>
      <td style={{ textAlign: 'right', fontSize: '0.82rem' }}>
        {r.estimated_time_minutes ?? '—'}m
      </td>
      <td>
        <span className={`badge ${isStudentVisible ? 'badge-green' : 'badge-gray'}`} style={{ fontSize: '0.7rem' }}>
          {isStudentVisible ? 'yes' : 'teacher only'}
        </span>
      </td>
      <td>
        <details className="resource-details">
          <summary>View</summary>
          <div className="resource-expand">
            <FieldBlock label="Student Prompt" value={r.student_prompt} />
            {opts.length > 0 && (
              <div className="field-block">
                <span className="field-label">Options</span>
                <div className="mcq-options">
                  {opts.map(([k, v]) => (
                    <><span className="opt-key">{k}.</span><span className="field-val">{v}</span></>
                  ))}
                </div>
              </div>
            )}
            <FieldBlock label="Correct Answer" value={r.correct_answer} />
            <FieldBlock label="Worked Solution" value={r.worked_solution} />
            <FieldBlock label="Marking Guidance" value={r.marking_guidance} />
            <FieldBlock label="Common Misconception" value={r.common_misconception} />
            <FieldBlock label="Teacher Note" value={r.teacher_note} />
          </div>
        </details>
      </td>
    </tr>
  )
}

// ---------------------------------------------------------------------------
// Resource browser — grouped by topic
// ---------------------------------------------------------------------------

function ResourceBrowser({ resources }: { resources: ResourceItem[] }) {
  if (resources.length === 0) {
    return <div className="empty-state">No resources loaded.</div>
  }

  // Group by topic, preserving insertion order
  const grouped = new Map<string, ResourceItem[]>()
  for (const r of resources) {
    const key = r.topic ?? 'Unknown Topic'
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(r)
  }

  return (
    <>
      {[...grouped.entries()].map(([topic, items]) => (
        <div key={topic} className="section" style={{ marginBottom: 16 }}>
          <div className="section-header">
            {topic}
            <span style={{ fontWeight: 400, fontSize: '0.82rem', marginLeft: 8, color: 'var(--text-muted)' }}>
              ({items.length} resource{items.length !== 1 ? 's' : ''})
            </span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Resource ID</th>
                  <th>Type</th>
                  <th>Skill</th>
                  <th>Skill Type</th>
                  <th>Difficulty</th>
                  <th style={{ textAlign: 'right' }}>Time</th>
                  <th>Student</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <ResourceRow key={r.resource_id} r={r} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function PackageDetailPage({
  params,
}: {
  params: Promise<{ packageId: string }>
}) {
  const { packageId } = await params
  const detail = await getPackageDetail(decodeURIComponent(packageId))

  if (!detail) notFound()

  const { pkg, teacherResources, studentResourceCount, teacherMissing, studentMissing } = detail
  const av = pkg.availability
  const p = pkg.paths

  const fileRows: Array<{ key: string; label: string; absPath: string }> = [
    { key: 'publish_package',  label: 'Publish Package JSON',  absPath: p.publish_package },
    { key: 'student_payload',  label: 'Student Payload JSON',  absPath: p.student_payload },
    { key: 'teacher_payload',  label: 'Teacher Payload JSON',  absPath: p.teacher_payload },
    { key: 'package_report',   label: 'Package Report JSON',   absPath: p.package_report },
    { key: 'package_manifest', label: 'Package Manifest MD',   absPath: p.package_manifest },
    { key: 'student_preview',  label: 'Student HTML Preview',  absPath: p.student_preview },
    { key: 'teacher_preview',  label: 'Teacher HTML Preview',  absPath: p.teacher_preview },
  ]

  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 18 }}>
        <a href="/content" className="back-link" style={{ marginBottom: 0 }}>← Content Registry</a>
        <a href="/content/review" className="action-link">Teacher Review Queue →</a>
      </div>

      <h1 className="page-title">{pkg.title}</h1>
      <p className="page-sub">
        Registered: {pkg.registered_at.slice(0, 19).replace('T', ' ')} UTC &nbsp;·&nbsp;
        <span className={`badge ${pkg.package_status === 'publish_ready' ? 'badge-green' : 'badge-blue'}`}>
          {pkg.package_status.replace(/_/g, ' ')}
        </span>
      </p>

      {/* Payload warnings */}
      {teacherMissing && (
        <div className="warn-card">
          Teacher payload file missing or unreadable — resource browser unavailable.
        </div>
      )}
      {studentMissing && (
        <div className="warn-card">
          Student payload file missing or unreadable.
        </div>
      )}

      {/* Summary cards */}
      <div className="card-row">
        {[
          { label: 'Total Resources',   value: pkg.resource_count },
          { label: 'Student Resources', value: studentResourceCount },
          { label: 'Teacher Resources', value: pkg.teacher_payload_count ?? teacherResources.length },
          { label: 'Teacher-only',      value: pkg.teacher_only_resource_count ?? '—' },
          { label: 'Est. Time (min)',   value: pkg.estimated_total_time_minutes },
        ].map((c) => (
          <div key={c.label} className="stat-card">
            <div className="value">{c.value}</div>
            <div className="label">{c.label}</div>
          </div>
        ))}
      </div>

      {/* Metadata */}
      <div className="section" style={{ marginBottom: 16 }}>
        <div className="section-header">Package Metadata</div>
        <div className="meta-grid">
          <MetaRow label="Package ID"       value={<code className="pkg-id">{pkg.package_id}</code>} />
          <MetaRow label="Version"          value={pkg.package_version} />
          <MetaRow label="Board"            value={pkg.board} />
          <MetaRow label="Level"            value={pkg.level.toUpperCase()} />
          <MetaRow label="Subject"          value={pkg.subject} />
          <MetaRow label="Syllabus Code"    value={pkg.syllabus_code} />
          <MetaRow label="Content Origin"   value={pkg.content_origin.replace(/_/g, ' ')} />
          <MetaRow label="Copyright Status" value={pkg.copyright_status.replace(/_/g, ' ')} />
          <MetaRow label="Student Visible"  value={pkg.app_visibility.student_visible ? 'Yes' : 'No'} />
          <MetaRow label="Teacher Visible"  value={pkg.app_visibility.teacher_visible ? 'Yes' : 'No'} />
          <MetaRow label="Admin Visible"    value={pkg.app_visibility.admin_visible   ? 'Yes' : 'No'} />
        </div>
      </div>

      {/* Distributions */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        <DistSection title="Resource Types" data={pkg.resource_types} />
        <DistSection title="Topics"         data={pkg.topics} />
        <DistSection title="Skill Types"    data={pkg.skill_types} />
        <DistSection title="Difficulties"   data={pkg.difficulties} />
      </div>

      {/* Resource browser */}
      <h2 style={{ fontSize: '1rem', fontWeight: 700, margin: '24px 0 12px', color: 'var(--text)' }}>
        Resource Browser — Teacher View ({teacherResources.length} resources)
      </h2>
      <ResourceBrowser resources={teacherResources} />

      {/* File availability */}
      <div className="section" style={{ marginTop: 24 }}>
        <div className="section-header">Files &amp; Availability</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Available</th>
                <th>Path</th>
                <th>Open</th>
              </tr>
            </thead>
            <tbody>
              {fileRows.map(({ key, label, absPath }) => (
                <tr key={key}>
                  <td style={{ whiteSpace: 'nowrap' }}>{label}</td>
                  <td><AvailBadge ok={!!av[key]} /></td>
                  <td><span className="path-text">{absPath || '—'}</span></td>
                  <td>
                    {av[key] ? (
                      <a className="action-link" href={fileApiUrl(absPath)} target="_blank" rel="noreferrer">
                        Open
                      </a>
                    ) : (
                      <span className="action-link disabled">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
