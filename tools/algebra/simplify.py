"""
Simplification tool with strategy selection.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, resolve_expr, store_expr, make_symbols
from sympy import (
    Symbol, latex, simplify, trigsimp, powsimp,
    collect, factor, apart, cancel, radsimp, expand,
    fu, sympify
)

STRATEGIES = {
    "auto":    simplify,
    "trig":    trigsimp,
    "power":   powsimp,
    "factor":  factor,
    "apart":   apart,
    "cancel":  cancel,
    "radsimp": radsimp,
    "expand":  expand,
    "fu":      fu,
}


@tool_main
def main(data: dict) -> dict:
    expr_str = data.get("expr")
    strategy = data.get("strategy", "auto")
    collect_var = data.get("collect_var")
    target_form = data.get("target_form")
    store_as = data.get("store_as")

    if not expr_str:
        write_error("'expr' is required", code="PARSE_ERROR")

    state = load_state()
    syms = make_symbols(state)
    expr = resolve_expr(expr_str, state)

    # Handle target_form as shortcut for strategy
    if target_form:
        form_map = {
            "factored": "factor",
            "expanded": "expand",
            "partial_fractions": "apart",
        }
        strategy = form_map.get(target_form, strategy)

    # Special case: collect
    if strategy == "collect" or collect_var:
        if collect_var:
            var = syms.get(collect_var, Symbol(collect_var))
            result = collect(expr, var)
        else:
            write_error("'collect_var' required for collect strategy", code="PARSE_ERROR")
    elif strategy in STRATEGIES:
        result = STRATEGIES[strategy](expr)
    else:
        write_error(
            f"Unknown strategy: {strategy}. Available: {list(STRATEGIES.keys()) + ['collect']}",
            code="METHOD_NOT_APPLICABLE"
        )

    result_str = str(result)
    result_latex = latex(result)

    if store_as:
        depends = [expr_str] if expr_str in state.get("expressions", {}) else []
        store_expr(store_as, result, state,
                   source_tool="simplify", depends_on=depends)

    return {
        "result": result_str,
        "latex": result_latex,
        "strategy_used": strategy,
    }


if __name__ == "__main__":
    main()
