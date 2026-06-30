import { NextResponse } from 'next/server'
import { existsSync } from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

function fileCheck(relPath: string): boolean {
  return existsSync(path.join(process.cwd(), relPath))
}

function repoFileCheck(relFromRoot: string): boolean {
  return existsSync(path.join(process.cwd(), '../..', relFromRoot))
}

export async function GET() {
  const contentSource = process.env.QA_CONTENT_SOURCE ?? 'local'
  const isLive        = contentSource === 'live_supabase'

  const checks: Record<string, boolean | string> = {
    content_source_valid:          contentSource === 'local' || contentSource === 'live_supabase',
    content_source_is_live:        isLive,
    demo_fallback_off:             process.env.QA_AUTH_DEMO_FALLBACK !== 'true',
    supabase_url_present:          Boolean(process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL),
    anon_key_present:              Boolean(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY),
    service_role_present:          Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY),
    login_ui_exists:               fileCheck('src/app/login/page.tsx'),
    role_access_module_exists:     fileCheck('src/lib/roleAccess.ts'),
    server_auth_module_exists:     fileCheck('src/lib/serverSupabaseAuth.ts'),
    browser_client_module_exists:  fileCheck('src/lib/browserSupabaseClient.ts'),
    rls_migration_exists:          repoFileCheck('supabase/migrations/000004_rls_role_hardening.sql'),
    rls_gate_marker_exists:        repoFileCheck('data/diagnostics/SUPABASE_GATE_62_RLS_ROLE_ACCESS_DONE.md'),
    health_page_exists:            fileCheck('src/app/system/health/page.tsx'),
    production_env_template:       repoFileCheck('.env.production.example'),
  }

  const criticalKeys: Array<keyof typeof checks> = [
    'content_source_valid',
    'login_ui_exists',
    'role_access_module_exists',
    'server_auth_module_exists',
    'browser_client_module_exists',
  ]

  const reviewKeys: Array<keyof typeof checks> = [
    'supabase_url_present',
    'anon_key_present',
    'service_role_present',
    'rls_migration_exists',
    'rls_gate_marker_exists',
    'production_env_template',
    'demo_fallback_off',
    'content_source_is_live',
  ]

  const criticalFailed  = criticalKeys.some(k => checks[k] === false)
  const reviewNeeded    = reviewKeys.some(k => checks[k] === false)

  const status = criticalFailed ? 'failed' : reviewNeeded ? 'needs_review' : 'ready'

  return NextResponse.json({
    status,
    checks,
    content_source: contentSource,
    timestamp: new Date().toISOString(),
  })
}
