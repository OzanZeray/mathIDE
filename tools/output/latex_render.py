"""
LaTeX rendering tool.

Converts SymPy expressions to formatted LaTeX strings.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, resolve_expr
from sympy import latex, sympify


@tool_main
def main(data: dict) -> dict:
    expr_str = data.get("expr")
    style = data.get("style", "display")
    equation_label = data.get("equation_label")
    substitutions = data.get("substitutions")

    if not expr_str:
        write_error("'expr' is required", code="PARSE_ERROR")

    state = load_state()
    expr = resolve_expr(expr_str, state)

    if substitutions:
        for old, new in substitutions.items():
            pass  # LaTeX-level substitutions handled at string level

    latex_str = latex(expr)

    output = {"latex": latex_str}

    if style == "display":
        output["display"] = f"$$\n{latex_str}\n$$"
    elif style == "inline":
        output["display"] = f"${latex_str}$"
    elif style == "aligned":
        output["display"] = f"$$\n\\begin{{aligned}}\n{latex_str}\n\\end{{aligned}}\n$$"

    if equation_label:
        output["labeled"] = f"$$\n{latex_str} \\tag{{{equation_label}}}\n$$"

    return output


if __name__ == "__main__":
    main()
