import json, struct, pathlib, sys

path = sys.argv[1] if len(sys.argv) > 1 else "public/models/001.glb"
data = pathlib.Path(path).read_bytes()
json_len = struct.unpack_from('<I', data, 12)[0]
gltf = json.loads(data[20:20+json_len])

nodes = gltf.get('nodes', [])
print(f"Total nodes: {len(nodes)}")
for i, n in enumerate(nodes):
    name = n.get('name','<no name>')
    mesh = n.get('mesh')
    children = n.get('children', [])
    t = n.get('translation')
    print(f"  [{i}] name={name!r:35s} mesh={str(mesh):4s} children={children} translation={t}")

meshes = gltf.get('meshes', [])
print(f"\nTotal meshes: {len(meshes)}")
for i, m in enumerate(meshes):
    print(f"  [{i}] {m.get('name','<no name>')!r}")

scenes = gltf.get('scenes', [])
print(f"\nScene root nodes: {gltf.get('scene')} -> {scenes[0].get('nodes') if scenes else 'N/A'}")
