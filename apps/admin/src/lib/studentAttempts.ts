import { readFile, writeFile, mkdir } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import crypto from 'crypto'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface StudentAttempt {
  attempt_id: string
  created_at: string
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
  self_confidence: 'low' | 'medium' | 'high' | null
  attempt_type: 'first_attempt' | 'resubmission'
  parent_attempt_id: string | null
  resubmission_of: string | null
  status: 'submitted'
  marking_status: 'unmarked'
}

export type AttemptInput = Omit<
  StudentAttempt,
  | 'attempt_id'
  | 'created_at'
  | 'student_id'
  | 'status'
  | 'marking_status'
  | 'attempt_type'
  | 'parent_attempt_id'
  | 'resubmission_of'
> & {
  attempt_type?: 'first_attempt' | 'resubmission'
  parent_attempt_id?: string | null
  resubmission_of?: string | null
}

export interface AttemptsFile {
  attempt_file_id: string
  version: string
  created_at: string
  updated_at: string
  attempts: StudentAttempt[]
}

export interface AttemptSummary {
  total: number
  submitted: number
  unmarked: number
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
const ATTEMPTS_FILE = path.join(ATTEMPTS_DIR, 'student_attempts_v1.json')

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function createAttemptId(): string {
  const ts = Date.now().toString(36)
  const rand = crypto.randomBytes(4).toString('hex')
  return `attempt_${ts}_${rand}`
}

function emptyFile(now: string): AttemptsFile {
  return {
    attempt_file_id: 'quanta_aptus_local_student_attempts_v1',
    version: '0.1.0',
    created_at: now,
    updated_at: now,
    attempts: [],
  }
}

export async function getStudentAttempts(): Promise<AttemptsFile> {
  try {
    const raw = await readFile(ATTEMPTS_FILE, 'utf-8')
    return JSON.parse(raw) as AttemptsFile
  } catch {
    const now = new Date().toISOString()
    return emptyFile(now)
  }
}

export async function saveStudentAttempt(input: AttemptInput): Promise<StudentAttempt> {
  await mkdir(ATTEMPTS_DIR, { recursive: true })

  const file = await getStudentAttempts()
  const now = new Date().toISOString()

  const attempt: StudentAttempt = {
    attempt_id: createAttemptId(),
    created_at: now,
    student_id: 'local_demo_student',
    ...input,
    attempt_type: input.attempt_type ?? 'first_attempt',
    parent_attempt_id: input.parent_attempt_id ?? null,
    resubmission_of: input.resubmission_of ?? null,
    status: 'submitted',
    marking_status: 'unmarked',
  }

  file.attempts.push(attempt)
  file.updated_at = now

  await writeFile(ATTEMPTS_FILE, JSON.stringify(file, null, 2), 'utf-8')
  return attempt
}

export function getAttemptSummary(file: AttemptsFile): AttemptSummary {
  return {
    total: file.attempts.length,
    submitted: file.attempts.filter((a) => a.status === 'submitted').length,
    unmarked: file.attempts.filter((a) => a.marking_status === 'unmarked').length,
  }
}
