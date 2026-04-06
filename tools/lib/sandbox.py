"""
Restricted SymPy execution environment.

Provides a safe namespace for executing SymPy code without
filesystem, network, or subprocess access.
"""
import threading
import sympy

# Build safe namespace from sympy's public API
SAFE_NAMESPACE = {}
for name in dir(sympy):
    if not name.startswith('_'):
        SAFE_NAMESPACE[name] = getattr(sympy, name)

# Minimal builtins — enough for math, not for mischief
SAFE_BUILTINS = {
    'range': range, 'len': len, 'int': int, 'str': str, 'float': float,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set, 'frozenset': frozenset,
    'True': True, 'False': False, 'None': None,
    'print': print, 'repr': repr, 'isinstance': isinstance, 'type': type,
    'enumerate': enumerate, 'zip': zip, 'map': map, 'filter': filter,
    'sum': sum, 'min': min, 'max': max, 'abs': abs, 'sorted': sorted,
    'reversed': reversed, 'all': all, 'any': any, 'bool': bool,
    'complex': complex, 'round': round, 'pow': pow, 'divmod': divmod,
    'KeyError': KeyError, 'ValueError': ValueError, 'TypeError': TypeError,
    'IndexError': IndexError, 'RuntimeError': RuntimeError,
    'StopIteration': StopIteration, 'ZeroDivisionError': ZeroDivisionError,
}

BLOCKED_NAMES = {
    'os', 'sys', 'subprocess', 'shutil', 'pathlib', 'socket',
    'http', 'urllib', 'requests', 'open', 'exec', 'eval',
    '__import__', 'compile', 'globals', 'locals', 'breakpoint',
}


def _build_namespace(extra_vars: dict = None) -> dict:
    """Build a fresh sandboxed namespace."""
    ns = dict(SAFE_NAMESPACE)
    ns['__builtins__'] = dict(SAFE_BUILTINS)
    if extra_vars:
        for k, v in extra_vars.items():
            if isinstance(v, str):
                try:
                    ns[k] = sympy.sympify(v)
                except (sympy.SympifyError, TypeError):
                    ns[k] = v
            else:
                ns[k] = v
    return ns


def execute_sympy(code: str, timeout: int = 30, extra_vars: dict = None) -> dict:
    """Execute SymPy code in a sandboxed namespace with timeout.

    Args:
        code: Python/SymPy code string to execute.
        timeout: Maximum execution time in seconds.
        extra_vars: Additional variables to inject (e.g. from workspace).

    Returns:
        Dict of all non-private variables in the namespace after execution.

    Raises:
        TimeoutError: If execution exceeds timeout.
        Various exceptions from the executed code.
    """
    # Check for blocked imports/names
    for blocked in BLOCKED_NAMES:
        if blocked in code:
            raise RuntimeError(f"Blocked operation: '{blocked}' is not allowed in sandbox")

    ns = _build_namespace(extra_vars)
    result = {}
    exception = [None]

    def _run():
        try:
            exec(code, ns)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        raise TimeoutError(f"Computation exceeded {timeout}s timeout")

    if exception[0] is not None:
        raise exception[0]

    # Extract user-defined variables
    for k, v in ns.items():
        if not k.startswith('_') and k not in SAFE_NAMESPACE and k != '__builtins__':
            result[k] = v

    return result
