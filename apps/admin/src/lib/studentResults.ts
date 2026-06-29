import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TopicSummary {
  topic: string
  attempt_count: number
  auto_marked_count: number
  // v2 fields
  teacher_reviewed_count?: number
  pending_teacher_review_count?: number
  partially_correct_count?: number
  needs_resubmission_count?: number
  // v1 compat
  teacher_review_required_count?: number
  correct_count: number
  incorrect_count: number
  accuracy: number | null
}

export interface SkillTypeSummary {
  skill_type: string
  attempt_count: number
  auto_marked_count: number
  correct_count: number
  incorrect_count: number
  teacher_review_required_count?: number
  teacher_reviewed_count?: number
  needs_resubmission_count?: number
  accuracy: number | null
}

export interface SkillGap {
  gap_id: string
  topic: string
  skill_name: string
  skill_type: string
  difficulty: string
  reason: string
  severity: 'low' | 'medium' | 'high'
  evidence: string
  recommended_action: string
}

export interface Strength {
  topic: string
  skill_name: string
  skill_type: string
  evidence: string
  note: string
}

export interface ReviewQueueItem {
  attempt_id: string
  resource_id: string
  topic: string
  skill_name: string
  resource_type: string
  student_answer: string
  feedback: string
  reason: string
}

export interface ResubmissionQueueItem {
  attempt_id: string
  resource_id: string
  topic: string
  skill_name: string
  resource_type: string
  student_answer: string
  teacher_feedback: string
  teacher_notes?: string
  recommended_action: string
}

export interface ReportMeta {
  report_version: 'v1' | 'v2'
  report_path: string
  is_latest: boolean
}

export interface StudentResultReport extends ReportMeta {
  report_id: string
  version: string
  created_at: string
  student_id: string
  source_marked_attempts: string
  attempt_count: number
  auto_marked_count: number
  // v1
  teacher_review_required_count?: number
  // v2
  teacher_reviewed_count?: number
  pending_teacher_review_count?: number
  partially_correct_count?: number
  needs_resubmission_count?: number
  correct_count: number
  incorrect_count: number
  accuracy: number | null
  topics: TopicSummary[]
  skill_types: SkillTypeSummary[]
  confidence_signals: Record<string, number>
  skill_gaps: SkillGap[]
  review_queue?: ReviewQueueItem[]
  resubmission_queue?: ResubmissionQueueItem[]
  strengths: Strength[]
  recommended_next_actions: string[]
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

const REPO_ROOT = findRepoRoot()
const REPORTS_DIR = path.join(REPO_ROOT, 'data', 'attempts', 'local', 'reports')

const REPORT_VERSIONS: Array<['v2' | 'v1', string]> = [
  ['v2', path.join(REPORTS_DIR, 'student_result_report_v2.json')],
  ['v1', path.join(REPORTS_DIR, 'student_result_report_v1.json')],
]

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function listAvailableStudentResultReports(): Array<{
  version: 'v1' | 'v2'
  report_path: string
  exists: boolean
}> {
  return REPORT_VERSIONS.map(([version, p]) => ({
    version,
    report_path: p,
    exists: existsSync(p),
  }))
}

export async function getLatestStudentResultReport(
  studentId = 'local_demo_student',
): Promise<StudentResultReport | null> {
  for (const [version, filePath] of REPORT_VERSIONS) {
    if (!existsSync(filePath)) continue
    try {
      const raw = await readFile(filePath, 'utf-8')
      const data = JSON.parse(raw)
      if (data.student_id && data.student_id !== studentId) continue
      return {
        ...data,
        report_version: version,
        report_path: filePath,
        is_latest: true,
      } as StudentResultReport
    } catch {
      continue
    }
  }
  return null
}

export async function getStudentResultReport(): Promise<StudentResultReport | null> {
  return getLatestStudentResultReport()
}

export async function getResubmissionItem(
  parentAttemptId: string,
): Promise<ResubmissionQueueItem | null> {
  const report = await getLatestStudentResultReport()
  if (!report?.resubmission_queue) return null
  return report.resubmission_queue.find((q) => q.attempt_id === parentAttemptId) ?? null
}

export function getStudentResultReportPath(): string {
  return REPORT_VERSIONS[0][1]
}
