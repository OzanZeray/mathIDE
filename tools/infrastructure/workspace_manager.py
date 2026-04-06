"""
Workspace state management tool.

Actions: store, load, list, delete, reset, export
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import (
    load_state, save_state, store_expr, resolve_expr,
    EMPTY_STATE, WORKSPACE_DIR
)
from sympy import latex, srepr, sympify
import json
import time


@tool_main
def main(data: dict) -> dict:
    action = data.get("action", "list")
    state = load_state()

    if action == "store":
        name = data.get("name")
        expr_str = data.get("expr")
        if not name or not expr_str:
            write_error("'name' and 'expr' required for store", code="PARSE_ERROR")

        expr = resolve_expr(expr_str, state)
        metadata = data.get("metadata", {})
        store_expr(
            name, expr, state,
            source_tool=metadata.get("source_tool", "workspace.store"),
            source_step=metadata.get("source_step"),
            depends_on=metadata.get("depends_on", []),
        )
        return {
            "stored": name,
            "latex": latex(expr),
            "workspace_size": len(state["expressions"]),
        }

    elif action == "load":
        name = data.get("name")
        if not name:
            write_error("'name' required for load", code="PARSE_ERROR")
        if name not in state.get("expressions", {}):
            write_error(
                f"'{name}' not found. Available: {list(state['expressions'].keys())}",
                code="WORKSPACE_NOT_FOUND"
            )
        entry = state["expressions"][name]
        expr = sympify(entry["srepr"] if isinstance(entry, dict) else entry)
        return {
            "name": name,
            "result": str(expr),
            "latex": latex(expr),
            "srepr": srepr(expr),
            "depends_on": entry.get("depends_on", []) if isinstance(entry, dict) else [],
        }

    elif action == "list":
        items = {}
        for name, entry in state.get("expressions", {}).items():
            if isinstance(entry, dict):
                items[name] = {
                    "latex": entry.get("latex", ""),
                    "source_tool": entry.get("source_tool"),
                    "depends_on": entry.get("depends_on", []),
                }
            else:
                items[name] = {"value": str(entry)}
        return {
            "expressions": items,
            "symbols": state.get("symbols", {}),
            "count": len(items),
        }

    elif action == "delete":
        name = data.get("name")
        if not name:
            write_error("'name' required for delete", code="PARSE_ERROR")
        if name in state.get("expressions", {}):
            del state["expressions"][name]
            state["history"].append({
                "action": "delete", "name": name, "timestamp": time.time()
            })
            save_state(state)
        return {"deleted": name, "workspace_size": len(state["expressions"])}

    elif action == "reset":
        save_state(json.loads(json.dumps(EMPTY_STATE)))
        return {"reset": True, "workspace_size": 0}

    elif action == "export":
        lines = ["from sympy import *", ""]
        # Symbol declarations
        for name, info in state.get("symbols", {}).items():
            assumptions = info.get("assumptions", [])
            kwargs = ", ".join(f"{a}=True" for a in assumptions)
            lines.append(f"{name} = Symbol('{name}', {kwargs})" if kwargs else f"{name} = Symbol('{name}')")
        lines.append("")
        # Expression definitions
        for name, entry in state.get("expressions", {}).items():
            srepr_val = entry["srepr"] if isinstance(entry, dict) else entry
            lines.append(f"{name} = sympify('{srepr_val}')")
        code = "\n".join(lines)

        export_path = WORKSPACE_DIR / "exports" / f"workspace_export.py"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(code, encoding="utf-8")
        return {"exported": str(export_path), "code": code}

    else:
        write_error(f"Unknown action: {action}", code="PARSE_ERROR")


if __name__ == "__main__":
    main()
