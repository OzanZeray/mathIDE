"""
Symbol assumption management tool.

Actions: declare, query, list, clear
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.io_contract import tool_main, write_error
from lib.workspace import load_state, save_state, declare_symbols, get_symbols
import time


@tool_main
def main(data: dict) -> dict:
    action = data.get("action", "list")
    state = load_state()

    if action == "declare":
        symbols = data.get("symbols", {})
        if not symbols:
            write_error("'symbols' dict required for declare", code="PARSE_ERROR")
        state = declare_symbols(symbols, state)
        return {"declared": symbols}

    elif action == "query":
        name = data.get("name")
        if not name:
            write_error("'name' required for query", code="PARSE_ERROR")
        sym_info = state.get("symbols", {}).get(name)
        if not sym_info:
            return {"name": name, "declared": False, "assumptions": []}
        return {"name": name, "declared": True, "assumptions": sym_info.get("assumptions", [])}

    elif action == "list":
        return {"symbols": get_symbols(state)}

    elif action == "clear":
        state["symbols"] = {}
        state["history"].append({"action": "clear_symbols", "timestamp": time.time()})
        save_state(state)
        return {"cleared": True}

    else:
        write_error(f"Unknown action: {action}", code="PARSE_ERROR")


if __name__ == "__main__":
    main()
