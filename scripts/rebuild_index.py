"""
Rebuild registry/index.json from all manifest files.

Usage: python scripts/rebuild_index.py
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
REGISTRY_DIR = PROJECT_ROOT / "registry"
INDEX_PATH = REGISTRY_DIR / "index.json"


def scan_tool_manifests() -> dict:
    tools = {}
    tools_dir = REGISTRY_DIR / "tools"
    if not tools_dir.exists():
        return tools

    for manifest_path in sorted(tools_dir.glob("*.json")):
        rel_path = str(manifest_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  WARN: skipping {manifest_path.name}: {e}", file=sys.stderr)
            continue

        for tool in data.get("tools", []):
            tool_id = tool["id"]
            tools[tool_id] = {
                "manifest": rel_path,
                "category": tool.get("category", ""),
                "tags": tool.get("tags", []),
            }
            print(f"  + tool: {tool_id}")

    return tools


def scan_flow_manifests() -> dict:
    flows = {}
    flows_dir = REGISTRY_DIR / "flows"
    if not flows_dir.exists():
        return flows

    for manifest_path in sorted(flows_dir.glob("*.json")):
        rel_path = str(manifest_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  WARN: skipping {manifest_path.name}: {e}", file=sys.stderr)
            continue

        flow_id = data.get("id", manifest_path.stem)
        flows[flow_id] = {"manifest": rel_path}
        print(f"  + flow: {flow_id}")

    return flows


def scan_backend_manifests() -> dict:
    backends = {}
    backends_dir = REGISTRY_DIR / "backends"
    if not backends_dir.exists():
        return backends

    for manifest_path in sorted(backends_dir.glob("*.json")):
        rel_path = str(manifest_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  WARN: skipping {manifest_path.name}: {e}", file=sys.stderr)
            continue

        backend_id = data.get("id", manifest_path.stem)
        backends[backend_id] = {"manifest": rel_path}
        print(f"  + backend: {backend_id}")

    return backends


def scan_renderer_manifests() -> dict:
    renderers = {}
    renderers_dir = REGISTRY_DIR / "renderers"
    if not renderers_dir.exists():
        return renderers

    for manifest_path in sorted(renderers_dir.glob("*.json")):
        rel_path = str(manifest_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  WARN: skipping {manifest_path.name}: {e}", file=sys.stderr)
            continue

        renderer_id = data.get("id", manifest_path.stem)
        renderers[renderer_id] = {"manifest": rel_path}
        print(f"  + renderer: {renderer_id}")

    return renderers


def main():
    print("Rebuilding registry index...")

    index = {
        "version": "0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tools": scan_tool_manifests(),
        "flows": scan_flow_manifests(),
        "backends": scan_backend_manifests(),
        "renderers": scan_renderer_manifests(),
    }

    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")

    total = len(index["tools"]) + len(index["flows"]) + len(index["backends"]) + len(index["renderers"])
    print(f"\nIndex written: {INDEX_PATH}")
    print(f"  {len(index['tools'])} tools, {len(index['flows'])} flows, {len(index['backends'])} backends, {len(index['renderers'])} renderers")
    print(f"  Total: {total} plugins")


if __name__ == "__main__":
    main()
