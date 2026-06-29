import { readFile, writeFile, mkdir } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'

// ─── Repo root (same MARKER strategy as contentRegistry) ──────────────────────
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
const REVIEW_DIR = path.join(
  REPO_ROOT,
  'data',
  'bank',
  'cambridge_igcse',
  'physics_0625',
  'teacher_review',
)
const QUEUE_FILE = path.join(REVIEW_DIR, 'teacher_review_queue_v1.json')
const DECISIONS_FILE = path.join(REVIEW_DIR, 'teacher_review_decisions_v1.json')

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ReviewItem {
  review_id: string
  bank_item_id: string
  resource_id: string
  resource_type: string
  component_type: string
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
  validation_warnings: string[]
  validation_errors: string[]
  review_status: string
  teacher_decision: string | null
  teacher_notes: string
  suggested_action: string | null
}

export interface ReviewQueue {
  queue_id: string
  version: string
  status: string
  created_at: string
  source_bank_id: string
  board: string
  level: string
  subject: string
  syllabus_code: string
  review_item_count: number
  items: ReviewItem[]
}

export type DecisionValue = 'approved' | 'revise' | 'rejected'

export interface Decision {
  review_id: string
  bank_item_id: string
  resource_id: string
  decision: DecisionValue
  teacher_notes: string
  decided_at: string
  decided_by: string
}

export interface DecisionFile {
  decision_file_id: string
  version: string
  created_at: string
  updated_at: string
  source_queue_id: string
  decisions: Decision[]
}

export interface ReviewSummary {
  total: number
  pending: number
  approved: number
  revise: number
  rejected: number
}

// ─── Readers ──────────────────────────────────────────────────────────────────

export async function getTeacherReviewQueue(): Promise<ReviewQueue | null> {
  try {
    const raw = await readFile(QUEUE_FILE, 'utf-8')
    return JSON.parse(raw) as ReviewQueue
  } catch {
    return null
  }
}

export async function getTeacherReviewDecisions(): Promise<DecisionFile> {
  try {
    const raw = await readFile(DECISIONS_FILE, 'utf-8')
    return JSON.parse(raw) as DecisionFile
  } catch {
    const now = new Date().toISOString()
    return {
      decision_file_id: 'cambridge_igcse_physics_0625_teacher_review_decisions_v1',
      version: '0.1.0',
      created_at: now,
      updated_at: now,
      source_queue_id: 'cambridge_igcse_physics_0625_teacher_review_queue_v1',
      decisions: [],
    }
  }
}

// ─── Writer ───────────────────────────────────────────────────────────────────

export async function saveTeacherReviewDecision(
  input: Omit<Decision, 'decided_at' | 'decided_by'>,
): Promise<void> {
  const file = await getTeacherReviewDecisions()
  const now = new Date().toISOString()

  const decision: Decision = { ...input, decided_at: now, decided_by: 'admin_local' }

  const idx = file.decisions.findIndex((d) => d.review_id === input.review_id)
  if (idx >= 0) {
    file.decisions[idx] = decision
  } else {
    file.decisions.push(decision)
  }
  file.updated_at = now

  await mkdir(REVIEW_DIR, { recursive: true })
  await writeFile(DECISIONS_FILE, JSON.stringify(file, null, 2), 'utf-8')
}

// ─── Summary ──────────────────────────────────────────────────────────────────

export function getReviewSummary(
  items: ReviewItem[],
  decisions: Decision[],
): ReviewSummary {
  const dm = new Map(decisions.map((d) => [d.review_id, d.decision]))
  let pending = 0, approved = 0, revise = 0, rejected = 0
  for (const item of items) {
    const d = dm.get(item.review_id)
    if (!d) pending++
    else if (d === 'approved') approved++
    else if (d === 'revise') revise++
    else rejected++
  }
  return { total: items.length, pending, approved, revise, rejected }
}
