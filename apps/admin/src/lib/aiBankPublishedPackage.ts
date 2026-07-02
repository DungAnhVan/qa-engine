import fs from "fs";
import path from "path";

const ROOT = path.resolve(process.cwd(), "../..");
const PKG_DIR = path.join(ROOT, "data/ai/published/gate70d_ai_bank_package_v1");

const PATHS = {
  publishPackage:     path.join(PKG_DIR, "publish_package_v1.json"),
  studentPayload:     path.join(PKG_DIR, "student_resource_payload_v1.json"),
  teacherPayload:     path.join(PKG_DIR, "teacher_resource_payload_v1.json"),
  publishReport:      path.join(PKG_DIR, "ai_bank_publish_report_v1.json"),
  studentPreview:     path.join(PKG_DIR, "static_preview/gate70d_student_ai_bank_published_preview_v1.html"),
  teacherPreview:     path.join(PKG_DIR, "static_preview/gate70d_teacher_ai_bank_published_preview_v1.html"),
  previewReport:      path.join(PKG_DIR, "static_preview/gate70d_ai_bank_published_preview_report_v1.json"),
  approvalFile:       path.join(ROOT, "data/ai/package_candidates/gate70d_ai_bank_final_publish_approval_v1.json"),
  registry:           path.join(ROOT, "data/ai/registry/gate70d_ai_bank_content_registry_v1.json"),
  validationReport:   path.join(ROOT, "data/diagnostics/gate70d_ai_bank_local_published_package_validation_report_v1.json"),
  buildReport:        path.join(ROOT, "data/diagnostics/gate70d_ai_bank_local_publish_build_report_v1.json"),
  approvalReport:     path.join(ROOT, "data/diagnostics/gate70d_ai_bank_final_publish_approval_report_v1.json"),
};

function readJsonOrNull(filePath: string): unknown {
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

export interface PublishedResource {
  resource_id: string;
  bank_item_id: string;
  resource_type: string;
  title: string;
  topic: string;
  subtopic?: string;
  skill_name?: string;
  skill_type?: string;
  difficulty: string;
  estimated_time_minutes: number;
  student_prompt: string;
  student_instructions?: string;
  answer_key?: string;
  marking_rubric?: { criterion: string; marks: number; guidance: string }[];
  teacher_notes?: string;
  provenance?: Record<string, unknown>;
  safety_declaration?: Record<string, unknown>;
  provider?: string;
  model?: string;
}

export interface PublishedPackage {
  package_id: string;
  version: string;
  status: string;
  published_at: string;
  source: string;
  active_content: boolean;
  supabase_write_performed: boolean;
  ai_api_called: boolean;
  teacher_final_approval: boolean;
  resource_count: number;
  approved_by?: string;
  approval_notes?: string;
  resources: PublishedResource[];
}

export function readGate70dAiBankPublishedPackage(): PublishedPackage | null {
  return readJsonOrNull(PATHS.publishPackage) as PublishedPackage | null;
}

export function readGate70dAiBankPublishedStudentPayload(): unknown {
  return readJsonOrNull(PATHS.studentPayload);
}

export function readGate70dAiBankPublishedTeacherPayload(): unknown {
  return readJsonOrNull(PATHS.teacherPayload);
}

export function readGate70dAiBankLocalRegistry(): unknown {
  return readJsonOrNull(PATHS.registry);
}

export function readGate70dAiBankValidationReport(): unknown {
  return readJsonOrNull(PATHS.validationReport);
}

export function readGate70dAiBankApprovalFile(): unknown {
  return readJsonOrNull(PATHS.approvalFile);
}

export function getGate70dAiBankPublishedSummary() {
  const pkg        = readGate70dAiBankPublishedPackage();
  const validation = readGate70dAiBankValidationReport() as Record<string, unknown> | null;
  const approval   = readGate70dAiBankApprovalFile() as Record<string, unknown> | null;
  const registry   = readGate70dAiBankLocalRegistry() as Record<string, unknown> | null;

  return {
    packageExists:            pkg !== null,
    resourceCount:            pkg?.resource_count ?? 0,
    status:                   pkg?.status ?? "not_built",
    activeContent:            pkg?.active_content ?? false,
    supabaseWritePerformed:   pkg?.supabase_write_performed ?? false,
    aiApiCalled:              pkg?.ai_api_called ?? false,
    teacherFinalApproval:     pkg?.teacher_final_approval ?? false,
    approvalStatus:           (approval as { approval_status?: string } | null)?.approval_status ?? "pending",
    approvedBy:               (approval as { approved_by?: string } | null)?.approved_by ?? null,
    validationPassed:         (validation as { valid?: boolean } | null)?.valid ?? null,
    registryExists:           registry !== null,
    studentPayloadExists:     fs.existsSync(PATHS.studentPayload),
    teacherPayloadExists:     fs.existsSync(PATHS.teacherPayload),
    studentPreviewExists:     fs.existsSync(PATHS.studentPreview),
    teacherPreviewExists:     fs.existsSync(PATHS.teacherPreview),
    validationReportExists:   fs.existsSync(PATHS.validationReport),
    finalApprovalExists:      fs.existsSync(PATHS.approvalFile),
    readyForGate70E:
      pkg !== null &&
      pkg.status === "published_local_not_active" &&
      !pkg.active_content &&
      !pkg.supabase_write_performed &&
      pkg.teacher_final_approval &&
      (validation as { valid?: boolean } | null)?.valid === true,
  };
}
