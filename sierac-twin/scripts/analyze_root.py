"""Analyze root-level children to find duplicate/overlapping assemblies."""
import json
import re
import struct
from pathlib import Path

data = Path(r"D:\ai\Sierac-tm\sierac-twin\public\models\roller_reject.glb").read_bytes()
cl = struct.unpack_from("<I", data, 12)[0]
gltf = json.loads(data[20 : 20 + cl].decode("utf-8"))
nodes = gltf["nodes"]
scenes = gltf["scenes"]


def decode_step(name: str) -> str:
    def _r(m):
        return bytes.fromhex(m.group(1)).decode("utf-16-be")
    return re.sub(r"\\X2\\([0-9A-Fa-f]+)\\X0\\", _r, name)


root_idx = scenes[0]["nodes"][0]
root = nodes[root_idx]
children = root.get("children", [])
print(f"Root '{root.get('name', '?')}' has {len(children)} direct children:\n")

# Collect all descendant node indices for each child
def collect_descendants(idx):
    result = set()
    stack = [idx]
    while stack:
        i = stack.pop()
        result.add(i)
        for c in nodes[i].get("children", []):
            stack.append(c)
    return result

# Find which children are assemblies (have sub-children)
assemblies = []
loose_parts = []
for ci in children:
    n = nodes[ci]
    name = decode_step(n.get("name", "?"))
    sub = n.get("children", [])
    desc_count = len(collect_descendants(ci)) - 1
    has_mesh = "mesh" in n
    if sub:
        assemblies.append((ci, name, desc_count))
    else:
        loose_parts.append((ci, name, has_mesh))

print(f"=== ASSEMBLIES ({len(assemblies)}) ===")
for ci, name, dc in assemblies:
    print(f"  [{ci:3d}] {name}  ({dc} descendants)")

print(f"\n=== LOOSE PARTS ({len(loose_parts)}) ===")
for ci, name, hm in loose_parts:
    mesh_tag = " [mesh]" if hm else ""
    print(f"  [{ci:3d}] {name}{mesh_tag}")
