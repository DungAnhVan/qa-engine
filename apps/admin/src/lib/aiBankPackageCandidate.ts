import fs from "fs";
import path from "path";

const ROOT = path.resolve(process.cwd(), "../..");
const PACKAGE_FILE = path.join(
  ROOT,
  "data/ai/package_candidates/gate70c_ai_bank_package_candidate_v1.json"
);
const STUDENT_PAYLOAD_FILE = path.join(
  ROOT,
  "data/ai/package_candidates/gate70c_student_payload_v1.json"
);
const TEACHER_PAYLOAD_FILE = path.join(
  ROOT,
  "data/ai/package_candidates/gate70c_teacher_payload_v1.json"
);
const VALIDATION_REPORT_FILE = path.join(
  ROOT,
  "data/diagnostics/gate70c_ai_bank_package_candidate_validation_report_v1.json"
);
const BUILD_REPORT_FILE = path.join(
  ROOT,
  "data/diagnostics/gate70c_ai_bank_package_candidate_build_report_v1.json"
);

function readJsonOrNull(filePath: string): unknown {
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

export interface PackageResource {
  resource_id: string;
  bank_item_id: string;
  resource_type: string;
  title: string;
  topic: string;
  difficulty: string;
  estimated_time_minutes: number;
  student_prompt: string;
  student_instructions: string;
  answer_key?: string;
  marking_rubric?: { criterion: string; marks: number; guidance: string }[];
  teacher_notes?: string;
  provenance?: Record<string, unknown>;
  provider?: string;
  model?: string;
}

export interface PackageCandidate {
  package_candidate_id: string;
  version: string;
  status: string;
  created_at: string;
  teacher_final_publish_required: boolean;
  auto_publish_enabled: boolean;
  supabase_write_performed: boolean;
  ai_api_called: boolean;
  resource_count: number;
  resources: PackageResource[];
  issues?: string[];
}

export function readPackageCandidate(): PackageCandidate | null {
  return readJsonOrNull(PACKAGE_FILE) as PackageCandidate | null;
}

export function readStudentPayload(): unknown {
  return readJsonOrNull(STUDENT_PAYLOAD_FILE);
}

export function readTeacherPayload(): unknown {
  return readJsonOrNull(TEACHER_PAYLOAD_FILE);
}

export function readPackageValidationReport(): unknown {
  return readJsonOrNull(VALIDATION_REPORT_FILE);
}

export function readPackageBuildReport(): unknown {
  return readJsonOrNull(BUILD_REPORT_FILE);
}

export function getPackageSummary() {
  const pkg = readPackageCandidate();
  const validation = readPackageValidationReport() as Record<string, unknown> | null;
  const build = readPackageBuildReport() as Record<string, unknown> | null;

  return {
    packageExists: pkg !== null,
    resourceCount: pkg?.resource_count ?? 0,
    status: pkg?.status ?? "not_built",
    teacherFinalPublishRequired: pkg?.teacher_final_publish_required ?? true,
    autoPublishEnabled: pkg?.auto_publish_enabled ?? false,
    supabaseWritePerformed: pkg?.supabase_write_performed ?? false,
    aiApiCalled: pkg?.ai_api_called ?? false,
    validationPassed: (validation as { valid?: boolean } | null)?.valid ?? null,
    buildStatus: (build as { status?: string } | null)?.status ?? null,
    studentPayloadExists: fs.existsSync(STUDENT_PAYLOAD_FILE),
    teacherPayloadExists: fs.existsSync(TEACHER_PAYLOAD_FILE),
    validationReportExists: fs.existsSync(VALIDATION_REPORT_FILE),
  };
}
