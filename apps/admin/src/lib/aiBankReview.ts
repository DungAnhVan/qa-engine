import fs from 'fs'
import path from 'path'

const ROOT = path.resolve(process.cwd(), '../..')

const QUEUE_FILE      = path.join(ROOT, 'data/ai/teacher_review/ai_teacher_review_queue_v1.json')
const DECISIONS_FILE  = path.join(ROOT, 'data/ai/review/gate70b_ai_bank_review_decisions_v1.json')
const APPROVED_FILE   = path.join(ROOT, 'data/ai/approved/gate70b_approved_ai_bank_items_v1.json')
const REVISION_FILE   = path.join(ROOT, 'data/ai/revision/gate70b_ai_bank_revision_items_v1.json')
const REJECTED_FILE   = path.join(ROOT, 'data/ai/rejected/gate70b_rejected_ai_bank_items_v1.json')
const PENDING_FILE    = path.join(ROOT, 'data/ai/review/gate70b_pending_ai_bank_review_items_v1.json')
const APPLY_RPT_FILE  = path.join(ROOT, 'data/diagnostics/gate70b_ai_bank_review_apply_report_v1.json')
const VALIDATE_FILE   = path.join(ROOT, 'data/diagnostics/gate70b_approved_ai_bank_items_validation_report_v1.json')

export interface ReviewQueueItem {
  bank_id:          string
  batch_id?:        string
  topic:            string
  subtopic?:        string
  skill_name?:      string
  skill_type?:      string
  difficulty?:      string
  resource_type?:   string
  learning_objective?: string
  generated_text:   string
  provider?:        string
  model?:           string
  dry_run:          boolean
  generated_at?:    string
  review_status:    string
  teacher_decision: string | null
  teacher_notes:    string | null
  approval_required: boolean
  auto_publish_enabled: boolean
}

export interface ReviewDecision {
  review_item_id: string
  bank_item_id:   string
  resource_id:    string
  decision:       'approve' | 'needs_revision' | 'reject'
  reviewer_id:    string
  review_notes:   string
  created_at:     string
}

export interface ApprovedBankItem {
  bank_id:                string
  resource_id:            string
  review_item_id:         string
  subject_slug?:          string
  topic:                  string
  subtopic?:              string
  skill_name?:            string
  skill_type?:            string
  difficulty?:            string
  resource_type?:         string
  learning_objective?:    string
  student_prompt:         string
  answer_key:             string
  marking_rubric:         Array<{ criterion: string; marks: number; guidance?: string }>
  safety_declaration:     Record<string, boolean>
  provider?:              string
  model?:                 string
  dry_run:                boolean
  generated_at?:          string
  decision:               string
  reviewer_id?:           string
  review_notes?:          string
  status:                 string
  teacher_review_required: boolean
  auto_publish_enabled:   boolean
  supabase_write_performed: boolean
}

export interface AiBankReviewSummary {
  bank_exists:             boolean
  queue_exists:            boolean
  decisions_file_exists:   boolean
  approved_file_exists:    boolean
  revision_file_exists:    boolean
  rejected_file_exists:    boolean
  pending_file_exists:     boolean
  total_queue:             number
  approved_count:          number
  revision_count:          number
  rejected_count:          number
  pending_count:           number
  decision_count:          number
  validation_passed:       boolean | null
  apply_report_status:     string | null
  teacher_review_required: boolean
  auto_publish_enabled:    boolean
  supabase_write_performed: boolean
  ai_api_called:           boolean
}

function readJson<T>(filePath: string): T | null {
  try {
    if (!fs.existsSync(filePath)) return null
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as T
  } catch {
    return null
  }
}

export function readAiBankReviewQueue(): ReviewQueueItem[] {
  const q = readJson<{ queue?: ReviewQueueItem[] }>(QUEUE_FILE)
  return q?.queue ?? []
}

export function readAiBankReviewDecisions(): ReviewDecision[] {
  const d = readJson<{ decisions?: ReviewDecision[] }>(DECISIONS_FILE)
  return d?.decisions ?? []
}

export function readApprovedAiBankItems(): ApprovedBankItem[] {
  const a = readJson<{ items?: ApprovedBankItem[] }>(APPROVED_FILE)
  return a?.items ?? []
}

export function readAiBankRevisionItems(): ApprovedBankItem[] {
  const r = readJson<{ items?: ApprovedBankItem[] }>(REVISION_FILE)
  return r?.items ?? []
}

export function readRejectedAiBankItems(): ApprovedBankItem[] {
  const r = readJson<{ items?: ApprovedBankItem[] }>(REJECTED_FILE)
  return r?.items ?? []
}

export function readPendingAiBankReviewItems(): ApprovedBankItem[] {
  const p = readJson<{ items?: ApprovedBankItem[] }>(PENDING_FILE)
  return p?.items ?? []
}

export function readGate70bApplyReport(): Record<string, unknown> | null {
  return readJson<Record<string, unknown>>(APPLY_RPT_FILE)
}

export function getAiBankReviewSummary(): AiBankReviewSummary {
  const queue      = readJson<Record<string, unknown>>(QUEUE_FILE)
  const decisions  = readJson<{ decisions?: ReviewDecision[] }>(DECISIONS_FILE)
  const approved   = readJson<{ item_count?: number }>(APPROVED_FILE)
  const revision   = readJson<{ item_count?: number }>(REVISION_FILE)
  const rejected   = readJson<{ item_count?: number }>(REJECTED_FILE)
  const pending    = readJson<{ item_count?: number }>(PENDING_FILE)
  const applyRpt   = readJson<Record<string, unknown>>(APPLY_RPT_FILE)
  const validateRpt = readJson<Record<string, unknown>>(VALIDATE_FILE)

  return {
    bank_exists:             fs.existsSync(path.join(ROOT, 'data/ai/question_bank/ai_generated_question_bank_v1.json')),
    queue_exists:            fs.existsSync(QUEUE_FILE),
    decisions_file_exists:   fs.existsSync(DECISIONS_FILE),
    approved_file_exists:    fs.existsSync(APPROVED_FILE),
    revision_file_exists:    fs.existsSync(REVISION_FILE),
    rejected_file_exists:    fs.existsSync(REJECTED_FILE),
    pending_file_exists:     fs.existsSync(PENDING_FILE),
    total_queue:             (queue?.queue_count as number) ?? 0,
    approved_count:          (approved?.item_count as number) ?? 0,
    revision_count:          (revision?.item_count as number) ?? 0,
    rejected_count:          (rejected?.item_count as number) ?? 0,
    pending_count:           (pending?.item_count as number) ?? 0,
    decision_count:          (decisions?.decisions?.length) ?? 0,
    validation_passed:       validateRpt ? (validateRpt.valid as boolean) : null,
    apply_report_status:     applyRpt ? (applyRpt.status as string) : null,
    teacher_review_required: true,
    auto_publish_enabled:    false,
    supabase_write_performed: false,
    ai_api_called:           false,
  }
}
