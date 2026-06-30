/**
 * SERVER-ONLY — Live Supabase student attempt write module.
 *
 * WARNING: This file reads SUPABASE_SERVICE_ROLE_KEY.
 * Must NEVER be imported in client components.
 * The `import 'server-only'` guard enforces this at build time.
 *
 * Gate 56: writes student attempts to the `attempts` table.
 * No marking is performed here — marking is Gate 57.
 * No Supabase schema or RLS is modified.
 * No Cambridge source text is written.
 */
import 'server-only'

import { createClient } from '@supabase/supabase-js'

const DEMO_STUDENT_EXTERNAL_CODE = 'local_demo_student'
const DEMO_STUDENT_UUID_FALLBACK  = '20000000-0000-0000-0000-000000000001'
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function isValidUuid(s: string | null | undefined): boolean {
  return s != null && UUID_REGEX.test(s)
}

// ---------------------------------------------------------------------------
// Client factory — same env-guard pattern as liveSupabaseContent.ts
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
      'live_supabase attempt write requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local.',
    )
  }
  return createClient(config.url, config.serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })
}

type AppClient = ReturnType<typeof requireSupabaseClient>

// ---------------------------------------------------------------------------
// Public lookup helpers
// ---------------------------------------------------------------------------

export interface DemoStudent {
  id: string
  display_name: string
  external_code: string
}

export async function getLiveSupabaseDemoStudent(): Promise<DemoStudent | null> {
  if (!isLiveSupabaseConfigured()) return null
  try {
    const client = requireSupabaseClient()
    const { data } = await client
      .from('students')
      .select('id, display_name, external_code')
      .eq('external_code', DEMO_STUDENT_EXTERNAL_CODE)
      .maybeSingle()
    if (!data) return null
    const row = (data as unknown) as { id: string; display_name: string; external_code: string }
    return { id: row.id, display_name: row.display_name, external_code: row.external_code }
  } catch {
    return null
  }
}

export interface ResourceLookup {
  id: string
  subject_id: string | null
}

export async function getLiveSupabaseResourceByKey(
  resourceKey: string,
): Promise<ResourceLookup | null> {
  if (!isLiveSupabaseConfigured()) return null
  try {
    const client = requireSupabaseClient()
    const { data } = await client
      .from('resources')
      .select('id, subject_id')
      .eq('resource_key', resourceKey)
      .maybeSingle()
    if (!data) return null
    const row = (data as unknown) as { id: string; subject_id: string | null }
    return { id: row.id, subject_id: row.subject_id }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Attempt write
// ---------------------------------------------------------------------------

export interface LiveAttemptInput {
  student_id?: string
  resource_key: string
  subject_slug?: string
  answer_text: string
  answer_json?: Record<string, unknown>
  confidence_level?: 'low' | 'medium' | 'high' | 'unknown'
  attempt_type?: 'first_attempt' | 'resubmission'
  parent_attempt_id?: string | null
}

export interface LiveAttemptResult {
  success: boolean
  attempt_id?: string
  submitted_at?: string
  marking_status?: string
  storage?: string
  error?: string
}

async function _resolveStudentId(
  client: AppClient,
  studentId?: string,
): Promise<string> {
  if (studentId && isValidUuid(studentId)) return studentId

  try {
    const { data } = await client
      .from('students')
      .select('id')
      .eq('external_code', DEMO_STUDENT_EXTERNAL_CODE)
      .maybeSingle()
    if (data) {
      const row = (data as unknown) as { id: string }
      return row.id
    }
  } catch {
    // fall through to hardcoded fallback
  }

  return DEMO_STUDENT_UUID_FALLBACK
}

export async function createLiveSupabaseAttempt(
  input: LiveAttemptInput,
): Promise<LiveAttemptResult> {
  if (!isLiveSupabaseConfigured()) {
    return { success: false, error: 'live_supabase is not configured (missing env vars).' }
  }

  try {
    const client = requireSupabaseClient()

    // 1. Resolve student
    const studentId = await _resolveStudentId(client, input.student_id)

    // 2. Resolve resource by resource_key
    const resource = await getLiveSupabaseResourceByKey(input.resource_key)
    if (!resource) {
      return {
        success: false,
        error: `Resource not found in Supabase: ${input.resource_key}`,
      }
    }

    // 3. Subject from resource (resource.subject_id is the FK to subjects table)
    const subjectId = resource.subject_id ?? null

    // 4. Validate parent_attempt_id — must be a real UUID (not a local attempt_xxx_yyy string)
    const parentAttemptId =
      input.parent_attempt_id && isValidUuid(input.parent_attempt_id)
        ? input.parent_attempt_id
        : null

    // 5. Insert attempt — marking_status starts as 'unmarked' (Gate 57 will mark)
    const { data, error: insertError } = await client
      .from('attempts')
      .insert({
        student_id:        studentId,
        resource_id:       resource.id,
        subject_id:        subjectId,
        attempt_type:      input.attempt_type ?? 'first_attempt',
        parent_attempt_id: parentAttemptId,
        answer_text:       input.answer_text,
        answer_json:       input.answer_json ?? {},
        confidence_level:  input.confidence_level ?? 'unknown',
        marking_status:    'unmarked',
      })
      .select('id, submitted_at, marking_status')
      .single()

    if (insertError || !data) {
      return {
        success: false,
        error: insertError?.message ?? 'Attempt insert returned no data.',
      }
    }

    const row = (data as unknown) as {
      id: string
      submitted_at: string
      marking_status: string
    }

    return {
      success:        true,
      attempt_id:     row.id,
      submitted_at:   row.submitted_at,
      marking_status: row.marking_status,
      storage:        'supabase',
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return { success: false, error: msg }
  }
}
