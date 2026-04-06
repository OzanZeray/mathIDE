"""
Differentiation tool.

Supports: ordinary, partial, nth-order, mixed partial derivatives.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, resolve_expr, store_expr, make_symbols
from sympy import Symbol, diff, Derivative, latex, simplify


@tool_main
def main(data: dict) -> dict:
    expr_str = data.get("expr")
    variable = data.get("variable", "x")
    order = data.get("order", 1)
    variables = data.get("variables")  # for mixed partials: ["x", "x", "y"]
    simplify_result = data.get("simplify", True)
    store_as = data.get("store_as")

    if not expr_str:
        write_error("'expr' is required", code="PARSE_ERROR")

    state = load_state()
    syms = make_symbols(state)
    expr = resolve_expr(expr_str, state)

    if variables:
        # Mixed partial: diff with respect to each variable in order
        diff_args = []
        for v in variables:
            sym = syms.get(v, Symbol(v))
            diff_args.append(sym)
        result = diff(expr, *diff_args)
    else:
        var = syms.get(variable, Symbol(variable))
        result = diff(expr, var, order)

    if simplify_result:
        result = simplify(result)

    result_str = str(result)
    result_latex = latex(result)

    if store_as:
        depends = [expr_str] if expr_str in state.get("expressions", {}) else []
        store_expr(store_as, result, state,
                   source_tool="calculus.diff", depends_on=depends)

    return {
        "result": result_str,
        "latex": result_latex,
        "variable": variable if not variables else variables,
        "order": order if not variables else len(variables),
    }


if __name__ == "__main__":
    main()
