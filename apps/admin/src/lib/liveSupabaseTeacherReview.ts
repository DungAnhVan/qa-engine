/**
 * SERVER-ONLY — Live Supabase teacher attempt review module.
 *
 * WARNING: This file reads SUPABASE_SERVICE_ROLE_KEY.
 * Must NEVER be imported in client components.
 * The `import 'server-only'` guard enforces this at build time.
 *
 * Gate 58: teacher review of student attempts.
 *   - Loads the teacher_review_required queue from Supabase.
 *   - Writes teacher_reviews rows.
 *   - Upserts marked_attempts with marking_method = 'teacher'.
 *   - Updates attempts.marking_status = 'teacher_reviewed'.
 *   - No auth yet: organization_id and reviewer_profile_id are null.
 *   - No OpenAI. No Cambridge source text.
 *
 * Gate 59 will add student results view.
 */
import 'server-only'

import { createClient } from '@supabase/supabase-js'

// ---------------------------------------------------------------------------
// Client factory
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
      'live_supabase teacher review requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local.',
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
  id:             string
  student_id:     string
  resource_id:    string
  subject_id:     string | null
  answer_text:    string | null
  submitted_at:   string
  marking_status: string
}

interface ResourceRow {
  id:            string
  resource_key:  string
  title:         string
  topic:         string | null
  skill_type:    string | null
  resource_type: string | null
}

interface StudentRow {
  id:           string
  display_name: string
}

interface SubjectRow {
  id:           string
  subject_slug: string
}

interface MarkedAttemptRow {
  id:       string
  result:   string | null
  feedback: string | null
}

interface TeacherReviewRow {
  id:         string
  decision:   string
  created_at: string
}

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface TeacherReviewQueueItem {
  attempt_id:       string
  student_name:     string
  subject_slug:     string | null
  resource_key:     string
  resource_title:   string
  topic:            string | null
  skill_type:       string | null
  resource_type:    string | null
  answer_text:      string | null
  submitted_at:     string
  current_feedback: string | null
  current_result:   string | null
}

export type TeacherDecision =
  | 'correct'
  | 'incorrect'
  | 'partially_correct'
  | 'needs_resubmission'

export interface TeacherReviewInput {
  attempt_id: string
  decision:   TeacherDecision
  score?:     number | null
  feedback:   string
  notes?:     string
}

export interface TeacherReviewResult {
  success:            boolean
  review_id?:         string
  marked_attempt_id?: string
  decision?:          string
  error?:             string
}

export interface TeacherReviewStats {
  queue_count:     number
  reviews_count:   number
  latest_review:   { id: string; decision: string; created_at: string } | null
}

// ---------------------------------------------------------------------------
// Queue loader
// ---------------------------------------------------------------------------

export async function getLiveSupabaseTeacherReviewQueue(
  limit = 10,
): Promise<TeacherReviewQueueItem[]> {
  if (!isLiveSupabaseConfigured()) return []
  try {
    const client = requireSupabaseClient()

    // 1. Attempts needing review
    const { data: attemptsData } = await client
      .from('attempts')
      .select('id, student_id, resource_id, subject_id, answer_text, submitted_at, marking_status')
      .eq('marking_status', 'teacher_review_required')
      .order('submitted_at', { ascending: false })
      .limit(limit)
    const attempts = ((attemptsData ?? []) as unknown) as AttemptRow[]
    if (!attempts.length) return []

    // 2. Batch load resources
    const resourceIds = [...new Set(attempts.map((a) => a.resource_id))]
    const { data: resourcesData } = await client
      .from('resources')
      .select('id, resource_key, title, topic, skill_type, resource_type')
      .in('id', resourceIds)
    const resourceMap = new Map<string, ResourceRow>()
    for (const r of ((resourcesData ?? []) as unknown) as ResourceRow[]) {
      resourceMap.set(r.id, r)
    }

    // 3. Batch load students
    const studentIds = [...new Set(attempts.map((a) => a.student_id))]
    const { data: studentsData } = await client
      .from('students')
      .select('id, display_name')
      .in('id', studentIds)
    const studentMap = new Map<string, StudentRow>()
    for (const s of ((studentsData ?? []) as unknown) as StudentRow[]) {
      studentMap.set(s.id, s)
    }

    // 4. Batch load subjects (for slug)
    const subjectIds = [
      ...new Set(attempts.map((a) => a.subject_id).filter((id): id is string => id !== null)),
    ]
    const subjectMap = new Map<string, SubjectRow>()
    if (subjectIds.length) {
      const { data: subjectsData } = await client
        .from('subjects')
        .select('id, subject_slug')
        .in('id', subjectIds)
      for (const s of ((subjectsData ?? []) as unknown) as SubjectRow[]) {
        subjectMap.set(s.id, s)
      }
    }

    // 5. Batch load latest marked_attempts (for current feedback/result)
    const attemptIds = attempts.map((a) => a.id)
    const { data: markedData } = await client
      .from('marked_attempts')
      .select('id, attempt_id, result, feedback')
      .in('attempt_id', attemptIds)
      .order('created_at', { ascending: false })
    const markedMap = new Map<string, MarkedAttemptRow & { attempt_id: string }>()
    for (const m of ((markedData ?? []) as unknown) as (MarkedAttemptRow & { attempt_id: string })[]) {
      // Keep only the latest per attempt_id
      if (!markedMap.has(m.attempt_id)) {
        markedMap.set(m.attempt_id, m)
      }
    }

    // 6. Join in memory
    return attempts.map((a): TeacherReviewQueueItem => {
      const resource = resourceMap.get(a.resource_id)
      const student  = studentMap.get(a.student_id)
      const subject  = a.subject_id ? subjectMap.get(a.subject_id) : undefined
      const marked   = markedMap.get(a.id)
      return {
        attempt_id:       a.id,
        student_name:     student?.display_name ?? 'Unknown Student',
        subject_slug:     subject?.subject_slug ?? null,
        resource_key:     resource?.resource_key ?? '—',
        resource_title:   resource?.title ?? '—',
        topic:            resource?.topic ?? null,
        skill_type:       resource?.skill_type ?? null,
        resource_type:    resource?.resource_type ?? null,
        answer_text:      a.answer_text,
        submitted_at:     a.submitted_at,
        current_feedback: marked?.feedback ?? null,
        current_result:   marked?.result ?? null,
      }
    })
  } catch {
    return []
  }
}

// ---------------------------------------------------------------------------
// Review submitter
// ---------------------------------------------------------------------------

export async function submitLiveSupabaseTeacherReview(
  input: TeacherReviewInput,
): Promise<TeacherReviewResult> {
  if (!isLiveSupabaseConfigured()) {
    return { success: false, error: 'live_supabase not configured (missing env vars).' }
  }
  try {
    const client = requireSupabaseClient()

    // 1. Load attempt
    const { data: attemptData } = await client
      .from('attempts')
      .select('id, student_id, resource_id, subject_id, marking_status')
      .eq('id', input.attempt_id)
      .maybeSingle()
    const attempt = attemptData ? ((attemptData as unknown) as AttemptRow) : null
    if (!attempt) {
      return { success: false, error: `Attempt not found: ${input.attempt_id}` }
    }

    // 2. Load resource (for resource_id FK in teacher_reviews + skill_gap)
    const { data: resourceData } = await client
      .from('resources')
      .select('id, resource_key, title, topic, skill_type, resource_type')
      .eq('id', attempt.resource_id)
      .maybeSingle()
    const resource = resourceData ? ((resourceData as unknown) as ResourceRow) : null

    // 3. Insert teacher_reviews row
    // organization_id and reviewer_profile_id are null until auth is implemented (Gate 6x)
    const { data: reviewData } = await client
      .from('teacher_reviews')
      .insert({
        organization_id:     null,
        reviewer_profile_id: null,
        review_type:         'attempt_review',
        resource_id:         attempt.resource_id,
        attempt_id:          attempt.id,
        decision:            input.decision,
        score:               input.score ?? null,
        feedback:            input.feedback,
        notes:               input.notes ?? null,
      })
      .select('id')
      .single()
    const reviewId = reviewData ? ((reviewData as unknown) as { id: string }).id : null
    if (!reviewId) {
      return { success: false, error: 'Failed to write teacher_reviews row.' }
    }

    // 4. Check for existing marked_attempts row (deduplication)
    const { data: existingMarked } = await client
      .from('marked_attempts')
      .select('id')
      .eq('attempt_id', attempt.id)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle()
    const existingMarkedId = existingMarked
      ? ((existingMarked as unknown) as { id: string }).id
      : null

    // 5. Upsert marked_attempts with marking_method = 'teacher'
    const markedPayload = {
      attempt_id:     attempt.id,
      student_id:     attempt.student_id,
      resource_id:    attempt.resource_id,
      subject_id:     attempt.subject_id ?? null,
      marking_method: 'teacher',
      score:          input.score ?? null,
      max_score:      input.score != null ? 1 : null,
      result:         input.decision,
      feedback:       input.feedback,
      skill_gap: {
        topic:         resource?.topic ?? null,
        skill_type:    resource?.skill_type ?? null,
        resource_type: resource?.resource_type ?? null,
        reason:        input.feedback,
        decision:      input.decision,
      },
    }

    let markedAttemptId: string | null = null
    if (existingMarkedId) {
      const { data: updatedMarked } = await client
        .from('marked_attempts')
        .update(markedPayload)
        .eq('id', existingMarkedId)
        .select('id')
        .single()
      markedAttemptId = updatedMarked
        ? ((updatedMarked as unknown) as { id: string }).id
        : existingMarkedId
    } else {
      const { data: insertedMarked } = await client
        .from('marked_attempts')
        .insert(markedPayload)
        .select('id')
        .single()
      markedAttemptId = insertedMarked
        ? ((insertedMarked as unknown) as { id: string }).id
        : null
    }

    if (!markedAttemptId) {
      return { success: false, error: 'Failed to write marked_attempts row.' }
    }

    // 6. Update attempts.marking_status = 'teacher_reviewed'
    await client
      .from('attempts')
      .update({ marking_status: 'teacher_reviewed' })
      .eq('id', attempt.id)

    return {
      success:            true,
      review_id:          reviewId,
      marked_attempt_id:  markedAttemptId,
      decision:           input.decision,
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return { success: false, error: msg }
  }
}

// ---------------------------------------------------------------------------
// Diagnostic stats
// ---------------------------------------------------------------------------

export async function getLiveSupabaseTeacherReviewStats(): Promise<TeacherReviewStats> {
  if (!isLiveSupabaseConfigured()) {
    return { queue_count: 0, reviews_count: 0, latest_review: null }
  }
  try {
    const client = requireSupabaseClient()

    const [queueRes, reviewsRes, latestRes] = await Promise.all([
      client
        .from('attempts')
        .select('id', { count: 'exact', head: true })
        .eq('marking_status', 'teacher_review_required'),
      client
        .from('teacher_reviews')
        .select('id', { count: 'exact', head: true })
        .eq('review_type', 'attempt_review'),
      client
        .from('teacher_reviews')
        .select('id, decision, created_at')
        .eq('review_type', 'attempt_review')
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle(),
    ])

    const latestRow = latestRes.data
      ? ((latestRes.data as unknown) as TeacherReviewRow)
      : null

    return {
      queue_count:   queueRes.count ?? 0,
      reviews_count: reviewsRes.count ?? 0,
      latest_review: latestRow
        ? { id: latestRow.id, decision: latestRow.decision, created_at: latestRow.created_at }
        : null,
    }
  } catch {
    return { queue_count: 0, reviews_count: 0, latest_review: null }
  }
}
