/**
 * Gate 69D — AI Teacher Review helpers (server-only).
 *
 * Reads local JSON files produced by the Python review queue scripts.
 * No secrets. No Supabase writes. No AI API calls.
 */

import fs from 'fs'
import path from 'path'

// ---------------------------------------------------------------------------
// File paths (resolved relative to the Next.js server process cwd)
// ---------------------------------------------------------------------------

function dataRoot(): string {
  // In the monorepo: apps/admin is the cwd, data/ is two levels up
  return path.join(process.cwd(), '..', '..', 'data')
}

function reviewQueuePath(): string {
  return path.join(dataRoot(), 'ai', 'review', 'ai_teacher_review_queue_v1.json')
}

function decisionsPath(): string {
  return path.join(dataRoot(), 'ai', 'review', 'ai_teacher_review_decisions_v1.json')
}

function approvedCandidatesPath(): string {
  return path.join(dataRoot(), 'ai', 'approved', 'ai_approved_resource_candidates_v1.json')
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ReviewDecision = 'approve' | 'needs_revision' | 'reject'

export interface ReviewItem {
  review_item_id:   string
  resource_id:      string
  resource_type:    string
  title:            string
  topic:            string
  skill_name:       string
  skill_type:       string
  difficulty:       string
  student_prompt:   string
  answer_key:       string
  marking_rubric:   Array<{ criterion: string; marks: number; guidance?: string }>
  teacher_notes:    string
  safety_declaration: {
    original_content:         boolean
    no_raw_source_text_used:  boolean
    no_mark_scheme_copied:    boolean
  }
  review_status:    string
  review_decision:  string | null
  review_notes:     string | null
}

export interface ReviewQueue {
  queue_id:    string
  version:     string
  source_batch: string
  batch_id:    string
  created_at:  string
  status:      string
  item_count:  number
  items:       ReviewItem[]
}

export interface DecisionRecord {
  review_item_id: string
  resource_id:    string
  decision:       ReviewDecision
  reviewer_id:    string
  review_notes:   string | null
  created_at:     string
}

export interface DecisionsFile {
  decision_file_id: string
  version:          string
  updated_at:       string | null
  decisions:        DecisionRecord[]
}

export interface ApprovedCandidates {
  bank_id:                  string
  approved_count:           number
  auto_publish_enabled:     boolean
  teacher_approval_required: boolean
  resources:                ReviewItem[]
}

export interface AiReviewSummary {
  queue_exists:             boolean
  decision_file_exists:     boolean
  approved_candidates_exists: boolean
  total_items:              number
  pending_count:            number
  approved_count:           number
  needs_revision_count:     number
  rejected_count:           number
  auto_publish_enabled:     false
  teacher_approval_required: true
  supabase_write_performed: false
}

// ---------------------------------------------------------------------------
// Readers — safe fallback if files missing
// ---------------------------------------------------------------------------

function readJson<T>(filePath: string): T | null {
  try {
    if (!fs.existsSync(filePath)) return null
    const raw = fs.readFileSync(filePath, 'utf-8')
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

export function readAiTeacherReviewQueue(): ReviewQueue | null {
  return readJson<ReviewQueue>(reviewQueuePath())
}

export function readAiTeacherReviewDecisions(): DecisionsFile | null {
  return readJson<DecisionsFile>(decisionsPath())
}

export function readAiApprovedCandidates(): ApprovedCandidates | null {
  return readJson<ApprovedCandidates>(approvedCandidatesPath())
}

// ---------------------------------------------------------------------------
// Summary helper
// ---------------------------------------------------------------------------

export function getAiReviewSummary(): AiReviewSummary {
  const queue     = readAiTeacherReviewQueue()
  const decisions = readAiTeacherReviewDecisions()
  const approved  = readAiApprovedCandidates()

  const items      = queue?.items ?? []
  const decisionMap = new Map<string, string>()
  for (const d of decisions?.decisions ?? []) {
    decisionMap.set(d.review_item_id, d.decision)
  }

  let pendingCount        = 0
  let approvedCount       = 0
  let needsRevisionCount  = 0
  let rejectedCount       = 0

  for (const item of items) {
    const dec = decisionMap.get(item.review_item_id) ?? item.review_decision ?? null
    if (dec === 'approve')           approvedCount++
    else if (dec === 'needs_revision') needsRevisionCount++
    else if (dec === 'reject')       rejectedCount++
    else                             pendingCount++
  }

  return {
    queue_exists:              queue !== null,
    decision_file_exists:      decisions !== null,
    approved_candidates_exists: approved !== null,
    total_items:               items.length,
    pending_count:             pendingCount,
    approved_count:            approvedCount,
    needs_revision_count:      needsRevisionCount,
    rejected_count:            rejectedCount,
    auto_publish_enabled:      false,
    teacher_approval_required: true,
    supabase_write_performed:  false,
  }
}
