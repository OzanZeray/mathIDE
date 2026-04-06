"""
Symbolic equation solver.

Supports: single equations, systems, with domain constraints.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, resolve_expr, store_expr, make_symbols
from sympy import (
    Symbol, solve, solveset, latex, sympify,
    S, Eq, FiniteSet, Reals, Complexes, Integers,
)

DOMAINS = {
    "real": Reals,
    "complex": Complexes,
    "integer": Integers,
}


@tool_main
def main(data: dict) -> dict:
    equations = data.get("equations", [])
    variables = data.get("variables", [])
    domain = data.get("domain", "complex")
    method = data.get("method", "auto")
    store_as = data.get("store_as")

    if not equations:
        write_error("'equations' list is required", code="PARSE_ERROR")

    state = load_state()
    syms = make_symbols(state)

    # Parse equations
    parsed_eqs = []
    for eq_str in equations:
        eq_expr = resolve_expr(eq_str, state)
        parsed_eqs.append(eq_expr)

    # Parse variables to solve for
    solve_vars = []
    for v in variables:
        solve_vars.append(syms.get(v, Symbol(v)))

    # If no variables specified, let SymPy figure it out
    if not solve_vars:
        all_free = set()
        for eq in parsed_eqs:
            all_free |= eq.free_symbols
        solve_vars = sorted(list(all_free), key=str)

    # Single equation + single variable → use solveset for richer output
    if len(parsed_eqs) == 1 and len(solve_vars) == 1 and domain in DOMAINS:
        result_set = solveset(parsed_eqs[0], solve_vars[0], domain=DOMAINS[domain])
        solutions = []
        if isinstance(result_set, FiniteSet):
            solutions = [str(s) for s in result_set]
        else:
            solutions = [str(result_set)]
        latex_solutions = []
        if isinstance(result_set, FiniteSet):
            latex_solutions = [latex(s) for s in result_set]
        else:
            latex_solutions = [latex(result_set)]
    else:
        # System or fallback
        raw = solve(parsed_eqs, solve_vars, dict=True)
        if isinstance(raw, list):
            solutions = [str(s) for s in raw]
            latex_solutions = [latex(s) for s in raw]
        else:
            solutions = [str(raw)]
            latex_solutions = [latex(raw)]

    output = {
        "solutions": solutions,
        "latex_solutions": latex_solutions,
        "num_solutions": len(solutions),
        "domain": domain,
    }

    if store_as and solutions:
        # Store first solution or the full set
        store_expr(store_as, sympify(solutions[0]) if len(solutions) == 1 else str(solutions),
                   state, source_tool="solve.equation")

    return output


if __name__ == "__main__":
    main()
