/**
 * RoleGate — Gate 62 server component role guard.
 *
 * Server Component — calls getCurrentProfile() server-side.
 * Use as a wrapper around page content that requires a specific role.
 *
 * Example:
 *   <RoleGate allowedRoles={['admin', 'teacher']}>
 *     <ContentPage />
 *   </RoleGate>
 *
 * For early-return guards at page level, use requireAppRole() from roleAccess.ts.
 * No secrets are rendered by this component.
 */
import { getCurrentProfile } from '@/lib/serverSupabaseAuth'
import type { UserRole } from '@/lib/serverSupabaseAuth'

interface Props {
  allowedRoles: UserRole[]
  children:     React.ReactNode
}

function LoginPrompt() {
  return (
    <main style={{ padding: '2rem', maxWidth: 480, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Sign in required</h1>
      <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 14 }}>
        You need to be signed in to access this page.
      </p>
      <a
        href="/login"
        style={{ color: '#3b82f6', fontWeight: 600, fontSize: 14 }}
      >
        Go to login →
      </a>
    </main>
  )
}

function AccessDenied({ role, allowedRoles }: { role: string | null; allowedRoles: UserRole[] }) {
  return (
    <main style={{ padding: '2rem', maxWidth: 480, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, color: '#991b1b' }}>
        Access denied
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 8, fontSize: 14 }}>
        Your role <code style={{ background: '#f3f4f6', padding: '1px 4px', borderRadius: 3 }}>{role ?? 'none'}</code> does
        not have access to this page.
      </p>
      <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 14 }}>
        Required role: <strong>{allowedRoles.join(' or ')}</strong>
      </p>
      <p style={{ fontSize: 13 }}>
        <a href="/login"             style={{ color: '#3b82f6', marginRight: 16 }}>Switch account</a>
        <a href="/system/auth-session" style={{ color: '#3b82f6' }}>Auth session</a>
      </p>
    </main>
  )
}

export default async function RoleGate({ allowedRoles, children }: Props) {
  const profile = await getCurrentProfile()

  if (!profile) {
    return <LoginPrompt />
  }

  const role = profile.role
  if (!role || !allowedRoles.includes(role)) {
    return <AccessDenied role={role ?? null} allowedRoles={allowedRoles} />
  }

  return <>{children}</>
}
