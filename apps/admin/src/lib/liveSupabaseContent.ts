/**
 * SERVER-ONLY — Live Supabase read module.
 *
 * WARNING: This file uses SUPABASE_SERVICE_ROLE_KEY.
 * It must NEVER be imported in client components or client-side code.
 * The `import 'server-only'` guard below enforces this at build time.
 *
 * The browser never connects to Supabase.
 * No writes are performed. Read-only queries only.
 */
import 'server-only'

import { createClient } from '@supabase/supabase-js'
import type { ActiveContentIndex, ActivePackage } from './activeContent'
import type { StudentPayload, StudentResource } from './studentResources'

const DEFAULT_SUBJECT_SLUG = 'physics_0625'

// ---------------------------------------------------------------------------
// Env helpers — key values never logged or returned to the browser
// ---------------------------------------------------------------------------

function getSupabaseConfig(): { url: string; serviceRoleKey: string } | null {
  const url = process.env.SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !key) return null
  return { url, serviceRoleKey: key }
}

export function isLiveSupabaseConfigured(): boolean {
  return getSupabaseConfig() !== null
}

/** Returns which env vars are present — values are NEVER returned. */
export function getLiveSupabaseEnvPresence(): {
  supabase_url: boolean
  service_role_key: boolean
} {
  return {
    supabase_url:      Boolean(process.env.SUPABASE_URL),
    service_role_key:  Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY),
  }
}

function requireSupabaseClient() {
  const config = getSupabaseConfig()
  if (!config) {
    throw new Error(
      'live_supabase mode requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local. ' +
      'See .env.example for setup instructions.',
    )
  }
  return createClient(config.url, config.serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })
}

// ---------------------------------------------------------------------------
// Raw query helpers
// ---------------------------------------------------------------------------

// Derive client type from the factory so generics always match exactly.
type AppClient = ReturnType<typeof requireSupabaseClient>

async function _querySubject(client: AppClient, slug: string) {
  const { data } = await client
    .from('subjects')
    .select('id, board, level, subject_slug, subject_name, syllabus_code')
    .eq('subject_slug', slug)
    .maybeSingle()
  return (data as unknown) as {
    id: string
    board: string
    level: string
    subject_slug: string
    subject_name: string
    syllabus_code: string
  } | null
}

async function _queryActivePackage(client: AppClient, subjectId: string) {
  const { data } = await client
    .from('resource_packages')
    .select(
      'id, package_key, version, status, ' +
      'resource_count, student_resource_count, teacher_resource_count, published_at',
    )
    .eq('subject_id', subjectId)
    .eq('status', 'active')
    .order('version', { ascending: false })
    .limit(1)
    .maybeSingle()
  return (data as unknown) as {
    id: string
    package_key: string
    version: number
    status: string
    resource_count: number
    student_resource_count: number
    teacher_resource_count: number
    published_at: string | null
  } | null
}

async function _queryPackageItems(client: AppClient, packageId: string) {
  const { data } = await client
    .from('resource_package_items')
    .select('id, resource_id, sort_order, visibility')
    .eq('package_id', packageId)
    .order('sort_order')
  return ((data ?? []) as unknown) as Array<{
    id: string
    resource_id: string
    sort_order: number
    visibility: string
  }>
}

async function _queryResourcesByIds(
  client: AppClient,
  ids: string[],
): Promise<Record<string, ResourceRow>> {
  if (!ids.length) return {}
  const { data } = await client
    .from('resources')
    .select(
      'id, resource_key, title, topic, subtopic, skill_type, resource_type, ' +
      'difficulty, estimated_time_minutes, student_prompt, worked_solution, ' +
      'marking_guidance, common_misconceptions, teacher_notes, ' +
      'needs_human_review, publish_status, copyright_status',
    )
    .in('id', ids)
  const rows = ((data ?? []) as unknown) as ResourceRow[]
  return Object.fromEntries(rows.map((r) => [r.id, r]))
}

interface ResourceRow {
  id: string
  resource_key: string
  title: string
  topic: string
  subtopic: string | null
  skill_type: string
  resource_type: string
  difficulty: string | null
  estimated_time_minutes: number | null
  student_prompt: string | null
  worked_solution: string | null
  marking_guidance: string | null
  common_misconceptions: string | null
  teacher_notes: string | null
  needs_human_review: boolean
  publish_status: string
  copyright_status: string
}

// ---------------------------------------------------------------------------
// Normalizers
// ---------------------------------------------------------------------------

function _normalizeStudentResource(
  res: ResourceRow,
  item: { sort_order: number },
): StudentResource {
  return {
    resource_id:            res.resource_key,
    resource_type:          res.resource_type,
    topic:                  res.topic,
    skill_name:             res.title,
    skill_type:             res.skill_type,
    difficulty:             res.difficulty,
    student_prompt:         res.student_prompt,
    options:                null,
    estimated_time_minutes: res.estimated_time_minutes,
    worked_solution:        res.worked_solution,
  }
}

function _synthesizeActivePackage(
  subject: NonNullable<Awaited<ReturnType<typeof _querySubject>>>,
  pkg: NonNullable<Awaited<ReturnType<typeof _queryActivePackage>>>,
): ActivePackage {
  return {
    content_key:                  subject.subject_slug,
    board:                        subject.board,
    level:                        subject.level,
    subject:                      subject.subject_name,
    syllabus_code:                subject.syllabus_code,
    active_package_id:            pkg.package_key,
    active_package_version:       String(pkg.version),
    active_package_status:        pkg.status,
    resource_count:               pkg.resource_count,
    student_payload_count:        pkg.student_resource_count,
    teacher_payload_count:        pkg.teacher_resource_count,
    teacher_only_resource_count:  pkg.teacher_resource_count - pkg.student_resource_count,
    estimated_total_time_minutes: 0,
    paths: {
      publish_package:  '',
      student_payload:  '',
      teacher_payload:  '',
      student_preview:  '',
      teacher_preview:  '',
    },
    previous_versions: [],
  }
}

// ---------------------------------------------------------------------------
// Live package result — used by the /system/supabase-live diagnostic page
// ---------------------------------------------------------------------------

export interface LivePackageResult {
  connected: boolean
  error?: string
  package_key?: string
  version?: number
  status?: string
  resource_count?: number
  student_resource_count?: number
  teacher_resource_count?: number
  needs_human_review_count?: number
  preview_resources?: Array<{
    resource_key: string
    title: string
    topic: string
    visibility: string
    needs_human_review: boolean
  }>
}

export async function getLiveSupabaseActivePackage(
  subjectSlug = DEFAULT_SUBJECT_SLUG,
): Promise<LivePackageResult> {
  if (!isLiveSupabaseConfigured()) {
    return {
      connected: false,
      error: 'Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env.local.',
    }
  }
  try {
    const client = requireSupabaseClient()
    const subject = await _querySubject(client, subjectSlug)
    if (!subject) {
      return { connected: true, error: `Subject '${subjectSlug}' not found in Supabase.` }
    }
    const pkg = await _queryActivePackage(client, subject.id)
    if (!pkg) {
      return { connected: true, error: `No active package found for '${subjectSlug}'.` }
    }
    const items = await _queryPackageItems(client, pkg.id)
    const ids = items.map((i) => i.resource_id)
    const byId = await _queryResourcesByIds(client, ids)

    let nhrCount = 0
    const preview: LivePackageResult['preview_resources'] = []
    for (const item of items) {
      const res = byId[item.resource_id]
      if (!res) continue
      if (res.needs_human_review) nhrCount++
      if (preview.length < 5) {
        preview.push({
          resource_key:       res.resource_key,
          title:              res.title,
          topic:              res.topic,
          visibility:         item.visibility,
          needs_human_review: res.needs_human_review,
        })
      }
    }

    return {
      connected:              true,
      package_key:            pkg.package_key,
      version:                pkg.version,
      status:                 pkg.status,
      resource_count:         pkg.resource_count,
      student_resource_count: pkg.student_resource_count,
      teacher_resource_count: pkg.teacher_resource_count,
      needs_human_review_count: nhrCount,
      preview_resources:      preview,
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return { connected: false, error: msg }
  }
}

// ---------------------------------------------------------------------------
// Public data API — compatible shapes with local / supabase_export modes
// ---------------------------------------------------------------------------

export async function getLiveSupabaseActiveContentIndex(
  subjectSlug = DEFAULT_SUBJECT_SLUG,
): Promise<ActiveContentIndex | null> {
  if (!isLiveSupabaseConfigured()) return null
  try {
    const client = requireSupabaseClient()
    const subject = await _querySubject(client, subjectSlug)
    if (!subject) return null
    const pkg = await _queryActivePackage(client, subject.id)
    if (!pkg) return null

    const activePkg = _synthesizeActivePackage(subject, pkg)
    const teacherOnly = pkg.teacher_resource_count - pkg.student_resource_count

    return {
      index_id:             'live_supabase',
      version:              String(pkg.version),
      status:               pkg.status,
      created_at:           new Date().toISOString(),
      source_registry_id:   'supabase_live',
      active_package_count: 1,
      active_packages:      [activePkg],
      summary: {
        active_package_count:          1,
        active_total_resources:        pkg.resource_count,
        active_student_resources:      pkg.student_resource_count,
        active_teacher_resources:      pkg.teacher_resource_count,
        active_teacher_only_resources: teacherOnly,
        archived_package_count:        0,
        all_registry_package_count:    1,
      },
    }
  } catch {
    return null
  }
}

export async function getLiveSupabaseStudentResources(
  subjectSlug = DEFAULT_SUBJECT_SLUG,
): Promise<{
  pkg: ActivePackage | null
  payload: StudentPayload | null
  resources: StudentResource[]
}> {
  if (!isLiveSupabaseConfigured()) return { pkg: null, payload: null, resources: [] }
  try {
    const client = requireSupabaseClient()
    const subject = await _querySubject(client, subjectSlug)
    if (!subject) return { pkg: null, payload: null, resources: [] }
    const pkg = await _queryActivePackage(client, subject.id)
    if (!pkg) return { pkg: null, payload: null, resources: [] }
    const items = await _queryPackageItems(client, pkg.id)
    const ids = items.map((i) => i.resource_id)
    const byId = await _queryResourcesByIds(client, ids)

    const resources: StudentResource[] = []
    for (const item of items) {
      if (item.visibility === 'teacher_only') continue
      const res = byId[item.resource_id]
      if (!res) continue
      resources.push(_normalizeStudentResource(res, item))
    }

    const activePkg = _synthesizeActivePackage(subject, pkg)
    const payload: StudentPayload = {
      package_id:     pkg.package_key,
      payload_type:   'student',
      created_at:     new Date().toISOString(),
      resource_count: resources.length,
      copyright_note: 'Original Quanta Aptus content. No Cambridge source text included.',
      resources,
    }

    return { pkg: activePkg, payload, resources }
  } catch {
    return { pkg: null, payload: null, resources: [] }
  }
}

export interface TeacherResource {
  resource_key: string
  title: string
  topic: string
  skill_type: string
  resource_type: string
  difficulty: string | null
  estimated_time_minutes: number | null
  student_prompt: string | null
  worked_solution: string | null
  marking_guidance: string | null
  common_misconceptions: string | null
  teacher_notes: string | null
  needs_human_review: boolean
  publish_status: string
  visibility: string
  sort_order: number
}

export async function getLiveSupabaseTeacherResources(
  subjectSlug = DEFAULT_SUBJECT_SLUG,
): Promise<{
  package_key: string | null
  resources: TeacherResource[]
  teacher_only_count: number
  needs_human_review_count: number
}> {
  if (!isLiveSupabaseConfigured()) {
    return { package_key: null, resources: [], teacher_only_count: 0, needs_human_review_count: 0 }
  }
  try {
    const client = requireSupabaseClient()
    const subject = await _querySubject(client, subjectSlug)
    if (!subject) return { package_key: null, resources: [], teacher_only_count: 0, needs_human_review_count: 0 }
    const pkg = await _queryActivePackage(client, subject.id)
    if (!pkg) return { package_key: null, resources: [], teacher_only_count: 0, needs_human_review_count: 0 }
    const items = await _queryPackageItems(client, pkg.id)
    const ids = items.map((i) => i.resource_id)
    const byId = await _queryResourcesByIds(client, ids)

    const resources: TeacherResource[] = []
    let teacherOnlyCount = 0
    let nhrCount = 0

    for (const item of items) {
      const res = byId[item.resource_id]
      if (!res) continue
      if (item.visibility === 'teacher_only') teacherOnlyCount++
      if (res.needs_human_review) nhrCount++
      resources.push({
        resource_key:           res.resource_key,
        title:                  res.title,
        topic:                  res.topic,
        skill_type:             res.skill_type,
        resource_type:          res.resource_type,
        difficulty:             res.difficulty,
        estimated_time_minutes: res.estimated_time_minutes,
        student_prompt:         res.student_prompt,
        worked_solution:        res.worked_solution,
        marking_guidance:       res.marking_guidance,
        common_misconceptions:  res.common_misconceptions,
        teacher_notes:          res.teacher_notes,
        needs_human_review:     res.needs_human_review,
        publish_status:         res.publish_status,
        visibility:             item.visibility,
        sort_order:             item.sort_order,
      })
    }

    return {
      package_key:            pkg.package_key,
      resources,
      teacher_only_count:     teacherOnlyCount,
      needs_human_review_count: nhrCount,
    }
  } catch {
    return { package_key: null, resources: [], teacher_only_count: 0, needs_human_review_count: 0 }
  }
}
