/**
 * /login — Gate 61 login page.
 *
 * Server Component: reads current session server-side so the page renders
 * the correct state on initial load without a client-side flash.
 * LoginForm (client component) handles interactive sign-in / sign-out.
 */
import { getServerAuthSession, getCurrentProfile } from '@/lib/serverSupabaseAuth'
import { isBrowserSupabaseConfigured } from '@/lib/browserSupabaseClient'
import LoginForm from './LoginForm'

export const dynamic = 'force-dynamic'

export default async function LoginPage() {
  const session = await getServerAuthSession()
  const profile = session && !session.is_demo ? await getCurrentProfile() : null

  const currentEmail = session?.email ?? null
  const currentRole  = profile?.role ?? (session?.is_demo ? 'admin (demo)' : null)
  const isDemo       = session?.is_demo ?? false

  const browserConfigured = isBrowserSupabaseConfigured()

  return (
    <main style={{ padding: '2rem', maxWidth: 480, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Quanta Aptus Login
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 28, fontSize: 14 }}>
        Gate 61 — auth foundation. Sign in with your Supabase Auth account.
      </p>

      {!browserConfigured && (
        <div style={{ marginBottom: 20, padding: '10px 14px', background: '#fef3c7', borderRadius: 4, fontSize: 13, color: '#92400e' }}>
          NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY not set.
          Copy <code>.env.example</code> to <code>.env.local</code> and fill in the values,
          then restart the dev server.
        </div>
      )}

      <LoginForm
        initialEmail={currentEmail}
        initialRole={currentRole}
        isDemo={isDemo}
        browserConfigured={browserConfigured}
      />

      <p style={{ marginTop: 24, fontSize: 13, color: '#6b7280' }}>
        <a href="/system/auth-roles"   style={{ color: '#3b82f6', marginRight: 16 }}>Auth Roles</a>
        <a href="/system/auth-session" style={{ color: '#3b82f6', marginRight: 16 }}>Auth Session</a>
        <a href="/learn"               style={{ color: '#3b82f6' }}>Learn</a>
      </p>
    </main>
  )
}
