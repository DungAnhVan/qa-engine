/**
 * Server-side readers for the Supabase export snapshot.
 *
 * Reads pre-exported JSON files from data/supabase_exports/ — never touches
 * Supabase directly, never uses the service role key, never runs in the browser.
 *
 * Used by activeContent.ts and studentResources.ts when
 * QA_CONTENT_SOURCE=supabase_export is set.
 */
import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import type { ActiveContentIndex, ActivePackage } from './activeContent'
import type { StudentPayload, StudentResource } from './studentResources'

// ── Repo root (same sentinel strategy as other lib files) ────────────────────
const MARKER = path.join('data', 'registry', 'content_registry_v1.json')

function findRepoRoot(): string {
  let dir = process.cwd()
  for (let i = 0; i < 10; i++) {
    if (existsSync(path.join(dir, MARKER))) return dir
    const parent = path.dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return process.cwd()
}

const REPO_ROOT = findRepoRoot()
export const EXPORT_DIR = path.join(REPO_ROOT, 'data', 'supabase_exports')

const ACTIVE_PKG_FILE = path.join(EXPORT_DIR, 'active_package_from_supabase_v1.json')
const STUDENT_FILE    = path.join(EXPORT_DIR, 'student_resource_payload_from_supabase_v1.json')
const TEACHER_FILE    = path.join(EXPORT_DIR, 'teacher_resource_payload_from_supabase_v1.json')

// ── Raw Supabase export shapes (mirroring read_active_package_from_supabase_v1.py output) ──

interface SupabaseExportPackage {
  source: string
  exported_at: string
  subject_slug: string
  subject_name: string
  board: string
  level: string
  syllabus_code: string
  package_key: string
  version: number
  status: string
  resource_count: number
  student_resource_count: number
  teacher_resource_count: number
  published_at: string | null
  copyright_note: string
  resources: SupabaseExportResource[]
}

interface SupabaseStudentPayload {
  source: string
  exported_at: string
  payload_type: string
  subject_slug: string
  package_key: string
  resource_count: number
  copyright_note: string
  resources: SupabaseExportResource[]
}

interface SupabaseExportResource {
  resource_key: string
  title: string
  topic: string
  skill_type: string
  resource_type: string
  difficulty: string | null
  estimated_time_minutes: number | null
  student_prompt: string | null
  worked_solution: string | null
  sort_order: number
}

// ── Export file availability ─────────────────────────────────────────────────

export interface ExportFileStatus {
  active_package: boolean
  student_payload: boolean
  teacher_payload: boolean
  export_dir: string
  active_package_path: string
  student_payload_path: string
  teacher_payload_path: string
}

export function getExportFileStatus(): ExportFileStatus {
  return {
    active_package:       existsSync(ACTIVE_PKG_FILE),
    student_payload:      existsSync(STUDENT_FILE),
    teacher_payload:      existsSync(TEACHER_FILE),
    export_dir:           EXPORT_DIR,
    active_package_path:  ACTIVE_PKG_FILE,
    student_payload_path: STUDENT_FILE,
    teacher_payload_path: TEACHER_FILE,
  }
}

// ── Normalizer ───────────────────────────────────────────────────────────────

function normalizeStudentResource(r: SupabaseExportResource): StudentResource {
  return {
    resource_id:             r.resource_key,
    resource_type:           r.resource_type,
    topic:                   r.topic,
    skill_name:              r.title,   // Supabase export uses "title"; local JSON uses "skill_name"
    skill_type:              r.skill_type,
    difficulty:              r.difficulty,
    student_prompt:          r.student_prompt,
    options:                 null,      // MCQ options not in Supabase export (physics resources have none)
    estimated_time_minutes:  r.estimated_time_minutes,
    worked_solution:         r.worked_solution,
  }
}

function synthesizeActivePackage(ep: SupabaseExportPackage): ActivePackage {
  return {
    content_key:                  ep.subject_slug,
    board:                        ep.board,
    level:                        ep.level,
    subject:                      ep.subject_name,
    syllabus_code:                ep.syllabus_code,
    active_package_id:            ep.package_key,
    active_package_version:       String(ep.version),
    active_package_status:        ep.status,
    resource_count:               ep.resource_count,
    student_payload_count:        ep.student_resource_count,
    teacher_payload_count:        ep.teacher_resource_count,
    teacher_only_resource_count:  ep.teacher_resource_count - ep.student_resource_count,
    estimated_total_time_minutes: 0,
    paths: {
      publish_package:  '',
      student_payload:  STUDENT_FILE,
      teacher_payload:  TEACHER_FILE,
      student_preview:  '',
      teacher_preview:  '',
    },
    previous_versions: [],
  }
}

// ── Public API ───────────────────────────────────────────────────────────────

export async function getSupabaseExportPackageData(): Promise<SupabaseExportPackage | null> {
  try {
    const raw = await readFile(ACTIVE_PKG_FILE, 'utf-8')
    return JSON.parse(raw) as SupabaseExportPackage
  } catch {
    return null
  }
}

export async function getSupabaseExportActiveContentIndex(): Promise<ActiveContentIndex | null> {
  const ep = await getSupabaseExportPackageData()
  if (!ep) return null

  const pkg = synthesizeActivePackage(ep)
  const teacherOnly = ep.teacher_resource_count - ep.student_resource_count

  return {
    index_id:             'supabase_export',
    version:              String(ep.version),
    status:               ep.status,
    created_at:           ep.exported_at,
    source_registry_id:   'supabase',
    active_package_count: 1,
    active_packages:      [pkg],
    summary: {
      active_package_count:          1,
      active_total_resources:        ep.resource_count,
      active_student_resources:      ep.student_resource_count,
      active_teacher_resources:      ep.teacher_resource_count,
      active_teacher_only_resources: teacherOnly,
      archived_package_count:        0,
      all_registry_package_count:    1,
    },
  }
}

export async function getSupabaseExportStudentResources(): Promise<{
  pkg: ActivePackage | null
  payload: StudentPayload | null
  resources: StudentResource[]
}> {
  const ep = await getSupabaseExportPackageData()
  if (!ep) return { pkg: null, payload: null, resources: [] }

  try {
    const raw = await readFile(STUDENT_FILE, 'utf-8')
    const exportPayload = JSON.parse(raw) as SupabaseStudentPayload
    const resources = (exportPayload.resources ?? []).map(normalizeStudentResource)

    const payload: StudentPayload = {
      package_id:     exportPayload.package_key,
      payload_type:   'student',
      created_at:     exportPayload.exported_at,
      resource_count: resources.length,
      copyright_note: exportPayload.copyright_note,
      resources,
    }

    return { pkg: synthesizeActivePackage(ep), payload, resources }
  } catch {
    return { pkg: synthesizeActivePackage(ep), payload: null, resources: [] }
  }
}
