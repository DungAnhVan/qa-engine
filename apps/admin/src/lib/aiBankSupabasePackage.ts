import fs from "fs";
import path from "path";

const ROOT = path.resolve(process.cwd(), "../..");

const PATHS = {
  syncPlan:       path.join(ROOT, "data/ai/supabase_sync/gate70e_ai_bank_supabase_sync_plan_v1.json"),
  syncReport:     path.join(ROOT, "data/diagnostics/gate70e_ai_bank_supabase_sync_execute_report_v1.json"),
  planReport:     path.join(ROOT, "data/diagnostics/gate70e_ai_bank_supabase_sync_plan_report_v1.json"),
  verifyReport:   path.join(ROOT, "data/diagnostics/gate70e_ai_bank_supabase_readback_verify_report_v1.json"),
  exportReport:   path.join(ROOT, "data/diagnostics/gate70e_ai_bank_supabase_export_report_v1.json"),
  pkgExport:      path.join(ROOT, "data/ai/supabase_exports/gate70e_ai_bank_package_from_supabase_v1.json"),
  studentExport:  path.join(ROOT, "data/ai/supabase_exports/gate70e_student_ai_bank_payload_from_supabase_v1.json"),
  teacherExport:  path.join(ROOT, "data/ai/supabase_exports/gate70e_teacher_ai_bank_payload_from_supabase_v1.json"),
  localPkg:       path.join(ROOT, "data/ai/published/gate70d_ai_bank_package_v1/publish_package_v1.json"),
};

function readJsonOrNull(filePath: string): unknown {
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

export function readGate70eAiBankSupabaseSyncPlan(): unknown {
  return readJsonOrNull(PATHS.syncPlan);
}

export function readGate70eAiBankSupabaseSyncReport(): unknown {
  return readJsonOrNull(PATHS.syncReport);
}

export function readGate70eAiBankSupabaseVerifyReport(): unknown {
  return readJsonOrNull(PATHS.verifyReport);
}

export function readGate70eAiBankSupabaseExportReport(): unknown {
  return readJsonOrNull(PATHS.exportReport);
}

export function getGate70eAiBankSupabaseSummary() {
  const plan   = readGate70eAiBankSupabaseSyncPlan() as Record<string, unknown> | null;
  const sync   = readGate70eAiBankSupabaseSyncReport() as Record<string, unknown> | null;
  const verify = readGate70eAiBankSupabaseVerifyReport() as Record<string, unknown> | null;
  const exp    = readGate70eAiBankSupabaseExportReport() as Record<string, unknown> | null;

  const supabaseWritePerformed = (sync as { supabase_write_performed?: boolean } | null)?.supabase_write_performed ?? false;
  const verifyPassed           = (verify as { status?: string } | null)?.status === "passed";
  const activeSwitch           = (sync as { active_switch_performed?: boolean } | null)?.active_switch_performed ?? false;
  const targetActive           = (sync as { target_active?: boolean } | null)?.target_active ?? false;

  return {
    syncPlanExists:                   fs.existsSync(PATHS.syncPlan),
    syncReportExists:                 fs.existsSync(PATHS.syncReport),
    verifyReportExists:               fs.existsSync(PATHS.verifyReport),
    exportReportExists:               fs.existsSync(PATHS.exportReport),
    localPkgExists:                   fs.existsSync(PATHS.localPkg),
    dryRunDefault:                    (plan as { dry_run_default?: boolean } | null)?.dry_run_default ?? true,
    activeSwitchAllowed:              (plan as { active_switch_allowed?: boolean } | null)?.active_switch_allowed ?? false,
    supabaseWritePerformed,
    targetActive,
    activeSwitchPerformed:            activeSwitch,
    existingActivePackagePreserved:   (sync as { existing_active_package_preserved?: boolean } | null)?.existing_active_package_preserved ?? true,
    resourcesUpserted:                (sync as { resources_upserted?: number } | null)?.resources_upserted ?? 0,
    packagesUpserted:                 (sync as { packages_upserted?: number } | null)?.packages_upserted ?? 0,
    itemsUpserted:                    (sync as { items_upserted?: number } | null)?.items_upserted ?? 0,
    readbackVerified:                 verifyPassed,
    aiApiCalled:                      false,
    secretsExposed:                   false,
    readyForGate70F:
      fs.existsSync(PATHS.syncPlan) &&
      !activeSwitch &&
      !targetActive,
  };
}
