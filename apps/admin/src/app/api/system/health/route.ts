import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  return NextResponse.json({
    status:                     'ok',
    app:                        'quanta-aptus-admin',
    content_source:             process.env.QA_CONTENT_SOURCE ?? 'local',
    demo_fallback:              process.env.QA_AUTH_DEMO_FALLBACK ?? 'not_set',
    node_env:                   process.env.NODE_ENV ?? 'development',
    supabase_url_present:       Boolean(process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL),
    anon_key_present:           Boolean(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY),
    service_role_present_server: Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY),
    timestamp:                  new Date().toISOString(),
  })
}
