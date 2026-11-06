# SPDX-License-Identifier: GPL-2.0-only
"""Make an app's icon PNGs (<app>/appicon/<app-id>-<size>.png) from artwork.

    python3 tools/make_icons.py ARTWORK.png APP_ID [APP_FOLDER] [--tile=L,T,SIDE,RADIUS]

e.g. python3 tools/make_icons.py "Neon Purple Audio Mixer Icon.png" sbae9-sbc ~/Projects/SbAe9-SBC

The artwork is a rounded tile on a dark, grainy backdrop with no
transparency. This cuts the tile out along a rounded square (drawn 4x and
scaled down, so the edge is smooth) and saves it at the sizes desktops ask
for. Re-measure TILE if the artwork changes.
"""
import os
import sys

from PIL import Image, ImageDraw

SIZES = (16, 24, 32, 48, 64, 128, 256, 512)
TILE = (76, 74, 1101, 196)          # left, top, side, corner radius (SBC's 1254 px artwork)


def cut(src, tile=TILE):
    left, top, side, radius = tile
    im = Image.open(src).convert("RGBA")
    k = 4
    mask = Image.new("L", (im.width * k, im.height * k), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (left * k, top * k, (left + side) * k - 1, (top + side) * k - 1), radius * k, fill=255)
    im.putalpha(mask.resize(im.size, Image.LANCZOS))
    return im.crop((left, top, left + side, top + side))


def main(src, app_id, app_dir=".", tile=TILE):
    out = os.path.join(app_dir, "appicon")
    image = cut(src, tile)
    os.makedirs(out, exist_ok=True)
    for size in SIZES:
        path = os.path.join(out, f"{app_id}-{size}.png")
        image.resize((size, size), Image.LANCZOS).save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--tile")]
    tile = next((tuple(int(v) for v in a.split("=", 1)[1].split(","))
                 for a in sys.argv[1:] if a.startswith("--tile=")), TILE)
    if len(args) < 2:
        sys.exit(__doc__)
    main(args[0], args[1], args[2] if len(args) > 2 else ".", tile)
