import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

export async function GET() {
  const provider        = process.env.QA_AI_PROVIDER        ?? 'mock'
  const dryRunRaw       = process.env.QA_AI_DRY_RUN         ?? 'true'
  const copyrightRaw    = process.env.QA_AI_COPYRIGHT_STRICT ?? 'true'
  const isProduction    = process.env.NODE_ENV === 'production'

  const dryRun          = dryRunRaw.trim().toLowerCase() !== 'false'
  const copyrightStrict = copyrightRaw.trim().toLowerCase() !== 'false'

  // Check if the sample batch exists (filesystem check, server-side only)
  let sampleBatchExists = false
  try {
    const batchPath = path.join(process.cwd(), '..', '..', 'data', 'ai',
      'generated_batches', 'gate69c_sample_generated_batch_v1.json')
    sampleBatchExists = fs.existsSync(batchPath)
  } catch {
    sampleBatchExists = false
  }

  const status: 'draft_only' | 'needs_review' | 'failed' =
    !dryRun && provider === 'mock' ? 'draft_only'
    : dryRun                       ? 'draft_only'
    : 'draft_only'

  return NextResponse.json({
    status,
    environment:              isProduction ? 'production' : 'development',
    provider,
    dry_run:                  dryRun,
    copyright_strict:         copyrightStrict,
    sample_batch_exists:      sampleBatchExists,
    teacher_approval_required: true,
    auto_publish_enabled:     false,
    timestamp:                new Date().toISOString(),
  })
}
