"""
Partial differential equation solver (transform method).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, store_expr, make_symbols
from sympy import (
    Symbol, Function, Eq, latex, sympify, simplify, symbols,
    fourier_transform, inverse_fourier_transform,
    laplace_transform, inverse_laplace_transform,
    dsolve, classify_ode, exp, oo, Integral
)


@tool_main
def main(data: dict) -> dict:
    equation_str = data.get("equation")
    func_str = data.get("function", "u(x,t)")
    conditions = data.get("conditions", {})
    domain = data.get("domain", {})
    method = data.get("method", "fourier")
    store_as = data.get("store_as")

    if not equation_str:
        write_error("'equation' is required", code="PARSE_ERROR")

    state = load_state()
    syms = make_symbols(state)

    # Parse function and variables
    func_name = func_str.split("(")[0].strip()
    vars_str = func_str.split("(")[1].rstrip(")").strip()
    var_names = [v.strip() for v in vars_str.split(",")]

    var_syms = [syms.get(v, Symbol(v)) for v in var_names]
    u = Function(func_name)

    # For PDE solving, we use the general sympy_compute approach
    # since SymPy's PDE support is limited — we compose transforms manually
    #
    # This tool generates the step-by-step transform method and executes it.

    method_steps = []

    if method == "fourier":
        if len(var_names) < 2:
            write_error("Fourier method needs at least 2 variables", code="METHOD_NOT_APPLICABLE")

        spatial_var = var_syms[0]  # x
        time_var = var_syms[1]     # t
        freq_var = Symbol('k', real=True)

        method_steps.append(f"Apply Fourier transform in {var_names[0]}")
        method_steps.append(f"Solve resulting ODE in {var_names[1]}")
        method_steps.append(f"Apply inverse Fourier transform to recover solution")

    elif method == "laplace":
        if len(var_names) < 2:
            write_error("Laplace method needs at least 2 variables", code="METHOD_NOT_APPLICABLE")

        method_steps.append(f"Apply Laplace transform in {var_names[1]}")
        method_steps.append(f"Solve resulting ODE in {var_names[0]}")
        method_steps.append(f"Apply inverse Laplace transform")

    elif method == "separation":
        method_steps.append("Assume separable solution u = X(x)*T(t)")
        method_steps.append("Substitute and separate variables")
        method_steps.append("Solve each ODE independently")
        method_steps.append("Combine with superposition")

    # Since full automated PDE solving is beyond SymPy's current capabilities
    # for most cases, we provide the method outline and delegate to sympy_compute
    # for the actual step-by-step execution.

    output = {
        "method": method,
        "method_steps": method_steps,
        "variables": var_names,
        "function": func_str,
        "note": "PDE solving requires step-by-step execution via the flow engine or sympy_compute tool.",
    }

    return output


if __name__ == "__main__":
    main()
