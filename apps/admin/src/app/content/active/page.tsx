import type { Metadata } from 'next'
import {
  getActiveContentIndex,
  type ActivePackage,
  type PreviousVersion,
} from '@/lib/activeContent'
import { fileApiUrl } from '@/lib/contentRegistry'

export const metadata: Metadata = { title: 'Active Content' }
export const dynamic = 'force-dynamic'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusBadge(status: string) {
  const cls =
    status === 'publish_ready' ? 'badge-green'
    : status === 'internal_demo' ? 'badge-blue'
    : 'badge-gray'
  return <span className={`badge ${cls}`}>{status.replace(/_/g, ' ')}</span>
}

function ActionLink({
  href,
  label,
  available = true,
}: {
  href: string
  label: string
  available?: boolean
}) {
  if (!available || !href || href === '#') {
    return <span className="action-link disabled">{label}</span>
  }
  return (
    <a className="action-link" href={href} target="_blank" rel="noreferrer">
      {label}
    </a>
  )
}

function PrevVersionList({ items }: { items: PreviousVersion[] }) {
  if (items.length === 0) {
    return <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>—</span>
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {items.map((v) => (
        <div key={v.package_id}>
          <span className="pkg-id" style={{ fontSize: '0.72rem' }}>
            {v.package_id}
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 4 }}>
            — {v.resource_count} resources
          </span>
        </div>
      ))}
    </div>
  )
}

function ActivePackageRow({ pkg }: { pkg: ActivePackage }) {
  const p = pkg.paths
  return (
    <tr>
      <td>
        <span className="pkg-id" style={{ fontSize: '0.75rem' }}>
          {pkg.content_key}
        </span>
      </td>
      <td>{pkg.board}</td>
      <td>{pkg.level.toUpperCase()}</td>
      <td style={{ textTransform: 'capitalize' }}>{pkg.subject}</td>
      <td>{pkg.syllabus_code}</td>
      <td>
        <a href={`/content/${encodeURIComponent(pkg.active_package_id)}`} className="pkg-id">
          {pkg.active_package_id}
        </a>
      </td>
      <td>{statusBadge(pkg.active_package_status)}</td>
      <td style={{ textAlign: 'right' }}>{pkg.resource_count}</td>
      <td style={{ textAlign: 'right' }}>{pkg.student_payload_count}</td>
      <td style={{ textAlign: 'right' }}>{pkg.teacher_payload_count}</td>
      <td style={{ textAlign: 'right' }}>{pkg.teacher_only_resource_count}</td>
      <td style={{ minWidth: 260 }}>
        <PrevVersionList items={pkg.previous_versions} />
      </td>
      <td>
        <div className="actions">
          <a
            className="action-link"
            href={`/content/${encodeURIComponent(pkg.active_package_id)}`}
          >
            Package Detail
          </a>
          <ActionLink
            href={fileApiUrl(p.student_preview)}
            label="Student Preview"
            available={!!p.student_preview}
          />
          <ActionLink
            href={fileApiUrl(p.teacher_preview)}
            label="Teacher Preview"
            available={!!p.teacher_preview}
          />
          <ActionLink
            href={fileApiUrl(p.publish_package)}
            label="Package JSON"
            available={!!p.publish_package}
          />
        </div>
      </td>
    </tr>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function ActiveContentPage() {
  const index = await getActiveContentIndex()

  if (!index) {
    return (
      <div className="page">
        <h1 className="page-title">Quanta Aptus Active Content</h1>
        <div className="empty-state" style={{ padding: '48px 0' }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>
            No active content index found.
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 16 }}>
            Run the following command to generate it:
          </div>
          <pre
            style={{
              display: 'inline-block',
              background: '#1a202c',
              color: '#e2e8f0',
              padding: '10px 18px',
              borderRadius: 6,
              fontSize: '0.78rem',
              textAlign: 'left',
            }}
          >
            {`.\\venv-ingest\\Scripts\\python.exe tools\\ingest\\build_active_content_index_v1.py data\\registry\\content_registry_v1.json`}
          </pre>
        </div>
      </div>
    )
  }

  const s = index.summary

  const cards = [
    { label: 'Active Packages',         value: s.active_package_count },
    { label: 'Archived Packages',        value: s.archived_package_count },
    { label: 'Active Resources',          value: s.active_total_resources },
    { label: 'Student Resources',         value: s.active_student_resources },
    { label: 'Teacher Resources',         value: s.active_teacher_resources },
    { label: 'Teacher-only Resources',    value: s.active_teacher_only_resources },
  ]

  return (
    <div className="page">
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          marginBottom: 4,
        }}
      >
        <h1 className="page-title">Quanta Aptus Active Content</h1>
        <div style={{ display: 'flex', gap: 10 }}>
          <a href="/content" className="action-link">Content Registry →</a>
          <a href="/content/review" className="action-link">Teacher Review →</a>
        </div>
      </div>
      <p className="page-sub">
        Current active packages for student and teacher apps.&nbsp;&nbsp;
        Index: <code>{index.index_id}</code> &nbsp;·&nbsp;
        Status: {index.status} &nbsp;·&nbsp;
        Source: <code>{index.source_registry_id}</code>
      </p>

      {/* Summary cards */}
      <div className="card-row">
        {cards.map((c) => (
          <div key={c.label} className="stat-card">
            <div className="value">{c.value}</div>
            <div className="label">{c.label}</div>
          </div>
        ))}
      </div>

      {/* Active packages table */}
      <div className="section">
        <div className="section-header">
          Active Packages &nbsp;
          <span
            style={{
              background: 'rgba(255,255,255,.15)',
              borderRadius: 9999,
              padding: '1px 8px',
              fontSize: '0.75rem',
              fontWeight: 400,
            }}
          >
            {index.active_package_count} active / {s.archived_package_count} archived
          </span>
        </div>
        {index.active_packages.length === 0 ? (
          <div className="empty-state">No active packages found.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Content Key</th>
                  <th>Board</th>
                  <th>Level</th>
                  <th>Subject</th>
                  <th>Syllabus</th>
                  <th>Active Package</th>
                  <th>Status</th>
                  <th>Resources</th>
                  <th>Student</th>
                  <th>Teacher</th>
                  <th>Teacher-only</th>
                  <th>Previous Versions</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {index.active_packages.map((pkg) => (
                  <ActivePackageRow key={pkg.content_key} pkg={pkg} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
