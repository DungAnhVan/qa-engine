"""
Gate 70A -- Run Live AI Generation to Bank v1

Reads safe generation requests, calls the AI provider for each one, and saves
results to the local AI question bank. Dry-run by default.

Safety policy:
  - Default: dry_run=True — mock responses only, no real API calls.
  - Real calls: require --execute --confirm LIVE_AI_GENERATION
  - Requires QA_AI_DRY_RUN=false in env when using --execute.
  - No raw Cambridge text sent to AI — requests are metadata-only.
  - No auto-publish. Teacher approval required.
  - No Supabase writes.
  - Output status: generated_needs_teacher_review.

Usage:
  # Dry-run (safe default):
  .venv-ingest\\Scripts\\python.exe tools\\ai\\run_live_ai_generation_to_bank_v1.py \\
      --requests data\\ai\\generation_requests\\ai_safe_generation_requests_v1.json

  # Real API calls (requires --execute --confirm and QA_AI_DRY_RUN=false):
  .venv-ingest\\Scripts\\python.exe tools\\ai\\run_live_ai_generation_to_bank_v1.py \\
      --requests data\\ai\\generation_requests\\ai_safe_generation_requests_v1.json \\
      --batch-id gate70a_live_ai_batch_v1 \\
      --limit 3 \\
      --execute --confirm LIVE_AI_GENERATION

Output:
  data/ai/generated_batches/<batch_id>.json
  data/ai/question_bank/ai_generated_question_bank_v1.json
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

ROOT    = Path(__file__).resolve().parents[2]
BANK_FILE = ROOT / "data" / "ai" / "question_bank" / "ai_generated_question_bank_v1.json"

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Run live AI generation to bank")
parser.add_argument("--requests",  required=True, help="Path to safe generation requests JSON")
parser.add_argument("--batch-id",  default="gate70a_batch_v1", dest="batch_id",
                    help="Batch identifier for this run (default: gate70a_batch_v1)")
parser.add_argument("--limit",     type=int, default=None,
                    help="Max requests to process (default: all)")
parser.add_argument("--execute",   action="store_true",
                    help="Enable real API calls (requires --confirm LIVE_AI_GENERATION)")
parser.add_argument("--confirm",   default="",
                    help="Must be LIVE_AI_GENERATION when using --execute")
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Imports (after arg parse so --help works without them)
# ---------------------------------------------------------------------------

sys.path.insert(0, str(ROOT))
from tools.ai.ai_client_v1 import generate_text
from tools.ai.ai_prompt_builder_v1 import build_resource_authoring_prompt
from tools.ai.ai_provider_config_v1 import load_env_local, resolve_env

env_local   = load_env_local()
env_dry_run = resolve_env("QA_AI_DRY_RUN", env_local)
qa_dry_run  = str(env_dry_run).lower() != "false"

# ---------------------------------------------------------------------------
# Determine execution mode
# ---------------------------------------------------------------------------

execute_mode = args.execute and args.confirm == "LIVE_AI_GENERATION"

if args.execute and not execute_mode:
    print("ERROR: --execute requires --confirm LIVE_AI_GENERATION")
    sys.exit(1)

# Real calls require QA_AI_DRY_RUN=false
if execute_mode and qa_dry_run:
    print("ERROR: Real API calls require QA_AI_DRY_RUN=false in .env.local")
    print("  Set QA_AI_DRY_RUN=false and QA_AI_PROVIDER=openai or anthropic")
    sys.exit(1)

dry_run = not execute_mode

print("Gate 70A -- Run Live AI Generation to Bank v1")
print("=" * 60)
print(f"  Mode:       {'DRY-RUN (mock)' if dry_run else 'EXECUTE -- real API calls'}")
print(f"  batch_id:   {args.batch_id}")
print()

if dry_run:
    print("  NOTE: Dry-run mode. Pass --execute --confirm LIVE_AI_GENERATION to use real AI.")
    print()

# ---------------------------------------------------------------------------
# Load requests
# ---------------------------------------------------------------------------

req_path = Path(args.requests)
if not req_path.is_absolute():
    req_path = ROOT / req_path

if not req_path.exists():
    print(f"ERROR: requests file not found: {req_path}")
    sys.exit(1)

req_doc  = json.loads(req_path.read_text(encoding="utf-8"))
requests = req_doc.get("requests", [])
limit    = args.limit if args.limit is not None else len(requests)
requests = requests[:limit]

print(f"  requests:   {req_path.relative_to(ROOT)}")
print(f"  total:      {len(req_doc.get('requests', []))} in file, {len(requests)} to process")
print()

# ---------------------------------------------------------------------------
# Run generation
# ---------------------------------------------------------------------------

generated: list[dict] = []
errors:    list[dict] = []

now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

for i, req in enumerate(requests, 1):
    req_id = req.get("_request_id", f"req_{i:03d}")
    print(f"[{i:02d}/{len(requests)}] {req_id}")

    # Build prompt (safe — only uses contract-approved metadata fields)
    try:
        prompt_dict = build_resource_authoring_prompt(req)
        full_prompt = prompt_dict.get("system", "") + "\n\n" + prompt_dict.get("user", "")
    except Exception as exc:
        err = {"request_id": req_id, "error": f"prompt build failed: {exc}"}
        errors.append(err)
        print(f"  ! prompt build error: {exc}")
        continue

    # Generate text
    result = generate_text(full_prompt, dry_run=dry_run)
    status = result.get("status", "failed")
    text   = result.get("text", "")

    print(f"  provider={result.get('provider')}  model={result.get('model', 'n/a')}  "
          f"status={status}  dry_run={result.get('dry_run')}")
    if result.get("issues"):
        for issue in result["issues"]:
            print(f"  ! {issue}")

    if status == "passed" and text:
        entry = {
            "bank_id":                  f"bank_{args.batch_id}_{i:04d}",
            "request_id":               req_id,
            "batch_id":                 args.batch_id,
            "generated_at":             now_str,
            "subject_slug":             req.get("subject_slug"),
            "syllabus_code":            req.get("syllabus_code"),
            "topic":                    req.get("topic"),
            "subtopic":                 req.get("subtopic"),
            "skill_name":               req.get("skill_name"),
            "skill_type":               req.get("skill_type"),
            "difficulty":               req.get("difficulty"),
            "resource_type":            req.get("resource_type"),
            "learning_objective":       req.get("learning_objective"),
            "generated_text":           text,
            "provider":                 result.get("provider"),
            "model":                    result.get("model"),
            "dry_run":                  result.get("dry_run"),
            "status":                   "generated_needs_teacher_review",
            "teacher_review_required":  True,
            "auto_publish_enabled":     False,
            "supabase_write_performed": False,
            "safety": {
                "no_raw_source_text":    True,
                "no_cambridge_pdf_text": True,
                "no_mark_scheme_text":   True,
                "metadata_only_prompt":  True,
            },
        }
        generated.append(entry)
    else:
        errors.append({
            "request_id": req_id,
            "status":     status,
            "issues":     result.get("issues", []),
        })

print()
print(f"Generated: {len(generated)}  Errors: {len(errors)}")

# ---------------------------------------------------------------------------
# Write batch file
# ---------------------------------------------------------------------------

batch_dir = ROOT / "data" / "ai" / "generated_batches"
batch_dir.mkdir(parents=True, exist_ok=True)
batch_file = batch_dir / f"{args.batch_id}.json"

batch_doc = {
    "schema_version":    "gate70a_v1",
    "batch_id":          args.batch_id,
    "generated_at":      now_str,
    "dry_run":           dry_run,
    "requests_file":     str(req_path.relative_to(ROOT)),
    "requests_total":    len(requests),
    "generated_count":   len(generated),
    "error_count":       len(errors),
    "status":            "generated_needs_teacher_review",
    "teacher_review_required":  True,
    "auto_publish_enabled":     False,
    "supabase_write_performed": False,
    "generated_items":   generated,
    "errors":            errors,
}
batch_file.write_text(json.dumps(batch_doc, indent=2), encoding="utf-8")
print(f"Batch:   {batch_file.relative_to(ROOT)}")

# ---------------------------------------------------------------------------
# Merge into bank
# ---------------------------------------------------------------------------

bank_dir = BANK_FILE.parent
bank_dir.mkdir(parents=True, exist_ok=True)

existing_bank: dict = {}
if BANK_FILE.exists():
    try:
        existing_bank = json.loads(BANK_FILE.read_text(encoding="utf-8"))
    except Exception:
        existing_bank = {}

existing_items: list[dict] = existing_bank.get("items", [])
existing_ids   = {e["bank_id"] for e in existing_items}

new_items = [g for g in generated if g["bank_id"] not in existing_ids]
all_items  = existing_items + new_items

bank_doc = {
    "schema_version":    "gate70a_v1",
    "updated_at":        now_str,
    "total_count":       len(all_items),
    "pending_review":    sum(1 for e in all_items if e.get("status") == "generated_needs_teacher_review"),
    "teacher_review_required":  True,
    "auto_publish_enabled":     False,
    "supabase_write_performed": False,
    "batches_merged":    list({e.get("batch_id") for e in all_items}),
    "items":             all_items,
}
BANK_FILE.write_text(json.dumps(bank_doc, indent=2), encoding="utf-8")
print(f"Bank:    {BANK_FILE.relative_to(ROOT)}  (total items: {len(all_items)})")

if errors:
    print()
    print("Errors:")
    for e in errors:
        print(f"  ! {e.get('request_id')}: {e.get('error') or e.get('issues')}")

print()
print("Done. All generated items require teacher review before publication.")
