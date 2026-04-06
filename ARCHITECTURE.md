# Math IDE — Extensible Architecture

This document replaces the static tool catalogue with a **plugin-based architecture** where tools, flows, backends, and output formats are all discoverable, registrable, and composable. Nothing is hardwired.

---

## 1. Core Abstraction: Everything is a Plugin

The system has four plugin dimensions. Each can be extended independently:

```
                    ┌──────────────────────────────┐
                    │         Plugin Registry       │
                    │      (registry/index.json)    │
                    └──────┬───┬───┬───┬───────────┘
                           │   │   │   │
              ┌────────────┘   │   │   └────────────┐
              ▼                ▼   ▼                ▼
        ┌──────────┐   ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Tools   │   │  Flows   │  │ Backends │  │ Renderers│
        │ (compute)│   │ (chains) │  │ (engines)│  │ (output) │
        └──────────┘   └──────────┘  └──────────┘  └──────────┘
```

| Dimension | What it is | Examples |
|-----------|-----------|----------|
| **Tool** | A single mathematical operation | `series.expand`, `integral.definite`, `linalg.eigenvalues` |
| **Flow** | A reusable multi-step recipe | `fourier_analysis`, `ode_via_laplace`, `parseval_verify` |
| **Backend** | A computation engine | `sympy` (v1), future: `sage`, `maxima`, `cadabra` |
| **Renderer** | An output formatter | `markdown_latex`, future: `jupyter`, `typst`, `pdf` |

---

## 2. Plugin Registry

### 2.1 Registry Structure

```
registry/
├── index.json              # Master index (auto-generated from manifests)
├── tools/
│   ├── series.json         # Tool manifest: series operations
│   ├── transform.json      # Tool manifest: integral transforms
│   ├── calculus.json       # Tool manifest: diff, integrate
│   └── ...
├── flows/
│   ├── fourier_analysis.json
│   ├── ode_via_laplace.json
│   └── ...
├── backends/
│   └── sympy.json
└── renderers/
    └── markdown_latex.json
```

### 2.2 Tool Manifest Schema

Every tool is described by a manifest that the orchestrator reads at runtime. Claude never needs to know about tools at import time — it discovers them.

```json
{
  "$schema": "mathide://tool-manifest/v1",
  "id": "series.expand",
  "version": "0.1.0",
  "name": "Series Expansion",
  "category": "analysis",
  "tags": ["taylor", "laurent", "puiseux", "asymptotic", "power_series"],

  "description": "Expand an expression as a series around a point.",
  "when_to_use": "User asks to expand, approximate, or write as a series.",

  "backend": "sympy",
  "entry_point": "tools/series/expand.py",

  "input_schema": {
    "type": "object",
    "required": ["expr", "variable"],
    "properties": {
      "expr":     {"type": "string", "description": "Expression or workspace ref"},
      "variable": {"type": "string"},
      "point":    {"type": "string", "default": "0"},
      "order":    {"type": "integer", "default": 6, "minimum": 1},
      "kind":     {"type": "string", "enum": ["taylor", "laurent", "puiseux", "formal_power", "asymptotic"], "default": "taylor"},
      "direction": {"type": "string", "enum": ["+", "-", "+-"], "default": "+-", "description": "For Laurent/asymptotic: direction of approach"}
    }
  },

  "output_schema": {
    "type": "object",
    "properties": {
      "result":    {"type": "string"},
      "latex":     {"type": "string"},
      "terms":     {"type": "object", "description": "Power → coefficient map"},
      "remainder": {"type": "string"},
      "success":   {"type": "boolean"}
    }
  },

  "capabilities": {
    "workspace_aware": true,
    "stores_result": true,
    "supports_assumptions": true
  },

  "examples": [
    {
      "input":  {"expr": "sin(x)/(1-x)", "variable": "x", "order": 5},
      "output": {"result": "x + x**2 + 5*x**3/6 + ...", "success": true}
    }
  ]
}
```

### 2.3 Flow Manifest Schema

A flow is a **template** for a multi-step computation. It references tools by ID, not by file path.

```json
{
  "$schema": "mathide://flow-manifest/v1",
  "id": "fourier_analysis",
  "version": "0.1.0",
  "name": "Fourier Analysis Pipeline",
  "description": "Define a function, compute its Fourier transform, verify via Parseval's theorem.",
  "tags": ["fourier", "transform", "parseval", "verification"],

  "parameters": {
    "expr":      {"type": "string", "description": "The function to analyze"},
    "input_var": {"type": "string", "default": "x"},
    "freq_var":  {"type": "string", "default": "k"}
  },

  "steps": [
    {
      "id": "define",
      "tool": "workspace.store",
      "inputs": {"name": "f", "expr": "{{expr}}"},
      "description": "Store the function in workspace"
    },
    {
      "id": "assume",
      "tool": "assumptions.declare",
      "inputs": {"symbols": {"{{input_var}}": ["real"], "{{freq_var}}": ["real"]}}
    },
    {
      "id": "forward_transform",
      "tool": "transform.fourier",
      "inputs": {"expr": "f", "input_var": "{{input_var}}", "output_var": "{{freq_var}}"},
      "store_as": "F"
    },
    {
      "id": "energy_time",
      "tool": "integral.definite",
      "inputs": {"expr": "Abs(f)**2", "variable": "{{input_var}}", "limits": ["-oo", "oo"]},
      "store_as": "E_time"
    },
    {
      "id": "energy_freq",
      "tool": "integral.definite",
      "inputs": {"expr": "Abs(F)**2", "variable": "{{freq_var}}", "limits": ["-oo", "oo"]},
      "store_as": "E_freq"
    },
    {
      "id": "parseval_check",
      "tool": "verify.identity",
      "inputs": {"claim": "Eq(E_time, E_freq / (2*pi))"},
      "on_failure": "warn"
    }
  ],

  "output": {
    "render": "markdown_latex",
    "sections": ["define", "forward_transform", "parseval_check"]
  }
}
```

### 2.4 Backend Manifest Schema

```json
{
  "$schema": "mathide://backend-manifest/v1",
  "id": "sympy",
  "version": "1.13",
  "name": "SymPy",
  "language": "python",

  "capabilities": [
    "symbolic_algebra", "calculus", "series", "transforms",
    "ode", "pde", "linear_algebra", "assumptions", "latex_output"
  ],

  "setup": {
    "check_command": "python -c \"import sympy; print(sympy.__version__)\"",
    "install_command": "pip install sympy"
  },

  "sandbox": {
    "timeout_seconds": 30,
    "blocked_modules": ["os", "sys", "subprocess", "shutil", "socket", "http"],
    "max_memory_mb": 512
  },

  "type_mapping": {
    "expression": "sympy.Expr",
    "matrix": "sympy.Matrix",
    "equation": "sympy.Eq",
    "set": "sympy.FiniteSet | sympy.Interval"
  }
}
```

### 2.5 Renderer Manifest Schema

```json
{
  "$schema": "mathide://renderer-manifest/v1",
  "id": "markdown_latex",
  "version": "0.1.0",
  "name": "Markdown + LaTeX",
  "file_extension": ".md",
  "entry_point": "renderers/markdown_latex.py",

  "features": {
    "math_delimiters": {"inline": "$...$", "display": "$$...$$"},
    "equation_labels": true,
    "collapsible_scripts": true,
    "cross_references": true
  },

  "template_dir": "renderers/templates/"
}
```

---

## 3. Master Index (Auto-Generated)

`registry/index.json` is rebuilt any time a manifest is added or changed. It is what the orchestrator actually loads.

```json
{
  "version": "0.1.0",
  "generated_at": "2026-04-06T17:00:00Z",

  "tools": {
    "series.expand":      {"manifest": "registry/tools/series.json",    "category": "analysis",      "tags": ["taylor", "laurent"]},
    "transform.fourier":  {"manifest": "registry/tools/transform.json", "category": "transforms",    "tags": ["fourier"]},
    "transform.laplace":  {"manifest": "registry/tools/transform.json", "category": "transforms",    "tags": ["laplace"]},
    "calculus.diff":      {"manifest": "registry/tools/calculus.json",  "category": "calculus",      "tags": ["derivative"]},
    "calculus.integrate":  {"manifest": "registry/tools/calculus.json",  "category": "calculus",      "tags": ["integral"]},
    "simplify":           {"manifest": "registry/tools/simplify.json",  "category": "algebra",       "tags": ["simplify"]},
    "linalg.eigenvalues": {"manifest": "registry/tools/linalg.json",   "category": "linear_algebra","tags": ["eigenvalue"]},
    "solve.equation":     {"manifest": "registry/tools/solve.json",    "category": "solvers",       "tags": ["solve"]},
    "solve.ode":          {"manifest": "registry/tools/solve.json",    "category": "solvers",       "tags": ["ode"]},
    "solve.pde":          {"manifest": "registry/tools/solve.json",    "category": "solvers",       "tags": ["pde"]},
    "workspace.store":    {"manifest": "registry/tools/workspace.json","category": "infrastructure", "tags": ["state"]},
    "workspace.load":     {"manifest": "registry/tools/workspace.json","category": "infrastructure", "tags": ["state"]},
    "assumptions.declare":{"manifest": "registry/tools/assumptions.json","category":"infrastructure","tags": ["assumptions"]},
    "verify.identity":    {"manifest": "registry/tools/verify.json",   "category": "verification",  "tags": ["check"]},
    "render.latex":       {"manifest": "registry/tools/render.json",   "category": "output",        "tags": ["latex"]},
    "compute.raw":        {"manifest": "registry/tools/compute.json",  "category": "general",       "tags": ["fallback"]}
  },

  "flows": {
    "fourier_analysis":   {"manifest": "registry/flows/fourier_analysis.json"},
    "ode_via_laplace":    {"manifest": "registry/flows/ode_via_laplace.json"},
    "parseval_verify":    {"manifest": "registry/flows/parseval_verify.json"}
  },

  "backends": {
    "sympy": {"manifest": "registry/backends/sympy.json"}
  },

  "renderers": {
    "markdown_latex": {"manifest": "registry/renderers/markdown_latex.json"}
  }
}
```

---

## 4. Tool Resolution: How the Orchestrator Finds Tools

The orchestrator does **not** have a hardcoded mapping of "user said X → call tool Y". Instead, it uses a resolution pipeline:

```
User utterance
      │
      ▼
┌─────────────────────────────────┐
│  1. Tag Match                   │  Search index tags for keyword overlap
│     "Taylor series" → ["taylor"]│  → candidates: [series.expand]
├─────────────────────────────────┤
│  2. Category Match              │  If ambiguous, narrow by category
│     "eigenvalues" → linalg.*   │
├─────────────────────────────────┤
│  3. Schema Fit                  │  Check if user-provided params match
│     input_schema of candidate   │  the tool's input_schema
├─────────────────────────────────┤
│  4. Backend Check               │  Confirm the required backend is available
│     tool.backend == "sympy" ✓   │
├─────────────────────────────────┤
│  5. Fallback                    │  No match? → compute.raw
│     General-purpose SymPy exec  │
└─────────────────────────────────┘
```

This means **adding a new tool** only requires:
1. Writing the Python script
2. Writing a manifest JSON
3. Running the index rebuild

No orchestrator code changes. No agent definition changes.

---

## 5. Flow Composition Engine

Flows are not opaque scripts. They are **declarative DAGs** that the orchestrator interprets step-by-step, giving Claude (and the mathematician) visibility and control at every node.

### 5.1 Step Execution Model

```
For each step in flow.steps:
  1. Resolve inputs (template variables, workspace refs)
  2. Load tool manifest by tool ID
  3. Validate inputs against tool.input_schema
  4. Execute tool via backend
  5. If store_as: save result to workspace
  6. If on_failure == "warn": log warning, continue
     If on_failure == "stop": halt flow, report to user
     If on_failure == "retry": adjust params, re-execute (max 2)
  7. Yield step result to orchestrator (Claude can narrate)
```

### 5.2 Flow Control Constructs

Flows support branching and conditionals for non-trivial pipelines:

```json
{
  "id": "conditional_example",
  "steps": [
    {
      "id": "try_closed_form",
      "tool": "calculus.integrate",
      "inputs": {"expr": "f", "variable": "x"},
      "store_as": "I"
    },
    {
      "id": "check_result",
      "type": "condition",
      "if": "I.has(Integral)",
      "then": "fallback_series",
      "else": "render_result"
    },
    {
      "id": "fallback_series",
      "tool": "series.expand",
      "inputs": {"expr": "f", "variable": "x", "order": 10},
      "store_as": "I_approx"
    },
    {
      "id": "render_result",
      "tool": "render.latex",
      "inputs": {"expr": "I"}
    }
  ]
}
```

### 5.3 Parallel Steps

Independent steps can declare parallel execution:

```json
{
  "id": "parallel_energies",
  "type": "parallel",
  "steps": ["energy_time", "energy_freq"]
}
```

### 5.4 User Intervention Points

A step can pause and ask the mathematician before continuing:

```json
{
  "id": "choose_method",
  "type": "user_choice",
  "prompt": "The integral has multiple evaluation paths. Prefer: (a) residue calculus, (b) Meijer-G?",
  "options": {
    "a": {"set": {"method": "residues"}},
    "b": {"set": {"method": "meijerg"}}
  }
}
```

---

## 6. Adding a New Tool (Contributor Guide)

### Step-by-step

```
1.  Create tool script
      tools/<category>/<operation>.py
      Must read JSON stdin, write JSON stdout, use lib/ helpers.

2.  Write manifest
      registry/tools/<category>.json
      Define id, input_schema, output_schema, tags, examples.

3.  Rebuild index
      python scripts/rebuild_index.py
      Validates all manifests, regenerates registry/index.json.

4.  (Optional) Add to a flow
      Edit or create a flow manifest referencing the new tool id.

5.  Done. The orchestrator discovers it on next invocation.
```

### Example: Adding a "Residue" Tool

```
tools/complex_analysis/residue.py    ← new script
registry/tools/complex_analysis.json ← new manifest:
```

```json
{
  "$schema": "mathide://tool-manifest/v1",
  "id": "complex.residue",
  "version": "0.1.0",
  "name": "Residue Computation",
  "category": "complex_analysis",
  "tags": ["residue", "pole", "contour", "laurent"],
  "description": "Compute the residue of a function at a given pole.",
  "when_to_use": "User asks for residue, pole analysis, or contour integral evaluation.",
  "backend": "sympy",
  "entry_point": "tools/complex_analysis/residue.py",
  "input_schema": {
    "type": "object",
    "required": ["expr", "variable", "point"],
    "properties": {
      "expr":     {"type": "string"},
      "variable": {"type": "string"},
      "point":    {"type": "string", "description": "Location of the pole"}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "result": {"type": "string"},
      "latex":  {"type": "string"},
      "pole_order": {"type": "integer"},
      "success": {"type": "boolean"}
    }
  }
}
```

Run `python scripts/rebuild_index.py` → the orchestrator now knows about `complex.residue`.

---

## 7. Adding a New Backend (Future-Proofing)

When SymPy can't handle something (e.g. tensor algebra, advanced group theory), a new backend slots in:

```
1.  Write backend adapter
      backends/<name>/adapter.py
      Must implement: execute(code, timeout) → result dict

2.  Write backend manifest
      registry/backends/<name>.json

3.  Tag tools that use this backend
      In tool manifest: "backend": "<name>"

4.  The sandbox, timeout, and type_mapping are read from
    the backend manifest — no hardcoding.
```

**Future backend candidates:**

| Backend | Strength | Use case |
|---------|----------|----------|
| SageMath | Algebraic geometry, number theory | When SymPy's algebra falls short |
| Maxima | Classical CAS, definite integrals | Alternative integration engine |
| Cadabra | Tensor algebra, field theory | Physics-oriented symbolic math |
| GAP | Computational group theory | Abstract algebra |
| FriCAS | Advanced special functions | When SymPy's special functions fail |

---

## 8. Adding a New Renderer (Future-Proofing)

```
1.  Write renderer
      renderers/<name>/render.py
      Must accept: list of step results + metadata → output file

2.  Write manifest
      registry/renderers/<name>.json

3.  Flows reference renderers by ID in their output block.
```

**Future renderer candidates:**

| Renderer | Output | Use case |
|----------|--------|----------|
| `jupyter` | `.ipynb` | Interactive notebooks with executable cells |
| `typst` | `.pdf` via Typst | Publication-quality PDFs |
| `html_katex` | `.html` | Browser-viewable with live KaTeX |
| `beamer` | `.tex` | Presentation slides |

---

## 9. Workspace Architecture (Revisited)

The workspace is no longer a flat JSON file. It is a **versioned symbolic environment**:

```
workspace/
├── state.json              # Current symbol table + expression store
├── sessions/
│   ├── 2026-04-06_001.json # Snapshot per session
│   └── ...
└── exports/
    └── session_001.py      # Reproducible Python export
```

### state.json structure

```json
{
  "schema_version": "1",
  "symbols": {
    "x": {"assumptions": ["real"], "declared_at": "step_001"},
    "k": {"assumptions": ["real", "positive"], "declared_at": "step_002"}
  },
  "expressions": {
    "f": {
      "srepr": "Mul(sin(Symbol('x')), Pow(Add(Integer(1), Mul(Integer(-1), Symbol('x'))), Integer(-1)))",
      "latex": "\\frac{\\sin x}{1 - x}",
      "source_tool": "workspace.store",
      "source_step": "step_001",
      "depends_on": []
    },
    "f_series": {
      "srepr": "...",
      "latex": "...",
      "source_tool": "series.expand",
      "source_step": "step_003",
      "depends_on": ["f"]
    }
  },
  "history": [
    {"id": "step_001", "tool": "workspace.store", "name": "f", "timestamp": "..."},
    {"id": "step_002", "tool": "assumptions.declare", "timestamp": "..."},
    {"id": "step_003", "tool": "series.expand", "result": "f_series", "timestamp": "..."}
  ]
}
```

Key additions over the flat model:
- **`depends_on`** — tracks which expressions were inputs, enabling dependency graphs and cache invalidation
- **`source_tool` / `source_step`** — full provenance for every expression
- **`schema_version`** — forward-compatible migrations
- **Session snapshots** — rewind to any prior state

---

## 10. Revised File Structure

```
Math IDE/
├── CLAUDE.md                      # Project instructions for Claude Code
├── DESIGN.md                      # High-level concept
├── ARCHITECTURE.md                # This document
├── TOOLS.md                       # Tool specifications (I/O contracts)
│
├── registry/                      # Plugin registry (all JSON manifests)
│   ├── index.json                 #   Auto-generated master index
│   ├── tools/                     #   Tool manifests
│   ├── flows/                     #   Flow manifests
│   ├── backends/                  #   Backend manifests
│   └── renderers/                 #   Renderer manifests
│
├── tools/                         # Tool implementations (Python scripts)
│   ├── lib/                       #   Shared library
│   │   ├── io_contract.py
│   │   ├── sandbox.py
│   │   ├── workspace.py
│   │   └── registry.py            #   Registry loader & tool resolver
│   ├── series/
│   │   └── expand.py
│   ├── calculus/
│   │   ├── differentiate.py
│   │   └── integrate.py
│   ├── transforms/
│   │   └── transform.py
│   ├── solvers/
│   │   ├── equation.py
│   │   ├── ode.py
│   │   └── pde.py
│   ├── algebra/
│   │   ├── simplify.py
│   │   └── substitute.py
│   ├── linalg/
│   │   └── matrix_ops.py
│   ├── infrastructure/
│   │   ├── workspace_manager.py
│   │   ├── assumption_manager.py
│   │   └── verify.py
│   └── output/
│       └── latex_render.py
│
├── backends/                      # Backend adapters
│   └── sympy/
│       └── adapter.py
│
├── renderers/                     # Output renderers
│   └── markdown_latex/
│       ├── render.py
│       └── templates/
│           └── research_note.md.j2
│
├── flows/                         # Flow engine
│   └── engine.py                  #   Interprets flow manifests
│
├── scripts/                       # Maintenance scripts
│   ├── rebuild_index.py           #   Regenerate registry/index.json
│   ├── validate_manifests.py      #   Check all manifests against schemas
│   └── new_tool.py                #   Scaffold a new tool (manifest + script)
│
├── agents/                        # Claude Code agent definitions
│   ├── math-planner.md
│   ├── sympy-runner.md
│   └── md-writer.md
│
├── workspace/                     # Runtime state
│   ├── state.json
│   ├── sessions/
│   └── exports/
│
└── research_notes/                # Generated output
    └── (*.md files)
```

---

## 11. Extension Scenarios

To show this isn't theoretical, here's how specific future features map onto the plugin system:

| Future feature | What to add | What changes |
|---|---|---|
| **Tensor algebra** | `backends/cadabra/`, tool manifests for `tensor.*` | Nothing in core |
| **Notebook export** | `renderers/jupyter/`, renderer manifest | Nothing in core |
| **Contour integration** | `tools/complex_analysis/contour.py` + manifest | Nothing in core |
| **Group theory** | `backends/gap/`, tool manifests for `group.*` | Nothing in core |
| **Diagrammatic output** | New renderer `tikz_commutative` | Nothing in core |
| **Custom user tools** | User drops `.py` + `.json` in `tools/` and `registry/` | Rebuild index |
| **Pade approximants** | `tools/series/pade.py` + add to `series.json` manifest | Nothing in core |
| **Lie algebra** | `tools/algebra/lie.py` + manifest | Nothing in core |

The pattern: **write script, write manifest, rebuild index. No core code touched.**

---

## 12. Design Constraints

1. **Tools are stateless.** All state flows through workspace. A tool receives inputs, returns outputs, never reads global mutable state directly.

2. **Manifests are the source of truth.** The orchestrator, the planner agent, and the index generator all read manifests. There is no second place where tool metadata lives.

3. **Backwards-compatible schemas.** Manifests carry a `$schema` version. The registry loader handles version differences. Adding fields is fine; removing fields requires a schema version bump.

4. **The fallback is always available.** `compute.raw` (general SymPy execution) ensures no user request is blocked by a missing specialized tool. Specialized tools exist for better UX, not as gatekeepers.

5. **Flows are optional.** The orchestrator can always run tools ad-hoc from chat. Flows are a convenience for known multi-step patterns, not a requirement.

6. **One backend per tool.** A tool targets exactly one backend. If the same operation exists in two backends (e.g. integration in SymPy vs Maxima), they are two separate tools with distinct IDs that the planner can choose between.
