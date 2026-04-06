# Math IDE — Claude Code Project Instructions

## What This Project Is

Math IDE is an **analytic symbolic mathematics research tool**. A mathematician uses Claude Code as a conversational interface to perform symbolic computations — series expansions, integral transforms, differential equations, simplifications — with all work documented in Markdown with LaTeX.

**Everything is symbolic. No numeric evaluation. No floating point. No approximations.**

## Architecture

- **Plugin registry** at `registry/` — tools, flows, backends, renderers are discovered from JSON manifests
- **Tools** at `tools/` — Python/SymPy scripts with JSON stdin/stdout contract
- **Workspace** at `workspace/state.json` — persistent symbolic state across turns
- **Research notes** at `research_notes/` — generated Markdown output

## How to Run Tools

Each tool reads JSON from stdin and writes JSON to stdout:

```bash
echo '{"expr": "sin(x)/(1-x)", "variable": "x", "order": 6}' | python tools/series/expand.py
```

Check `"success": true` in output before using the result.

## Tool Quick Reference

| Operation | Script | Key Inputs |
|-----------|--------|------------|
| Series expansion | `tools/series/expand.py` | expr, variable, order, kind |
| Differentiate | `tools/calculus/differentiate.py` | expr, variable, order |
| Integrate | `tools/calculus/integrate.py` | expr, variable, limits |
| Transform | `tools/transforms/transform.py` | expr, transform, input_var, output_var |
| Solve equation | `tools/solvers/equation.py` | equations, variables, domain |
| Solve ODE | `tools/solvers/ode.py` | equation, function, conditions |
| Simplify | `tools/algebra/simplify.py` | expr, strategy |
| Substitute | `tools/algebra/substitute.py` | expr, substitutions |
| Matrix ops | `tools/linalg/matrix_ops.py` | matrix, operation |
| Workspace | `tools/infrastructure/workspace_manager.py` | action, name, expr |
| Assumptions | `tools/infrastructure/assumption_manager.py` | action, symbols |
| Verify | `tools/infrastructure/verify.py` | claim or lhs+rhs, method |
| LaTeX render | `tools/output/latex_render.py` | expr, style |
| Raw compute | `tools/infrastructure/sympy_compute.py` | code |

## Workflow

When the mathematician asks for a computation:

1. **Plan** — Decompose into tool calls. Identify needed assumptions.
2. **Declare assumptions** — Use assumption_manager before any computation that depends on symbol properties.
3. **Execute** — Run tools step by step, storing results in workspace with `store_as`.
4. **Verify** — Check critical results with the verify tool.
5. **Write up** — Present results in Markdown with `$$LaTeX$$`, explain each step.
6. **Save** — Write research note to `research_notes/` for significant derivations.

## Rules

- **NEVER use float(), N(), evalf(), or any numeric evaluation**
- **ALWAYS store intermediate results** in the workspace if they'll be referenced again
- **ALWAYS declare symbol assumptions** before computations that depend on them
- **Use display math** (`$$...$$`) for important results, inline (`$...$`) for references in prose
- **Verify non-trivial results** — at minimum, a simplify(LHS - RHS) == 0 check
- When a tool fails, diagnose and retry with adjusted parameters before falling back to `compute.raw`
- The workspace persists across turns — check what's already defined before re-computing

## Extending the System

To add a new tool:
1. Write Python script in `tools/<category>/`
2. Add manifest entry in `registry/tools/`
3. Run `python scripts/rebuild_index.py`

See `ARCHITECTURE.md` for the full plugin system documentation.
