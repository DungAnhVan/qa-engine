import { NextResponse } from 'next/server'
import { existsSync } from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

type CheckStatus = 'PASS' | 'FAIL' | 'WARN' | 'SKIP'

interface Check {
  key: string
  label: string
  status: CheckStatus
  detail: string | null
  critical: boolean
}

function fileCheck(relPath: string): boolean {
  return existsSync(path.join(process.cwd(), relPath))
}

function repoFileCheck(relFromRoot: string): boolean {
  return existsSync(path.join(process.cwd(), '../..', relFromRoot))
}

export async function GET() {
  const contentSource = process.env.QA_CONTENT_SOURCE ?? 'local'
  const isLive        = contentSource === 'live_supabase'
  const isProduction  = process.env.NODE_ENV === 'production'
  const demoFallback  = process.env.QA_AUTH_DEMO_FALLBACK

  const checks: Check[] = []

  // ── Content source ────────────────────────────────────────────────────────
  const contentValid = ['local', 'live_supabase'].includes(contentSource)
  checks.push({
    key:      'content_source_valid',
    label:    'QA_CONTENT_SOURCE valid',
    status:   contentValid ? 'PASS' : 'FAIL',
    detail:   contentValid ? contentSource : `invalid: "${contentSource}"`,
    critical: true,
  })

  checks.push({
    key:      'content_source_is_live',
    label:    'QA_CONTENT_SOURCE is live_supabase',
    status:   isLive ? 'PASS' : 'WARN',
    detail:   isLive
      ? 'live_supabase active'
      : `currently "${contentSource}" — production requires live_supabase`,
    critical: false,
  })

  checks.push({
    key:      'demo_fallback_off',
    label:    'QA_AUTH_DEMO_FALLBACK off',
    status:   demoFallback === 'false' ? 'PASS' : 'WARN',
    detail:   demoFallback === 'false'
      ? 'disabled (correct for production)'
      : `current: ${demoFallback ?? 'not_set'} — set to false for production`,
    critical: false,
  })

  // ── Supabase env vars ─────────────────────────────────────────────────────
  const supabaseUrlPresent   = Boolean(process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL)
  const nextPublicUrlPresent = Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL)
  const anonKeyPresent       = Boolean(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY)
  const serviceRolePresent   = Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY)

  checks.push({
    key:      'supabase_url_present',
    label:    'SUPABASE_URL present',
    status:   supabaseUrlPresent ? 'PASS' : (isLive ? 'FAIL' : 'WARN'),
    detail:   supabaseUrlPresent ? 'present' : 'missing',
    critical: isLive,
  })

  checks.push({
    key:      'next_public_supabase_url_present',
    label:    'NEXT_PUBLIC_SUPABASE_URL present',
    status:   nextPublicUrlPresent ? 'PASS' : (isLive ? 'FAIL' : 'WARN'),
    detail:   nextPublicUrlPresent ? 'present' : 'missing — required for browser auth',
    critical: isLive,
  })

  checks.push({
    key:      'anon_key_present',
    label:    'NEXT_PUBLIC_SUPABASE_ANON_KEY present',
    status:   anonKeyPresent ? 'PASS' : (isLive ? 'FAIL' : 'WARN'),
    detail:   anonKeyPresent ? 'present' : 'missing — required for browser auth',
    critical: isLive,
  })

  checks.push({
    key:      'service_role_present',
    label:    'SUPABASE_SERVICE_ROLE_KEY present (server-only)',
    status:   serviceRolePresent ? 'PASS' : (isLive ? 'FAIL' : 'WARN'),
    detail:   serviceRolePresent ? 'present (value never shown)' : 'missing — required for server data reads',
    critical: isLive,
  })

  // ── Source file checks: local dev only ────────────────────────────────────
  // Vercel production deploys only compiled .next output; source files are
  // absent so existsSync on src/** always returns false there.
  const SKIP_DETAIL = 'skipped in production runtime — source files absent from build output'

  const fileChecks: Array<[string, string, () => boolean]> = [
    ['login_ui_exists',              'Login UI (src/app/login/page.tsx)',         () => fileCheck('src/app/login/page.tsx')],
    ['logout_page_exists',           'Logout page (src/app/logout/page.tsx)',     () => fileCheck('src/app/logout/page.tsx')],
    ['role_access_module_exists',    'roleAccess.ts module',                     () => fileCheck('src/lib/roleAccess.ts')],
    ['server_auth_module_exists',    'serverSupabaseAuth.ts module',             () => fileCheck('src/lib/serverSupabaseAuth.ts')],
    ['browser_client_module_exists', 'browserSupabaseClient.ts module',          () => fileCheck('src/lib/browserSupabaseClient.ts')],
    ['role_gate_exists',             'RoleGate.tsx component',                   () => fileCheck('src/components/RoleGate.tsx')],
    ['health_page_exists',           'Health page (src/app/system/health)',       () => fileCheck('src/app/system/health/page.tsx')],
    ['rls_migration_exists',         'RLS migration 000004',                     () => repoFileCheck('supabase/migrations/000004_rls_role_hardening.sql')],
    ['gate62_marker_exists',         'Gate 62 done marker',                      () => repoFileCheck('data/diagnostics/SUPABASE_GATE_62_RLS_ROLE_ACCESS_DONE.md')],
    ['env_template_exists',          '.env.production.example template',          () => repoFileCheck('.env.production.example')],
    ['deploy_checklist_exists',      'Deployment checklist',                     () => repoFileCheck('deployment/VERCEL_DEPLOYMENT_CHECKLIST.md')],
    ['security_checklist_exists',    'Security pre-deploy checklist',            () => repoFileCheck('deployment/SECURITY_PREDEPLOY_CHECKLIST.md')],
  ]

  for (const [key, label, check] of fileChecks) {
    if (isProduction) {
      checks.push({ key, label, status: 'SKIP', detail: SKIP_DETAIL, critical: false })
    } else {
      const exists = check()
      checks.push({
        key,
        label,
        status:   exists ? 'PASS' : 'WARN',
        detail:   exists ? 'found' : 'not found',
        critical: false,
      })
    }
  }

  // ── Derive overall status ─────────────────────────────────────────────────
  const hasFail = checks.some(c => c.status === 'FAIL')
  const hasWarn = checks.some(c => c.status === 'WARN')
  const status  = hasFail ? 'failed' : hasWarn ? 'needs_review' : 'ready'

  return NextResponse.json({
    status,
    environment:    isProduction ? 'production' : 'development',
    content_source: contentSource,
    checks,
    timestamp:      new Date().toISOString(),
  })
}
