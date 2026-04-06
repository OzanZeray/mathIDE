"""
Variable substitution tool.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, resolve_expr, store_expr, make_symbols
from sympy import Symbol, latex, sympify, simplify


@tool_main
def main(data: dict) -> dict:
    expr_str = data.get("expr")
    substitutions = data.get("substitutions", {})
    evaluate = data.get("evaluate", True)
    simplify_result = data.get("simplify", False)
    store_as = data.get("store_as")

    if not expr_str:
        write_error("'expr' is required", code="PARSE_ERROR")
    if not substitutions:
        write_error("'substitutions' dict is required", code="PARSE_ERROR")

    state = load_state()
    syms = make_symbols(state)
    expr = resolve_expr(expr_str, state)

    # Build substitution dict: {Symbol: expression}
    subs_dict = {}
    for var_name, val_str in substitutions.items():
        var_sym = syms.get(var_name, Symbol(var_name))
        val_expr = resolve_expr(str(val_str), state)
        subs_dict[var_sym] = val_expr

    if evaluate:
        result = expr.subs(subs_dict)
    else:
        result = expr.subs(subs_dict, simultaneous=True)

    if simplify_result:
        result = simplify(result)

    result_str = str(result)
    result_latex = latex(result)

    if store_as:
        depends = [expr_str] if expr_str in state.get("expressions", {}) else []
        store_expr(store_as, result, state,
                   source_tool="algebra.substitute", depends_on=depends)

    return {
        "result": result_str,
        "latex": result_latex,
        "substitutions_applied": {k: str(v) for k, v in subs_dict.items()},
    }


if __name__ == "__main__":
    main()
