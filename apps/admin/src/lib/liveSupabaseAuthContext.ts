/**
 * SERVER-ONLY — Live Supabase auth context module.
 *
 * WARNING: This file reads SUPABASE_SERVICE_ROLE_KEY.
 * Must NEVER be imported in client components.
 * The `import 'server-only'` guard enforces this at build time.
 *
 * Gate 60: auth/roles foundation.
 *   - Provides a demo auth context when no real auth user is present.
 *   - Exposes profile, role, and linked-student queries for server components.
 *   - No login UI yet — that is Gate 61.
 *   - No OpenAI. No Cambridge source text.
 *
 * Gate 61 will wire real Supabase Auth session to replace getDemoAuthContext().
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
      'live_supabase auth context requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local.',
    )
  }
  return createClient(config.url, config.serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })
}

type AppClient = ReturnType<typeof requireSupabaseClient>

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type UserRole = 'admin' | 'teacher' | 'student' | 'parent'

export interface DemoAuthContext {
  mode:              'demo_auth_context'
  role:              UserRole
  organization_slug: string
}

export interface ProfileRow {
  id:              string
  organization_id: string | null
  display_name:    string | null
  email:           string | null
  role:            UserRole | null
}

export interface RoleSummary {
  role:  UserRole
  count: number
}

export interface AuthRoleStats {
  profiles_total:     number
  by_role:            RoleSummary[]
  organizations:      Array<{ id: string; name: string; slug: string }>
  students_count:     number
  parent_links_count: number
}

// ---------------------------------------------------------------------------
// Demo context — returned until real auth is wired (Gate 61)
// ---------------------------------------------------------------------------

export function getDemoAuthContext(): DemoAuthContext {
  return {
    mode:              'demo_auth_context',
    role:              'admin',
    organization_slug: 'quanta-aptus-local-demo',
  }
}

// ---------------------------------------------------------------------------
// Profile queries
// ---------------------------------------------------------------------------

export async function getProfileById(profileId: string): Promise<ProfileRow | null> {
  if (!isLiveSupabaseConfigured()) return null
  try {
    const client = requireSupabaseClient()
    const { data } = await client
      .from('profiles')
      .select('id, organization_id, display_name, email, role')
      .eq('id', profileId)
      .maybeSingle()
    return data ? ((data as unknown) as ProfileRow) : null
  } catch {
    return null
  }
}

export async function getProfilesByRole(role: UserRole): Promise<ProfileRow[]> {
  if (!isLiveSupabaseConfigured()) return []
  try {
    const client = requireSupabaseClient()
    const { data } = await client
      .from('profiles')
      .select('id, organization_id, display_name, email, role')
      .eq('role', role)
      .order('display_name')
    return ((data ?? []) as unknown) as ProfileRow[]
  } catch {
    return []
  }
}

// ---------------------------------------------------------------------------
// Student / parent linkage queries
// ---------------------------------------------------------------------------

export async function getStudentForProfile(profileId: string): Promise<{
  id: string
  display_name: string
  external_code: string | null
} | null> {
  if (!isLiveSupabaseConfigured()) return null
  try {
    const client = requireSupabaseClient()
    const { data } = await client
      .from('students')
      .select('id, display_name, external_code')
      .eq('profile_id', profileId)
      .maybeSingle()
    return data
      ? ((data as unknown) as { id: string; display_name: string; external_code: string | null })
      : null
  } catch {
    return null
  }
}

export async function getParentLinkedStudents(profileId: string): Promise<
  Array<{ student_id: string; student_name: string; relationship: string | null }>
> {
  if (!isLiveSupabaseConfigured()) return []
  try {
    const client = requireSupabaseClient()
    // 1. Fetch links for this parent profile
    const { data: links } = await client
      .from('parent_student_links')
      .select('student_id, relationship')
      .eq('parent_profile_id', profileId)
    if (!links || !links.length) return []

    // 2. Batch fetch student names
    const studentIds = (links as Array<{ student_id: string; relationship: string | null }>).map(
      (l) => l.student_id,
    )
    const { data: students } = await client
      .from('students')
      .select('id, display_name')
      .in('id', studentIds)
    const studentMap = new Map<string, string>()
    for (const s of ((students ?? []) as Array<{ id: string; display_name: string }>)) {
      studentMap.set(s.id, s.display_name)
    }

    return (links as Array<{ student_id: string; relationship: string | null }>).map((l) => ({
      student_id:    l.student_id,
      student_name:  studentMap.get(l.student_id) ?? 'Unknown',
      relationship:  l.relationship ?? null,
    }))
  } catch {
    return []
  }
}

// ---------------------------------------------------------------------------
// Diagnostic stats — for /system/auth-roles page
// ---------------------------------------------------------------------------

export async function getAuthRoleStats(): Promise<AuthRoleStats | null> {
  if (!isLiveSupabaseConfigured()) return null
  try {
    const client = requireSupabaseClient()
    const VALID_ROLES: UserRole[] = ['admin', 'teacher', 'student', 'parent']

    const [orgsRes, studentsRes, parentLinksRes, ...roleCounts] = await Promise.all([
      client.from('organizations').select('id, name, slug'),
      client.from('students').select('id', { count: 'exact', head: true }),
      client.from('parent_student_links').select('id', { count: 'exact', head: true }),
      ...VALID_ROLES.map((r) =>
        client
          .from('profiles')
          .select('id', { count: 'exact', head: true })
          .eq('role', r),
      ),
    ])

    const by_role: RoleSummary[] = VALID_ROLES.map((r, i) => ({
      role:  r,
      count: roleCounts[i]?.count ?? 0,
    }))

    const profiles_total = by_role.reduce((sum, r) => sum + r.count, 0)

    const organizations = ((orgsRes.data ?? []) as Array<{ id: string; name: string; slug: string }>)

    return {
      profiles_total,
      by_role,
      organizations,
      students_count:     studentsRes.count ?? 0,
      parent_links_count: parentLinksRes.count ?? 0,
    }
  } catch {
    return null
  }
}
