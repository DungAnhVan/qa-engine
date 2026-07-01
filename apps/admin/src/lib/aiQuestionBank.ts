import fs from 'fs'
import path from 'path'

const ROOT = path.resolve(process.cwd(), '../..')

const BANK_FILE         = path.join(ROOT, 'data/ai/question_bank/ai_generated_question_bank_v1.json')
const REVIEW_QUEUE_FILE = path.join(ROOT, 'data/ai/teacher_review/ai_teacher_review_queue_v1.json')
const VALIDATION_FILE   = path.join(ROOT, 'data/diagnostics/ai_question_bank_validation_v1.json')
const REQUESTS_FILE     = path.join(ROOT, 'data/ai/generation_requests/ai_safe_generation_requests_v1.json')

export interface AiBankItem {
  bank_id:                 string
  request_id:              string
  batch_id:                string
  generated_at:            string
  subject_slug:            string
  syllabus_code?:          string
  topic:                   string
  subtopic?:               string
  skill_name?:             string
  skill_type?:             string
  difficulty?:             string
  resource_type?:          string
  learning_objective?:     string
  generated_text:          string
  provider:                string
  model?:                  string
  dry_run:                 boolean
  status:                  string
  teacher_review_required: boolean
  auto_publish_enabled:    boolean
  supabase_write_performed: boolean
}

export interface AiReviewQueueItem {
  bank_id:             string
  batch_id?:           string
  topic:               string
  subtopic?:           string
  skill_name?:         string
  skill_type?:         string
  difficulty?:         string
  resource_type?:      string
  learning_objective?: string
  generated_text:      string
  provider?:           string
  model?:              string
  dry_run:             boolean
  generated_at?:       string
  review_status:       string
  teacher_decision:    string | null
  teacher_notes:       string | null
  approval_required:   boolean
  auto_publish_enabled: boolean
}

export interface AiBankSummary {
  bank_exists:             boolean
  total_items:             number
  pending_review:          number
  batches:                 string[]
  teacher_review_required: boolean
  auto_publish_enabled:    boolean
  supabase_write_performed: boolean
  updated_at?:             string
  validation_valid?:       boolean | null
  request_count?:          number
  queue_count?:            number
}

function readJson<T>(filePath: string): T | null {
  try {
    if (!fs.existsSync(filePath)) return null
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as T
  } catch {
    return null
  }
}

export function readAiBankItems(): AiBankItem[] {
  const bank = readJson<{ items?: AiBankItem[] }>(BANK_FILE)
  return bank?.items ?? []
}

export function readAiReviewQueue(): AiReviewQueueItem[] {
  const queue = readJson<{ queue?: AiReviewQueueItem[] }>(REVIEW_QUEUE_FILE)
  return queue?.queue ?? []
}

export function getAiBankSummary(): AiBankSummary {
  const bank       = readJson<Record<string, unknown>>(BANK_FILE)
  const queue      = readJson<Record<string, unknown>>(REVIEW_QUEUE_FILE)
  const validation = readJson<Record<string, unknown>>(VALIDATION_FILE)
  const requests   = readJson<Record<string, unknown>>(REQUESTS_FILE)

  if (!bank) {
    return {
      bank_exists:             false,
      total_items:             0,
      pending_review:          0,
      batches:                 [],
      teacher_review_required: true,
      auto_publish_enabled:    false,
      supabase_write_performed: false,
      validation_valid:        null,
      request_count:           (requests?.request_count as number) ?? 0,
      queue_count:             0,
    }
  }

  return {
    bank_exists:             true,
    total_items:             (bank.total_count as number) ?? 0,
    pending_review:          (bank.pending_review as number) ?? 0,
    batches:                 (bank.batches_merged as string[]) ?? [],
    teacher_review_required: (bank.teacher_review_required as boolean) ?? true,
    auto_publish_enabled:    (bank.auto_publish_enabled as boolean) ?? false,
    supabase_write_performed: (bank.supabase_write_performed as boolean) ?? false,
    updated_at:              bank.updated_at as string | undefined,
    validation_valid:        validation ? (validation.valid as boolean) : null,
    request_count:           (requests?.request_count as number) ?? 0,
    queue_count:             (queue?.queue_count as number) ?? 0,
  }
}
