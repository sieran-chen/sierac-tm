# Copy 3d/罐装机图片/*.png to public/images/ with English names (design §2.2).
# Run from repo root: python sierac-twin/scripts/copy_images.py

from __future__ import annotations

import os
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(REPO_ROOT, "3d", "罐装机图片")
DST_DIR = os.path.join(REPO_ROOT, "sierac-twin", "public", "images")

# 14 files: 前/后/左/右/上/下, 左上角/右上角, 左下/右下, 后左上/后右上/后左下/后右下
# -> design: front, back, left, right, top, bottom, top-left, top-right,
#            front-left, front-right, top-back, back-right, back-left, top-front
NAME_MAP = {
    "前": "front",
    "后": "back",
    "左": "left",
    "右": "right",
    "上": "top",
    "下": "bottom",
    "左上角": "top-left",
    "右上角": "top-right",
    "左下": "front-left",
    "右下": "front-right",
    "后左上": "top-back",
    "后右上": "back-right",
    "后左下": "back-left",
    "后右下": "top-front",  # use as top-front view
}


def main() -> None:
    if not os.path.isdir(SRC_DIR):
        print(f"Source dir not found: {SRC_DIR}")
        return
    os.makedirs(DST_DIR, exist_ok=True)

    copied = 0
    for name in sorted(os.listdir(SRC_DIR)):
        if not name.lower().endswith(".png"):
            continue
        base = name[:-4]
        en = NAME_MAP.get(base)
        if not en:
            print(f"  skip (no mapping): {name}")
            continue
        src = os.path.join(SRC_DIR, name)
        dst = os.path.join(DST_DIR, f"{en}.png")
        shutil.copy2(src, dst)
        print(f"  {name} -> {en}.png")
        copied += 1
    print(f"Copied {copied} files to {DST_DIR}")


if __name__ == "__main__":
    main()
