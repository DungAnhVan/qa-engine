/**
 * SERVER-ONLY — Supabase Auth session module — Gate 61.
 *
 * WARNING: This file reads SUPABASE_SERVICE_ROLE_KEY (for profile queries).
 * Must NEVER be imported in client components.
 * The `import 'server-only'` guard enforces this at build time.
 *
 * Session flow:
 *   1. Browser LoginForm calls createBrowserSupabaseClient().auth.signInWithPassword()
 *      → @supabase/ssr stores the session in cookies automatically.
 *   2. On each server render, createServerClient() reads those cookies to
 *      verify the JWT via auth.getUser().
 *   3. Profile (role, org) is looked up from public.profiles via service role.
 *
 * Fallback:
 *   When QA_AUTH_DEMO_FALLBACK=true and no real session exists, returns a
 *   static demo admin context so pages don't break in dev without a login.
 *
 * Gate 62 will harden RLS and remove the demo fallback for production.
 */
import 'server-only'

import { createServerClient } from '@supabase/ssr'
import { createClient } from '@supabase/supabase-js'
import { cookies } from 'next/headers'

// ---------------------------------------------------------------------------
// Config helpers
// ---------------------------------------------------------------------------

function getAnonConfig(): { url: string; anonKey: string } | null {
  const url     = process.env.NEXT_PUBLIC_SUPABASE_URL
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!url || !anonKey) return null
  return { url, anonKey }
}

function getServiceConfig(): { url: string; serviceRoleKey: string } | null {
  const url            = process.env.SUPABASE_URL
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !serviceRoleKey) return null
  return { url, serviceRoleKey }
}

async function createAnonServerClient() {
  const cfg = getAnonConfig()
  if (!cfg) return null
  const cookieStore = await cookies()
  return createServerClient(cfg.url, cfg.anonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll()
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options),
          )
        } catch {
          // Server Components can't set cookies — Route Handlers / Middleware only
        }
      },
    },
  })
}

function createServiceRoleClient() {
  const cfg = getServiceConfig()
  if (!cfg) return null
  return createClient(cfg.url, cfg.serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })
}

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type UserRole = 'admin' | 'teacher' | 'student' | 'parent'

export interface AuthSession {
  user_id:      string
  email:        string | null
  is_demo:      boolean
}

export interface ProfileRow {
  id:              string
  organization_id: string | null
  display_name:    string | null
  email:           string | null
  role:            UserRole | null
}

export type AuthMode = 'live_session' | 'demo_fallback' | 'no_auth'

// ---------------------------------------------------------------------------
// Demo fallback constants
// ---------------------------------------------------------------------------

const DEMO_SESSION: AuthSession = {
  user_id: 'a0000000-0000-0000-0000-000000000001',
  email:   'admin@demo.local',
  is_demo: true,
}

const DEMO_PROFILE: ProfileRow = {
  id:              'a0000000-0000-0000-0000-000000000001',
  organization_id: null,
  display_name:    'Demo Admin',
  email:           'admin@demo.local',
  role:            'admin',
}

function isDemoFallbackEnabled(): boolean {
  return process.env.QA_AUTH_DEMO_FALLBACK === 'true'
}

// ---------------------------------------------------------------------------
// getAuthMode — used by diagnostic pages
// ---------------------------------------------------------------------------

export function getAuthMode(): AuthMode {
  const liveConfigured = !!(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  )
  if (liveConfigured) return 'live_session'
  if (isDemoFallbackEnabled()) return 'demo_fallback'
  return 'no_auth'
}

// ---------------------------------------------------------------------------
// _getRealSession — reads session from @supabase/ssr cookie (no fallback)
// ---------------------------------------------------------------------------

async function _getRealSession(): Promise<{ user_id: string; email: string | null } | null> {
  const client = await createAnonServerClient()
  if (!client) return null
  try {
    const { data: { user }, error } = await client.auth.getUser()
    if (!error && user) return { user_id: user.id, email: user.email ?? null }
  } catch {
    // no session cookie or invalid token
  }
  return null
}

// ---------------------------------------------------------------------------
// getServerAuthSession
// ---------------------------------------------------------------------------

export async function getServerAuthSession(): Promise<AuthSession | null> {
  const real = await _getRealSession()
  if (real) return { ...real, is_demo: false }
  if (isDemoFallbackEnabled()) return DEMO_SESSION
  return null
}

// ---------------------------------------------------------------------------
// getCurrentProfile
// ---------------------------------------------------------------------------

export async function getCurrentProfile(): Promise<ProfileRow | null> {
  const real = await _getRealSession()

  // No real session — use demo profile if fallback is on
  if (!real) {
    if (isDemoFallbackEnabled()) return DEMO_PROFILE
    return null
  }

  // Real session — look up profile via service role (bypasses draft RLS)
  const serviceClient = createServiceRoleClient()
  if (!serviceClient) {
    // Service role not configured; fall through to demo if enabled
    if (isDemoFallbackEnabled()) return DEMO_PROFILE
    return null
  }

  try {
    const { data } = await serviceClient
      .from('profiles')
      .select('id, organization_id, display_name, email, role')
      .eq('id', real.user_id)
      .maybeSingle()
    return data ? ((data as unknown) as ProfileRow) : null
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// getCurrentRole
// ---------------------------------------------------------------------------

export async function getCurrentRole(): Promise<UserRole | null> {
  const profile = await getCurrentProfile()
  return profile?.role ?? null
}

// ---------------------------------------------------------------------------
// requireRole — returns redirect info if caller lacks an allowed role.
// Foundation only — Gate 62 will enforce this strictly.
// ---------------------------------------------------------------------------

export async function requireRole(
  allowedRoles: UserRole[],
): Promise<{ redirect: boolean; redirectTo?: string }> {
  const role = await getCurrentRole()
  if (!role || !allowedRoles.includes(role)) {
    return { redirect: true, redirectTo: '/login' }
  }
  return { redirect: false }
}
