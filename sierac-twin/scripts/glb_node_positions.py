#!/usr/bin/env python3
"""
Print node names and their local translation (position) from a GLB.
Use this to place the conveyor product box on the belt.
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
    if len(data) < 12 or data[0:4] != b"glTF":
        raise ValueError("Not a valid GLB")
    pos = 12
    while pos + 8 <= len(data):
        chunk_len = int.from_bytes(data[pos : pos + 4], "little")
        chunk_type = data[pos + 4 : pos + 8]
        pos += 8
        if chunk_type == b"JSON":
            return json.loads(data[pos : pos + chunk_len].decode("utf-8"))
        pos += chunk_len
    raise ValueError("No JSON chunk")


def walk_nodes(gltf: dict, node_index: int, parent_pos: list[float], depth: int) -> None:
    nodes = gltf.get("nodes") or []
    if node_index < 0 or node_index >= len(nodes):
        return
    node = nodes[node_index]
    name = node.get("name") or "(unnamed)"
    trans = node.get("translation") or [0.0, 0.0, 0.0]
    x, y, z = trans[0], trans[1], trans[2]
    # simple world pos (no rotation/scale)
    wx = parent_pos[0] + x
    wy = parent_pos[1] + y
    wz = parent_pos[2] + z
    indent = "  " * depth
    print(f"{indent}{name}: translation=({x}, {y}, {z})  world≈({wx:.1f}, {wy:.1f}, {wz:.1f})")
    for child_idx in node.get("children") or []:
        walk_nodes(gltf, child_idx, [wx, wy, wz], depth + 1)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GLB
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)
    gltf = read_glb_json(path)
    scenes = gltf.get("scenes") or []
    print("Node positions (translation + approximate world):\n")
    if scenes:
        for root_idx in scenes[0].get("nodes") or []:
            walk_nodes(gltf, root_idx, [0.0, 0.0, 0.0], 0)
    else:
        for i in range(len(gltf.get("nodes") or [])):
            walk_nodes(gltf, i, [0.0, 0.0, 0.0], 0)


if __name__ == "__main__":
    main()
