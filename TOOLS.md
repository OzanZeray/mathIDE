# Math IDE — Tools & Scripts Architecture

This document defines the concrete tools that Claude Code agents invoke during a math research session. Each tool is a Python script under `tools/` with a standardized I/O contract.

---

## Design Philosophy

Claude cannot do symbolic algebra in its head reliably. Every symbolic claim **must** be computed by SymPy and returned as structured output. The tools are the bridge: Claude decides *what* to compute, the tools *execute* it, and Claude *interprets* the result for the mathematician.

**Contract:** Every tool reads JSON from stdin, writes JSON to stdout. Errors go to stderr. Exit code 0 = success. Non-zero = failure with diagnostic on stderr.

---

## Tool Catalogue

### Overview

```
tools/
├── sympy_compute.py       # Core: evaluate any SymPy expression string
├── series_expand.py       # Taylor / Laurent / Puiseux series
├── transform.py           # Fourier, Laplace, Mellin, Z, inverse transforms
├── solve_equation.py      # Symbolic equation / system solving
├── differentiate.py       # Derivatives (partial, total, nth order)
├── integrate.py           # Definite & indefinite integrals
├── simplify_expr.py       # Simplification with strategy selection
├── substitute.py          # Variable substitution & evaluation
├── matrix_ops.py          # Symbolic linear algebra
├── ode_solve.py           # Ordinary differential equations
├── pde_solve.py           # Partial differential equations (transform method)
├── assumption_manager.py  # Declare / query symbol assumptions
├── workspace_manager.py   # Read / write / list workspace expressions
├── verify.py              # Verification checks on results
├── latex_render.py        # Expression → LaTeX string
└── lib/
    ├── io_contract.py     # Shared JSON I/O helpers
    ├── sympy_sandbox.py   # Safe SymPy import & execution environment
    └── workspace.py       # Workspace file read/write
```

---

## Tool Specifications

### 1. `sympy_compute.py` — General Computation

The escape hatch. Executes arbitrary SymPy code when no specialized tool fits.

```
Input:
{
  "code": "from sympy import *\nx = symbols('x')\nresult = integrate(exp(-x**2), (x, -oo, oo))",
  "workspace_vars": {"f": "sin(x)/(1-x)"}   // optional: inject workspace
}

Output:
{
  "result": "sqrt(pi)",
  "latex": "\\sqrt{\\pi}",
  "type": "Expression",
  "success": true
}
```

**Safety:** Runs in a restricted namespace. No `os`, `sys`, `subprocess`, `open`. Only `sympy` and `math` constants. Timeout: 30 seconds.

---

### 2. `series_expand.py` — Series Expansion

```
Input:
{
  "expr": "sin(x) / (1 - x)",      // SymPy-parseable string or workspace ref
  "variable": "x",
  "point": "0",                      // expansion point
  "order": 6,                        // number of terms
  "kind": "taylor"                   // taylor | laurent | puiseux | formal_power
}

Output:
{
  "result": "x + x**2 + 5*x**3/6 + 2*x**4/3 + 101*x**5/120 + ...",
  "latex": "x + x^{2} + \\frac{5 x^{3}}{6} + ...",
  "terms": {
    "0": "0",
    "1": "1",
    "2": "1",
    "3": "5/6",
    "4": "2/3",
    "5": "101/120"
  },
  "remainder": "O(x**6)",
  "success": true
}
```

**Capabilities:**
- Taylor series around any point (finite or 0)
- Laurent series (allowing negative powers)
- Asymptotic expansion (point = oo)
- Multivariate series (sequential expansion)

---

### 3. `transform.py` — Integral Transforms

```
Input:
{
  "expr": "exp(-a*t) * sin(w*t)",
  "transform": "laplace",            // fourier | inv_fourier | laplace | inv_laplace | mellin | inv_mellin
  "input_var": "t",
  "output_var": "s",
  "assumptions": {"a": ["positive"], "w": ["real"]}
}

Output:
{
  "result": "w / (s**2 + 2*a*s + a**2 + w**2)",
  "latex": "\\frac{\\omega}{s^{2} + 2 a s + a^{2} + \\omega^{2}}",
  "convergence": "Re(s) > -a",
  "success": true
}
```

**Supported transforms:**
| Transform | SymPy function | Typical use |
|-----------|---------------|-------------|
| Fourier | `fourier_transform` | Signal analysis, PDE on R |
| Inverse Fourier | `inverse_fourier_transform` | Reconstruction |
| Laplace | `laplace_transform` | ODE/control theory |
| Inverse Laplace | `inverse_laplace_transform` | Time-domain recovery |
| Mellin | `mellin_transform` | Number theory, asymptotics |
| Inverse Mellin | `inverse_mellin_transform` | Recovery |
| Z-transform | Custom via summation | Discrete signals |

---

### 4. `solve_equation.py` — Equation Solving

```
Input:
{
  "equations": ["x**3 - 3*x + 1"],       // list of expressions = 0
  "variables": ["x"],                      // solve for these
  "domain": "complex",                     // real | complex | integer | positive
  "method": "auto"                         // auto | factor | groebner | trig
}

Output:
{
  "solutions": [
    "2*cos(pi/9)",
    "-2*cos(2*pi/9)",
    "2*cos(4*pi/9) - 2"
  ],
  "latex_solutions": ["2\\cos\\frac{\\pi}{9}", ...],
  "num_solutions": 3,
  "method_used": "solve",
  "success": true
}
```

---

### 5. `differentiate.py` — Differentiation

```
Input:
{
  "expr": "f_series",                      // workspace ref or expression string
  "variable": "x",
  "order": 1,                              // nth derivative
  "partial": false                         // true for partial derivatives
}

Output:
{
  "result": "cos(x)*(1-x) + sin(x)) / (1-x)**2",
  "latex": "...",
  "success": true
}
```

Supports: `diff`, `Derivative` (unevaluated for display), mixed partials via list `["x", "x", "y"]`.

---

### 6. `integrate.py` — Integration

```
Input:
{
  "expr": "exp(-x**2) * cos(k*x)",
  "variable": "x",
  "limits": ["-oo", "oo"],                // omit for indefinite
  "method": "auto",                        // auto | meijerg | residues | risch
  "assumptions": {"k": ["real"]}
}

Output:
{
  "result": "sqrt(pi) * exp(-k**2/4)",
  "latex": "\\sqrt{\\pi} \\, e^{-k^{2}/4}",
  "converges": true,
  "method_used": "meijerg",
  "success": true
}
```

---

### 7. `simplify_expr.py` — Simplification

```
Input:
{
  "expr": "sin(x)**2 + cos(x)**2 + sin(2*x)/2",
  "strategy": "auto",                     // auto | trig | power | collect | factor | apart | cancel | radsimp
  "collect_var": null,                     // variable to collect terms around
  "target_form": null                      // optional: "factored", "expanded", "partial_fractions"
}

Output:
{
  "result": "1 + sin(x)*cos(x)",
  "latex": "1 + \\sin{x}\\cos{x}",
  "strategy_used": "trigsimp",
  "success": true
}
```

**Strategy dispatch table:**

| Strategy | SymPy call | When to use |
|----------|-----------|-------------|
| `auto` | `simplify()` | Default, tries heuristics |
| `trig` | `trigsimp()` | Trig identities |
| `power` | `powsimp()` | Power / exponential laws |
| `collect` | `collect(expr, var)` | Group by variable |
| `factor` | `factor()` | Polynomial factoring |
| `apart` | `apart()` | Partial fractions |
| `cancel` | `cancel()` | Cancel common factors |
| `radsimp` | `radsimp()` | Denest radicals |
| `fu` | `fu()` | Advanced trig (Fu's algorithm) |

---

### 8. `substitute.py` — Substitution

```
Input:
{
  "expr": "F_k",                           // workspace ref
  "substitutions": {"k": "2*pi*n", "a": "1"},
  "evaluate": false                        // false keeps unevaluated for display
}

Output:
{
  "result": "...",
  "latex": "...",
  "success": true
}
```

---

### 9. `matrix_ops.py` — Symbolic Linear Algebra

```
Input:
{
  "operation": "eigenvalues",              // det | inv | eigenvalues | eigenvectors | jordan | svd_symbolic | nullspace | rank
  "matrix": "[[a, b], [c, d]]",           // SymPy Matrix string
  "assumptions": {"a": ["real"], "b": ["real"]}
}

Output:
{
  "result": {"(a + d - sqrt(a**2 - 2*a*d + 4*b*c + d**2))/2": 1, ...},
  "latex": "...",
  "success": true
}
```

---

### 10. `ode_solve.py` — ODE Solver

```
Input:
{
  "equation": "f(x).diff(x, 2) + f(x)",   // SymPy ODE string
  "function": "f(x)",
  "conditions": {"f(0)": "1", "f'(0)": "0"},  // initial / boundary
  "method": "auto"                          // auto | variation_of_parameters | power_series | lie_group
}

Output:
{
  "general_solution": "C1*sin(x) + C2*cos(x)",
  "particular_solution": "cos(x)",
  "latex": "...",
  "classification": "2nd_linear_constant_coeff_homogeneous",
  "success": true
}
```

---

### 11. `pde_solve.py` — PDE Solver (Transform Method)

```
Input:
{
  "equation": "Eq(u(x,t).diff(t), u(x,t).diff(x,2))",
  "function": "u(x,t)",
  "conditions": {"u(x,0)": "exp(-x**2)"},
  "domain": {"x": ["-oo", "oo"], "t": ["0", "oo"]},
  "method": "fourier"                      // fourier | laplace | separation
}

Output:
{
  "solution": "exp(-x**2/(1+4*t)) / sqrt(1+4*t)",
  "latex": "...",
  "method_steps": [
    "Apply Fourier transform in x",
    "Solve resulting ODE in t",
    "Apply inverse Fourier transform"
  ],
  "success": true
}
```

---

### 12. `assumption_manager.py` — Symbol Assumptions

```
Input:
{
  "action": "declare",                     // declare | query | list | clear
  "symbols": {
    "x": ["real"],
    "n": ["integer", "positive"],
    "epsilon": ["positive", "infinitesimal"]
  }
}

Output:
{
  "declared": {"x": ["real"], "n": ["integer", "positive"], ...},
  "success": true
}
```

Assumptions propagate to all tools via the workspace. Critical for transforms and integrals where convergence depends on sign/domain.

---

### 13. `workspace_manager.py` — State Management

```
Input:
{
  "action": "store",                       // store | load | list | delete | reset | export
  "name": "f_hat",
  "expr": "sqrt(pi) * exp(-k**2/4)",
  "metadata": {"source_step": "Fourier transform of f"}
}

Output:
{
  "stored": "f_hat",
  "workspace_size": 5,
  "success": true
}
```

**Actions:**
| Action | Purpose |
|--------|---------|
| `store` | Save named expression |
| `load` | Retrieve by name |
| `list` | List all stored names + short descriptions |
| `delete` | Remove a named expression |
| `reset` | Clear entire workspace |
| `export` | Dump full workspace as SymPy-parseable Python |

---

### 14. `verify.py` — Result Verification

```
Input:
{
  "claim": "integrate(exp(-x**2), (x, -oo, oo)) == sqrt(pi)",
  "method": "direct",                     // direct | substitution | limit | series_compare | identity
  "tolerance_order": null                  // for series comparison: agree to O(x^n)
}

Output:
{
  "verified": true,
  "method_used": "direct",
  "detail": "simplify(LHS - RHS) = 0",
  "success": true
}
```

**Verification strategies:**
- **direct** — `simplify(LHS - RHS) == 0`
- **substitution** — evaluate both sides at several rational points, confirm symbolic equality
- **limit** — check boundary / limiting behavior matches
- **series_compare** — expand both sides as series, compare term by term
- **identity** — check against known identities (e.g. Parseval's theorem)

---

### 15. `latex_render.py` — LaTeX Formatting

```
Input:
{
  "expr": "sqrt(pi) * exp(-k**2/4)",
  "style": "display",                     // display | inline | aligned
  "substitutions": null,                   // optional: pretty-print with replacements
  "equation_label": "eq:fourier_gaussian"  // optional
}

Output:
{
  "latex": "\\sqrt{\\pi} \\, e^{-k^{2}/4}",
  "display": "$$\n\\sqrt{\\pi} \\, e^{-k^{2}/4}\n$$",
  "labeled": "$$\n\\sqrt{\\pi} \\, e^{-k^{2}/4} \\tag{eq:fourier_gaussian}\n$$",
  "success": true
}
```

---

## Shared Library: `tools/lib/`

### `io_contract.py` — Standard I/O

```python
"""
Every tool imports this. Ensures uniform JSON contract.
"""
import json, sys

def read_input() -> dict:
    """Read JSON from stdin."""
    return json.loads(sys.stdin.read())

def write_output(data: dict):
    """Write JSON to stdout."""
    data.setdefault("success", True)
    print(json.dumps(data, indent=2))

def write_error(message: str, code: str = "COMPUTATION_ERROR"):
    """Write error to stderr and exit."""
    print(json.dumps({"success": False, "error": code, "message": message}), file=sys.stderr)
    sys.exit(1)
```

### `sympy_sandbox.py` — Safe Execution

```python
"""
Restricted SymPy execution environment.
- No filesystem access
- No network access
- No subprocess spawning
- 30-second timeout
"""
import signal
from sympy import *

BLOCKED_MODULES = {'os', 'sys', 'subprocess', 'shutil', 'pathlib', 'socket', 'http', 'urllib'}

SAFE_NAMESPACE = {
    name: getattr(__import__('sympy'), name)
    for name in dir(__import__('sympy'))
    if not name.startswith('_')
}
SAFE_NAMESPACE['__builtins__'] = {
    'range': range, 'len': len, 'int': int, 'str': str,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
    'True': True, 'False': False, 'None': None,
    'print': print, 'isinstance': isinstance, 'type': type,
    'enumerate': enumerate, 'zip': zip, 'map': map, 'filter': filter,
    'sum': sum, 'min': min, 'max': max, 'abs': abs, 'sorted': sorted,
}

def execute_sympy(code: str, timeout: int = 30) -> dict:
    """Execute SymPy code in sandbox, return namespace."""
    def handler(signum, frame):
        raise TimeoutError(f"Computation exceeded {timeout}s")

    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(timeout)
    try:
        ns = dict(SAFE_NAMESPACE)
        exec(code, ns)
        return {k: v for k, v in ns.items() if not k.startswith('_')}
    finally:
        signal.alarm(0)
```

### `workspace.py` — Workspace File Access

```python
"""
Read/write workspace.json with SymPy serialization.
Expressions stored as SymPy-parseable strings (srepr for lossless round-trip).
"""
import json
from pathlib import Path
from sympy import sympify, srepr, latex

WORKSPACE_PATH = Path(__file__).parent.parent.parent / "workspace.json"

def load_workspace() -> dict:
    if not WORKSPACE_PATH.exists():
        return {"symbols": {}, "expressions": {}, "history": []}
    return json.loads(WORKSPACE_PATH.read_text())

def save_workspace(ws: dict):
    WORKSPACE_PATH.write_text(json.dumps(ws, indent=2))

def resolve_expr(name_or_expr: str, ws: dict):
    """If name_or_expr is a workspace key, return stored expr. Else parse as SymPy."""
    if name_or_expr in ws.get("expressions", {}):
        return sympify(ws["expressions"][name_or_expr])
    return sympify(name_or_expr)

def store_expr(name: str, expr, ws: dict, metadata: dict = None):
    """Store expression in workspace."""
    ws["expressions"][name] = srepr(expr)
    ws["history"].append({
        "action": "store",
        "name": name,
        "latex": latex(expr),
        **(metadata or {})
    })
    save_workspace(ws)
```

---

## How Claude Code Invokes Tools

Each tool is called via the **Bash tool** with a JSON pipe:

```bash
echo '{"expr": "sin(x)/(1-x)", "variable": "x", "point": "0", "order": 6, "kind": "taylor"}' \
  | python tools/series_expand.py
```

The agent reads stdout (JSON), checks `"success": true`, and extracts `result` and `latex`.

On failure, the agent reads stderr, diagnoses, and either:
1. Adjusts parameters and retries (e.g. increase timeout, change method)
2. Falls back to `sympy_compute.py` with raw code
3. Reports the issue to the mathematician

---

## Tool Selection Logic (for Math Planner)

```
User says                          → Tool
─────────────────────────────────────────────
"expand as Taylor series"          → series_expand.py (kind=taylor)
"Fourier transform"                → transform.py (transform=fourier)
"solve for x"                      → solve_equation.py
"differentiate with respect to"    → differentiate.py
"integrate over"                   → integrate.py
"simplify" / "reduce"              → simplify_expr.py
"substitute x = ..."               → substitute.py
"eigenvalues of"                   → matrix_ops.py
"solve the ODE"                    → ode_solve.py
"solve the PDE"                    → pde_solve.py
"let x be real and positive"       → assumption_manager.py
"call that result f_hat"           → workspace_manager.py (store)
"what's in the workspace"          → workspace_manager.py (list)
"verify that"                      → verify.py
[any other symbolic computation]   → sympy_compute.py (general fallback)
```

---

## Chaining Example: Full Pipeline

**User:** *"Take f(x) = 1/(1+x^2). Compute its Fourier transform analytically, then verify using Parseval's theorem."*

```
Step 1: workspace_manager.py  → store  f = 1/(1+x**2)
Step 2: assumption_manager.py → declare x: real, k: real
Step 3: transform.py          → fourier(f, x, k) → result: pi*exp(-abs(k))  → store as F_k
Step 4: latex_render.py       → render F_k
Step 5: integrate.py          → ∫|f|² dx = ∫ 1/(1+x²)² dx = pi/2
Step 6: integrate.py          → ∫|F_k|² dk = ∫ pi²*exp(-2|k|) dk = pi²
Step 7: verify.py             → check ∫|f|²dx == (1/2π)∫|F_k|²dk → pi/2 == pi²/2π ✓
Step 8: md_writer             → assemble research note with all steps
```

---

## Error Taxonomy

| Error Code | Meaning | Agent Response |
|-----------|---------|----------------|
| `PARSE_ERROR` | Expression string not valid SymPy | Ask user to clarify notation |
| `COMPUTATION_TIMEOUT` | Exceeded 30s | Try simpler form or different method |
| `NO_CLOSED_FORM` | SymPy cannot find closed form | Report honestly, suggest numeric note |
| `ASSUMPTION_MISSING` | Result depends on undeclared sign/domain | Prompt for assumptions |
| `VERIFICATION_FAILED` | Result didn't pass verification check | Flag to user, show discrepancy |
| `WORKSPACE_NOT_FOUND` | Referenced name not in workspace | List available names |
| `METHOD_NOT_APPLICABLE` | Requested method doesn't apply | Fall back to auto |

---

## Next: Implementation Order

1. **`lib/` foundation** — `io_contract.py`, `sympy_sandbox.py`, `workspace.py`
2. **`workspace_manager.py`** — state management must work first
3. **`sympy_compute.py`** — general fallback ensures nothing blocks
4. **Core tools** — `series_expand.py`, `differentiate.py`, `integrate.py`, `simplify_expr.py`
5. **Transform tools** — `transform.py`
6. **Solver tools** — `solve_equation.py`, `ode_solve.py`, `pde_solve.py`
7. **Support tools** — `verify.py`, `latex_render.py`, `substitute.py`, `matrix_ops.py`, `assumption_manager.py`
8. **Agent definitions** — wire tools into agent `.md` files
