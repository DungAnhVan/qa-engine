/**
 * Gate 69E — AI Package Candidate helpers (server-only).
 *
 * Reads local JSON files produced by the Python package builder scripts.
 * No secrets. No Supabase writes. No AI API calls.
 */

import fs from 'fs'
import path from 'path'

function dataRoot(): string {
  return path.join(process.cwd(), '..', '..', 'data')
}

function pkgCandidatePath(): string {
  return path.join(dataRoot(), 'ai', 'package_candidates',
    'ai_resource_package_candidate_v1.json')
}

function studentPayloadPath(): string {
  return path.join(dataRoot(), 'ai', 'package_candidates',
    'student_ai_package_payload_v1.json')
}

function teacherPayloadPath(): string {
  return path.join(dataRoot(), 'ai', 'package_candidates',
    'teacher_ai_package_payload_v1.json')
}

function validationReportPath(): string {
  return path.join(dataRoot(), 'diagnostics',
    'ai_package_candidate_validation_report_v1.json')
}

function studentPreviewPath(): string {
  return path.join(dataRoot(), 'ai', 'package_candidates', 'static_preview',
    'student_ai_package_preview_v1.html')
}

function teacherPreviewPath(): string {
  return path.join(dataRoot(), 'ai', 'package_candidates', 'static_preview',
    'teacher_ai_package_preview_v1.html')
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PackageResource {
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

export interface PackageCandidate {
  package_candidate_id:          string
  version:                       string
  status:                        string
  created_at:                    string
  source:                        string
  auto_publish_enabled:          boolean
  supabase_write_performed:      boolean
  teacher_final_publish_required: boolean
  resource_count:                number
  student_payload_count:         number
  teacher_payload_count:         number
  resources:                     PackageResource[]
}

export interface PayloadFile {
  payload_id:                    string
  payload_type:                  'student' | 'teacher'
  generated_at:                  string
  resource_count:                number
  auto_publish_enabled:          boolean
  teacher_final_publish_required: boolean
  resources:                     Partial<PackageResource>[]
}

export interface ValidationReport {
  valid:                         boolean
  status:                        string
  resource_count:                number
  resources_valid:               number
  auto_publish_enabled:          boolean
  teacher_final_publish_required: boolean
  issues:                        string[]
}

export interface AiPackageCandidateSummary {
  package_candidate_exists:      boolean
  student_payload_exists:        boolean
  teacher_payload_exists:        boolean
  student_preview_exists:        boolean
  teacher_preview_exists:        boolean
  validation_report_exists:      boolean
  validation_passed:             boolean
  resource_count:                number
  student_payload_count:         number
  teacher_payload_count:         number
  status:                        string
  auto_publish_enabled:          false
  supabase_write_performed:      false
  teacher_final_publish_required: true
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

export function readAiPackageCandidate(): PackageCandidate | null {
  return readJson<PackageCandidate>(pkgCandidatePath())
}

export function readAiStudentPayload(): PayloadFile | null {
  return readJson<PayloadFile>(studentPayloadPath())
}

export function readAiTeacherPayload(): PayloadFile | null {
  return readJson<PayloadFile>(teacherPayloadPath())
}

export function readAiPackageValidationReport(): ValidationReport | null {
  return readJson<ValidationReport>(validationReportPath())
}

// ---------------------------------------------------------------------------
// Summary helper
// ---------------------------------------------------------------------------

export function getAiPackageCandidateSummary(): AiPackageCandidateSummary {
  const pkg        = readAiPackageCandidate()
  const student    = readAiStudentPayload()
  const teacher    = readAiTeacherPayload()
  const validation = readAiPackageValidationReport()

  return {
    package_candidate_exists:      pkg !== null,
    student_payload_exists:        student !== null,
    teacher_payload_exists:        teacher !== null,
    student_preview_exists:        fs.existsSync(studentPreviewPath()),
    teacher_preview_exists:        fs.existsSync(teacherPreviewPath()),
    validation_report_exists:      validation !== null,
    validation_passed:             validation?.valid ?? false,
    resource_count:                pkg?.resource_count ?? 0,
    student_payload_count:         student?.resource_count ?? 0,
    teacher_payload_count:         teacher?.resource_count ?? 0,
    status:                        pkg?.status ?? 'not_created',
    auto_publish_enabled:          false,
    supabase_write_performed:      false,
    teacher_final_publish_required: true,
  }
}
