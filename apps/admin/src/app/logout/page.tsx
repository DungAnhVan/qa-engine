'use client'

/**
 * /logout — Gate 61 logout page.
 * Auto-calls signOut() on mount and redirects to /login.
 */
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createBrowserSupabaseClient, isBrowserSupabaseConfigured } from '@/lib/browserSupabaseClient'

type Status = 'signing_out' | 'done' | 'no_client'

export default function LogoutPage() {
  const router = useRouter()
  const [status, setStatus] = useState<Status>('signing_out')

  useEffect(() => {
    if (!isBrowserSupabaseConfigured()) {
      setStatus('no_client')
      return
    }
    const client = createBrowserSupabaseClient()
    client.auth.signOut()
      .then(() => {
        setStatus('done')
        router.push('/login')
      })
      .catch(() => {
        setStatus('done')
        router.push('/login')
      })
  }, [router])

  return (
    <main style={{ padding: '2rem', maxWidth: 480, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 12 }}>
        {status === 'signing_out' ? 'Signing out…' : 'Signed out'}
      </h1>
      {status === 'no_client' && (
        <p style={{ color: '#92400e', fontSize: 14 }}>
          Supabase not configured — nothing to sign out of.{' '}
          <a href="/login" style={{ color: '#3b82f6' }}>Go to login</a>
        </p>
      )}
      {status === 'done' && (
        <p style={{ color: '#6b7280', fontSize: 14 }}>
          Redirecting… <a href="/login" style={{ color: '#3b82f6' }}>Click here if not redirected</a>
        </p>
      )}
    </main>
  )
}
