import { readFile } from 'fs/promises'
import { getActiveContentIndex, type ActivePackage } from './activeContent'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface StudentResource {
  resource_id: string
  resource_type: string
  topic: string
  skill_name: string
  skill_type: string
  difficulty: string | null
  student_prompt: string | null
  options: Record<string, string | null> | null
  estimated_time_minutes: number | null
  worked_solution?: string | null
}

export interface StudentPayload {
  package_id: string
  payload_type: string
  created_at: string
  resource_count: number
  copyright_note: string
  resources: StudentResource[]
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export async function getDefaultActivePackage(): Promise<ActivePackage | null> {
  const index = await getActiveContentIndex()
  return index?.active_packages[0] ?? null
}

export async function getActiveStudentResources(): Promise<{
  pkg: ActivePackage | null
  payload: StudentPayload | null
  resources: StudentResource[]
}> {
  const pkg = await getDefaultActivePackage()
  if (!pkg) return { pkg: null, payload: null, resources: [] }

  const payloadPath = pkg.paths.student_payload
  if (!payloadPath) return { pkg, payload: null, resources: [] }

  try {
    const raw = await readFile(payloadPath, 'utf-8')
    const payload = JSON.parse(raw) as StudentPayload
    return { pkg, payload, resources: payload.resources ?? [] }
  } catch {
    return { pkg, payload: null, resources: [] }
  }
}

export function groupResourcesByTopic(
  resources: StudentResource[],
): Map<string, StudentResource[]> {
  const map = new Map<string, StudentResource[]>()
  for (const r of resources) {
    const topic = r.topic || 'Other'
    const group = map.get(topic)
    if (group) {
      group.push(r)
    } else {
      map.set(topic, [r])
    }
  }
  return map
}
