# tau-decorators

Lightweight Python decorators for TAU formal verification.

## Installation

```bash
pip install tau-decorators
```

## Usage

Use these decorators to mark your Python functions for formal verification with TAU:

```python
from tau_decorators import safe, requires, ensures, invariant, variant

@safe
@requires("n >= 0")
@ensures("result = n")
@invariant("0 <= !i <= n")
@invariant("!c = !i")
@variant("n - !i")
def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c
```

## What are these decorators?

These decorators are **markers** that tell the TAU verification system what properties your code should satisfy:

- **`@safe`** - Mark a function for formal verification
- **`@requires(spec)`** - Precondition that must hold when function is called
- **`@ensures(spec)`** - Postcondition that will hold when function returns
- **`@invariant(spec)`** - Loop invariant (holds before/after each iteration)
- **`@variant(spec)`** - Expression that decreases each iteration (proves termination)

## Runtime Behavior

These decorators are **no-ops at runtime** - they don't change your code's behavior. They're purely for:

1. **Static analysis** - Help linters and type checkers understand your code
2. **TAU verification** - The TAU VS Code extension reads these to verify correctness

The actual verification happens via the TAU server when using the VS Code extension.

## WhyML Syntax Quick Reference

Specifications use WhyML (Why3's formal language):

| Python | WhyML | Example |
|--------|-------|---------|
| `and` | `/\` | `n >= 0 /\ x >= 0` |
| `or` | `\/` | `x < 0 \/ x > 10` |
| `not` | `not` | `not (x = 0)` |
| `==` | `=` | `result = n` |
| `!=` | `<>` | `x <> 0` |
| Loop var | `!var` | `!i`, `!count` |
| Parameter | `var` | `n`, `x` |

**Important:** Loop variables are references - use `!i` not `i` in specs!

## Example

```python
from tau_decorators import safe, requires, ensures, invariant, variant

@safe
@requires("n >= 0 /\\ x >= 0")
@ensures("result = n * x")
@invariant("0 <= !i <= n")
@invariant("!result = !i * x")
@variant("n - !i")
def multiply(x: int, n: int) -> int:
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result
```

## VS Code Extension

For automatic verification, install the TAU VS Code extension:

1. Install this package: `pip install tau-decorators`
2. Install TAU extension from VS Code marketplace
3. Write code with `@safe` decorators
4. Click "▶ Run TAU Verification" in the editor
5. See ✔ or ✗ results inline!

## License

MIT

## Links

- [TAU Project](https://github.com/pedronobrol/tau)
- [VS Code Extension](https://github.com/pedronobrol/tau/tree/main/tau-vscode)
- [Documentation](https://github.com/pedronobrol/tau#readme)
