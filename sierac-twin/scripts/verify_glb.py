"""Quick GLB header verification."""
import struct
from pathlib import Path

p = Path(r"D:\ai\Sierac-tm\sierac-twin\public\models\roller_reject.glb")
data = p.read_bytes()

magic = data[:4]
version = struct.unpack_from("<I", data, 4)[0]
total_len = struct.unpack_from("<I", data, 8)[0]

print(f"Magic: {magic!r} (expect b'glTF')")
print(f"Version: {version} (expect 2)")
print(f"Header total length: {total_len}")
print(f"Actual file size: {len(data)}")
print(f"Match: {total_len == len(data)}")

pos = 12
chunk_idx = 0
while pos + 8 <= len(data):
    cl = struct.unpack_from("<I", data, pos)[0]
    ct = data[pos + 4 : pos + 8]
    print(f"Chunk {chunk_idx}: type={ct!r}, length={cl}")
    if ct == b"JSON":
        snippet = data[pos + 8 : pos + 8 + min(300, cl)].decode("utf-8", errors="replace")
        print(f"  JSON snippet: {snippet[:300]}")
    pos += 8 + cl
    chunk_idx += 1
