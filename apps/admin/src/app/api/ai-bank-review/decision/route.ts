import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

const ROOT           = path.resolve(process.cwd(), '../..')
const DECISIONS_FILE = path.join(ROOT, 'data/ai/review/gate70b_ai_bank_review_decisions_v1.json')

const VALID_DECISIONS = new Set(['approve', 'needs_revision', 'reject'])

interface DecisionPayload {
  review_item_id?: string
  bank_item_id:    string
  resource_id?:    string
  decision:        string
  review_notes?:   string
  reviewer_id?:    string
}

interface ReviewDecision {
  review_item_id: string
  bank_item_id:   string
  resource_id:    string
  decision:       string
  reviewer_id:    string
  review_notes:   string
  created_at:     string
}

interface DecisionsDoc {
  decision_file_id: string
  version:          string
  source_queue:     string
  updated_at:       string | null
  decisions:        ReviewDecision[]
}

export async function POST(req: NextRequest) {
  let body: DecisionPayload
  try {
    body = await req.json() as DecisionPayload
  } catch {
    return NextResponse.json({ status: 'failed', error: 'Invalid JSON body' }, { status: 400 })
  }

  const { bank_item_id, decision, review_notes = '', reviewer_id, review_item_id, resource_id } = body

  if (!bank_item_id) {
    return NextResponse.json({ status: 'failed', error: 'bank_item_id is required' }, { status: 400 })
  }
  if (!VALID_DECISIONS.has(decision)) {
    return NextResponse.json({
      status: 'failed',
      error: `decision must be one of: ${[...VALID_DECISIONS].join(', ')}`,
    }, { status: 400 })
  }

  const now = new Date().toISOString()

  // Load existing decisions doc
  let doc: DecisionsDoc
  try {
    if (fs.existsSync(DECISIONS_FILE)) {
      doc = JSON.parse(fs.readFileSync(DECISIONS_FILE, 'utf-8')) as DecisionsDoc
    } else {
      doc = {
        decision_file_id: 'quanta_aptus_gate70b_ai_bank_review_decisions_v1',
        version:          '0.1.0',
        source_queue:     'data/ai/teacher_review/ai_teacher_review_queue_v1.json',
        updated_at:       null,
        decisions:        [],
      }
    }
  } catch {
    return NextResponse.json({ status: 'failed', error: 'Could not read decisions file' }, { status: 500 })
  }

  const newDecision: ReviewDecision = {
    review_item_id: review_item_id ?? `review_${bank_item_id}`,
    bank_item_id,
    resource_id:    resource_id   ?? `ai_res_70b_${bank_item_id.slice(-8)}`,
    decision,
    reviewer_id:    reviewer_id   ?? 'local_demo_teacher',
    review_notes,
    created_at:     now,
  }

  // Upsert: replace existing decision for this bank_item_id if present
  const idx = doc.decisions.findIndex(d => d.bank_item_id === bank_item_id)
  if (idx >= 0) {
    doc.decisions[idx] = newDecision
  } else {
    doc.decisions.push(newDecision)
  }
  doc.updated_at = now

  try {
    fs.mkdirSync(path.dirname(DECISIONS_FILE), { recursive: true })
    fs.writeFileSync(DECISIONS_FILE, JSON.stringify(doc, null, 2), 'utf-8')
  } catch {
    return NextResponse.json({ status: 'failed', error: 'Could not write decisions file' }, { status: 500 })
  }

  return NextResponse.json({
    status:                  'passed',
    decision_saved:          true,
    bank_item_id,
    decision,
    auto_publish_enabled:    false,
    supabase_write_performed: false,
    ai_api_called:           false,
  })
}
