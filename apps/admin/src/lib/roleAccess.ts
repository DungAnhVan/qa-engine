/**
 * SERVER-ONLY — Role-based route access logic — Gate 62.
 *
 * Provides helpers to check whether the current authenticated user
 * (or demo fallback) has permission to access a given page or feature.
 *
 * No JSX here — use RoleGate.tsx for the component wrapper.
 * Use requireAppRole() for inline early-return checks in page.tsx files.
 *
 * Rules (Gate 62 foundation — Gate 63 may tighten further):
 *   admin   → all routes
 *   teacher → content, learn, system/student-results, system/teacher-review, system/marking
 *   student → learn routes, system/auth-session
 *   parent  → learn/supabase-results, system/auth-session
 *   none    → login, logout, public diagnostic pages only
 */
import 'server-only'

import { getCurrentProfile } from './serverSupabaseAuth'
import type { UserRole } from './serverSupabaseAuth'

// ---------------------------------------------------------------------------
// Route access config
// ---------------------------------------------------------------------------

const ADMIN_ALL = true  // admin has access to everything

const ROLE_ALLOWED_PREFIXES: Record<Exclude<UserRole, 'admin'>, string[]> = {
  teacher: [
    '/content',
    '/learn/attempt-review',
    '/learn/supabase-attempt-review',
    '/learn/results',
    '/learn/supabase-results',
    '/system/student-results',
    '/system/teacher-review',
    '/system/marking',
    '/system/auth-session',
    '/system/auth-roles',
    '/system/role-access',
  ],
  student: [
    '/learn/practice',
    '/learn/results',
    '/learn/supabase-results',
    '/system/auth-session',
  ],
  parent: [
    '/learn/supabase-results',
    '/system/auth-session',
  ],
}

const PUBLIC_PREFIXES = [
  '/login',
  '/logout',
  '/system/content-source',
  '/system/auth-roles',
  '/system/auth-session',
  '/system/role-access',
]

// ---------------------------------------------------------------------------
// canAccessRoute
// ---------------------------------------------------------------------------

export function canAccessRoute(role: UserRole | null, pathname: string): boolean {
  if (!role) {
    return PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + '/'))
  }
  if (role === 'admin') return ADMIN_ALL
  const allowed = ROLE_ALLOWED_PREFIXES[role] ?? []
  return allowed.some((p) => pathname === p || pathname.startsWith(p + '/'))
}

// ---------------------------------------------------------------------------
// getRoleHomePath
// ---------------------------------------------------------------------------

export function getRoleHomePath(role: UserRole | null): string {
  switch (role) {
    case 'admin':   return '/system/auth-session'
    case 'teacher': return '/content'
    case 'student': return '/learn/practice'
    case 'parent':  return '/learn/supabase-results'
    default:        return '/login'
  }
}

// ---------------------------------------------------------------------------
// Route access matrix — all roles vs all key routes (for diagnostic page)
// ---------------------------------------------------------------------------

export const ROUTE_ACCESS_MATRIX: Array<{
  path:    string
  label:   string
  admin:   boolean
  teacher: boolean
  student: boolean
  parent:  boolean
}> = [
  { path: '/',                             label: 'Home',              admin: true,  teacher: false, student: false, parent: false },
  { path: '/content',                      label: 'Content Registry',  admin: true,  teacher: true,  student: false, parent: false },
  { path: '/content/active',               label: 'Active Content',    admin: true,  teacher: true,  student: false, parent: false },
  { path: '/content/review',               label: 'Teacher Review',    admin: true,  teacher: true,  student: false, parent: false },
  { path: '/learn/practice',               label: 'Practice',          admin: true,  teacher: true,  student: true,  parent: false },
  { path: '/learn/results',                label: 'Results',           admin: true,  teacher: true,  student: true,  parent: false },
  { path: '/learn/supabase-results',       label: 'Live Results',      admin: true,  teacher: true,  student: true,  parent: true  },
  { path: '/learn/supabase-attempt-review',label: 'Attempt Review',    admin: true,  teacher: true,  student: false, parent: false },
  { path: '/system/marking',               label: 'Marking System',    admin: true,  teacher: true,  student: false, parent: false },
  { path: '/system/teacher-review',        label: 'Teacher Review Sys',admin: true,  teacher: true,  student: false, parent: false },
  { path: '/system/student-results',       label: 'Student Results Sys',admin: true, teacher: true,  student: false, parent: false },
  { path: '/system/auth-roles',            label: 'Auth Roles',        admin: true,  teacher: true,  student: false, parent: false },
  { path: '/system/auth-session',          label: 'Auth Session',      admin: true,  teacher: true,  student: true,  parent: true  },
  { path: '/system/role-access',           label: 'Role Access',       admin: true,  teacher: true,  student: false, parent: false },
  { path: '/login',                        label: 'Login',             admin: true,  teacher: true,  student: true,  parent: true  },
  { path: '/logout',                       label: 'Logout',            admin: true,  teacher: true,  student: true,  parent: true  },
]

// ---------------------------------------------------------------------------
// requireAppRole — call at the top of server page functions
// ---------------------------------------------------------------------------

export interface RoleCheckResult {
  allowed:      boolean
  currentRole:  UserRole | null
  currentEmail: string | null
  is_demo:      boolean
}

export async function requireAppRole(allowedRoles: UserRole[]): Promise<RoleCheckResult> {
  const profile = await getCurrentProfile()
  const role    = profile?.role ?? null
  return {
    allowed:      !!role && allowedRoles.includes(role),
    currentRole:  role,
    currentEmail: profile?.email ?? null,
    is_demo:      false,
  }
}
