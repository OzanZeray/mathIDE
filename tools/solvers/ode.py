"""
Ordinary differential equation solver.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, store_expr, make_symbols
from sympy import (
    Symbol, Function, Eq, dsolve, classify_ode,
    latex, sympify, symbols
)


@tool_main
def main(data: dict) -> dict:
    equation_str = data.get("equation")
    func_str = data.get("function", "f(x)")
    conditions = data.get("conditions", {})
    method = data.get("method", "auto")
    store_as = data.get("store_as")

    if not equation_str:
        write_error("'equation' is required", code="PARSE_ERROR")

    state = load_state()
    syms = make_symbols(state)

    # Parse function name and variable
    # e.g. "f(x)" → Function('f'), Symbol('x')
    func_name = func_str.split("(")[0].strip()
    var_name = func_str.split("(")[1].rstrip(")").strip()

    var = syms.get(var_name, Symbol(var_name))
    f = Function(func_name)

    # Build local namespace for parsing
    local_ns = dict(syms)
    local_ns[var_name] = var
    local_ns[func_name] = f

    # Parse the equation
    # Support both "expr" (meaning expr = 0) and "Eq(lhs, rhs)" forms
    eq_str = equation_str.replace(f"{func_name}({var_name})", f"{func_name}({var_name})")
    eq_expr = sympify(eq_str, locals=local_ns)

    if not isinstance(eq_expr, Eq):
        eq_expr = Eq(eq_expr, 0)

    # Classify
    classification = classify_ode(eq_expr, f(var))

    # Solve
    hint = method if method != "auto" else None
    if hint:
        sol = dsolve(eq_expr, f(var), hint=hint)
    else:
        sol = dsolve(eq_expr, f(var))

    general_solution = sol

    # Apply initial/boundary conditions
    particular = None
    if conditions:
        ics = {}
        for cond_str, val_str in conditions.items():
            cond_val = sympify(val_str)
            # Parse conditions like "f(0)" → {f(0): value}
            cond_expr = sympify(cond_str, locals=local_ns)
            ics[cond_expr] = cond_val
        if ics:
            try:
                particular = dsolve(eq_expr, f(var), ics=ics)
            except Exception:
                particular = None

    output = {
        "general_solution": str(general_solution.rhs if isinstance(general_solution, Eq) else general_solution),
        "general_latex": latex(general_solution.rhs if isinstance(general_solution, Eq) else general_solution),
        "classification": list(classification) if isinstance(classification, tuple) else str(classification),
    }

    if particular:
        output["particular_solution"] = str(particular.rhs if isinstance(particular, Eq) else particular)
        output["particular_latex"] = latex(particular.rhs if isinstance(particular, Eq) else particular)

    if store_as:
        result_expr = particular.rhs if particular and isinstance(particular, Eq) else general_solution.rhs if isinstance(general_solution, Eq) else general_solution
        store_expr(store_as, result_expr, state, source_tool="solve.ode")

    return output


if __name__ == "__main__":
    main()
