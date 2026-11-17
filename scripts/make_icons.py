"""Generate the app icons: python3 scripts/make_icons.py [out_dir]

The Cast mark (the corner of a screen with waves coming out of it) on a small
grey-green reflective LCD, set in a matte white case: a Braun clock or a first
iPod rather than a glossy hi-fi front. The case has a fine grain, a soft bevel
and a soft shadow; the window is milled into it, the LCD sits behind with a
soft inner shadow, and its dark pixels cast a faint shadow on the reflector.
The unlit pixels are faintly visible, as on a real LCD. The screen's frame is
what tells the mark apart from an RSS feed icon.

Each icon is written as an SVG, then rasterised with the Chromium that
Playwright installs for the frontend's e2e tests (frontend/node_modules).
- icon-192/512: the case as drawn, rounded, with its shadow (purpose "any").
- maskable-512: the case fills the canvas, the LCD inside the 80% safe zone.
- apple-touch-icon: the case fills the canvas (iOS rounds the corners).
- icon.svg: the same as icon-512, as a vector, for other uses.
- favicon.svg / favicon-32.png: too small for pixels, the solid mark on the
  LCD's grey-green, the same on light and dark tabs.
"""

from __future__ import annotations

import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "icons"
GRID = 24  # the mark's grid; the mark is 18 dots wide
LCD_GRID = 26  # pixels across the LCD, a margin of unlit pixels around the mark
CASE = [(0, "#fbfaf7"), (1, "#e6e4df")]  # matte white, lit from above
LCD = ("#c4cbb2", "#a9b195")  # the reflector, lighter in the middle
PIXEL = ("#2b3328", "#1b2219")  # a dark pixel, a little lighter at the top
BEZEL = "#8d9384"


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


def grad(id_: str, stops: list[tuple[float, str]]) -> str:
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<linearGradient id="{id_}" x1="0" y1="0" x2="0" y2="1">{s}</linearGradient>'


def icon(size: int, bleed: bool, window: float) -> str:
    """bleed: the case fills the square canvas, unrounded and without shadow
    (the platform crops it); otherwise a rounded case with a margin for its
    shadow. window: the LCD's side as a share of the case's."""
    if bleed:
        bx, by, bw, br = 0.0, 0.0, float(size), 0.0
    else:
        k = size / 512
        bx, by, bw = 28 * k, 22 * k, 456 * k
        br = 104 * k
    u = bw / 456  # the design's unit: everything was drawn on a 456 case
    dw = bw * window
    dx, dy = bx + (bw - dw) / 2, by + (bw - dw) / 2
    dr = 20 * u
    lit = mark(LCD_GRID)
    pad = dw * 0.06
    cell = (dw - 2 * pad) / LCD_GRID
    dot = cell * 0.8
    o = (cell - dot) / 2

    def pixels(on: bool) -> str:
        return "".join(
            f'<rect x="{dx + pad + i * cell + o:.2f}" y="{dy + pad + j * cell + o:.2f}" '
            f'width="{dot:.2f}" height="{dot:.2f}" rx="{dot * 0.25:.2f}"/>'
            for j in range(LCD_GRID)
            for i in range(LCD_GRID)
            if ((i, j) in lit) == on
        )

    rnd = random.Random(5)
    grain = "".join(
        f'<circle cx="{rnd.uniform(bx, bx + bw):.1f}" cy="{rnd.uniform(by, by + bw):.1f}" r="{0.8 * u:.2f}" '
        f'fill="{rnd.choice(("#000", "#fff"))}" opacity=".06"/>'
        for _ in range(1600)
    )
    lip = 7 * u
    defs = [
        grad("case", CASE),
        f'<radialGradient id="lcd" cx=".5" cy=".55" r=".75"><stop offset="0" stop-color="{LCD[0]}"/>'
        f'<stop offset="1" stop-color="{LCD[1]}"/></radialGradient>',
        grad("pixel", [(0, PIXEL[0]), (1, PIXEL[1])]),
        grad("bevel", [(0, "rgba(255,255,255,.9)"), (0.12, "rgba(255,255,255,0)"), (0.88, "rgba(0,0,0,0)"), (1, "rgba(0,0,0,.25)")]),
        grad("lip", [(0, "rgba(0,0,0,.35)"), (0.5, "rgba(0,0,0,.05)"), (1, "rgba(255,255,255,.9)")]),
        grad("sheen", [(0, "rgba(255,255,255,.25)"), (1, "rgba(255,255,255,0)")]),
        f'<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="{6 * u:.2f}"/></filter>',
        f'<filter id="drop" x="-15%" y="-15%" width="130%" height="135%"><feGaussianBlur in="SourceAlpha" stdDeviation="{10 * u:.2f}"/>'
        f'<feOffset dy="{9 * u:.2f}"/><feComponentTransfer><feFuncA type="linear" slope=".32"/></feComponentTransfer>'
        "<feMerge><feMergeNode/><feMergeNode in=\"SourceGraphic\"/></feMerge></filter>",
        f'<clipPath id="body"><rect x="{bx}" y="{by}" width="{bw}" height="{bw}" rx="{br}"/></clipPath>',
        f'<clipPath id="win"><rect x="{dx}" y="{dy}" width="{dw}" height="{dw}" rx="{dr}"/></clipPath>',
    ]
    case = f'<rect x="{bx}" y="{by}" width="{bw}" height="{bw}" rx="{br}" fill="url(#case)"/>'
    parts = [case if bleed else f'<g filter="url(#drop)">{case}</g>', f'<g clip-path="url(#body)">{grain}</g>']
    if not bleed:  # soft bevel: lit top edge, shaded bottom edge
        parts.append(
            f'<rect x="{bx + u}" y="{by + u}" width="{bw - 2 * u}" height="{bw - 2 * u}" rx="{br - u}" '
            f'fill="none" stroke="url(#bevel)" stroke-width="{3 * u:.2f}"/>'
            f'<rect x="{bx + 0.5}" y="{by + 0.5}" width="{bw - 1}" height="{bw - 1}" rx="{br}" fill="none" stroke="#000" stroke-opacity=".18"/>'
        )
    parts += [
        # the window milled into the case, its bezel, the LCD
        f'<rect x="{dx - lip}" y="{dy - lip}" width="{dw + 2 * lip}" height="{dw + 2 * lip}" rx="{dr + lip}" fill="url(#lip)" opacity=".9"/>',
        f'<rect x="{dx - 2 * u}" y="{dy - 2 * u}" width="{dw + 4 * u}" height="{dw + 4 * u}" rx="{dr + 2 * u}" fill="{BEZEL}"/>',
        f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dw}" rx="{dr}" fill="url(#lcd)"/>',
        '<g clip-path="url(#win)">',
        f'<g fill="{PIXEL[1]}" opacity=".07">{pixels(False)}</g>',
        f'<g fill="#000" opacity=".18" transform="translate({1.5 * u:.2f} {2 * u:.2f})">{pixels(True)}</g>',
        f'<g fill="url(#pixel)">{pixels(True)}</g>',
        f'<rect x="{dx - 8 * u}" y="{dy - 5 * u}" width="{dw + 16 * u}" height="{dw + 16 * u}" rx="{dr + 8 * u}" '
        f'fill="none" stroke="#000" stroke-opacity=".25" stroke-width="{16 * u:.2f}" filter="url(#soft)"/>',
        f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dw / 2:.2f}" fill="url(#sheen)"/>',
        "</g>",
    ]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">'
        f'<defs>{"".join(defs)}</defs>{"".join(parts)}</svg>\n'
    )


def favicon_svg() -> str:
    """The mark as solid squares, one rectangle per run of lit dots in a row,
    on a rounded square of the LCD's grey-green."""
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
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        f'<rect width="24" height="24" rx="4" fill="{LCD[0]}"/>'
        f'<g fill="{PIXEL[1]}" shape-rendering="crispEdges">' + "".join(rects) + "</g></svg>\n"
    )


RASTERISE = """
const { chromium } = require('playwright');
(async () => {
  const jobs = JSON.parse(process.argv[1]);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const [svg, png, size] of jobs) {
    await page.setViewportSize({ width: size, height: size });
    await page.goto('file://' + svg);
    await page.screenshot({ path: png, omitBackground: true });
  }
  await browser.close();
})();
"""


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.mkdir(parents=True, exist_ok=True)
    sources = {
        "icon-192.png": icon(192, bleed=False, window=316 / 456),
        "icon-512.png": icon(512, bleed=False, window=316 / 456),
        # The LCD and its lip inside the central 80% circle.
        "maskable-512.png": icon(512, bleed=True, window=0.53),
        # iOS only rounds the corners: a full-bleed square.
        "apple-touch-icon.png": icon(180, bleed=True, window=316 / 456),
        "favicon-32.png": favicon_svg().replace('viewBox="0 0 24 24"', 'viewBox="0 0 24 24" width="32" height="32"'),
    }
    sizes = {"icon-192.png": 192, "icon-512.png": 512, "maskable-512.png": 512, "apple-touch-icon.png": 180, "favicon-32.png": 32}
    with tempfile.TemporaryDirectory() as tmp:
        jobs = []
        for name, svg in sources.items():
            src = Path(tmp) / name.replace(".png", ".svg")
            src.write_text(svg)
            jobs.append([str(src), str((out / name).resolve()), sizes[name]])
        subprocess.run(["node", "-e", RASTERISE, json.dumps(jobs)], cwd=ROOT / "frontend", check=True)
    for name in sources:
        print("wrote", out / name)
    # The full icon as a vector, kept for other uses (docs, store pages).
    (out / "icon.svg").write_text(icon(512, bleed=False, window=316 / 456))
    print("wrote", out / "icon.svg")
    (out / "favicon.svg").write_text(favicon_svg())
    print("wrote", out / "favicon.svg")


if __name__ == "__main__":
    main()
