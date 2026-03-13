import json
from pathlib import Path

p = Path(r"D:\ai\Sierac-tm\sierac-twin\public\models\001.glb")
data = p.read_bytes()
pos = 12
gltf = None
while pos + 8 <= len(data):
    cl = int.from_bytes(data[pos:pos+4], "little")
    ct = data[pos+4:pos+8]
    pos += 8
    if ct == b"JSON":
        gltf = json.loads(data[pos:pos+cl])
        break
    pos += cl

nodes = gltf.get("nodes", [])

def dump(idx, depth=0):
    n = nodes[idx]
    name = n.get("name", "(unnamed)")
    mesh = n.get("mesh")
    tag = f"  [mesh={mesh}]" if mesh is not None else ""
    prefix = "  " * depth
    print(f"{prefix}{idx}: {name}{tag}")
    for c in n.get("children", []):
        dump(c, depth + 1)

scenes = gltf.get("scenes", [])
for ri in scenes[0].get("nodes", []):
    dump(ri)
print(f"\nTotal nodes: {len(nodes)}")
