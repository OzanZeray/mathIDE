"""
Result verification tool.

Methods: direct, substitution, series_compare
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, resolve_expr, make_symbols
from sympy import (
    simplify, Eq, Rational, series, latex, oo,
    Symbol, sympify, Abs
)


def verify_direct(lhs, rhs):
    """Check simplify(LHS - RHS) == 0."""
    diff = simplify(lhs - rhs)
    return {
        "verified": diff == 0,
        "method_used": "direct",
        "detail": f"simplify(LHS - RHS) = {latex(diff)}",
        "difference": str(diff),
    }


def verify_substitution(lhs, rhs, symbols_dict):
    """Evaluate at several rational points and check equality."""
    test_points = [Rational(1, 10), Rational(1, 3), Rational(-1, 5), Rational(2, 7)]
    free_syms = list((lhs.free_symbols | rhs.free_symbols))
    if not free_syms:
        return verify_direct(lhs, rhs)

    all_match = True
    details = []
    for point in test_points[:len(free_syms) + 2]:
        subs = {s: point for s in free_syms}
        lval = simplify(lhs.subs(subs))
        rval = simplify(rhs.subs(subs))
        match = simplify(lval - rval) == 0
        details.append(f"at {subs}: LHS={lval}, RHS={rval}, match={match}")
        if not match:
            all_match = False

    return {
        "verified": all_match,
        "method_used": "substitution",
        "detail": "; ".join(details),
    }


def verify_series_compare(lhs, rhs, variable=None, order=10):
    """Expand both as series and compare term by term."""
    free_syms = list((lhs.free_symbols | rhs.free_symbols))
    if variable:
        var = Symbol(variable)
    elif free_syms:
        var = free_syms[0]
    else:
        return verify_direct(lhs, rhs)

    lhs_series = series(lhs, var, 0, n=order).removeO()
    rhs_series = series(rhs, var, 0, n=order).removeO()
    diff = simplify(lhs_series - rhs_series)

    return {
        "verified": diff == 0,
        "method_used": "series_compare",
        "detail": f"Series agree to O({var}^{order}): diff = {latex(diff)}",
        "lhs_series": str(lhs_series),
        "rhs_series": str(rhs_series),
    }


@tool_main
def main(data: dict) -> dict:
    claim = data.get("claim")
    lhs_str = data.get("lhs")
    rhs_str = data.get("rhs")
    method = data.get("method", "direct")

    state = load_state()

    if claim:
        # Parse "expr1 == expr2" style claim
        eq = sympify(claim)
        if isinstance(eq, Eq):
            lhs, rhs = eq.lhs, eq.rhs
        elif "==" in claim:
            parts = claim.split("==")
            lhs = resolve_expr(parts[0].strip(), state)
            rhs = resolve_expr(parts[1].strip(), state)
        else:
            write_error("Claim must contain '==' or be a SymPy Eq()", code="PARSE_ERROR")
    elif lhs_str and rhs_str:
        lhs = resolve_expr(lhs_str, state)
        rhs = resolve_expr(rhs_str, state)
    else:
        write_error("Provide 'claim' string or 'lhs'+'rhs' fields", code="PARSE_ERROR")

    if method == "direct":
        return verify_direct(lhs, rhs)
    elif method == "substitution":
        return verify_substitution(lhs, rhs, make_symbols(state))
    elif method == "series_compare":
        variable = data.get("variable")
        order = data.get("tolerance_order", 10)
        return verify_series_compare(lhs, rhs, variable, order)
    else:
        write_error(f"Unknown method: {method}", code="METHOD_NOT_APPLICABLE")


if __name__ == "__main__":
    main()
