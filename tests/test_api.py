#!/usr/bin/env python3
"""
Test TAU API functionality
"""
from tau.server.client import TauClient
from tau.api_models import FunctionInfo

# Initialize API
api = TauClient()

print("=" * 60)
print("TAU API Test Suite")
print("=" * 60)

# Test 1: Generate specs for a simple function
print("\n[Test 1] Spec Generation")
print("-" * 60)

function_source = """
def multiply(x: int, n: int) -> int:
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result
"""

print("Function:")
print(function_source)

specs = api.generate_specs(function_source.strip())
if specs:
    print("\n✅ Generated Specs:")
    and_op = ' /\\ '
    print(f"  @requires: {and_op.join(specs.requires)}")
    print(f"  @ensures: {and_op.join(specs.ensures)}")
    if specs.suggested_invariants:
        print(f"  @invariant:")
        for inv in specs.suggested_invariants:
            print(f"    - {inv}")
    if specs.suggested_variant:
        print(f"  @variant: {specs.suggested_variant}")
    print(f"\n  Reasoning: {specs.reasoning}")
    print(f"  Confidence: {specs.confidence * 100:.1f}%")
else:
    print("⚠️  Spec generation not available (requires ANTHROPIC_API_KEY)")

# Test 2: Validate specs
print("\n[Test 2] Spec Validation")
print("-" * 60)

validation = api.validate_specs(
    requires="n >= 0 && x >= 0",  # Wrong syntax (should be /\)
    ensures="result = n * x",
    function_source=function_source
)

print(f"Valid: {validation.valid}")
if validation.errors:
    print("Errors:")
    for err in validation.errors:
        print(f"  - {err}")
if validation.warnings:
    print("Warnings:")
    for warn in validation.warnings:
        print(f"  - {warn}")

# Test 3: Extract function info
print("\n[Test 3] Function Info Extraction")
print("-" * 60)

func_info = api.extract_function_info("examples/safe_functions.py", "count_to")
if func_info:
    print(f"✅ Extracted function info:")
    print(f"  Name: {func_info.name}")
    print(f"  Line: {func_info.line_number}")
    print(f"  Signature: {func_info.signature}")
    print(f"  Has loop: {func_info.has_loop}")
    print(f"  Parameters: {func_info.parameters}")
    print(f"  Return type: {func_info.return_type}")
else:
    print("❌ Could not extract function info")

# Test 4: Verify function with streaming
print("\n[Test 4] Verification with Streaming")
print("-" * 60)

def progress_callback(progress):
    stage_emoji = {
        "parsing": "📖",
        "transpiling": "🔄",
        "generating_specs": "🤖",
        "llm_round": "🔄",
        "proving": "🔍",
        "completed": "✅",
        "failed": "❌"
    }
    emoji = stage_emoji.get(progress.stage, "⚙️")
    progress_bar = int(progress.progress * 20)
    bar = "█" * progress_bar + "░" * (20 - progress_bar)

    msg = f"{emoji} [{bar}] {progress.progress * 100:5.1f}% | {progress.message}"
    if progress.llm_round:
        msg += f" (Round {progress.llm_round}/{progress.llm_max_rounds})"
    print(msg)

result = api.verify_function_stream(
    file_path="examples/safe_functions.py",
    function_name="count_to",
    callback=progress_callback,
    auto_generate_invariants=False
)

if result:
    print(f"\n{'✅' if result.verified else '❌'} {result.name}")
    print(f"  Status: {result.reason}")
    if result.verified:
        print(f"  Hash: #{result.specification.whyml_hash[:8]}")
    print(f"  Duration: {result.duration:.2f}s")
else:
    print("❌ Verification failed")

print("\n" + "=" * 60)
print("API Tests Complete!")
print("=" * 60)
