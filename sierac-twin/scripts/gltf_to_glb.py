"""Convert a .gltf + .bin pair into a single .glb file."""

import json
import struct
import sys
from pathlib import Path


def gltf_to_glb(gltf_path: Path, glb_path: Path):
    gltf_text = gltf_path.read_text(encoding="utf-8")
    gltf = json.loads(gltf_text)

    buffers = gltf.get("buffers", [])
    if not buffers:
        raise ValueError("No buffers found in glTF")

    bin_uri = buffers[0].get("uri", "")
    bin_path = gltf_path.parent / bin_uri
    if not bin_path.exists():
        raise FileNotFoundError(f"Binary file not found: {bin_path}")

    bin_data = bin_path.read_bytes()

    buffers[0].pop("uri", None)
    buffers[0]["byteLength"] = len(bin_data)

    json_str = json.dumps(gltf, ensure_ascii=False, separators=(",", ":"))
    json_bytes = json_str.encode("utf-8")
    json_pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * json_pad

    bin_pad = (4 - len(bin_data) % 4) % 4
    bin_data += b"\x00" * bin_pad

    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_data)

    with open(glb_path, "wb") as f:
        f.write(b"glTF")
        f.write(struct.pack("<I", 2))
        f.write(struct.pack("<I", total_length))

        f.write(struct.pack("<I", len(json_bytes)))
        f.write(b"JSON")
        f.write(json_bytes)

        f.write(struct.pack("<I", len(bin_data)))
        f.write(b"BIN\x00")
        f.write(bin_data)

    print(f"GLB written: {glb_path} ({total_length / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\ai\Sierac-tm\3d\new.gltf")
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".glb")
    gltf_to_glb(src, dst)
