import { NextRequest, NextResponse } from 'next/server'
import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'

function findRepoRoot(): string {
  const marker = path.join('data', 'registry', 'content_registry_v1.json')
  let dir = process.cwd()
  for (let i = 0; i < 10; i++) {
    if (existsSync(path.join(dir, marker))) return dir
    const parent = path.dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return process.cwd()
}

const REPO_ROOT = findRepoRoot()

const EXT_TYPES: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md':   'text/markdown; charset=utf-8',
  '.txt':  'text/plain; charset=utf-8',
}

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl
  const relPath = searchParams.get('p')

  if (!relPath) {
    return new NextResponse('Missing ?p= parameter', { status: 400 })
  }

  // Normalise and enforce data/ prefix (security guard)
  const normalized = relPath.replace(/\\/g, '/').replace(/^\/+/, '')
  if (!normalized.startsWith('data/')) {
    return new NextResponse('Access denied: path must start with data/', { status: 403 })
  }

  // Resolve absolute path (prevent path-traversal)
  const segments = normalized.split('/').filter(Boolean)
  const absPath = path.resolve(REPO_ROOT, ...segments)
  if (!absPath.startsWith(REPO_ROOT)) {
    return new NextResponse('Access denied', { status: 403 })
  }

  try {
    const content = await readFile(absPath)
    const ext = path.extname(absPath).toLowerCase()
    const contentType = EXT_TYPES[ext] ?? 'application/octet-stream'
    return new NextResponse(content, {
      headers: { 'Content-Type': contentType },
    })
  } catch {
    return new NextResponse('File not found', { status: 404 })
  }
}
