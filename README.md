# TAU - Python Formal Verification

Automatic formal verification for Python using Why3 and Claude AI. Write `@safe` above your functions and TAU proves them correct or finds bugs.

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Set API key (optional - for auto-spec generation)
export ANTHROPIC_API_KEY=sk-ant-...

# Start server
python3 -m tau.server.app
```

**VS Code Extension:**
1. Open `tau-vscode` folder in VS Code
2. Press F5 to launch extension
3. Add `@safe` above a function → Press Tab → Click "Verify"

## Example

```python
@safe
# @requires: n >= 0
# @ensures: result = n
def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c
```

**Result:** `✔ Proof passed #bfbf2199`

## Monorepo Structure

```
tau-mvp/
├── tau/                    # Core verification engine
│   ├── core/              # Python → WhyML transpiler
│   ├── llm/               # Claude AI integration
│   ├── server/            # REST API server
│   ├── proofs/            # Proof certificate caching
│   └── verify.py          # Main API
├── tau-vscode/            # VS Code extension
│   ├── src/
│   └── package.json
├── examples/              # Example verified functions
├── tests/                 # Test suite
└── proofs/                # Cached proof certificates
```

## Features

**🤖 AI-Powered Specs**
- Type `@safe` + Tab → Claude generates `@requires`/`@ensures`
- Auto-generates loop invariants and variants

**⚡ Instant Verification**
- Proof caching: verified functions show status instantly
- Hash-based: only re-verify when code changes
- Team-wide: commit `proofs/` to share proofs

**🐛 Bug Detection**
- Finds off-by-one errors, wrong accumulators, infinite loops
- Shows exactly which specification failed

**💻 Multiple Interfaces**
- VS Code extension (recommended)
- REST API (`http://localhost:8000/docs`)
- Python API (`from tau.server.client import TauClient`)

## Requirements

- Python 3.7+
- Why3 (`brew install why3` or `opam install why3`)
- Anthropic API key (optional, for spec generation)

## Development

```bash
# Run tests
python3 -m pytest tests/ -v

# Run examples
python3 examples/demo.py

# VS Code extension development
cd tau-vscode
npm install
npm run compile
# Press F5 in VS Code
```

## Proof Caching

TAU caches verification results in `proofs/`:

```
proofs/
├── index.json             # Fast lookup index
├── artifacts/             # Proof certificates
├── whyml/                # Generated WhyML code
└── logs/                 # Why3 outputs
```

Benefits:
- **Instant results** for previously verified functions
- **Team sharing** - commit proofs to git
- **Formatting-safe** - AST-based hashing ignores whitespace

## License

MIT
