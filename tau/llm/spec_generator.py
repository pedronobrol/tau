"""
LLM-based specification generator for Python functions
"""
import os
from typing import Optional, List
from tau.server.models import GeneratedSpecs, FunctionInfo


SPEC_GENERATION_PROMPT = """You are a formal verification expert. Analyze this Python function and generate formal specifications.

Function to analyze:
```python
{function_source}
```

Context (surrounding code):
```python
{context}
```

Your task:
1. Identify the function's preconditions (@requires) - What must be true before the function runs?
2. Identify the function's postconditions (@ensures) - What will be true after the function runs?
3. If the function has a loop, suggest loop invariants (optional)
4. If the function has a loop, suggest a variant for termination (optional)

Use WhyML syntax:
- Loop variables are references: use !var (e.g., !i, !count)
- Parameters don't need !: use directly (e.g., n, x)
- Operators: /\\ (and), \\/ (or), -> (implies), not
- Math: +, -, *, div, mod
- Comparisons: =, <>, <, <=, >, >=

Examples:
- Precondition: "n >= 0 /\\ x >= 0"
- Postcondition: "result = n * x"
- Loop invariant: "0 <= !i <= n /\\ !acc = !i * x"
- Variant: "n - !i"

Respond in this exact JSON format:
{{
  "requires": ["precondition1", "precondition2"],
  "ensures": ["postcondition1", "postcondition2"],
  "reasoning": "Brief explanation of why these specifications are correct",
  "confidence": 0.95,
  "suggested_invariants": ["invariant1", "invariant2"],
  "suggested_variant": "variant_expression"
}}

If no preconditions are needed, use ["true"].
If no loop exists, leave suggested_invariants and suggested_variant empty.
"""


def _get_client():
    """Get Anthropic client, with graceful fallback"""
    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        return None


async def generate_specifications(
    function_info: FunctionInfo,
    context: str = "",
    api_key: Optional[str] = None,
    model: str = "claude-3-5-haiku-20241022"
) -> Optional[GeneratedSpecs]:
    """
    Generate formal specifications for a Python function using Claude.

    Args:
        function_info: Information about the function to analyze
        context: Surrounding code for better context
        api_key: Anthropic API key (uses env var if not provided)
        model: Claude model to use

    Returns:
        GeneratedSpecs object or None if LLM not available
    """
    # Set API key if provided
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    client = _get_client()
    if not client:
        print("⚠️  Warning: Anthropic client not available. Install 'anthropic' package and set ANTHROPIC_API_KEY.")
        return None

    # Prepare prompt
    prompt = SPEC_GENERATION_PROMPT.format(
        function_source=function_info.source,
        context=context if context else "# No surrounding context provided"
    )

    try:
        # Call Claude
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        import json
        response_text = response.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        data = json.loads(response_text)

        # Convert to GeneratedSpecs
        return GeneratedSpecs(
            requires=data.get("requires", ["true"]),
            ensures=data.get("ensures", ["true"]),
            reasoning=data.get("reasoning", ""),
            confidence=float(data.get("confidence", 0.0)),
            suggested_invariants=data.get("suggested_invariants", []),
            suggested_variant=data.get("suggested_variant")
        )

    except Exception as e:
        print(f"❌ Error generating specifications: {e}")
        return None


def generate_specifications_sync(
    function_info: FunctionInfo,
    context: str = "",
    api_key: Optional[str] = None,
    model: str = "claude-3-5-haiku-20241022"
) -> Optional[GeneratedSpecs]:
    """
    Synchronous version of generate_specifications.

    Args:
        function_info: Information about the function to analyze
        context: Surrounding code for better context
        api_key: Anthropic API key (uses env var if not provided)
        model: Claude model to use

    Returns:
        GeneratedSpecs object or None if LLM not available
    """
    # Set API key if provided
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    client = _get_client()
    if not client:
        print("⚠️  Warning: Anthropic client not available. Install 'anthropic' package and set ANTHROPIC_API_KEY.")
        return None

    # Prepare prompt
    prompt = SPEC_GENERATION_PROMPT.format(
        function_source=function_info.source,
        context=context if context else "# No surrounding context provided"
    )

    try:
        # Call Claude
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        import json
        response_text = response.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        data = json.loads(response_text)

        # Convert to GeneratedSpecs
        return GeneratedSpecs(
            requires=data.get("requires", ["true"]),
            ensures=data.get("ensures", ["true"]),
            reasoning=data.get("reasoning", ""),
            confidence=float(data.get("confidence", 0.0)),
            suggested_invariants=data.get("suggested_invariants", []),
            suggested_variant=data.get("suggested_variant")
        )

    except Exception as e:
        print(f"❌ Error generating specifications: {e}")
        return None
