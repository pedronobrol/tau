# TAU - Python Formal Verification with AI

Automatic formal verification for Python using decorators, Why3, and Claude AI. Write `@safe` above your functions and let TAU prove them correct or find bugs automatically.

[![Tests](https://img.shields.io/badge/tests-20%2F20%20passing-brightgreen)]() [![Python](https://img.shields.io/badge/python-3.7%2B-blue)]() [![License](https://img.shields.io/badge/license-MIT-green)]()

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (optional, for auto-spec generation)
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# Start TAU server
./start_server.sh
```

Then in VS Code:
1. Write `@safe` above a function
2. Press Tab → Claude generates `@requires` and `@ensures`
3. Click "▶ Run TAU" → See ✔ or ✗ inline

## Features

### 1. Auto-Generate Specs (VS Code)
```python
@safe  # Press Tab here!
def multiply(x: int, n: int) -> int:
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result
```

Becomes:
```python
@safe
@requires("n >= 0 /\\ x >= 0")
@ensures("result = n * x")
# @invariant("0 <= !i <= n")
# @invariant("!result = !i * x")
# @variant("n - !i")
def multiply(x: int, n: int) -> int:
    ...
```

### 2. One-Click Verification
```python
@safe ✔ #b8c1e1d7  # Click "▶ Run TAU" above @safe
@requires("n >= 0")
@ensures("result = n")
def count_to(n: int) -> int:
    ...
```

### 3. Automatic Bug Detection
```python
@safe ✗  # Detects off-by-one errors
@requires("n >= 0")
@ensures("result = n")
def buggy_count(n: int) -> int:
    c = 0
    i = 0
    while i <= n:  # BUG: should be i < n
        c = c + 1
        i = i + 1
    return c
```

## Installation

### Requirements
1. **Python 3.7+**
2. **Why3** - Theorem prover
   ```bash
   brew install why3        # macOS
   opam install why3        # Linux
   why3 config detect
   ```
3. **Anthropic API Key** - For spec generation (optional)
   - Get from https://console.anthropic.com/

### Install TAU
```bash
git clone https://github.com/pedronobrol/tau.git
cd tau
pip install -r requirements.txt
```

## Usage

### Option 1: VS Code Extension (Recommended)

#### 1. Start TAU Server
```bash
./start_server.sh
# Server runs on http://localhost:8000
# API docs: http://localhost:8000/docs
```

#### 2. Install Extension
```bash
cd tau-vscode
npm install
npm run compile
```

Press F5 in VS Code to launch extension in debug mode.

#### 3. Use It
- **Generate Specs**: Type `@safe`, press Tab
- **Verify**: Click "▶ Run TAU" or `Cmd+Shift+V`
- **See Results**: ✔ #hash (success) or ✗ (failed)

#### Extension Settings
- `tau.serverUrl`: API server URL (default: `http://localhost:8000`)
- `tau.anthropicApiKey`: Claude API key
- `tau.autoVerifyOnSave`: Auto-verify on save
- `tau.showInlineSpinner`: Show animated spinner

### Option 2: Python API

```python
from tau.server.client import TauClient

client = TauClient(api_key="sk-ant-...")

# Generate specs
specs = client.generate_specs("""
def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c
""")

print(f"@requires: {specs.requires}")
print(f"@ensures: {specs.ensures}")

# Verify function
result = client.verify_function(
    file_path="examples/safe_functions.py",
    function_name="count_to"
)

print(f"Verified: {result.verified}")
```

### Option 3: REST API

```bash
# Generate specs
curl -X POST http://localhost:8000/api/generate-specs \
  -H "Content-Type: application/json" \
  -d '{
    "function_source": "def count_to(n: int) -> int: ..."
  }'

# Verify function
curl -X POST http://localhost:8000/api/verify-function \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "examples/safe_functions.py",
    "function_name": "count_to"
  }'
```

API docs: http://localhost:8000/docs

### Option 4: Command Line

```python
# examples/mycode.py
from tau.decorators import safe, requires, ensures

@safe
@requires("n >= 0")
@ensures("result = n")
def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c
```

```bash
python3 -c "from tau.verify import verify_file; verify_file('examples/mycode.py')"
```

## WhyML Syntax

| Python | WhyML | Example |
|--------|-------|---------|
| `and` | `/\` | `n >= 0 /\ x >= 0` |
| `or` | `\/` | `x < 0 \/ x > 10` |
| `not` | `not` | `not (x = 0)` |
| `==` | `=` | `result = n` |
| `!=` | `<>` | `x <> 0` |
| `/` | `div` | `div n 2` |
| `%` | `mod` | `mod n 2` |
| Loop var | `!var` | `!i`, `!count` |
| Parameter | `var` | `n`, `x` |

**Important**: Loop variables are references - use `!i` not `i` in specs!

## Architecture

```
tau/
├── core/                # Core transpiler (Python → WhyML)
├── decorators.py        # @safe, @requires, @ensures, @invariant, @variant
├── parser.py            # Extract @safe functions
├── verify.py            # Main verification API
├── llm/                 # Claude integration
│   ├── feedback_loop.py # Auto-generate invariants
│   └── spec_generator.py# Generate requires/ensures
├── server/              # FastAPI REST API
│   ├── app.py          # FastAPI server
│   ├── client.py       # Python client
│   └── models.py       # Data models
└── output/              # JSON export with SHA-256 hashes

tau-vscode/              # VS Code extension
├── src/
│   ├── extension.ts    # Main extension
│   ├── tauClient.ts    # HTTP client
│   ├── completionProvider.ts  # @safe + Tab
│   ├── codeLensProvider.ts    # "Run TAU" link
│   └── decorationProvider.ts  # ✔/✗ decorations
└── package.json
```

## Examples

See [examples/safe_functions.py](examples/safe_functions.py):
- `count_to` - Basic counter with manual invariants
- `multiply` - LLM auto-generated invariants
- `buggy_count` - Off-by-one error detection
- `clamp` - Conditional logic
- `sum_to` - Complex mathematical invariant

## Supported Python

**✅ Supported:**
- Variables, integers, booleans
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Boolean: `and`, `or`, `not`
- If/else (both branches required)
- While loops (one per function)
- Type annotations (required)

**❌ Not Supported:**
- For loops, list comprehensions
- Multiple while loops per function
- Lists, dicts, classes
- String operations
- Floating point

## Troubleshooting

**"TAU server not running"**
```bash
./start_server.sh
```

**"ANTHROPIC_API_KEY not set"**
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

**"Why3 not found"**
```bash
brew install why3        # macOS
opam install why3        # Linux
why3 config detect
```

**"Verification failed"**
- Check Problems panel in VS Code for details
- Ensure specs match your code's actual behavior
- Try running `why3 prove why_out/yourfunction.why` manually

**"Port 8000 in use"**
```bash
lsof -ti:8000 | xargs kill -9
```

## Testing

```bash
# Run all tests
python3 -m pytest tau/tests/ -v

# Test API
python3 test_api.py

# Test server
curl http://localhost:8000/
```

## Performance

- **Spec Generation**: ~1-5 seconds (Claude 3.5 Haiku)
- **Verification**: ~0.1-10 seconds (depends on complexity)
- **Cost**: ~$0.0005 per function (Claude Haiku)
- **Bug Detection**: 100% on common bugs (off-by-one, wrong accumulator, infinite loops)

## License

MIT

## References

- [Why3 Documentation](http://why3.lri.fr/)
- [Lean 4](https://lean-lang.org/)
- [Anthropic Claude](https://www.anthropic.com/claude)
