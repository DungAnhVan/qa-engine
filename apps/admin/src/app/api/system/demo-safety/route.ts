import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  const contentSource  = process.env.QA_CONTENT_SOURCE ?? 'local'
  const demoFallback   = process.env.QA_AUTH_DEMO_FALLBACK
  const isProduction   = process.env.NODE_ENV === 'production'

  const demoFallbackOff = demoFallback === 'false'
  const isLive          = contentSource === 'live_supabase'

  // Public launch is NOT safe while demo accounts exist with known passwords.
  // This is always false from the API's perspective — the API has no way to
  // verify whether passwords have been rotated. Manual confirmation is required.
  const publicLaunchSafe = false

  // Internal testing is safe when demo fallback is off and env is configured.
  const internalTestingSafe = demoFallbackOff && (isLive || !isProduction)

  const status: 'internal_testing_ok' | 'public_launch_blocked' | 'failed' =
    !demoFallbackOff ? 'failed'
    : internalTestingSafe ? 'internal_testing_ok'
    : 'public_launch_blocked'

  return NextResponse.json({
    status,
    environment:         isProduction ? 'production' : 'development',
    qa_auth_demo_fallback: demoFallbackOff,
    content_source:      contentSource,
    demo_safety_warning: true,
    public_launch_safe:  publicLaunchSafe,
    public_launch_blocked_reason:
      'Demo accounts exist with known passwords. Rotate or remove before public launch.',
    internal_testing_safe: internalTestingSafe,
    timestamp:           new Date().toISOString(),
  })
}
