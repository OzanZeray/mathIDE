"""
Symbolic linear algebra tool.

Operations: det, inv, eigenvalues, eigenvectors, jordan, nullspace, rank, transpose, rref
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, store_expr, make_symbols
from sympy import Matrix, latex, sympify, simplify


@tool_main
def main(data: dict) -> dict:
    operation = data.get("operation")
    matrix_str = data.get("matrix")
    store_as = data.get("store_as")

    if not operation:
        write_error("'operation' is required", code="PARSE_ERROR")
    if not matrix_str:
        write_error("'matrix' is required", code="PARSE_ERROR")

    state = load_state()
    syms = make_symbols(state)

    # Parse matrix
    local_ns = dict(syms)
    M = Matrix(sympify(matrix_str, locals=local_ns))

    result = None
    result_str = ""
    result_latex = ""

    if operation == "det":
        result = M.det()
        result = simplify(result)
        result_str = str(result)
        result_latex = latex(result)

    elif operation == "inv":
        result = M.inv()
        result_str = str(result)
        result_latex = latex(result)

    elif operation == "eigenvalues":
        result = M.eigenvals()
        result_str = str(result)
        result_latex = latex(result)

    elif operation == "eigenvectors":
        result = M.eigenvects()
        result_str = str(result)
        result_latex = latex(result)

    elif operation == "jordan":
        P, J = M.jordan_form()
        result_str = f"P = {P}, J = {J}"
        result_latex = f"P = {latex(P)}, \\quad J = {latex(J)}"
        result = J

    elif operation == "nullspace":
        result = M.nullspace()
        result_str = str(result)
        result_latex = latex(Matrix(result)) if result else "\\emptyset"

    elif operation == "rank":
        result = M.rank()
        result_str = str(result)
        result_latex = str(result)

    elif operation == "transpose":
        result = M.T
        result_str = str(result)
        result_latex = latex(result)

    elif operation == "rref":
        rref_matrix, pivots = M.rref()
        result = rref_matrix
        result_str = str(rref_matrix)
        result_latex = latex(rref_matrix)

    elif operation == "charpoly":
        lam = sympify('lambda')
        result = M.charpoly()
        result_str = str(result.as_expr())
        result_latex = latex(result.as_expr())

    else:
        write_error(
            f"Unknown operation: {operation}. Available: det, inv, eigenvalues, eigenvectors, jordan, nullspace, rank, transpose, rref, charpoly",
            code="METHOD_NOT_APPLICABLE"
        )

    output = {
        "result": result_str,
        "latex": result_latex,
        "operation": operation,
        "matrix_size": f"{M.rows}x{M.cols}",
    }

    if store_as and result is not None:
        store_expr(store_as, result, state, source_tool=f"linalg.{operation}")

    return output


if __name__ == "__main__":
    main()
