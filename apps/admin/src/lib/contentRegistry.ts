import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import { getContentSourceMode, type ContentSourceMode } from './contentSource'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ResourceItem {
  resource_id: string
  resource_type: string
  topic: string
  skill_name: string
  skill_type: string
  difficulty: string | null
  student_prompt: string | null
  options: Record<string, string | null> | null
  correct_answer: string | null
  worked_solution: string | null
  marking_guidance: string | null
  common_misconception: string | null
  teacher_note: string | null
  estimated_time_minutes: number | null
  validation_status?: string
  bank_status?: string
}

export interface PackageDetail {
  pkg: RegistryPackage
  teacherResources: ResourceItem[]
  studentResourceCount: number
  teacherMissing: boolean
  studentMissing: boolean
}

export interface RegistryPackage {
  package_id: string
  package_version: string
  package_status: string
  board: string
  level: string
  subject: string
  syllabus_code: string
  title: string
  content_origin: string
  copyright_status: string
  resource_count: number
  student_payload_count: number | null
  teacher_payload_count: number | null
  teacher_only_resource_count: number | null
  estimated_total_time_minutes: number
  resource_types: Record<string, number>
  component_types: Record<string, number>
  topics: Record<string, number>
  skill_types: Record<string, number>
  difficulties: Record<string, number>
  paths: {
    publish_package: string
    student_payload: string
    teacher_payload: string
    package_report: string
    package_manifest: string
    student_preview: string
    teacher_preview: string
  }
  availability: Record<string, boolean>
  app_visibility: {
    student_visible: boolean
    teacher_visible: boolean
    admin_visible: boolean
  }
  registered_at: string
}

export interface RegistrySummary {
  boards: Record<string, number>
  levels: Record<string, number>
  subjects: Record<string, number>
  syllabus_codes: Record<string, number>
  total_packages: number
  total_resources: number
  total_student_resources: number
  total_teacher_resources: number
  total_teacher_only_resources: number
  estimated_total_time_minutes: number
  topics: Record<string, number>
  resource_types: Record<string, number>
}

export interface ContentRegistry {
  registry_id: string
  version: string
  status: string
  created_at: string
  package_count: number
  packages: RegistryPackage[]
  summary: RegistrySummary
}

export interface RegistryResult {
  registry: ContentRegistry
  repoRoot: string
  sourceMode: ContentSourceMode
}

// ---------------------------------------------------------------------------
// Repo root discovery
// ---------------------------------------------------------------------------

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

// Computed once at module load (server-side only)
const REPO_ROOT = findRepoRoot()

// ---------------------------------------------------------------------------
// Path helpers
// ---------------------------------------------------------------------------

/** Convert an absolute path from the registry into a repo-relative forward-slash path. */
export function toRelativePath(absPath: string): string {
  if (!absPath) return ''
  const normalized = absPath.replace(/\\/g, '/')
  const rootNorm = REPO_ROOT.replace(/\\/g, '/').replace(/\/$/, '') + '/'
  if (normalized.startsWith(rootNorm)) {
    return normalized.slice(rootNorm.length)
  }
  // Fallback: strip drive + leading separator if path is absolute
  return normalized.replace(/^[A-Za-z]:\//, '')
}

/** Return the URL path for the /api/files proxy route. */
export function fileApiUrl(absPath: string): string {
  const rel = toRelativePath(absPath)
  return rel ? `/api/files?p=${encodeURIComponent(rel)}` : '#'
}

// ---------------------------------------------------------------------------
// Registry loader
// ---------------------------------------------------------------------------

const EMPTY_SUMMARY: RegistrySummary = {
  boards: {},
  levels: {},
  subjects: {},
  syllabus_codes: {},
  total_packages: 0,
  total_resources: 0,
  total_student_resources: 0,
  total_teacher_resources: 0,
  total_teacher_only_resources: 0,
  estimated_total_time_minutes: 0,
  topics: {},
  resource_types: {},
}

const EMPTY_REGISTRY: ContentRegistry = {
  registry_id: 'quanta_aptus_content_registry_v1',
  version: '0.1.0',
  status: 'empty',
  created_at: new Date().toISOString(),
  package_count: 0,
  packages: [],
  summary: EMPTY_SUMMARY,
}

export async function getContentRegistry(): Promise<RegistryResult> {
  const sourceMode = getContentSourceMode()
  try {
    const registryPath = path.join(REPO_ROOT, 'data', 'registry', 'content_registry_v1.json')
    const raw = await readFile(registryPath, 'utf-8')
    const registry = JSON.parse(raw) as ContentRegistry
    return { registry, repoRoot: REPO_ROOT, sourceMode }
  } catch {
    return { registry: EMPTY_REGISTRY, repoRoot: REPO_ROOT, sourceMode }
  }
}

// ---------------------------------------------------------------------------
// Package detail helpers
// ---------------------------------------------------------------------------

export async function readJsonFileSafe<T>(absPath: string): Promise<T | null> {
  if (!absPath) return null
  try {
    const raw = await readFile(absPath, 'utf-8')
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

export async function getPackageById(packageId: string): Promise<RegistryPackage | null> {
  const { registry } = await getContentRegistry()
  return registry.packages.find((p) => p.package_id === packageId) ?? null
}

export async function getPackageDetail(packageId: string): Promise<PackageDetail | null> {
  const pkg = await getPackageById(packageId)
  if (!pkg) return null

  type TeacherDoc = { resource_count: number; resources: ResourceItem[] }
  type StudentDoc = { resource_count: number }

  const [teacherDoc, studentDoc] = await Promise.all([
    readJsonFileSafe<TeacherDoc>(pkg.paths.teacher_payload),
    readJsonFileSafe<StudentDoc>(pkg.paths.student_payload),
  ])

  return {
    pkg,
    teacherResources: teacherDoc?.resources ?? [],
    studentResourceCount: studentDoc?.resource_count ?? pkg.student_payload_count ?? 0,
    teacherMissing: !teacherDoc,
    studentMissing: !studentDoc,
  }
}
