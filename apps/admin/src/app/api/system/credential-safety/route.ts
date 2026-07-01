import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  const contentSource  = process.env.QA_CONTENT_SOURCE ?? 'local'
  const demoFallback   = process.env.QA_AUTH_DEMO_FALLBACK
  const isProduction   = process.env.NODE_ENV === 'production'

  const demoFallbackOff = demoFallback === 'false'
  const isLive          = contentSource === 'live_supabase'

  // Credential hardening is always required while demo accounts may exist.
  // The API cannot verify whether passwords have been rotated — that requires
  // the check_gate69a_credential_safety_v1.py script with service role access.
  const credentialHardeningRequired = true

  // Internal testing is safe when demo fallback is off and env is live.
  const internalTestingSafe = demoFallbackOff && (isLive || !isProduction)

  // Public launch requires:
  //  1. demo fallback off (checked here)
  //  2. demo passwords rotated or accounts disabled (cannot verify from this API)
  //  3. real admin account created (cannot verify from this API)
  // So this API always reports public_launch_blocked until manual confirmation.
  const status: 'internal_testing_ok' | 'public_launch_blocked' | 'failed' =
    !demoFallbackOff ? 'failed'
    : internalTestingSafe ? 'internal_testing_ok'
    : 'public_launch_blocked'

  return NextResponse.json({
    status,
    environment:                  isProduction ? 'production' : 'development',
    content_source:               contentSource,
    qa_auth_demo_fallback:        demoFallbackOff,
    credential_hardening_required: credentialHardeningRequired,
    secrets_exposed:              false,
    public_launch_blocked_reason:
      'Demo accounts may still exist with known passwords. ' +
      'Run check_gate69a_credential_safety_v1.py to verify.',
    internal_testing_safe:        internalTestingSafe,
    timestamp:                    new Date().toISOString(),
  })
}
