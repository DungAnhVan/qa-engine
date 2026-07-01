import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

// No Supabase writes. No API keys. Local file-backed for MVP.

const VALID_DECISIONS = new Set(['approve', 'needs_revision', 'reject'])

function decisionsPath(): string {
  return path.join(process.cwd(), '..', '..', 'data', 'ai', 'review',
    'ai_teacher_review_decisions_v1.json')
}

interface DecisionBody {
  review_item_id: string
  resource_id:    string
  decision:       string
  review_notes?:  string | null
  reviewer_id?:   string
}

export async function POST(request: NextRequest) {
  let body: DecisionBody
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const { review_item_id, resource_id, decision, review_notes, reviewer_id } = body

  // Validate required fields
  if (!review_item_id || typeof review_item_id !== 'string') {
    return NextResponse.json({ error: 'review_item_id is required' }, { status: 400 })
  }
  if (!resource_id || typeof resource_id !== 'string') {
    return NextResponse.json({ error: 'resource_id is required' }, { status: 400 })
  }
  if (!decision || !VALID_DECISIONS.has(decision)) {
    return NextResponse.json(
      { error: `decision must be one of: ${[...VALID_DECISIONS].join(', ')}` },
      { status: 400 },
    )
  }

  const filePath = decisionsPath()
  let fileData: { decision_file_id: string; version: string; updated_at: string | null; decisions: object[] }

  // Load existing file or start fresh
  try {
    if (fs.existsSync(filePath)) {
      fileData = JSON.parse(fs.readFileSync(filePath, 'utf-8'))
    } else {
      fileData = {
        decision_file_id: 'quanta_aptus_ai_teacher_review_decisions_v1',
        version:          '0.1.0',
        updated_at:       null,
        decisions:        [],
      }
    }
  } catch {
    return NextResponse.json({ error: 'Failed to read decisions file' }, { status: 500 })
  }

  const now = new Date().toISOString()

  // Remove any previous decision for this review_item_id, then append new one
  const existing = (fileData.decisions as Array<{ review_item_id: string }>) ?? []
  const filtered = existing.filter(d => d.review_item_id !== review_item_id)

  const newDecision = {
    review_item_id,
    resource_id,
    decision,
    reviewer_id:  reviewer_id ?? 'local_demo_teacher',
    review_notes: review_notes ?? null,
    created_at:   now,
  }

  fileData.decisions = [...filtered, newDecision]
  fileData.updated_at = now

  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true })
    fs.writeFileSync(filePath, JSON.stringify(fileData, null, 2), 'utf-8')
  } catch {
    return NextResponse.json({ error: 'Failed to write decisions file' }, { status: 500 })
  }

  return NextResponse.json({
    ok:             true,
    review_item_id,
    resource_id,
    decision,
    created_at:     now,
    total_decisions: fileData.decisions.length,
  })
}
