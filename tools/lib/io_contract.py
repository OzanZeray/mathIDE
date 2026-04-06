"""
Standardized JSON I/O contract for all Math IDE tools.

Every tool reads JSON from stdin, writes JSON to stdout.
Errors go to stderr with non-zero exit code.
"""
import json
import sys
import traceback
from functools import wraps


def read_input() -> dict:
    """Read JSON input from stdin."""
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        write_error(f"Invalid JSON input: {e}", code="PARSE_ERROR")


def write_output(data: dict):
    """Write successful JSON result to stdout."""
    data.setdefault("success", True)
    print(json.dumps(data, indent=2, default=str))
    sys.exit(0)


def write_error(message: str, code: str = "COMPUTATION_ERROR", details: dict = None):
    """Write error JSON to stderr and exit with code 1."""
    err = {"success": False, "error": code, "message": message}
    if details:
        err["details"] = details
    print(json.dumps(err, indent=2, default=str), file=sys.stderr)
    sys.exit(1)


def tool_main(func):
    """Decorator that wraps a tool's main function with I/O handling.

    Usage:
        @tool_main
        def main(input_data: dict) -> dict:
            ...
            return {"result": "...", "latex": "..."}
    """
    @wraps(func)
    def wrapper():
        try:
            input_data = read_input()
            result = func(input_data)
            write_output(result)
        except SystemExit:
            raise
        except TimeoutError as e:
            write_error(str(e), code="COMPUTATION_TIMEOUT")
        except Exception as e:
            write_error(
                f"{type(e).__name__}: {e}",
                code="COMPUTATION_ERROR",
                details={"traceback": traceback.format_exc()}
            )
    return wrapper
