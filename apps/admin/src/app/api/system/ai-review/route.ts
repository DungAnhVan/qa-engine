import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

function dataRoot(): string {
  return path.join(process.cwd(), '..', '..', 'data')
}

export async function GET() {
  const queuePath    = path.join(dataRoot(), 'ai', 'review', 'ai_teacher_review_queue_v1.json')
  const decisionPath = path.join(dataRoot(), 'ai', 'review', 'ai_teacher_review_decisions_v1.json')
  const approvedPath = path.join(dataRoot(), 'ai', 'approved', 'ai_approved_resource_candidates_v1.json')

  const queueExists    = fs.existsSync(queuePath)
  const decisionExists = fs.existsSync(decisionPath)
  const approvedExists = fs.existsSync(approvedPath)

  let queueItemCount  = 0
  let decisionCount   = 0
  let approvedCount   = 0

  try {
    if (queueExists) {
      const q = JSON.parse(fs.readFileSync(queuePath, 'utf-8'))
      queueItemCount = q.item_count ?? (q.items?.length ?? 0)
    }
    if (decisionExists) {
      const d = JSON.parse(fs.readFileSync(decisionPath, 'utf-8'))
      decisionCount = d.decisions?.length ?? 0
    }
    if (approvedExists) {
      const a = JSON.parse(fs.readFileSync(approvedPath, 'utf-8'))
      approvedCount = a.approved_count ?? (a.resources?.length ?? 0)
    }
  } catch {
    // Filesystem errors handled gracefully
  }

  const allFilesExist = queueExists && decisionExists
  const status: 'pending_review' | 'ready' | 'needs_review' | 'failed' =
    !queueExists        ? 'needs_review'
    : !decisionExists   ? 'needs_review'
    : approvedExists    ? 'ready'
    : 'pending_review'

  return NextResponse.json({
    status,
    queue_exists:                 queueExists,
    decision_file_exists:         decisionExists,
    approved_candidate_bank_exists: approvedExists,
    queue_item_count:             queueItemCount,
    decision_count:               decisionCount,
    approved_count:               approvedCount,
    teacher_approval_required:    true,
    auto_publish_enabled:         false,
    supabase_write_performed:     false,
    timestamp:                    new Date().toISOString(),
  })
}
