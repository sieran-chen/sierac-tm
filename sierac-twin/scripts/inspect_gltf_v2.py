import json
import sys
from pathlib import Path

p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\ai\Sierac-tm\3d\new.gltf")
raw = p.read_bytes()

if p.suffix == ".glb":
    pos = 12
    while pos + 8 <= len(raw):
        cl = int.from_bytes(raw[pos:pos+4], "little")
        ct = raw[pos+4:pos+8]
        pos += 8
        if ct == b"JSON":
            raw = raw[pos:pos+cl]
            break
        pos += cl

gltf = json.loads(raw.decode("utf-8"))
nodes = gltf.get("nodes", [])
meshes = gltf.get("meshes", [])
materials = gltf.get("materials", [])

output = []
output.append("=== SCENE HIERARCHY ===\n")

def dump(idx, depth=0):
    n = nodes[idx]
    name = n.get("name", "(unnamed)")
    mesh_idx = n.get("mesh")
    mesh_name = ""
    if mesh_idx is not None and mesh_idx < len(meshes):
        mesh_name = f"  [mesh: {meshes[mesh_idx].get('name', '?')}]"
    extras = n.get("extras")
    extras_str = f"  extras={extras}" if extras else ""
    prefix = "  " * depth
    output.append(f"{prefix}{idx}: {name}{mesh_name}{extras_str}")
    for c in n.get("children", []):
        dump(c, depth + 1)

scenes = gltf.get("scenes", [])
if scenes:
    for ri in scenes[0].get("nodes", []):
        dump(ri)

output.append(f"\nTotal nodes: {len(nodes)}")
output.append(f"Total meshes: {len(meshes)}")
output.append(f"Total materials: {len(materials)}")

output.append("\n=== MATERIALS ===\n")
for i, m in enumerate(materials):
    output.append(f"  {i}: {m.get('name', '(unnamed)')}")

output.append("\n=== MESH NAMES ===\n")
for i, m in enumerate(meshes):
    output.append(f"  {i}: {m.get('name', '(unnamed)')}")

result = "\n".join(output)
Path(r"D:\ai\Sierac-tm\3d\gltf_inspect_result.txt").write_text(result, encoding="utf-8")
print("Done. Result written to 3d/gltf_inspect_result.txt")
