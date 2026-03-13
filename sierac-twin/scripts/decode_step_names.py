"""Decode STEP \X2\...\X0\ Unicode escapes in glTF node/mesh names.

STEP AP214/AP242 encodes non-ASCII characters as \X2\<hex UTF-16BE>\X0\.
This script reads a glTF file, decodes all such names, and outputs a
readable hierarchy with Chinese names restored.
"""

import json
import re
import sys
from pathlib import Path


def decode_step_unicode(name: str) -> str:
    """Decode \\X2\\<hex>\\X0\\ sequences to Unicode text."""

    def _replace(m: re.Match) -> str:
        hex_str = m.group(1)
        bs = bytes.fromhex(hex_str)
        return bs.decode("utf-16-be")

    return re.sub(r"\\X2\\([0-9A-Fa-f]+)\\X0\\", _replace, name)


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\ai\Sierac-tm\3d\new.gltf")
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name("gltf_decoded_names.txt")

    raw = src.read_bytes()
    if src.suffix == ".glb":
        pos = 12
        while pos + 8 <= len(raw):
            cl = int.from_bytes(raw[pos : pos + 4], "little")
            ct = raw[pos + 4 : pos + 8]
            pos += 8
            if ct == b"JSON":
                raw = raw[pos : pos + cl]
                break
            pos += cl

    gltf = json.loads(raw.decode("utf-8"))
    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])

    lines: list[str] = []
    lines.append("=== DECODED SCENE HIERARCHY ===\n")

    def dump(idx: int, depth: int = 0):
        n = nodes[idx]
        name = decode_step_unicode(n.get("name", "(unnamed)"))
        mesh_idx = n.get("mesh")
        mesh_info = ""
        if mesh_idx is not None and mesh_idx < len(meshes):
            mesh_info = f"  [mesh: {decode_step_unicode(meshes[mesh_idx].get('name', '?'))}]"
        lines.append(f"{'  ' * depth}{idx}: {name}{mesh_info}")
        for c in n.get("children", []):
            dump(c, depth + 1)

    scenes = gltf.get("scenes", [])
    if scenes:
        for ri in scenes[0].get("nodes", []):
            dump(ri)

    lines.append(f"\nTotal nodes: {len(nodes)}")
    lines.append(f"Total meshes: {len(meshes)}")

    unique_names = sorted(
        {decode_step_unicode(n.get("name", "")) for n in nodes if n.get("name")}
    )
    lines.append(f"\n=== UNIQUE NODE NAMES ({len(unique_names)}) ===\n")
    for name in unique_names:
        lines.append(f"  {name}")

    result = "\n".join(lines)
    dst.write_text(result, encoding="utf-8")
    print(f"Done. Decoded result written to {dst}")


if __name__ == "__main__":
    main()
