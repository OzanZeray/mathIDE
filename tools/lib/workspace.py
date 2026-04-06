"""
Workspace state management.

Handles reading/writing the symbolic workspace (workspace/state.json),
resolving expression references, and tracking provenance.
"""
import json
import time
from pathlib import Path
from sympy import sympify, srepr, latex

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace"
STATE_PATH = WORKSPACE_DIR / "state.json"

EMPTY_STATE = {
    "schema_version": "1",
    "symbols": {},
    "expressions": {},
    "history": [],
}


def load_state() -> dict:
    """Load current workspace state."""
    if not STATE_PATH.exists():
        return json.loads(json.dumps(EMPTY_STATE))
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict):
    """Persist workspace state to disk."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def resolve_expr(name_or_expr: str, state: dict = None):
    """Resolve a string to a SymPy expression.

    If name_or_expr matches a workspace key, return that stored expression.
    Otherwise parse it as a SymPy expression string.
    """
    if state is None:
        state = load_state()
    if name_or_expr in state.get("expressions", {}):
        entry = state["expressions"][name_or_expr]
        expr_str = entry["srepr"] if isinstance(entry, dict) else entry
        return sympify(expr_str)
    return sympify(name_or_expr)


def store_expr(name: str, expr, state: dict = None,
               source_tool: str = None, source_step: str = None,
               depends_on: list = None):
    """Store a named expression in the workspace.

    Args:
        name: Variable name to store under.
        expr: SymPy expression (or string to sympify).
        state: Workspace state dict (loaded if None).
        source_tool: Tool ID that produced this expression.
        source_step: Step ID in the current flow.
        depends_on: List of workspace names this expression depends on.

    Returns:
        Updated state dict.
    """
    if state is None:
        state = load_state()

    if isinstance(expr, str):
        expr = sympify(expr)

    state["expressions"][name] = {
        "srepr": srepr(expr),
        "latex": latex(expr),
        "source_tool": source_tool,
        "source_step": source_step,
        "depends_on": depends_on or [],
    }

    state["history"].append({
        "action": "store",
        "name": name,
        "tool": source_tool,
        "latex": latex(expr),
        "timestamp": time.time(),
    })

    save_state(state)
    return state


def get_symbols(state: dict = None) -> dict:
    """Get all declared symbols and their assumptions."""
    if state is None:
        state = load_state()
    return state.get("symbols", {})


def declare_symbols(symbols: dict, state: dict = None) -> dict:
    """Declare symbols with assumptions.

    Args:
        symbols: Dict of {name: [assumption1, assumption2, ...]}.
        state: Workspace state dict.

    Returns:
        Updated state dict.
    """
    if state is None:
        state = load_state()

    for name, assumptions in symbols.items():
        state["symbols"][name] = {
            "assumptions": assumptions,
        }

    state["history"].append({
        "action": "declare_symbols",
        "symbols": symbols,
        "timestamp": time.time(),
    })

    save_state(state)
    return state


def build_symbol_kwargs(state: dict = None) -> dict:
    """Build SymPy Symbol keyword arguments from workspace assumptions.

    Returns dict like: {"x": {"real": True}, "n": {"integer": True, "positive": True}}
    """
    if state is None:
        state = load_state()
    result = {}
    for name, info in state.get("symbols", {}).items():
        kwargs = {}
        for assumption in info.get("assumptions", []):
            kwargs[assumption] = True
        result[name] = kwargs
    return result


def make_symbols(state: dict = None) -> dict:
    """Create SymPy Symbol objects from workspace declarations.

    Returns dict of {name: Symbol(name, **assumptions)}.
    """
    from sympy import Symbol
    sym_kwargs = build_symbol_kwargs(state)
    return {name: Symbol(name, **kwargs) for name, kwargs in sym_kwargs.items()}
