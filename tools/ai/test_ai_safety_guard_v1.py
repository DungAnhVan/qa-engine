"""
Gate 69B -- AI Safety Guard Tests v1

Tests the copyright safety guard and authoring contract.
No real AI API calls are made — all tests use mock provider or pure validation.

Output:
  data/diagnostics/ai_safety_guard_test_report_v1.json
"""

import json
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT_DIR  = ROOT / "data" / "diagnostics"
OUTPUT_FILE = OUTPUT_DIR / "ai_safety_guard_test_report_v1.json"

from tools.ai.copyright_safety_guard_v1 import (
    scan_prompt_for_disallowed_source_text,
    scan_generated_content_for_risk,
    assert_ai_input_is_safe,
    build_safe_ai_payload_from_generation_target,
)
from tools.ai.ai_authoring_contract_v1 import (
    make_safe_authoring_request,
    validate_safe_authoring_request,
    summarize_authoring_request,
)
from tools.ai.ai_client_v1 import generate_text

# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

class TestResult:
    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name   = name
        self.passed = passed
        self.detail = detail

    def to_dict(self) -> dict:
        return {
            "name":   self.name,
            "passed": self.passed,
            "detail": self.detail,
        }


def run_test(name: str, fn) -> TestResult:
    try:
        passed, detail = fn()
        return TestResult(name, passed, detail)
    except Exception as exc:
        return TestResult(name, False, f"Exception: {exc}")

# ---------------------------------------------------------------------------
# Individual tests
# ---------------------------------------------------------------------------

def test_safe_metadata_payload_passes():
    payload = {
        "subject_slug": "physics",
        "topic":        "Wave Superposition",
        "subtopic":     "Diffraction",
        "difficulty":   "medium",
        "skill_type":   "application",
    }
    result = assert_ai_input_is_safe(payload)
    if not result["safe"]:
        return False, f"Expected safe=True, got issues: {result['issues']}"
    return True, f"risk_level={result['risk_level']}"


def test_payload_with_original_raw_block_fails():
    payload = {
        "subject_slug":      "physics",
        "topic":             "Waves",
        "original_raw_block": "A long piece of copied question text from a Cambridge paper.",
    }
    result = assert_ai_input_is_safe(payload)
    if result["safe"]:
        return False, "Expected safe=False for original_raw_block but got safe=True"
    return True, f"issues={result['issues'][:2]}"


def test_payload_with_normalized_raw_block_fails():
    payload = {
        "subject_slug":         "physics",
        "topic":                "Electricity",
        "normalized_raw_block": "Normalised version of a Cambridge question text.",
    }
    result = assert_ai_input_is_safe(payload)
    if result["safe"]:
        return False, "Expected safe=False for normalized_raw_block"
    return True, f"issues={result['issues'][:2]}"


def test_payload_with_raw_mark_scheme_fails():
    payload = {
        "subject_slug":   "physics",
        "topic":          "Mechanics",
        "raw_mark_scheme": "1 mark for correct identification of force...",
    }
    result = assert_ai_input_is_safe(payload)
    if result["safe"]:
        return False, "Expected safe=False for raw_mark_scheme"
    return True, f"issues={result['issues'][:2]}"


def test_prompt_with_cambridge_long_block_fails():
    # A prompt that embeds what looks like a paste from an exam paper
    long_line = (
        "The following is taken from Cambridge A Level Physics 9702/21/O/N/23 "
        "Question 3: A student investigates the motion of a ball bearing falling "
        "through a viscous liquid. She measures the terminal velocity by recording "
        "the time taken for the ball to fall between two marks on the container. "
        "The marks are 250 mm apart. She repeats the experiment five times to "
        "calculate the mean terminal velocity. Question Answer Marks [3]"
    )
    # Make it longer than the 400-char threshold
    long_line = long_line * 2
    result = scan_prompt_for_disallowed_source_text(long_line)
    if result["safe"]:
        return False, f"Expected safe=False for long Cambridge block (len={len(long_line)})"
    return True, f"risk_level={result['risk_level']} issues_count={len(result['issues'])}"


def test_prompt_with_raw_data_path_fails():
    prompt = "Please generate a question based on the content in data/raw/physics_0625.pdf"
    result = scan_prompt_for_disallowed_source_text(prompt)
    if result["safe"]:
        return False, "Expected safe=False for data/raw path"
    return True, f"issues={result['issues']}"


def test_generated_content_with_copyright_phrase_fails():
    text = (
        "This is a question from Cambridge International Examinations "
        "Physics paper 9702/12/M/J/24."
    )
    result = scan_generated_content_for_risk(text)
    if result["safe"]:
        return False, "Expected safe=False for Cambridge copyright phrase in output"
    return True, f"risk_level={result['risk_level']} issues={result['issues']}"


def test_mock_provider_returns_deterministic_response():
    prompt = "Generate a question about kinetic theory of gases."
    result1 = generate_text(prompt, provider="mock", dry_run=True)
    result2 = generate_text(prompt, provider="mock", dry_run=True)
    if result1["status"] != "passed":
        return False, f"Mock returned status={result1['status']}"
    if result1["text"] != result2["text"]:
        return False, "Mock responses not deterministic"
    if "DRY-RUN" not in result1["text"]:
        return False, "Mock response missing DRY-RUN marker"
    return True, f"text[:60]={result1['text'][:60]!r}"


def test_authoring_contract_rejects_raw_source_fields():
    bad_req = {
        "subject_slug":      "physics",
        "topic":             "Waves",
        "original_raw_block": "Verbatim text from Cambridge paper",
        "constraints": {
            "must_be_original":    True,
            "no_source_copying":   True,
            "cambridge_style_but_original": True,
        },
        "source_metadata": {
            "no_raw_text_included": True,
        },
    }
    result = validate_safe_authoring_request(bad_req)
    if result["valid"]:
        return False, "Expected valid=False when original_raw_block present"
    return True, f"disallowed={result['disallowed_fields']} issues_count={len(result['issues'])}"


def test_authoring_contract_accepts_valid_request():
    req = make_safe_authoring_request(
        subject_slug="physics",
        topic="Electromagnetic Induction",
        subtopic="Faraday's Law",
        difficulty="hard",
        resource_type="question",
        learning_objective="Derive the magnitude of the induced EMF using Faraday's law.",
        student_level="A-Level Year 2",
        source_ids=["src_001", "src_002"],
    )
    result = validate_safe_authoring_request(req)
    if not result["valid"]:
        return False, f"Expected valid=True, got issues={result['issues']}"
    summary = summarize_authoring_request(req)
    if "physics" not in summary:
        return False, f"Summary missing subject: {summary}"
    return True, f"summary={summary}"


def test_build_safe_payload_drops_disallowed_fields():
    target = {
        "subject_slug":      "biology",
        "topic":             "Cell Division",
        "original_raw_block": "Raw block that should be dropped",
        "normalized_raw_block": "Also dropped",
        "difficulty":        "easy",
    }
    result = build_safe_ai_payload_from_generation_target(target)
    if result["safe"]:
        return False, "Expected safe=False when disallowed fields dropped"
    dropped = result["dropped_fields"]
    if "original_raw_block" not in dropped or "normalized_raw_block" not in dropped:
        return False, f"Expected both raw fields dropped, got: {dropped}"
    payload = result["payload"]
    if "original_raw_block" in payload or "normalized_raw_block" in payload:
        return False, "Disallowed fields not removed from payload"
    return True, f"dropped={dropped}"


def test_safe_prompt_passes():
    prompt = (
        "Generate an original Cambridge-style A-Level Physics question on the topic "
        "of wave-particle duality. Difficulty: hard. The question must be entirely "
        "original and must not copy any existing source material. Include a mark scheme."
    )
    result = scan_prompt_for_disallowed_source_text(prompt)
    if not result["safe"]:
        return False, f"Expected safe=True for safe prompt, got issues={result['issues']}"
    return True, f"risk_level={result['risk_level']}"


def test_mock_copyright_guard_allows_metadata_only():
    result = generate_text(
        "subject=physics topic=Waves difficulty=medium skill=application "
        "Generate original question. No source copying.",
        provider="mock",
        dry_run=True,
        copyright_strict=True,
    )
    if result["status"] != "passed":
        return False, f"status={result['status']} issues={result['issues']}"
    return True, "Mock passed with metadata-only prompt"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TESTS = [
    ("safe_metadata_payload_passes",              test_safe_metadata_payload_passes),
    ("payload_with_original_raw_block_fails",     test_payload_with_original_raw_block_fails),
    ("payload_with_normalized_raw_block_fails",   test_payload_with_normalized_raw_block_fails),
    ("payload_with_raw_mark_scheme_fails",        test_payload_with_raw_mark_scheme_fails),
    ("prompt_with_cambridge_long_block_fails",    test_prompt_with_cambridge_long_block_fails),
    ("prompt_with_raw_data_path_fails",           test_prompt_with_raw_data_path_fails),
    ("generated_content_copyright_phrase_fails",  test_generated_content_with_copyright_phrase_fails),
    ("mock_provider_deterministic_response",      test_mock_provider_returns_deterministic_response),
    ("authoring_contract_rejects_raw_fields",     test_authoring_contract_rejects_raw_source_fields),
    ("authoring_contract_accepts_valid_request",  test_authoring_contract_accepts_valid_request),
    ("build_safe_payload_drops_disallowed",       test_build_safe_payload_drops_disallowed_fields),
    ("safe_prompt_passes",                        test_safe_prompt_passes),
    ("mock_copyright_guard_allows_metadata",      test_mock_copyright_guard_allows_metadata_only),
]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Gate 69B -- AI Safety Guard Tests")
    print("-" * 55)

    results: list[TestResult] = []
    for name, fn in TESTS:
        r = run_test(name, fn)
        results.append(r)
        symbol = "+" if r.passed else "!"
        print(f"  [{symbol}] {name}")
        if not r.passed or r.detail:
            print(f"       {r.detail}")

    passed_count = sum(1 for r in results if r.passed)
    total        = len(results)
    all_passed   = passed_count == total

    print(f"\n{passed_count}/{total} tests passed")
    status = "passed" if all_passed else "needs_review" if passed_count >= total * 0.8 else "failed"
    print(f"Status: {status}")

    report = {
        "gate":         "69B",
        "title":        "AI Safety Guard Tests v1",
        "status":       status,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tests_passed": passed_count,
        "tests_total":  total,
        "tests":        [r.to_dict() for r in results],
        "raw_cambridge_text_blocked": any(
            r.name in (
                "payload_with_original_raw_block_fails",
                "payload_with_normalized_raw_block_fails",
                "payload_with_raw_mark_scheme_fails",
                "prompt_with_cambridge_long_block_fails",
                "prompt_with_raw_data_path_fails",
            ) and r.passed
            for r in results
        ),
        "mock_provider_works": next(
            (r.passed for r in results if r.name == "mock_provider_deterministic_response"), False
        ),
        "authoring_contract_works": next(
            (r.passed for r in results if r.name == "authoring_contract_accepts_valid_request"), False
        ),
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {OUTPUT_FILE}")

    if not all_passed:
        failed = [r.name for r in results if not r.passed]
        print("Failed tests:", failed)


if __name__ == "__main__":
    main()
