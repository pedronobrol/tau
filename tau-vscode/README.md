# TAU for VS Code

Automatic formal verification for Python with Claude AI.

## Features

### 1. Auto-Generate Specifications with @safe + Tab

Write `@safe` above your function and press Tab to automatically generate `@requires` and `@ensures` specifications using Claude AI:

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
def multiply(x: int, n: int) -> int:
    ...
```

### 2. One-Click Verification

Click "▶ Run TAU Verification" above `@safe` decorators to verify your function:

```python
@safe ✔ #b8c1e1d7  # Success with integrity hash
@requires("n >= 0")
@ensures("result = n")
def count_to(n: int) -> int:
    ...
```

Or if verification fails:

```python
@safe ✗  # Failed - see Problems panel for details
@requires("n >= 0")
@ensures("result = n")
def buggy_count(n: int) -> int:
    ...
```

### 3. Real-Time Progress with Spinner

See live progress while specs are generated or verification runs:

```python
@safe ⠙  # Animated spinner
@requires("...") ⠙
@ensures("...") ⠙
def foo(...):
    ...
```

### 4. Automatic Bug Detection

TAU detects common bugs automatically:
- Off-by-one errors
- Wrong accumulators
- Infinite loops
- Specification mismatches

## Requirements

1. **TAU API Server** must be running:
   ```bash
   cd /path/to/tau-mvp
   python3 tau/server.py
   ```

2. **Python 3.7+** with TAU installed

3. **Why3** theorem prover:
   ```bash
   # macOS
   brew install why3

   # Linux
   opam install why3
   ```

4. **Anthropic API Key** (for spec generation):
   - Get from https://console.anthropic.com/
   - Set in extension settings or environment variable

## Quick Start

1. Install the extension
2. Start TAU server: `python3 tau/server.py`
3. Open a Python file
4. Write `@safe` above a function
5. Press Tab to generate specs
6. Click "▶ Run TAU Verification"

## Extension Settings

- `tau.serverUrl`: TAU API server URL (default: `http://localhost:8000`)
- `tau.anthropicApiKey`: Claude API key for spec generation
- `tau.pythonPath`: Python interpreter path
- `tau.proverTimeout`: Why3 prover timeout in seconds (default: 10)
- `tau.autoVerifyOnSave`: Auto-verify on file save (default: false)
- `tau.showInlineSpinner`: Show animated spinner (default: true)

## Keyboard Shortcuts

- `Cmd+Shift+G` (Mac) / `Ctrl+Shift+G` (Win/Linux): Generate specifications
- `Cmd+Shift+V` (Mac) / `Ctrl+Shift+V` (Win/Linux): Verify current function

## Commands

- `TAU: Generate Specifications` - Generate specs for function at cursor
- `TAU: Verify Function` - Verify function at cursor
- `TAU: Verify All Functions in File` - Verify entire file

## How It Works

1. **Specification Generation**: Claude analyzes your function and generates formal specifications in WhyML syntax
2. **Transpilation**: Python code is converted to WhyML (Why3's formal language)
3. **Verification**: Why3 prover attempts to prove correctness
4. **Results**: Success (✔), failure (✗), or bug detection displayed inline

## WhyML Syntax Quick Reference

- **Logic**: `/\` (and), `\/` (or), `->` (implies), `not`
- **Refs**: `!var` (dereference loop variables)
- **Math**: `+`, `-`, `*`, `div`, `mod`
- **Compare**: `=`, `<>`, `<`, `<=`, `>`, `>=`

Examples:
```python
@requires("n >= 0 /\\ x >= 0")
@ensures("result = n * x")
@invariant("0 <= !i <= n")
@variant("n - !i")
```

## Troubleshooting

### "TAU server is not running"
Start the server:
```bash
python3 tau/server.py
```

### "Failed to generate specifications"
- Check ANTHROPIC_API_KEY is set in settings or environment
- Verify server is running at configured URL

### "Verification failed"
- Check the Problems panel for details
- Ensure specifications match your code's actual behavior
- Try running `why3 prove` manually for more details

## Support

- GitHub: https://github.com/yourusername/tau
- Issues: https://github.com/yourusername/tau/issues
- Docs: https://github.com/yourusername/tau/blob/main/README.md

## License

MIT
