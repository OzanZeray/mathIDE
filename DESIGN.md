# Math IDE — Symbolic Mathematics Research Assistant

## Vision

An agentic workflow inside Claude Code that lets a mathematician conduct **symbolic (analytic) mathematics** interactively through natural language. The mathematician describes what to compute — series expansions, transforms, substitutions, simplifications — and the system produces verified symbolic results written up in clean Markdown with LaTeX math.

No numeric evaluation. Everything stays in closed-form.

---

## How It Works

```
Mathematician (chat)
        │
        ▼
  ┌─────────────┐
  │  Orchestrator │  ← Claude Code main agent
  │  (CLAUDE.md)  │
  └──────┬────────┘
         │ dispatches
         ▼
  ┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
  │  Math Planner    │────▶│ SymPy Runner │────▶│  MD Writer   │
  │  (decompose &   │     │ (execute &   │     │ (format &    │
  │   strategize)   │     │  verify)     │     │  explain)    │
  └─────────────────┘     └──────────────┘     └──────────────┘
```

### Flow

1. **Mathematician speaks** — e.g. *"Expand sin(x)/(1-x) as a Taylor series around x=0 to order 6, then take the Fourier transform"*
2. **Math Planner** decomposes the request into discrete symbolic steps, each with a clear input/output contract.
3. **SymPy Runner** executes each step as a Python/SymPy script, captures the symbolic result, and verifies it (e.g. substitution checks, limit checks).
4. **MD Writer** assembles a Markdown research note: numbered steps, LaTeX-rendered math, prose explanation, and a final collected result.
5. **Mathematician reviews** the output and can say *"now differentiate that with respect to k"* — the system picks up from the last result.

---

## Core Principles

| Principle | Detail |
|-----------|--------|
| **Symbolic only** | All computation via SymPy with `evaluate=False` where needed. No `float()`, no `N()`, no numeric approximation. |
| **Verifiable** | Every symbolic result is checked by an independent SymPy assertion (e.g. `simplify(result - expected) == 0`). |
| **Transparent** | The generated Python scripts are saved alongside the Markdown so the mathematician can inspect, re-run, or modify them. |
| **Conversational** | Each turn builds on prior context. A running "symbolic workspace" holds named expressions the mathematician can reference. |
| **Publication-ready** | Output Markdown uses proper LaTeX (`$$...$$`) and follows mathematical writing conventions. |

---

## Components

The system is built on a **plugin architecture** — tools, flows, backends, and renderers are all registered via JSON manifests and discovered at runtime. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full extensibility model.

### Agents

| Agent | Role |
|-------|------|
| **Math Planner** | Decomposes natural language into ordered symbolic steps, selects tools from the registry |
| **SymPy Runner** | Executes tools, captures results, runs verification, stores to workspace |
| **MD Writer** | Assembles step results into a LaTeX-rich Markdown research note |

### Plugin Dimensions

| Dimension | What it is | V1 | Extensible to |
|-----------|-----------|-----|---------------|
| **Tools** | Single math operations | series, calculus, transforms, solvers, linalg | complex analysis, Lie algebra, tensor algebra, ... |
| **Flows** | Multi-step recipes | fourier_analysis, ode_via_laplace | any reusable pipeline |
| **Backends** | Computation engines | SymPy | SageMath, Maxima, Cadabra, GAP, ... |
| **Renderers** | Output formatters | Markdown + LaTeX | Jupyter, Typst, HTML, Beamer, ... |

### Workspace

A versioned symbolic environment (`workspace/state.json`) tracking symbols, expressions with dependency graphs, and full step provenance. Supports session snapshots and Python export. See [ARCHITECTURE.md §9](ARCHITECTURE.md#9-workspace-architecture-revisited).

---

## Interaction Examples

### Example 1: Series + Transform
```
User: Take f(x) = e^(-x^2). Expand as Taylor series to order 8,
      then compute the Fourier transform of the result.

System: [Plans 3 steps → runs SymPy → writes MD]
        Produces: research_notes/fourier_of_gaussian_series.md
```

### Example 2: Iterative Refinement
```
User: Write the generating function for Bernoulli numbers.

System: [Produces t/(e^t - 1) = sum B_n t^n / n!]

User: Now extract B_0 through B_10.

System: [Extends previous result, lists coefficients symbolically]

User: Express B_{2n} in terms of the Riemann zeta function.

System: [Derives B_{2n} = (-1)^{n+1} * 2*(2n)! / (2*pi)^{2n} * zeta(2n)]
```

### Example 3: PDE / Transform Method
```
User: Solve the heat equation u_t = u_xx on the real line
      using the Fourier transform method. Assume u(x,0) = e^{-x^2}.

System: [Plans: FT in x → solve ODE in t → inverse FT → simplify]
        Produces full derivation with each step.
```

---

## File Structure

See [ARCHITECTURE.md §10](ARCHITECTURE.md#10-revised-file-structure) for the full tree. Key directories:

| Directory | Purpose |
|-----------|---------|
| `registry/` | JSON manifests for all plugins (tools, flows, backends, renderers) |
| `tools/` | Python scripts organized by math category |
| `backends/` | Computation engine adapters |
| `renderers/` | Output format generators |
| `flows/` | Flow engine that interprets flow manifests |
| `workspace/` | Runtime state, session snapshots, exports |
| `research_notes/` | Generated Markdown output |
| `agents/` | Claude Code agent definitions |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | Claude Code agents (subagent_type in CLAUDE.md) |
| Symbolic math | Python 3 + SymPy (v1 backend; extensible) |
| Output format | Markdown + LaTeX (v1 renderer; extensible) |
| Plugin system | JSON manifests + auto-generated index |
| State | Versioned workspace with dependency tracking |
| Version control | Git (each research session can be a commit) |

---

## What's NOT in Scope (V1)

- **Numeric computation** — no numpy, no floating point, no plots
- **GUI** — this is a CLI/chat-first tool
- **Proof assistants** — no Lean, no Coq; this is computation, not formal proof

Note: Additional CAS backends (Sage, Maxima, etc.) are **architecturally supported** but not shipped in V1.

---

## Related Documents

| Document | Contents |
|----------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Plugin system, registry, extensibility model, flow engine |
| [TOOLS.md](TOOLS.md) | Tool I/O contracts and specifications |

---

## Next Steps

1. Set up `CLAUDE.md` with project rules and agent routing
2. Create `registry/` with manifest schemas and initial tool manifests
3. Implement `tools/lib/` foundation (io_contract, sandbox, workspace, registry loader)
4. Write the three agent definitions (`math-planner`, `sympy-runner`, `md-writer`)
5. Implement core tools (series, calculus, transforms)
6. Build `flows/engine.py` to interpret flow manifests
7. Build a `/math` skill as the entry point
8. Test with 3-4 representative mathematical workflows
