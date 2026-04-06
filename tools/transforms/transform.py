"""
Integral transform tool.

Supports: Fourier, inverse Fourier, Laplace, inverse Laplace, Mellin, inverse Mellin.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, resolve_expr, store_expr, make_symbols, declare_symbols
from sympy import (
    Symbol, latex, simplify,
    fourier_transform, inverse_fourier_transform,
    laplace_transform, inverse_laplace_transform,
    mellin_transform, inverse_mellin_transform,
)

TRANSFORMS = {
    "fourier":       fourier_transform,
    "inv_fourier":   inverse_fourier_transform,
    "laplace":       laplace_transform,
    "inv_laplace":   inverse_laplace_transform,
    "mellin":        mellin_transform,
    "inv_mellin":    inverse_mellin_transform,
}


@tool_main
def main(data: dict) -> dict:
    expr_str = data.get("expr")
    transform = data.get("transform", "fourier")
    input_var = data.get("input_var", "t")
    output_var = data.get("output_var", "s")
    simplify_result = data.get("simplify", True)
    store_as = data.get("store_as")
    assumptions = data.get("assumptions", {})

    if not expr_str:
        write_error("'expr' is required", code="PARSE_ERROR")
    if transform not in TRANSFORMS:
        write_error(
            f"Unknown transform: {transform}. Available: {list(TRANSFORMS.keys())}",
            code="METHOD_NOT_APPLICABLE"
        )

    state = load_state()

    # Declare any provided assumptions
    if assumptions:
        state = declare_symbols(assumptions, state)

    syms = make_symbols(state)
    expr = resolve_expr(expr_str, state)
    in_var = syms.get(input_var, Symbol(input_var))
    out_var = syms.get(output_var, Symbol(output_var))

    transform_fn = TRANSFORMS[transform]
    raw_result = transform_fn(expr, in_var, out_var)

    # Some transforms return (result, convergence_condition, ...)
    convergence = None
    if isinstance(raw_result, tuple):
        result = raw_result[0]
        if len(raw_result) > 1:
            convergence = str(raw_result[1])
    else:
        result = raw_result

    if simplify_result:
        result = simplify(result)

    result_str = str(result)
    result_latex = latex(result)

    if store_as:
        depends = [expr_str] if expr_str in state.get("expressions", {}) else []
        store_expr(store_as, result, state,
                   source_tool=f"transform.{transform}", depends_on=depends)

    output = {
        "result": result_str,
        "latex": result_latex,
        "transform": transform,
        "input_var": input_var,
        "output_var": output_var,
    }
    if convergence:
        output["convergence"] = convergence

    return output


if __name__ == "__main__":
    main()
