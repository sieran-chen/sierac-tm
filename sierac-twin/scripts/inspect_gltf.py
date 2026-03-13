import json
import sys
from pathlib import Path

p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\ai\Sierac-tm\3d\new.gltf")

if p.suffix == ".glb":
    data = p.read_bytes()
    pos = 12
    while pos + 8 <= len(data):
        cl = int.from_bytes(data[pos:pos+4], "little")
        ct = data[pos+4:pos+8]
        pos += 8
        if ct == b"JSON":
            gltf = json.loads(data[pos:pos+cl])
            break
        pos += cl
else:
    gltf = json.loads(p.read_text(encoding="utf-8"))

nodes = gltf.get("nodes", [])
meshes = gltf.get("meshes", [])
materials = gltf.get("materials", [])

print("=== SCENE HIERARCHY ===\n")

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
    print(f"{prefix}{idx}: {name}{mesh_name}{extras_str}")
    for c in n.get("children", []):
        dump(c, depth + 1)

scenes = gltf.get("scenes", [])
if scenes:
    for ri in scenes[0].get("nodes", []):
        dump(ri)

print(f"\nTotal nodes: {len(nodes)}")
print(f"Total meshes: {len(meshes)}")
print(f"Total materials: {len(materials)}")

print("\n=== MATERIALS ===\n")
for i, m in enumerate(materials):
    print(f"  {i}: {m.get('name', '(unnamed)')}")

print("\n=== MESH NAMES ===\n")
for i, m in enumerate(meshes):
    print(f"  {i}: {m.get('name', '(unnamed)')}")
