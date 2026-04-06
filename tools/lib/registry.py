"""
Plugin registry loader and tool resolver.

Reads the master index and individual manifests to discover
available tools, flows, backends, and renderers at runtime.
"""
import json
from pathlib import Path

REGISTRY_DIR = Path(__file__).parent.parent.parent / "registry"
INDEX_PATH = REGISTRY_DIR / "index.json"


def load_index() -> dict:
    """Load the master registry index."""
    if not INDEX_PATH.exists():
        return {"tools": {}, "flows": {}, "backends": {}, "renderers": {}}
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def load_manifest(manifest_path: str) -> dict:
    """Load a specific manifest file relative to project root."""
    full_path = REGISTRY_DIR.parent / manifest_path
    return json.loads(full_path.read_text(encoding="utf-8"))


def resolve_tool(query: str, index: dict = None) -> dict | None:
    """Find a tool by ID or tag match.

    Args:
        query: Tool ID (e.g. "series.expand") or keyword (e.g. "taylor").
        index: Pre-loaded index dict (loaded if None).

    Returns:
        Tool entry from index with loaded manifest, or None.
    """
    if index is None:
        index = load_index()

    tools = index.get("tools", {})

    # Exact ID match
    if query in tools:
        entry = dict(tools[query])
        entry["id"] = query
        entry["manifest_data"] = load_manifest(entry["manifest"])
        return entry

    # Tag search
    matches = []
    query_lower = query.lower()
    for tool_id, entry in tools.items():
        tags = entry.get("tags", [])
        if any(query_lower in tag.lower() for tag in tags):
            matches.append((tool_id, entry))

    if len(matches) == 1:
        tool_id, entry = matches[0]
        entry = dict(entry)
        entry["id"] = tool_id
        entry["manifest_data"] = load_manifest(entry["manifest"])
        return entry

    if len(matches) > 1:
        # Return all candidates — let the caller decide
        return {
            "ambiguous": True,
            "candidates": [{"id": tid, **e} for tid, e in matches]
        }

    return None


def list_tools(category: str = None, index: dict = None) -> list:
    """List available tools, optionally filtered by category."""
    if index is None:
        index = load_index()

    tools = []
    for tool_id, entry in index.get("tools", {}).items():
        if category and entry.get("category") != category:
            continue
        tools.append({"id": tool_id, **entry})
    return tools


def get_tool_entry_point(tool_id: str, index: dict = None) -> str | None:
    """Get the script path for a tool."""
    if index is None:
        index = load_index()
    entry = index.get("tools", {}).get(tool_id)
    if not entry:
        return None
    manifest = load_manifest(entry["manifest"])
    # Find the specific tool in manifest
    for tool in manifest.get("tools", []):
        if tool["id"] == tool_id:
            return tool.get("entry_point")
    return manifest.get("entry_point")
