/**
 * Gate 69F — AI Published Package helpers (server-only).
 *
 * Reads local JSON files from data/ai/published/ produced by the Python
 * local publish scripts. No secrets. No Supabase writes. No AI API calls.
 */

import fs from 'fs'
import path from 'path'

function dataRoot(): string {
  return path.join(process.cwd(), '..', '..', 'data')
}

function publishedDir(): string {
  return path.join(dataRoot(), 'ai', 'published', 'ai_resource_package_v1')
}

function publishedPkgPath(): string {
  return path.join(publishedDir(), 'publish_package_v1.json')
}

function studentPayloadPath(): string {
  return path.join(publishedDir(), 'student_resource_payload_v1.json')
}

function teacherPayloadPath(): string {
  return path.join(publishedDir(), 'teacher_resource_payload_v1.json')
}

function localRegistryPath(): string {
  return path.join(dataRoot(), 'ai', 'registry', 'ai_content_registry_v1.json')
}

function validationReportPath(): string {
  return path.join(dataRoot(), 'diagnostics',
    'ai_local_published_package_validation_report_v1.json')
}

function approvalFilePath(): string {
  return path.join(dataRoot(), 'ai', 'package_candidates',
    'ai_final_publish_approval_v1.json')
}

function studentPreviewPath(): string {
  return path.join(publishedDir(), 'static_preview',
    'student_ai_published_package_preview_v1.html')
}

function teacherPreviewPath(): string {
  return path.join(publishedDir(), 'static_preview',
    'teacher_ai_published_package_preview_v1.html')
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PublishedResource {
  resource_id:          string
  resource_type:        string
  title:                string
  topic:                string
  skill_name:           string
  skill_type:           string
  difficulty:           string
  estimated_time_minutes: number
  student_prompt:       string
  student_instructions: string
  answer_key:           string
  marking_rubric:       Array<{ criterion: string; marks: number; guidance?: string }>
  teacher_notes:        string
  safety_declaration:   {
    original_content:         boolean
    no_raw_source_text_used:  boolean
    no_mark_scheme_copied:    boolean
  }
  provenance: {
    origin:                     string
    approved_by_teacher_review: boolean
    reviewer_id:                string
    no_raw_source_text_used:    boolean
  }
}

export interface PublishedPackage {
  package_id:               string
  version:                  string
  status:                   string
  published_at:             string
  approved_by:              string | null
  active_content:           boolean
  supabase_write_performed: boolean
  teacher_final_approval:   boolean
  allow_active_switch:      boolean
  allow_supabase_sync:      boolean
  resource_count:           number
  resources:                PublishedResource[]
}

export interface PublishedPayload {
  payload_id:               string
  payload_type:             'student' | 'teacher'
  package_id:               string
  status:                   string
  resource_count:           number
  active_content:           boolean
  resources:                Partial<PublishedResource>[]
}

export interface LocalRegistry {
  registry_id:    string
  updated_at:     string
  package_count:  number
  packages:       Array<{
    package_id:     string
    status:         string
    active_content: boolean
    resource_count: number
    path:           string
  }>
}

export interface ValidationReport {
  valid:                         boolean
  status:                        string
  resource_count:                number
  active_content:                boolean
  supabase_write_performed:      boolean
  teacher_final_approval:        boolean
}

export interface FinalApproval {
  approval_status:    string
  approved_by:        string | null
  allow_local_publish: boolean
  allow_active_switch: boolean
  allow_supabase_sync: boolean
}

export interface AiPublishedPackageSummary {
  approval_exists:              boolean
  approval_status:              string
  local_published_package_exists: boolean
  student_payload_exists:       boolean
  teacher_payload_exists:       boolean
  student_preview_exists:       boolean
  teacher_preview_exists:       boolean
  registry_exists:              boolean
  validation_passed:            boolean
  resource_count:               number
  status:                       string
  active_content:               false
  supabase_write_performed:     false
  teacher_final_approval:       true
  ready_for_gate69g:            boolean
}

// ---------------------------------------------------------------------------
// Readers — safe fallback if files missing
// ---------------------------------------------------------------------------

function readJson<T>(filePath: string): T | null {
  try {
    if (!fs.existsSync(filePath)) return null
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as T
  } catch {
    return null
  }
}

export function readAiPublishedPackage(): PublishedPackage | null {
  return readJson<PublishedPackage>(publishedPkgPath())
}

export function readAiPublishedStudentPayload(): PublishedPayload | null {
  return readJson<PublishedPayload>(studentPayloadPath())
}

export function readAiPublishedTeacherPayload(): PublishedPayload | null {
  return readJson<PublishedPayload>(teacherPayloadPath())
}

export function readAiLocalRegistry(): LocalRegistry | null {
  return readJson<LocalRegistry>(localRegistryPath())
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

export function getAiPublishedPackageSummary(): AiPublishedPackageSummary {
  const approval   = readJson<FinalApproval>(approvalFilePath())
  const pkg        = readAiPublishedPackage()
  const student    = readAiPublishedStudentPayload()
  const teacher    = readAiPublishedTeacherPayload()
  const registry   = readAiLocalRegistry()
  const validation = readJson<ValidationReport>(validationReportPath())

  const validationPassed = validation?.valid ?? false
  const pkgExists        = pkg !== null

  return {
    approval_exists:              approval !== null,
    approval_status:              approval?.approval_status ?? 'not_created',
    local_published_package_exists: pkgExists,
    student_payload_exists:       student !== null,
    teacher_payload_exists:       teacher !== null,
    student_preview_exists:       fs.existsSync(studentPreviewPath()),
    teacher_preview_exists:       fs.existsSync(teacherPreviewPath()),
    registry_exists:              registry !== null,
    validation_passed:            validationPassed,
    resource_count:               pkg?.resource_count ?? 0,
    status:                       pkg?.status ?? 'not_created',
    active_content:               false,
    supabase_write_performed:     false,
    teacher_final_approval:       true,
    ready_for_gate69g:            pkgExists && validationPassed && (registry !== null),
  }
}
