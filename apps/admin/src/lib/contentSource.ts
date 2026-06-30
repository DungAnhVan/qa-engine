/**
 * Content source mode selector.
 * Controls whether the app reads from local JSON files (default)
 * or from the Supabase export snapshot (supabase_export).
 *
 * The browser never connects directly to Supabase.
 * The service role key is never exposed to the frontend.
 * Reading is server-side only (fs/readFile in Server Components / route handlers).
 *
 * Set QA_CONTENT_SOURCE=supabase_export in .env.local to enable.
 */

export type ContentSourceMode = 'local' | 'supabase_export' | 'live_supabase'

export function getContentSourceMode(): ContentSourceMode {
  const raw = process.env.QA_CONTENT_SOURCE
  if (raw === 'supabase_export') return 'supabase_export'
  if (raw === 'live_supabase') return 'live_supabase'
  return 'local'
}

export function isSupabaseExportMode(): boolean {
  return getContentSourceMode() === 'supabase_export'
}

export function isLiveSupabaseMode(): boolean {
  return getContentSourceMode() === 'live_supabase'
}
