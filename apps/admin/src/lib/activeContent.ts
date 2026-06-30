import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import { getContentSourceMode } from './contentSource'
import { getSupabaseExportActiveContentIndex } from './supabaseExportContent'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ActivePackagePaths {
  publish_package: string
  student_payload: string
  teacher_payload: string
  student_preview: string
  teacher_preview: string
}

export interface PreviousVersion {
  package_id: string
  resource_count: number
  student_payload_count: number
  teacher_payload_count: number
}

export interface ActivePackage {
  content_key: string
  board: string
  level: string
  subject: string
  syllabus_code: string
  active_package_id: string
  active_package_version: string
  active_package_status: string
  resource_count: number
  student_payload_count: number
  teacher_payload_count: number
  teacher_only_resource_count: number
  estimated_total_time_minutes: number
  paths: ActivePackagePaths
  previous_versions: PreviousVersion[]
}

export interface ActiveIndexSummary {
  active_package_count: number
  active_total_resources: number
  active_student_resources: number
  active_teacher_resources: number
  active_teacher_only_resources: number
  archived_package_count: number
  all_registry_package_count: number
}

export interface ActiveContentIndex {
  index_id: string
  version: string
  status: string
  created_at: string
  source_registry_id: string
  active_package_count: number
  active_packages: ActivePackage[]
  summary: ActiveIndexSummary
}

// ---------------------------------------------------------------------------
// Repo root discovery (same MARKER strategy as contentRegistry.ts)
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

const REPO_ROOT = findRepoRoot()
const INDEX_PATH = path.join(REPO_ROOT, 'data', 'registry', 'active_content_index_v1.json')

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function getActiveContentIndex(): Promise<ActiveContentIndex | null> {
  if (getContentSourceMode() === 'supabase_export') {
    return getSupabaseExportActiveContentIndex()
  }
  try {
    const raw = await readFile(INDEX_PATH, 'utf-8')
    return JSON.parse(raw) as ActiveContentIndex
  } catch {
    return null
  }
}

export async function getActivePackages(): Promise<ActivePackage[]> {
  const index = await getActiveContentIndex()
  return index?.active_packages ?? []
}

export async function getActivePackageByContentKey(
  contentKey: string,
): Promise<ActivePackage | null> {
  const pkgs = await getActivePackages()
  return pkgs.find((p) => p.content_key === contentKey) ?? null
}
