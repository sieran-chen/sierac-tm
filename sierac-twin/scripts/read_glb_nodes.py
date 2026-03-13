#!/usr/bin/env python3
"""
Read node names (and optional extras) from a GLB file. No BOM in glTF spec;
this dumps the scene graph so you can align partMapping or infer a part list.
Usage: python read_glb_nodes.py [path/to/model.glb]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GLB = REPO_ROOT / "public" / "models" / "001.glb"


def read_glb_json(path: Path) -> dict:
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 12:
        raise ValueError("File too short for GLB header")
    magic = data[0:4]
    if magic != b"glTF":
        raise ValueError("Not a GLB file (bad magic)")
    # Chunk 0: length (4) + type (4) + payload
    pos = 12
    while pos + 8 <= len(data):
        chunk_len = int.from_bytes(data[pos : pos + 4], "little")
        chunk_type = data[pos + 4 : pos + 8]
        pos += 8
        if pos + chunk_len > len(data):
            break
        if chunk_type == b"JSON":
            return json.loads(data[pos : pos + chunk_len].decode("utf-8"))
        pos += chunk_len
    raise ValueError("No JSON chunk in GLB")


def collect_node_names(gltf: dict, node_index: int, names: list[str], depth: int = 0) -> None:
    nodes = gltf.get("nodes") or []
    if node_index < 0 or node_index >= len(nodes):
        return
    node = nodes[node_index]
    name = node.get("name") or ""
    indent = "  " * depth
    extras = node.get("extras") or {}
    names.append((indent, name, extras))
    for child_idx in node.get("children") or []:
        collect_node_names(gltf, child_idx, names, depth + 1)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GLB
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)
    gltf = read_glb_json(path)
    scenes = gltf.get("scenes") or []
    node_list: list[tuple[str, str, dict]] = []
    if scenes:
        for root_idx in scenes[0].get("nodes") or []:
            collect_node_names(gltf, root_idx, node_list, 0)
    else:
        for i in range(len(gltf.get("nodes") or [])):
            collect_node_names(gltf, i, node_list, 0)
    print("Nodes (name, extras) - use partName in partMapping to match:\n")
    for indent, name, extras in node_list:
        extra_str = f"  extras={extras}" if extras else ""
        print(f"{indent}{name or '(unnamed)'}{extra_str}")
    print(f"\nTotal: {len(node_list)} nodes")


if __name__ == "__main__":
    main()
