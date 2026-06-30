/**
 * SERVER-ONLY — Live Supabase rule-based marking module.
 *
 * WARNING: This file reads SUPABASE_SERVICE_ROLE_KEY.
 * Must NEVER be imported in client components.
 * The `import 'server-only'` guard enforces this at build time.
 *
 * Gate 57: rule-based marking of student attempts.
 *   - Writes results into marked_attempts table.
 *   - Updates attempts.marking_status.
 *   - No OpenAI or AI calls. No Cambridge source text read.
 *   - Teacher-review path exists for non-numeric resource types.
 *   - Deduplication: existing marked_attempts row is updated, not duplicated.
 *
 * Gate 58 will add teacher review decision UI.
 */
import 'server-only'

import { createClient } from '@supabase/supabase-js'

// ---------------------------------------------------------------------------
// Client factory (same env-guard pattern as liveSupabaseContent/Attempts)
// ---------------------------------------------------------------------------

function getSupabaseConfig(): { url: string; serviceRoleKey: string } | null {
  const url = process.env.SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !key) return null
  return { url, serviceRoleKey: key }
}

export function isLiveSupabaseConfigured(): boolean {
  return getSupabaseConfig() !== null
}

function requireSupabaseClient() {
  const config = getSupabaseConfig()
  if (!config) {
    throw new Error(
      'live_supabase marking requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local.',
    )
  }
  return createClient(config.url, config.serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })
}

type AppClient = ReturnType<typeof requireSupabaseClient>

// ---------------------------------------------------------------------------
// Internal row types
// ---------------------------------------------------------------------------

interface AttemptRow {
  id: string
  student_id: string
  resource_id: string
  subject_id: string | null
  answer_text: string | null
  answer_json: Record<string, unknown>
  attempt_type: string
  marking_status: string
}

interface ResourceRow {
  id: string
  resource_key: string
  resource_type: string
  skill_type: string
  topic: string
  worked_solution: string | null
  marking_guidance: string | null
}

interface MarkedAttemptRow {
  id: string
  result: string
  score: number | null
  max_score: number | null
  marking_status: string
}

// ---------------------------------------------------------------------------
// Resource type routing
// ---------------------------------------------------------------------------

const TEACHER_REVIEW_TYPES = new Set([
  'graphing_drill',
  'diagram_or_graph_drill',
  'experiment_planning_task',
  'planning_marking_checklist',
  'graph_marking_checklist',
  'marking_checklist',
  'data_interpretation_drill',
  'worked_example',
  'conceptual_explanation',
  'essay_planning',
])

const NUMERIC_MARKING_TYPES = new Set([
  'calculation_drill',
  'short_answer_calculation',
  'algebra_drill',
])

// ---------------------------------------------------------------------------
// Number extraction helpers
// ---------------------------------------------------------------------------

function extractNumerics(text: string | null | undefined): Set<string> {
  if (!text) return new Set()
  const matches = text.match(/-?\d+(?:\.\d+)?/g) ?? []
  const result = new Set<string>()
  for (const m of matches) {
    const n = parseFloat(m)
    if (!isNaN(n) && isFinite(n)) {
      result.add(n.toFixed(2))
    }
  }
  return result
}

function setsOverlap(a: Set<string>, b: Set<string>): boolean {
  for (const v of a) {
    if (b.has(v)) return true
  }
  return false
}

// ---------------------------------------------------------------------------
// Core marking logic — pure, no DB calls
// ---------------------------------------------------------------------------

type MarkingResult_v =
  | 'correct'
  | 'incorrect'
  | 'pending_teacher_review'

interface RuleMarkResult {
  result: MarkingResult_v
  score: number | null
  max_score: number | null
  marking_status: 'auto_marked' | 'teacher_review_required'
  feedback: string
}

function applyRuleBasedMarking(
  resource: ResourceRow,
  answerText: string | null,
): RuleMarkResult {
  const rtype = resource.resource_type

  // ── Teacher-review-only resource types ────────────────────────────────────
  if (TEACHER_REVIEW_TYPES.has(rtype)) {
    return {
      result:         'pending_teacher_review',
      score:          null,
      max_score:      null,
      marking_status: 'teacher_review_required',
      feedback:       'This response requires teacher review.',
    }
  }

  // ── Numeric auto-marking ───────────────────────────────────────────────────
  if (NUMERIC_MARKING_TYPES.has(rtype)) {
    const expectedNums = new Set([
      ...extractNumerics(resource.worked_solution),
      ...extractNumerics(resource.marking_guidance),
    ])

    if (expectedNums.size === 0) {
      return {
        result:         'pending_teacher_review',
        score:          null,
        max_score:      null,
        marking_status: 'teacher_review_required',
        feedback:       'No expected numerical answer found in solution guide. Teacher review required.',
      }
    }

    const studentNums = extractNumerics(answerText)

    if (setsOverlap(studentNums, expectedNums)) {
      return {
        result:         'correct',
        score:          1,
        max_score:      1,
        marking_status: 'auto_marked',
        feedback:       'Your answer contains the correct numerical result.',
      }
    } else {
      return {
        result:         'incorrect',
        score:          0,
        max_score:      1,
        marking_status: 'auto_marked',
        feedback:       'Your numerical answer does not match the expected result. Check your working.',
      }
    }
  }

  // ── All other types → teacher review ─────────────────────────────────────
  return {
    result:         'pending_teacher_review',
    score:          null,
    max_score:      null,
    marking_status: 'teacher_review_required',
    feedback:       'This resource type requires teacher review.',
  }
}

// ---------------------------------------------------------------------------
// Public result type
// ---------------------------------------------------------------------------

export interface MarkAttemptResult {
  success: boolean
  attempt_id?: string
  marked_attempt_id?: string
  result?: string
  score?: number | null
  max_score?: number | null
  marking_method?: string
  marking_status?: string
  feedback?: string
  resource_type?: string
  error?: string
}

// ---------------------------------------------------------------------------
// DB helpers
// ---------------------------------------------------------------------------

async function _loadAttempt(client: AppClient, id: string): Promise<AttemptRow | null> {
  const { data } = await client
    .from('attempts')
    .select('id, student_id, resource_id, subject_id, answer_text, answer_json, attempt_type, marking_status')
    .eq('id', id)
    .maybeSingle()
  return data ? ((data as unknown) as AttemptRow) : null
}

async function _loadResource(client: AppClient, id: string): Promise<ResourceRow | null> {
  const { data } = await client
    .from('resources')
    .select('id, resource_key, resource_type, skill_type, topic, worked_solution, marking_guidance')
    .eq('id', id)
    .maybeSingle()
  return data ? ((data as unknown) as ResourceRow) : null
}

async function _findExistingMarkedAttempt(
  client: AppClient,
  attemptId: string,
): Promise<{ id: string } | null> {
  const { data } = await client
    .from('marked_attempts')
    .select('id')
    .eq('attempt_id', attemptId)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle()
  return data ? ((data as unknown) as { id: string }) : null
}

async function _upsertMarkedAttempt(
  client: AppClient,
  attempt: AttemptRow,
  resource: ResourceRow,
  marking: RuleMarkResult,
  existingId: string | null,
): Promise<MarkedAttemptRow | null> {
  const payload = {
    attempt_id:     attempt.id,
    student_id:     attempt.student_id,
    resource_id:    attempt.resource_id,
    subject_id:     attempt.subject_id ?? null,
    marking_method: 'rule_based',
    score:          marking.score,
    max_score:      marking.max_score,
    result:         marking.result,
    feedback:       marking.feedback,
    skill_gap: {
      topic:         resource.topic,
      skill_type:    resource.skill_type,
      resource_type: resource.resource_type,
      reason:        marking.result === 'incorrect'
        ? 'Numerical answer does not match expected result.'
        : marking.result === 'pending_teacher_review'
          ? 'Requires teacher assessment for this resource type.'
          : 'Answer is correct.',
    },
  }

  if (existingId) {
    const { data } = await client
      .from('marked_attempts')
      .update(payload)
      .eq('id', existingId)
      .select('id, result, score, max_score')
      .single()
    if (!data) return null
    const row = (data as unknown) as MarkedAttemptRow
    return { ...row, marking_status: marking.marking_status }
  } else {
    const { data } = await client
      .from('marked_attempts')
      .insert(payload)
      .select('id, result, score, max_score')
      .single()
    if (!data) return null
    const row = (data as unknown) as MarkedAttemptRow
    return { ...row, marking_status: marking.marking_status }
  }
}

async function _updateAttemptMarkingStatus(
  client: AppClient,
  attemptId: string,
  status: string,
): Promise<void> {
  await client
    .from('attempts')
    .update({ marking_status: status })
    .eq('id', attemptId)
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function markLiveSupabaseAttempt(
  attemptId: string,
): Promise<MarkAttemptResult> {
  if (!isLiveSupabaseConfigured()) {
    return { success: false, error: 'live_supabase not configured (missing env vars).' }
  }
  try {
    const client = requireSupabaseClient()

    // 1. Load attempt
    const attempt = await _loadAttempt(client, attemptId)
    if (!attempt) {
      return { success: false, attempt_id: attemptId, error: `Attempt not found: ${attemptId}` }
    }

    // 2. Load resource
    const resource = await _loadResource(client, attempt.resource_id)
    if (!resource) {
      return { success: false, attempt_id: attemptId, error: `Resource not found for attempt: ${attemptId}` }
    }

    // 3. Apply marking rules
    const marking = applyRuleBasedMarking(resource, attempt.answer_text)

    // 4. Check for existing marked_attempts row (deduplication)
    const existing = await _findExistingMarkedAttempt(client, attemptId)

    // 5. Insert or update marked_attempts
    const markedRow = await _upsertMarkedAttempt(client, attempt, resource, marking, existing?.id ?? null)
    if (!markedRow) {
      return { success: false, attempt_id: attemptId, error: 'Failed to write marked_attempts row.' }
    }

    // 6. Update attempts.marking_status
    await _updateAttemptMarkingStatus(client, attemptId, marking.marking_status)

    return {
      success:           true,
      attempt_id:        attemptId,
      marked_attempt_id: existing?.id ?? markedRow.id,
      result:            marking.result,
      score:             marking.score,
      max_score:         marking.max_score,
      marking_method:    'rule_based',
      marking_status:    marking.marking_status,
      feedback:          marking.feedback,
      resource_type:     resource.resource_type,
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return { success: false, attempt_id: attemptId, error: msg }
  }
}

export async function getLiveSupabaseUnmarkedAttempts(limit = 10): Promise<Array<{
  id: string
  student_id: string
  resource_id: string
  submitted_at: string
  answer_text: string | null
}>> {
  if (!isLiveSupabaseConfigured()) return []
  try {
    const client = requireSupabaseClient()
    const { data } = await client
      .from('attempts')
      .select('id, student_id, resource_id, submitted_at, answer_text')
      .eq('marking_status', 'unmarked')
      .order('submitted_at', { ascending: false })
      .limit(limit)
    return ((data ?? []) as unknown) as Array<{
      id: string
      student_id: string
      resource_id: string
      submitted_at: string
      answer_text: string | null
    }>
  } catch {
    return []
  }
}

export async function markLatestUnmarkedLiveSupabaseAttempt(): Promise<MarkAttemptResult> {
  const unmarked = await getLiveSupabaseUnmarkedAttempts(1)
  if (!unmarked.length) {
    return { success: false, error: 'No unmarked attempts found.' }
  }
  return markLiveSupabaseAttempt(unmarked[0].id)
}
