"""
Series expansion tool.

Supports: Taylor, Laurent, Puiseux, asymptotic, formal power series.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, resolve_expr, store_expr, make_symbols
from sympy import (
    Symbol, series, fps, latex, O, oo, Rational,
    Add, Mul, Pow, sympify, collect
)


@tool_main
def main(data: dict) -> dict:
    expr_str = data.get("expr")
    variable = data.get("variable", "x")
    point = data.get("point", "0")
    order = data.get("order", 6)
    kind = data.get("kind", "taylor")
    store_as = data.get("store_as")

    if not expr_str:
        write_error("'expr' is required", code="PARSE_ERROR")

    state = load_state()
    syms = make_symbols(state)
    var = syms.get(variable, Symbol(variable))
    expr = resolve_expr(expr_str, state)
    pt = sympify(point)

    if kind == "taylor" or kind == "laurent":
        result = series(expr, var, pt, n=order + 1)
        truncated = result.removeO()
        remainder = f"O({var}^{order + 1})"

        # Extract term coefficients
        terms = {}
        if pt == 0:
            for i in range(order + 1):
                coeff = truncated.coeff(var, i)
                if coeff != 0:
                    terms[str(i)] = str(coeff)
        else:
            shifted = var - pt
            for i in range(order + 1):
                coeff = truncated.coeff(shifted, i)
                if coeff != 0:
                    terms[str(i)] = str(coeff)

    elif kind == "asymptotic":
        result = series(expr, var, oo, n=order + 1)
        truncated = result.removeO()
        remainder = f"O(1/{var}^{order + 1})"
        terms = {}

    elif kind == "formal_power":
        result = fps(expr, var)
        truncated = result.truncate(order + 1)
        remainder = "..."
        terms = {}

    elif kind == "puiseux":
        # SymPy series handles Puiseux (fractional powers) automatically
        result = series(expr, var, pt, n=order + 1)
        truncated = result.removeO()
        remainder = f"O({var}^{order + 1})"
        terms = {}

    else:
        write_error(f"Unknown series kind: {kind}", code="METHOD_NOT_APPLICABLE")

    result_str = str(truncated)
    result_latex = latex(truncated)

    if store_as:
        store_expr(store_as, truncated, state,
                   source_tool="series.expand",
                   depends_on=[expr_str] if expr_str in state.get("expressions", {}) else [])

    return {
        "result": result_str,
        "latex": result_latex,
        "terms": terms,
        "remainder": remainder,
        "kind": kind,
        "point": str(pt),
        "order": order,
    }


if __name__ == "__main__":
    main()
