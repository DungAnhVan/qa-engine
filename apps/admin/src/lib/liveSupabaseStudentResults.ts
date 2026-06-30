/**
 * SERVER-ONLY — Live Supabase student results module.
 *
 * WARNING: This file reads SUPABASE_SERVICE_ROLE_KEY.
 * Must NEVER be imported in client components.
 * The `import 'server-only'` guard enforces this at build time.
 *
 * Gate 59: build a student result report from live Supabase data.
 *   - Reads attempts, marked_attempts, resources, teacher_reviews.
 *   - Derives accuracy, strengths, skill_gaps, resubmission_queue.
 *   - No writes. Read-only view of student progress.
 *   - No OpenAI. No Cambridge source text.
 *
 * Gate 60 will add auth / per-user data scoping.
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
      'live_supabase student results requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local.',
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
  id:                      string
  resource_id:             string
  attempt_type:            string
  parent_attempt_id:       string | null
  answer_text:             string | null
  submitted_at:            string
  marking_status:          string
  superseded_by_attempt_id: string | null
}

interface MarkedAttemptRow {
  id:             string
  attempt_id:     string
  resource_id:    string
  marking_method: string | null
  score:          number | null
  max_score:      number | null
  result:         string | null
  feedback:       string | null
  created_at:     string
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
  external_code: string | null
}

interface SubjectRow {
  id:           string
  subject_slug: string
}

// ---------------------------------------------------------------------------
// Public return types
// ---------------------------------------------------------------------------

export interface StrengthItem {
  topic:     string | null
  skill_type: string | null
  count:     number
}

export interface SkillGapItem {
  attempt_id:     string
  resource_title: string
  resource_key:   string
  topic:          string | null
  skill_type:     string | null
  result:         string
  feedback:       string | null
}

export interface ResubmissionItem {
  attempt_id:     string
  resource_title: string
  resource_key:   string
  topic:          string | null
  feedback:       string | null
  submitted_at:   string
}

export interface RecentAttemptItem {
  attempt_id:     string
  resource_title: string
  resource_key:   string
  topic:          string | null
  result:         string | null
  marking_method: string | null
  submitted_at:   string
  attempt_type:   string
  marking_status: string
}

export interface StudentResultReport {
  student_id:                    string
  student_name:                  string
  subject_slug:                  string
  attempt_count:                 number
  marked_attempt_count:          number
  unmarked_count:                number
  auto_marked_count:             number
  teacher_review_required_count: number
  teacher_reviewed_count:        number
  correct_count:                 number
  incorrect_count:               number
  partially_correct_count:       number
  needs_resubmission_count:      number
  pending_teacher_review_count:  number
  accuracy:                      number | null
  strengths:                     StrengthItem[]
  skill_gaps:                    SkillGapItem[]
  resubmission_queue:            ResubmissionItem[]
  recent_attempts:               RecentAttemptItem[]
}

export interface LearningState {
  student_name:       string
  subject_slug:       string
  total_attempted:    number
  accuracy:           number | null
  pending_count:      number
  resubmission_count: number
  top_gaps:           SkillGapItem[]
  next_action:        string
}

// ---------------------------------------------------------------------------
// DB helpers
// ---------------------------------------------------------------------------

const DEMO_STUDENT_CODE = 'local_demo_student'
const DEMO_SUBJECT_SLUG = 'physics_0625'

async function _resolveStudent(
  client: AppClient,
  studentCode: string,
): Promise<StudentRow | null> {
  const { data } = await client
    .from('students')
    .select('id, display_name, external_code')
    .eq('external_code', studentCode)
    .limit(1)
    .maybeSingle()
  return data ? ((data as unknown) as StudentRow) : null
}

async function _resolveSubject(
  client: AppClient,
  subjectSlug: string,
): Promise<SubjectRow | null> {
  const { data } = await client
    .from('subjects')
    .select('id, subject_slug')
    .eq('subject_slug', subjectSlug)
    .limit(1)
    .maybeSingle()
  return data ? ((data as unknown) as SubjectRow) : null
}

async function _loadAttempts(
  client: AppClient,
  studentId: string,
  subjectId: string,
): Promise<AttemptRow[]> {
  const { data } = await client
    .from('attempts')
    .select(
      'id, resource_id, attempt_type, parent_attempt_id, answer_text, submitted_at, marking_status, superseded_by_attempt_id',
    )
    .eq('student_id', studentId)
    .eq('subject_id', subjectId)
    .order('submitted_at', { ascending: true })
  return ((data ?? []) as unknown) as AttemptRow[]
}

async function _loadMarkedAttempts(
  client: AppClient,
  attemptIds: string[],
): Promise<MarkedAttemptRow[]> {
  if (!attemptIds.length) return []
  const { data } = await client
    .from('marked_attempts')
    .select(
      'id, attempt_id, resource_id, marking_method, score, max_score, result, feedback, created_at',
    )
    .in('attempt_id', attemptIds)
    .order('created_at', { ascending: true }) // oldest first so latest overwrites
  return ((data ?? []) as unknown) as MarkedAttemptRow[]
}

async function _loadResources(
  client: AppClient,
  resourceIds: string[],
): Promise<ResourceRow[]> {
  if (!resourceIds.length) return []
  const { data } = await client
    .from('resources')
    .select('id, resource_key, title, topic, skill_type, resource_type')
    .in('id', resourceIds)
  return ((data ?? []) as unknown) as ResourceRow[]
}

// ---------------------------------------------------------------------------
// Report builder
// ---------------------------------------------------------------------------

function _buildReport(
  student: StudentRow,
  subject: SubjectRow,
  attempts: AttemptRow[],
  latestMarkedByAttempt: Map<string, MarkedAttemptRow>,
  resourceMap: Map<string, ResourceRow>,
): StudentResultReport {
  // "Current" attempts: superseded_by_attempt_id IS NULL
  // (attempts that have not been superseded by a newer resubmission)
  const currentAttempts = attempts.filter((a) => !a.superseded_by_attempt_id)

  // Attempt status counts
  let unmarked_count                = 0
  let auto_marked_count             = 0
  let teacher_review_required_count = 0
  let teacher_reviewed_count        = 0

  for (const a of currentAttempts) {
    switch (a.marking_status) {
      case 'unmarked':                  unmarked_count++;                  break
      case 'auto_marked':               auto_marked_count++;               break
      case 'teacher_review_required':   teacher_review_required_count++;   break
      case 'teacher_reviewed':          teacher_reviewed_count++;          break
    }
  }

  // Result counts (from latest marked_attempt per current attempt)
  let correct_count                = 0
  let incorrect_count              = 0
  let partially_correct_count      = 0
  let needs_resubmission_count     = 0
  let pending_teacher_review_count = 0

  for (const a of currentAttempts) {
    const marked = latestMarkedByAttempt.get(a.id)
    if (!marked) continue
    switch (marked.result) {
      case 'correct':                 correct_count++;                break
      case 'incorrect':               incorrect_count++;              break
      case 'partially_correct':       partially_correct_count++;      break
      case 'needs_resubmission':      needs_resubmission_count++;     break
      case 'pending_teacher_review':  pending_teacher_review_count++; break
    }
  }

  // Accuracy: correct / (correct + incorrect + partially_correct)
  const resolvedCount = correct_count + incorrect_count + partially_correct_count
  const accuracy = resolvedCount > 0 ? correct_count / resolvedCount : null

  // Strengths: (topic, skill_type) grouped where latest result = correct
  const strengthMap = new Map<string, StrengthItem>()
  for (const a of currentAttempts) {
    const marked   = latestMarkedByAttempt.get(a.id)
    if (!marked || marked.result !== 'correct') continue
    const resource = resourceMap.get(a.resource_id)
    const key      = `${resource?.topic ?? '—'}|${resource?.skill_type ?? '—'}`
    const existing = strengthMap.get(key)
    if (existing) {
      existing.count++
    } else {
      strengthMap.set(key, {
        topic:      resource?.topic ?? null,
        skill_type: resource?.skill_type ?? null,
        count:      1,
      })
    }
  }
  const strengths = [...strengthMap.values()].sort((a, b) => b.count - a.count)

  // Skill gaps: incorrect / partially_correct / needs_resubmission / pending_teacher_review
  const GAP_RESULTS = new Set([
    'incorrect',
    'partially_correct',
    'needs_resubmission',
    'pending_teacher_review',
  ])
  const skill_gaps: SkillGapItem[] = []
  for (const a of currentAttempts) {
    const marked   = latestMarkedByAttempt.get(a.id)
    if (!marked || !marked.result || !GAP_RESULTS.has(marked.result)) continue
    const resource = resourceMap.get(a.resource_id)
    skill_gaps.push({
      attempt_id:     a.id,
      resource_title: resource?.title ?? '—',
      resource_key:   resource?.resource_key ?? '—',
      topic:          resource?.topic ?? null,
      skill_type:     resource?.skill_type ?? null,
      result:         marked.result,
      feedback:       marked.feedback ?? null,
    })
  }

  // Resubmission queue: current attempts where latest result = needs_resubmission
  const resubmission_queue: ResubmissionItem[] = []
  for (const a of currentAttempts) {
    const marked = latestMarkedByAttempt.get(a.id)
    if (!marked || marked.result !== 'needs_resubmission') continue
    const resource = resourceMap.get(a.resource_id)
    resubmission_queue.push({
      attempt_id:     a.id,
      resource_title: resource?.title ?? '—',
      resource_key:   resource?.resource_key ?? '—',
      topic:          resource?.topic ?? null,
      feedback:       marked.feedback ?? null,
      submitted_at:   a.submitted_at,
    })
  }

  // Recent attempts (latest 10, newest first)
  const recent_attempts: RecentAttemptItem[] = [...attempts]
    .sort((a, b) => b.submitted_at.localeCompare(a.submitted_at))
    .slice(0, 10)
    .map((a) => {
      const marked   = latestMarkedByAttempt.get(a.id)
      const resource = resourceMap.get(a.resource_id)
      return {
        attempt_id:     a.id,
        resource_title: resource?.title ?? '—',
        resource_key:   resource?.resource_key ?? '—',
        topic:          resource?.topic ?? null,
        result:         marked?.result ?? null,
        marking_method: marked?.marking_method ?? null,
        submitted_at:   a.submitted_at,
        attempt_type:   a.attempt_type,
        marking_status: a.marking_status,
      }
    })

  return {
    student_id:                    student.id,
    student_name:                  student.display_name,
    subject_slug:                  subject.subject_slug,
    attempt_count:                 attempts.length,
    marked_attempt_count:          latestMarkedByAttempt.size,
    unmarked_count,
    auto_marked_count,
    teacher_review_required_count,
    teacher_reviewed_count,
    correct_count,
    incorrect_count,
    partially_correct_count,
    needs_resubmission_count,
    pending_teacher_review_count,
    accuracy,
    strengths,
    skill_gaps,
    resubmission_queue,
    recent_attempts,
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function getLiveSupabaseStudentResults(
  studentCode = DEMO_STUDENT_CODE,
  subjectSlug = DEMO_SUBJECT_SLUG,
): Promise<StudentResultReport | null> {
  if (!isLiveSupabaseConfigured()) return null
  try {
    const client = requireSupabaseClient()

    const [student, subject] = await Promise.all([
      _resolveStudent(client, studentCode),
      _resolveSubject(client, subjectSlug),
    ])
    if (!student || !subject) return null

    const attempts = await _loadAttempts(client, student.id, subject.id)
    if (!attempts.length) {
      // Return empty report rather than null — student exists but has no attempts
      return {
        student_id:                    student.id,
        student_name:                  student.display_name,
        subject_slug:                  subject.subject_slug,
        attempt_count:                 0,
        marked_attempt_count:          0,
        unmarked_count:                0,
        auto_marked_count:             0,
        teacher_review_required_count: 0,
        teacher_reviewed_count:        0,
        correct_count:                 0,
        incorrect_count:               0,
        partially_correct_count:       0,
        needs_resubmission_count:      0,
        pending_teacher_review_count:  0,
        accuracy:                      null,
        strengths:                     [],
        skill_gaps:                    [],
        resubmission_queue:            [],
        recent_attempts:               [],
      }
    }

    const attemptIds = attempts.map((a) => a.id)
    const resourceIds = [...new Set(attempts.map((a) => a.resource_id))]

    const [markedRows, resourceRows] = await Promise.all([
      _loadMarkedAttempts(client, attemptIds),
      _loadResources(client, resourceIds),
    ])

    // Latest marked_attempt per attempt (oldest-first iteration, latest wins)
    const latestMarkedByAttempt = new Map<string, MarkedAttemptRow>()
    for (const m of markedRows) {
      latestMarkedByAttempt.set(m.attempt_id, m)
    }

    // Resource map
    const resourceMap = new Map<string, ResourceRow>()
    for (const r of resourceRows) {
      resourceMap.set(r.id, r)
    }

    return _buildReport(student, subject, attempts, latestMarkedByAttempt, resourceMap)
  } catch {
    return null
  }
}

export async function getLiveSupabaseLatestLearningState(
  studentCode = DEMO_STUDENT_CODE,
  subjectSlug = DEMO_SUBJECT_SLUG,
): Promise<LearningState | null> {
  const report = await getLiveSupabaseStudentResults(studentCode, subjectSlug)
  if (!report) return null

  const pending_count = report.unmarked_count + report.teacher_review_required_count

  let next_action = 'No pending actions.'
  if (report.resubmission_queue.length > 0) {
    next_action = `Resubmit ${report.resubmission_queue.length} item${report.resubmission_queue.length > 1 ? 's' : ''} flagged for resubmission.`
  } else if (pending_count > 0) {
    next_action = `${pending_count} attempt${pending_count > 1 ? 's' : ''} awaiting marking.`
  } else if (report.skill_gaps.filter((g) => g.result === 'incorrect').length > 0) {
    next_action = 'Review incorrect answers and retry.'
  } else if (report.attempt_count === 0) {
    next_action = 'No attempts yet. Start practising.'
  }

  return {
    student_name:       report.student_name,
    subject_slug:       report.subject_slug,
    total_attempted:    report.attempt_count,
    accuracy:           report.accuracy,
    pending_count,
    resubmission_count: report.resubmission_queue.length,
    top_gaps:           report.skill_gaps.slice(0, 3),
    next_action,
  }
}
