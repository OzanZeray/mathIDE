"""
General-purpose SymPy computation tool.

The fallback tool — executes arbitrary SymPy code in a sandbox
when no specialized tool fits the request.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.sandbox import execute_sympy
from lib.workspace import load_state, resolve_expr, store_expr
from sympy import latex, srepr


@tool_main
def main(data: dict) -> dict:
    code = data.get("code", "")
    if not code:
        write_error("No code provided", code="PARSE_ERROR")

    workspace_vars = data.get("workspace_vars", {})
    timeout = data.get("timeout", 30)
    store_as = data.get("store_as")

    # Resolve workspace references in vars
    state = load_state()
    resolved_vars = {}
    for k, v in workspace_vars.items():
        resolved_vars[k] = resolve_expr(v, state)

    ns = execute_sympy(code, timeout=timeout, extra_vars=resolved_vars)

    # Look for a 'result' variable in the namespace
    result_expr = ns.get("result")
    if result_expr is None:
        # Return all computed variables
        output = {"variables": {}}
        for k, v in ns.items():
            try:
                output["variables"][k] = {
                    "value": str(v),
                    "latex": latex(v),
                }
            except Exception:
                output["variables"][k] = {"value": str(v)}
        return output

    result_str = str(result_expr)
    result_latex = latex(result_expr)

    if store_as:
        store_expr(store_as, result_expr, state, source_tool="compute.raw")

    return {
        "result": result_str,
        "latex": result_latex,
        "type": type(result_expr).__name__,
    }


if __name__ == "__main__":
    main()
