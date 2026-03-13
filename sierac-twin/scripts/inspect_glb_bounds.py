"""Print bounding box center and size for each mesh in a GLB, using pygltflib or raw parsing."""
import json, struct, pathlib, sys
import numpy as np

path = sys.argv[1] if len(sys.argv) > 1 else "public/models/001.glb"
data = pathlib.Path(path).read_bytes()

# Parse GLB
json_len = struct.unpack_from('<I', data, 12)[0]
gltf = json.loads(data[20:20+json_len])

# BIN chunk starts after JSON chunk
bin_offset = 20 + json_len
# chunk1 header: length(4) + type(4)
bin_data_offset = bin_offset + 8
bin_chunk_len = struct.unpack_from('<I', data, bin_offset)[0]
bin_data = data[bin_data_offset:bin_data_offset + bin_chunk_len]

accessors = gltf.get('accessors', [])
buffer_views = gltf.get('bufferViews', [])

def get_accessor_data(acc_idx):
    acc = accessors[acc_idx]
    bv = buffer_views[acc['bufferView']]
    offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    count = acc['count']
    comp_type = acc['componentType']  # 5126 = float
    type_str = acc['type']
    num_components = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[type_str]
    fmt = {5126: 'f', 5125: 'I', 5123: 'H', 5121: 'B', 5120: 'b'}[comp_type]
    item_size = struct.calcsize(fmt) * num_components
    stride = bv.get('byteStride', item_size)
    result = []
    for i in range(count):
        vals = struct.unpack_from(f'{num_components}{fmt}', bin_data, offset + i * stride)
        result.append(vals)
    return np.array(result, dtype=np.float32)

nodes = gltf.get('nodes', [])
meshes = gltf.get('meshes', [])

print(f"{'Node':<30} {'Min X':>8} {'Min Y':>8} {'Min Z':>8}   {'Max X':>8} {'Max Y':>8} {'Max Z':>8}   {'Size X':>8} {'Size Y':>8} {'Size Z':>8}   {'Ctr X':>8} {'Ctr Y':>8} {'Ctr Z':>8}")
print("-" * 140)

for node in nodes:
    name = node.get('name', '<no name>')
    mesh_idx = node.get('mesh')
    if mesh_idx is None:
        continue
    mesh = meshes[mesh_idx]
    all_pos = []
    for prim in mesh.get('primitives', []):
        attrs = prim.get('attributes', {})
        if 'POSITION' in attrs:
            pos = get_accessor_data(attrs['POSITION'])
            all_pos.append(pos)
    if not all_pos:
        print(f"{name:<30} (no position data)")
        continue
    pts = np.vstack(all_pos)
    mn = pts.min(axis=0)
    mx = pts.max(axis=0)
    sz = mx - mn
    ctr = (mn + mx) / 2
    print(f"{name:<30} {mn[0]:>8.1f} {mn[1]:>8.1f} {mn[2]:>8.1f}   {mx[0]:>8.1f} {mx[1]:>8.1f} {mx[2]:>8.1f}   {sz[0]:>8.1f} {sz[1]:>8.1f} {sz[2]:>8.1f}   {ctr[0]:>8.1f} {ctr[1]:>8.1f} {ctr[2]:>8.1f}")
