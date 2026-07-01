/**
 * Gate 69G — AI Supabase Package helpers (server-only).
 *
 * Reads local JSON diagnostic files produced by the Gate 69G Python tools.
 * No secrets. No Supabase writes. No AI API calls.
 */

import fs from 'fs'
import path from 'path'

function dataRoot(): string {
  return path.join(process.cwd(), '..', '..', 'data')
}

function syncPlanPath(): string {
  return path.join(dataRoot(), 'ai', 'supabase_sync', 'ai_supabase_sync_plan_v1.json')
}

function syncReportPath(): string {
  return path.join(dataRoot(), 'diagnostics', 'ai_supabase_sync_execute_report_v1.json')
}

function verifyReportPath(): string {
  return path.join(dataRoot(), 'diagnostics', 'ai_supabase_readback_verify_report_v1.json')
}

function activeSwitchReportPath(): string {
  return path.join(dataRoot(), 'diagnostics', 'ai_supabase_active_switch_report_v1.json')
}

function syncPlanReportPath(): string {
  return path.join(dataRoot(), 'diagnostics', 'ai_supabase_sync_plan_report_v1.json')
}

function exportReportPath(): string {
  return path.join(dataRoot(), 'diagnostics', 'ai_supabase_export_report_v1.json')
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AiSyncPlan {
  sync_plan_id:            string
  package_id:              string
  dry_run_default:         boolean
  active_switch_default:   boolean
  resource_count:          number
  operation_count:         number
  operations:              Array<{ op: string; resource_key?: string; package_key?: string }>
  safety: {
    no_delete:             boolean
    no_active_switch:      boolean
    no_raw_source_text:    boolean
    no_api_keys:           boolean
  }
  created_at:              string
}

export interface AiSyncReport {
  gate:                             string
  status:                           string
  dry_run:                          boolean
  execute:                          boolean
  confirm_ok:                       boolean
  supabase_write_performed:         boolean
  resources_upserted:               number
  packages_upserted:                number
  items_upserted:                   number
  active_switch_performed:          boolean
  existing_active_package_preserved: boolean
  secrets_exposed:                  boolean
  issues:                           string[]
  generated_at:                     string
}

export interface AiVerifyReport {
  gate:                   string
  status:                 string
  sync_executed:          boolean
  package_exists:         boolean
  resources_verified:     number
  resource_count_match:   boolean
  active_false:           boolean
  no_raw_source_text:     boolean
  no_api_keys:            boolean
  issues:                 string[]
  generated_at:           string
}

export interface AiActiveSwitchReport {
  gate:                       string
  status:                     string
  dry_run:                    boolean
  active_switch_performed:    boolean
  previous_active_package_id: string | null
  new_active_package_id:      string
  rollback_instructions:      string
  issues:                     string[]
  generated_at:               string
}

export interface AiSupabasePackageSummary {
  sync_plan_exists:                boolean
  dry_run_default:                 boolean
  active_switch_default:           boolean
  supabase_write_performed:        boolean
  readback_verified:               boolean
  active_switch_performed:         boolean
  existing_active_package_preserved: boolean
  secrets_exposed:                 boolean
  resource_count:                  number
  status:                          'not_synced' | 'synced_not_active' | 'active' | 'needs_review' | 'failed'
}

// ---------------------------------------------------------------------------
// Readers
// ---------------------------------------------------------------------------

function readJson<T>(filePath: string): T | null {
  try {
    if (!fs.existsSync(filePath)) return null
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as T
  } catch {
    return null
  }
}

export function readAiSyncPlan(): AiSyncPlan | null {
  return readJson<AiSyncPlan>(syncPlanPath())
}

export function readAiSyncReport(): AiSyncReport | null {
  return readJson<AiSyncReport>(syncReportPath())
}

export function readAiVerifyReport(): AiVerifyReport | null {
  return readJson<AiVerifyReport>(verifyReportPath())
}

export function readAiActiveSwitchReport(): AiActiveSwitchReport | null {
  return readJson<AiActiveSwitchReport>(activeSwitchReportPath())
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

export function getAiSupabasePackageSummary(): AiSupabasePackageSummary {
  const plan    = readAiSyncPlan()
  const sync    = readAiSyncReport()
  const verify  = readAiVerifyReport()
  const active  = readAiActiveSwitchReport()

  const supabaseWritePerformed   = sync?.supabase_write_performed ?? false
  const readbackVerified         = verify?.package_exists ?? false
  const activeSwitchPerformed    = active?.active_switch_performed ?? false
  const existingActivePreserved  = sync?.existing_active_package_preserved ?? true
  const secretsExposed           = sync?.secrets_exposed ?? false

  let status: AiSupabasePackageSummary['status'] = 'not_synced'
  if (supabaseWritePerformed && activeSwitchPerformed) {
    status = 'active'
  } else if (supabaseWritePerformed && readbackVerified) {
    status = 'synced_not_active'
  } else if (supabaseWritePerformed) {
    status = 'needs_review'
  }

  return {
    sync_plan_exists:                 plan !== null,
    dry_run_default:                  plan?.dry_run_default ?? true,
    active_switch_default:            plan?.active_switch_default ?? false,
    supabase_write_performed:         supabaseWritePerformed,
    readback_verified:                readbackVerified,
    active_switch_performed:          activeSwitchPerformed,
    existing_active_package_preserved: existingActivePreserved,
    secrets_exposed:                  secretsExposed,
    resource_count:                   plan?.resource_count ?? 0,
    status,
  }
}
