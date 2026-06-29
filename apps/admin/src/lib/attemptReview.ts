import { readFile, writeFile, mkdir } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AttemptDecisionValue =
  | 'correct'
  | 'partially_correct'
  | 'incorrect'
  | 'needs_resubmission'

export interface AttemptDecision {
  decision_id: string
  marked_attempt_id: string
  attempt_id: string
  student_id: string
  resource_id: string
  decision: AttemptDecisionValue
  score: number | null
  max_score: number
  teacher_feedback: string
  teacher_notes: string
  decided_at: string
  decided_by: string
}

export type AttemptDecisionInput = Omit<
  AttemptDecision,
  'decision_id' | 'decided_at' | 'decided_by'
>

export interface AttemptDecisionFile {
  decision_file_id: string
  version: string
  created_at: string
  updated_at: string
  source_marked_attempts: string
  decisions: AttemptDecision[]
}

export interface TeacherReference {
  correct_answer: string | null
  worked_solution: string | null
  marking_guidance: string | null
  common_misconception: string | null
}

export interface MarkedAttemptItem {
  marked_attempt_id: string
  attempt_id: string
  student_id: string
  package_id: string
  resource_id: string
  resource_type: string
  topic: string
  skill_name: string
  skill_type: string
  difficulty: string | null
  student_answer: string
  selected_option: string | null
  self_confidence: string | null
  marking_status: string
  score: number | null
  max_score: number
  is_correct: boolean | null
  feedback: string
  needs_teacher_review: boolean
  teacher_reference: TeacherReference
  confidence_signal: string
}

export interface MarkedAttemptsFile {
  marked_attempt_file_id: string
  version: string
  attempt_count: number
  auto_marked_count: number
  teacher_review_required_count: number
  items: MarkedAttemptItem[]
}

export interface AttemptReviewSummary {
  total: number
  auto_marked: number
  review_required: number
  pending_review: number
  reviewed: number
  correct_after_review: number
  needs_resubmission: number
}

// ---------------------------------------------------------------------------
// Repo root + paths
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
const ATTEMPTS_DIR = path.join(REPO_ROOT, 'data', 'attempts', 'local')
const MARKED_FILE  = path.join(ATTEMPTS_DIR, 'marked_attempts_v1.json')
const DECISIONS_FILE = path.join(ATTEMPTS_DIR, 'teacher_attempt_review_decisions_v1.json')

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function getMarkedAttempts(): Promise<MarkedAttemptsFile | null> {
  try {
    const raw = await readFile(MARKED_FILE, 'utf-8')
    return JSON.parse(raw) as MarkedAttemptsFile
  } catch {
    return null
  }
}

export async function getTeacherAttemptReviewDecisions(): Promise<AttemptDecisionFile> {
  try {
    const raw = await readFile(DECISIONS_FILE, 'utf-8')
    return JSON.parse(raw) as AttemptDecisionFile
  } catch {
    const now = new Date().toISOString()
    return {
      decision_file_id: 'quanta_aptus_teacher_attempt_review_decisions_v1',
      version: '0.1.0',
      created_at: now,
      updated_at: now,
      source_marked_attempts: MARKED_FILE,
      decisions: [],
    }
  }
}

export async function saveTeacherAttemptReviewDecision(
  input: AttemptDecisionInput,
): Promise<AttemptDecision> {
  const file = await getTeacherAttemptReviewDecisions()
  const now = new Date().toISOString()

  const decision: AttemptDecision = {
    decision_id: `decision_${input.marked_attempt_id}`,
    ...input,
    decided_at: now,
    decided_by: 'teacher_local',
  }

  const idx = file.decisions.findIndex(
    (d) => d.marked_attempt_id === input.marked_attempt_id,
  )
  if (idx >= 0) {
    file.decisions[idx] = decision
  } else {
    file.decisions.push(decision)
  }
  file.updated_at = now

  await mkdir(ATTEMPTS_DIR, { recursive: true })
  await writeFile(DECISIONS_FILE, JSON.stringify(file, null, 2), 'utf-8')
  return decision
}

export function getAttemptReviewSummary(
  items: MarkedAttemptItem[],
  decisions: AttemptDecision[],
): AttemptReviewSummary {
  const dm = new Map(decisions.map((d) => [d.marked_attempt_id, d]))

  const reviewItems = items.filter(
    (i) => i.marking_status === 'teacher_review_required' || i.needs_teacher_review,
  )

  let pending = 0, reviewed = 0, correct_after = 0, resubmit = 0
  for (const item of reviewItems) {
    const d = dm.get(item.marked_attempt_id)
    if (!d) {
      pending++
    } else {
      reviewed++
      if (d.decision === 'correct' || d.decision === 'partially_correct') correct_after++
      if (d.decision === 'needs_resubmission') resubmit++
    }
  }

  return {
    total:               items.length,
    auto_marked:         items.filter((i) => i.marking_status === 'auto_marked').length,
    review_required:     reviewItems.length,
    pending_review:      pending,
    reviewed,
    correct_after_review: correct_after,
    needs_resubmission:  resubmit,
  }
}
