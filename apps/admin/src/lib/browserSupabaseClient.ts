/**
 * Browser-safe Supabase client — Gate 61.
 *
 * Uses @supabase/ssr createBrowserClient so the session is stored in cookies,
 * making it readable by server components in the same request.
 *
 * Uses NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY ONLY.
 * NEVER imports or references the service role key.
 *
 * Safe to import in client components ('use client').
 * Do NOT import 'server-only' here — this module runs in the browser.
 */
import { createBrowserClient } from '@supabase/ssr'

export function createBrowserSupabaseClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!url || !anonKey) {
    throw new Error(
      'NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set for browser auth.',
    )
  }
  return createBrowserClient(url, anonKey)
}

export function isBrowserSupabaseConfigured(): boolean {
  return !!(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  )
}
