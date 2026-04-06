"""
Integration tool.

Supports: definite, indefinite, with method hints.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, resolve_expr, store_expr, make_symbols
from sympy import (
    Symbol, integrate, Integral, latex, simplify, sympify,
    oo, zoo, nan, S
)


@tool_main
def main(data: dict) -> dict:
    expr_str = data.get("expr")
    variable = data.get("variable", "x")
    limits = data.get("limits")  # [lower, upper] or None for indefinite
    method = data.get("method", "auto")
    simplify_result = data.get("simplify", True)
    store_as = data.get("store_as")
    assumptions = data.get("assumptions", {})

    if not expr_str:
        write_error("'expr' is required", code="PARSE_ERROR")

    state = load_state()
    syms = make_symbols(state)
    expr = resolve_expr(expr_str, state)
    var = syms.get(variable, Symbol(variable))

    kwargs = {}
    if method == "meijerg":
        kwargs["meijerg"] = True
    elif method == "risch":
        kwargs["risch"] = True
    elif method == "manual":
        kwargs["manual"] = True

    if limits:
        lower = sympify(limits[0])
        upper = sympify(limits[1])
        result = integrate(expr, (var, lower, upper), **kwargs)
        is_definite = True
    else:
        result = integrate(expr, var, **kwargs)
        is_definite = False

    # Check if integration succeeded
    has_unevaluated = result.has(Integral)

    if simplify_result and not has_unevaluated:
        result = simplify(result)

    # Check convergence for definite integrals
    converges = None
    if is_definite:
        converges = result not in (oo, -oo, zoo, nan, S.NaN)

    result_str = str(result)
    result_latex = latex(result)

    if store_as:
        depends = [expr_str] if expr_str in state.get("expressions", {}) else []
        store_expr(store_as, result, state,
                   source_tool="calculus.integrate", depends_on=depends)

    output = {
        "result": result_str,
        "latex": result_latex,
        "definite": is_definite,
        "has_unevaluated_integral": has_unevaluated,
    }
    if method != "auto":
        output["method_used"] = method
    if converges is not None:
        output["converges"] = converges

    return output


if __name__ == "__main__":
    main()
