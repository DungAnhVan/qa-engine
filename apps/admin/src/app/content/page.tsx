
import type { Metadata } from 'next'
import { getContentRegistry, fileApiUrl, type RegistryPackage } from '@/lib/contentRegistry'
import { requireAppRole } from '@/lib/roleAccess'

export const metadata: Metadata = { title: 'Content Registry' }

// Force dynamic so the file is read fresh on each request
export const dynamic = 'force-dynamic'

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function statusBadge(status: string) {
  const cls =
    status === 'publish_ready' ? 'badge-green'
    : status === 'internal_demo' ? 'badge-blue'
    : 'badge-gray'
  return <span className={`badge ${cls}`}>{status.replace(/_/g, ' ')}</span>
}

function topN(rec: Record<string, number>, n = 3): string {
  return Object.entries(rec)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([k]) => k)
    .join(', ')
}

function ActionLink({
  href,
  label,
  available,
}: {
  href: string
  label: string
  available: boolean
}) {
  if (!available) {
    return <span className="action-link disabled">{label}</span>
  }
  return (
    <a className="action-link" href={href} target="_blank" rel="noreferrer">
      {label}
    </a>
  )
}

function PackageRow({ pkg }: { pkg: RegistryPackage }) {
  const av = pkg.availability
  const p = pkg.paths

  return (
    <tr>
      <td>
        <a href={`/content/${encodeURIComponent(pkg.package_id)}`} className="pkg-id">
          {pkg.package_id}
        </a>
      </td>
      <td>{pkg.board}</td>
      <td>{pkg.level.toUpperCase()}</td>
      <td>{pkg.subject}</td>
      <td>{pkg.syllabus_code}</td>
      <td>{statusBadge(pkg.package_status)}</td>
      <td style={{ textAlign: 'right' }}>{pkg.resource_count}</td>
      <td style={{ textAlign: 'right' }}>{pkg.student_payload_count ?? '—'}</td>
      <td style={{ textAlign: 'right' }}>{pkg.teacher_payload_count ?? '—'}</td>
      <td style={{ textAlign: 'right' }}>{pkg.teacher_only_resource_count ?? '—'}</td>
      <td style={{ maxWidth: 200 }}>{topN(pkg.topics)}</td>
      <td>
        <div className="actions">
          <ActionLink
            href={fileApiUrl(p.student_preview)}
            label="Student Preview"
            available={av.student_preview}
          />
          <ActionLink
            href={fileApiUrl(p.teacher_preview)}
            label="Teacher Preview"
            available={av.teacher_preview}
          />
          <ActionLink
            href={fileApiUrl(p.publish_package)}
            label="Package JSON"
            available={av.publish_package}
          />
          <ActionLink
            href={fileApiUrl(p.student_payload)}
            label="Student Payload"
            available={av.student_payload}
          />
          <ActionLink
            href={fileApiUrl(p.teacher_payload)}
            label="Teacher Payload"
            available={av.teacher_payload}
          />
        </div>
      </td>
    </tr>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function ContentPage() {
  const { allowed, currentRole } = await requireAppRole(['admin', 'teacher'])
  if (!allowed) return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Access denied</h1>
      <p style={{ color: '#6b7280', fontSize: 14, marginBottom: 12 }}>
        Required: admin or teacher. Your role: <code>{currentRole ?? 'none'}</code>
      </p>
      <a href="/login" style={{ color: '#3b82f6' }}>Sign in →</a>
    </main>
  )
  const { registry } = await getContentRegistry()
  const sm = registry.summary

  const cards = [
    { label: 'Packages',            value: sm.total_packages },
    { label: 'Total Resources',     value: sm.total_resources },
    { label: 'Student Resources',   value: sm.total_student_resources },
    { label: 'Teacher Resources',   value: sm.total_teacher_resources },
    { label: 'Teacher-only',        value: sm.total_teacher_only_resources },
    { label: 'Est. Time (min)',      value: sm.estimated_total_time_minutes },
  ]

  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 4 }}>
        <h1 className="page-title">Quanta Aptus Content Registry</h1>
        <div style={{ display: 'flex', gap: 10 }}>
          <a href="/content/active" className="action-link">View Active Content →</a>
          <a href="/content/review" className="action-link">Teacher Review Queue →</a>
        </div>
      </div>
      <p className="page-sub">
        Registry ID: <code>{registry.registry_id}</code> &nbsp;·&nbsp;
        Status: {registry.status} &nbsp;·&nbsp;
        {registry.package_count} package(s)
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

      {/* Packages table */}
      <div className="section">
        <div className="section-header">Packages</div>
        {registry.packages.length === 0 ? (
          <div className="empty-state">No packages found in registry.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Package ID</th>
                  <th>Board</th>
                  <th>Level</th>
                  <th>Subject</th>
                  <th>Syllabus</th>
                  <th>Status</th>
                  <th>Resources</th>
                  <th>Student</th>
                  <th>Teacher</th>
                  <th>Teacher-only</th>
                  <th>Top Topics</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {registry.packages.map((pkg) => (
                  <PackageRow key={pkg.package_id} pkg={pkg} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Registry summary breakdowns */}
      {sm.total_packages > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <DistSection title="Resource Types" data={sm.resource_types} />
          <DistSection title="Topics" data={sm.topics} />
        </div>
      )}
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
        {entries.map(([k, v]) => (
          <div key={k} className="dist-row">
            <span className="dist-label" title={k}>{k}</span>
            <div className="dist-bar-bg">
              <div className="dist-bar" style={{ width: `${(v / max) * 100}%` }} />
            </div>
            <span className="dist-count">{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
