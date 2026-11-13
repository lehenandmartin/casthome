"""Generate the PWA icons (no dependencies): python3 scripts/make_icons.py

Draws a "cast" glyph (three arcs and a dot) on a dark rounded square.
Maskable variants keep the glyph inside the 80% safe zone and fill the canvas.
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "icons"
BG = (16, 20, 24)
FG = (106, 160, 255)


def coverage(distance: float) -> float:
    """Anti-aliased coverage for a signed distance (negative = inside)."""
    return max(0.0, min(1.0, 0.5 - distance))


def render(size: int, maskable: bool) -> bytes:
    s = size / 512  # design grid is 512 px
    radius = 0 if maskable else 112 * s
    glyph_scale = 0.62 if maskable else 0.8
    # Arc centre (bottom-left of the glyph). The glyph spans -52..302 design px
    # on both axes, so offsetting by 125 centres it.
    cx = size / 2 - 125 * s * glyph_scale
    cy = size / 2 + 125 * s * glyph_scale
    arcs = [r * s * glyph_scale for r in (110, 195, 280)]
    stroke = 44 * s * glyph_scale
    dot = 52 * s * glyph_scale
    rows = []
    for y in range(size):
        row = bytearray([0])  # filter type 0
        py = y + 0.5
        for x in range(size):
            px = x + 0.5
            # Rounded-square background alpha.
            if radius:
                qx = max(abs(px - size / 2) - (size / 2 - radius), 0)
                qy = max(abs(py - size / 2) - (size / 2 - radius), 0)
                bg_alpha = coverage(math.hypot(qx, qy) - radius)
            else:
                bg_alpha = 1.0
            dx, dy = px - cx, cy - py  # dy grows upwards
            fg = 0.0
            if dx >= -stroke / 2 and dy >= -stroke / 2:
                dist = math.hypot(dx, dy)
                for r in arcs:
                    fg = max(fg, coverage(abs(dist - r) - stroke / 2))
            fg = max(fg, coverage(math.hypot(dx, dy) - dot))
            fg *= bg_alpha
            r_, g_, b_ = (round(BG[i] * (1 - fg) + FG[i] * fg) for i in range(3))
            row += bytes((r_, g_, b_, round(255 * bg_alpha)))
        rows.append(bytes(row))
    return png(size, size, b"".join(rows))


def png(width: int, height: int, raw: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    targets = {
        "icon-192.png": (192, False),
        "icon-512.png": (512, False),
        "maskable-512.png": (512, True),
        # iOS applies its own rounding: give it a full-bleed square.
        "apple-touch-icon.png": (180, True),
        "favicon-32.png": (32, False),
    }
    for name, (size, maskable) in targets.items():
        (OUT / name).write_bytes(render(size, maskable))
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
