"""Generate the PWA icons (no dependencies): python3 scripts/make_icons.py [out_dir]

The Cast mark (the corner of a screen with waves coming out of it) lit in
amber on the dark glass of the app's hi-fi display, drawn with the display's
square dots: the mark's dots are lit, the others faintly visible like unlit
segments. The screen's frame is what tells it apart from an RSS feed icon.
The favicon is too small for dots: the same mark, solid and without the
glass around it so it fills the tab: an SVG in dark amber on light tabs and
bright amber on dark ones, and a PNG in a mid amber for browsers without SVG
favicons.
Maskable variants keep the mark inside the 80% safe zone and fill the canvas.
"""

from __future__ import annotations

import math
import struct
import sys
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "icons"
BG = (20, 19, 18)  # the display's glass, #141312
FG = (242, 164, 58)  # amber, #f2a43a (--lamp in the app)
GHOST = 0.07  # unlit dots: a trace of the amber
GRID = 24  # dots across the icon; the mark is 18 dots wide
DOT = 0.78  # dot size, as a share of its cell
FAVICON_LIGHT = "#b45309"  # amber that reads on a light tab (--lamp, light theme)
FAVICON_DARK = "#f2a43a"  # amber on a dark tab
FAVICON_PNG = (200, 112, 16)  # in between, for the PNG that cannot switch


def mark(grid: int) -> set[tuple[int, int]]:
    """The lit dots: a screen frame two dots thick, open at its bottom-left
    corner, where a dot and two quarter rings (two dots thick) sit."""
    off = (grid - GRID) // 2

    def rect(x0: int, y0: int, x1: int, y1: int) -> set[tuple[int, int]]:
        return {(i, j) for j in range(y0, y1 + 1) for i in range(x0, x1 + 1)}

    cells = rect(3, 4, 20, 19) - rect(5, 6, 18, 17)  # the frame
    cells -= rect(3, 8, 13, 19)  # open where the waves come out
    cx, cy = 4, 18
    for j in range(GRID):
        for i in range(GRID):
            dx, dy = i - cx, cy - j  # dy grows upwards
            dist = math.hypot(dx, dy)
            if dist <= 1.5 or (dx >= 0 and dy >= 0 and any(r - 1 <= dist < r + 1 for r in (4.5, 8))):
                cells.add((i, j))
    return {(i + off, j + off) for i, j in cells}


def coverage(distance: float) -> float:
    """Anti-aliased coverage for a signed distance (negative = inside)."""
    return max(0.0, min(1.0, 0.5 - distance))


def render(size: int, bleed: bool, safe_zone: bool, dots: bool = True) -> list[list[tuple[int, int, int, int]]]:
    """bleed: a full square (the platform rounds it); safe_zone: the mark kept
    inside the central 80% (maskable icons, cropped to any shape); dots: the
    dot matrix, else solid cells (to be reduced for the favicon)."""
    radius = 0 if bleed else 112 * size / 512
    grid = GRID + 6 if safe_zone else GRID
    cell = size / grid
    lit = mark(grid)
    half = cell * (DOT if dots else 1) / 2
    rows = []
    for y in range(size):
        py = y + 0.5
        row = []
        for x in range(size):
            px = x + 0.5
            # Rounded-square background alpha.
            if radius:
                qx = max(abs(px - size / 2) - (size / 2 - radius), 0)
                qy = max(abs(py - size / 2) - (size / 2 - radius), 0)
                bg_alpha = coverage(math.hypot(qx, qy) - radius)
            else:
                bg_alpha = 1.0
            i, j = min(int(px / cell), grid - 1), min(int(py / cell), grid - 1)
            # Square dot centred in its cell.
            ox = abs(px - (i + 0.5) * cell) - half
            oy = abs(py - (j + 0.5) * cell) - half
            fg = coverage(max(ox, oy)) * (1.0 if (i, j) in lit else GHOST if dots else 0.0) * bg_alpha
            r_, g_, b_ = (round(BG[k] * (1 - fg) + FG[k] * fg) for k in range(3))
            row.append((r_, g_, b_, round(255 * bg_alpha)))
        rows.append(row)
    return rows


def reduce(rows: list[list[tuple[int, int, int, int]]], factor: int) -> list[list[tuple[int, int, int, int]]]:
    """Average blocks of factor x factor pixels (a smooth small version)."""
    size = len(rows) // factor
    out = []
    for y in range(size):
        row = []
        for x in range(size):
            block = [rows[y * factor + b][x * factor + a] for b in range(factor) for a in range(factor)]
            alpha = sum(p[3] for p in block)
            if alpha == 0:
                row.append((0, 0, 0, 0))
                continue
            rgb = tuple(round(sum(p[k] * p[3] for p in block) / alpha) for k in range(3))
            row.append((*rgb, round(alpha / len(block))))
        out.append(row)
    return out


def favicon_rows(size: int) -> list[list[tuple[int, int, int, int]]]:
    """The mark alone, solid, filling a transparent square (drawn 4x larger,
    then reduced)."""
    lit = mark(GRID)
    x0, y0, span = 3, 3, 18  # the mark's 18 dots, centred vertically
    big = size * 4
    cell = big / span
    rows = []
    for y in range(big):
        row = []
        for x in range(big):
            on = (x0 + int(x / cell), y0 + int(y / cell)) in lit
            row.append((*FAVICON_PNG, 255) if on else (0, 0, 0, 0))
        rows.append(row)
    return reduce(rows, 4)


def favicon_svg() -> str:
    """The mark as squares, one rectangle per run of lit dots in a row."""
    lit = mark(GRID)
    rects = []
    for j in range(GRID):
        i = 0
        while i < GRID:
            if (i, j) in lit:
                start = i
                while (i, j) in lit:
                    i += 1
                rects.append(f'<rect x="{start}" y="{j}" width="{i - start}" height="1"/>')
            else:
                i += 1
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="3 3 18 18" shape-rendering="crispEdges">'
        f"<style>rect{{fill:{FAVICON_LIGHT}}}"
        f"@media (prefers-color-scheme:dark){{rect{{fill:{FAVICON_DARK}}}}}</style>"
        + "".join(rects)
        + "</svg>\n"
    )


def png(rows: list[list[tuple[int, int, int, int]]]) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\x00" + b"".join(bytes(p) for p in row) for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.mkdir(parents=True, exist_ok=True)
    icons = {
        "icon-192.png": render(192, bleed=False, safe_zone=False),
        "icon-512.png": render(512, bleed=False, safe_zone=False),
        "maskable-512.png": render(512, bleed=True, safe_zone=True),
        # iOS only rounds the corners: a full-bleed square, no safe zone.
        "apple-touch-icon.png": render(180, bleed=True, safe_zone=False),
        "favicon-32.png": favicon_rows(32),
    }
    for name, rows in icons.items():
        (out / name).write_bytes(png(rows))
        print("wrote", out / name)
    (out / "favicon.svg").write_text(favicon_svg())
    print("wrote", out / "favicon.svg")


if __name__ == "__main__":
    main()
