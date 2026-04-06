"""
Flow execution engine.

Interprets flow manifests (declarative DAGs) and executes
them step-by-step, yielding results at each node.
"""
import json
import subprocess
import sys
from pathlib import Path
from string import Template

PROJECT_ROOT = Path(__file__).parent.parent


def load_flow(flow_path: str) -> dict:
    """Load a flow manifest from file."""
    full_path = PROJECT_ROOT / flow_path
    return json.loads(full_path.read_text(encoding="utf-8"))


def resolve_template(value, params: dict) -> str:
    """Replace {{param}} placeholders with actual values."""
    if not isinstance(value, str):
        return value
    result = value
    for k, v in params.items():
        result = result.replace("{{" + k + "}}", str(v))
    return result


def resolve_inputs(inputs: dict, params: dict) -> dict:
    """Resolve all template variables in a step's inputs."""
    resolved = {}
    for k, v in inputs.items():
        if isinstance(v, str):
            resolved[k] = resolve_template(v, params)
        elif isinstance(v, dict):
            resolved[k] = {
                resolve_template(dk, params): resolve_template(dv, params)
                for dk, dv in v.items()
            }
        elif isinstance(v, list):
            resolved[k] = [resolve_template(item, params) for item in v]
        else:
            resolved[k] = v
    return resolved


def find_entry_point(tool_id: str) -> str | None:
    """Look up the entry point script for a tool ID from the index."""
    index_path = PROJECT_ROOT / "registry" / "index.json"
    if not index_path.exists():
        return None
    index = json.loads(index_path.read_text(encoding="utf-8"))
    tool_entry = index.get("tools", {}).get(tool_id)
    if not tool_entry:
        return None

    manifest_path = PROJECT_ROOT / tool_entry["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for tool in manifest.get("tools", []):
        if tool["id"] == tool_id:
            return tool.get("entry_point")

    return manifest.get("entry_point")


def execute_tool(tool_id: str, inputs: dict) -> dict:
    """Execute a single tool by ID with given inputs."""
    entry_point = find_entry_point(tool_id)
    if not entry_point:
        return {"success": False, "error": "TOOL_NOT_FOUND", "message": f"No entry point for {tool_id}"}

    script_path = PROJECT_ROOT / entry_point
    if not script_path.exists():
        return {"success": False, "error": "TOOL_NOT_FOUND", "message": f"Script not found: {entry_point}"}

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(inputs),
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            try:
                return json.loads(result.stderr)
            except json.JSONDecodeError:
                return {"success": False, "error": "COMPUTATION_ERROR", "message": result.stderr}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "COMPUTATION_TIMEOUT", "message": "Tool execution exceeded 60s"}
    except Exception as e:
        return {"success": False, "error": "COMPUTATION_ERROR", "message": str(e)}


def run_flow(flow: dict, params: dict = None, on_step=None) -> list:
    """Execute a flow manifest.

    Args:
        flow: Parsed flow manifest dict.
        params: Parameter values to fill template placeholders.
        on_step: Optional callback(step_id, step_result) called after each step.

    Returns:
        List of (step_id, result_dict) tuples.
    """
    params = params or {}
    # Merge flow-level defaults with provided params
    for pname, pdef in flow.get("parameters", {}).items():
        if pname not in params and "default" in pdef:
            params[pname] = pdef["default"]

    results = []

    for step in flow.get("steps", []):
        step_id = step["id"]
        step_type = step.get("type", "tool")

        if step_type == "tool":
            tool_id = step["tool"]
            inputs = resolve_inputs(step.get("inputs", {}), params)
            result = execute_tool(tool_id, inputs)

            # Handle store_as
            if result.get("success", False) and "store_as" in step:
                store_name = resolve_template(step["store_as"], params)
                # Store via workspace tool
                execute_tool("workspace.store", {
                    "action": "store",
                    "name": store_name,
                    "expr": result.get("result", ""),
                })
                params[store_name] = result.get("result", "")

            results.append((step_id, result))

            # Handle failure
            if not result.get("success", True):
                on_failure = step.get("on_failure", "stop")
                if on_failure == "stop":
                    if on_step:
                        on_step(step_id, result)
                    break
                elif on_failure == "warn":
                    pass  # Continue

        elif step_type == "condition":
            # Evaluate condition — for now, simple string check
            condition = resolve_template(step.get("if", "False"), params)
            then_step = step.get("then")
            else_step = step.get("else")
            # Conditions are resolved by the orchestrator (Claude), not here
            results.append((step_id, {
                "type": "condition",
                "condition": condition,
                "then": then_step,
                "else": else_step,
            }))

        elif step_type == "user_choice":
            results.append((step_id, {
                "type": "user_choice",
                "prompt": step.get("prompt"),
                "options": step.get("options"),
            }))
            break  # Pause for user input

        if on_step:
            on_step(step_id, results[-1][1] if results else {})

    return results


if __name__ == "__main__":
    # CLI: python flows/engine.py <flow_manifest.json> [param=value ...]
    if len(sys.argv) < 2:
        print("Usage: python flows/engine.py <flow_manifest.json> [param=value ...]")
        sys.exit(1)

    flow = load_flow(sys.argv[1])
    params = {}
    for arg in sys.argv[2:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            params[k] = v

    results = run_flow(flow, params, on_step=lambda sid, r: print(f"  [{sid}] {'OK' if r.get('success', True) else 'FAIL'}"))

    print("\n--- Flow Results ---")
    for step_id, result in results:
        print(f"\n[{step_id}]")
        print(json.dumps(result, indent=2, default=str))
