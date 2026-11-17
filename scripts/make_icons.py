"""Generate the app icons: python3 scripts/make_icons.py [out_dir]

The Cast mark (the corner of a screen with waves coming out of it) on a small
grey-green reflective LCD, set in a matte white case: a Braun clock or a first
iPod rather than a glossy hi-fi front. The case has a fine grain and a soft
shadow; the window, shaped like the iOS icon (a squircle), is milled into it
with a lip in shadow at the top and lit at the bottom; the LCD sits behind with
the case's shadow falling inside, and its dark pixels cast a faint shadow on
the reflector.
The unlit pixels are faintly visible, as on a real LCD. The screen's frame is
what tells the mark apart from an RSS feed icon.

Each icon is written as an SVG, then rasterised with the Chromium that
Playwright installs for the frontend's e2e tests (frontend/node_modules).
- icon-192/512: the case as a squircle, with its shadow (purpose "any").
- maskable-512: the case fills the canvas, the LCD inside the 80% safe zone.
- apple-touch-icon: the case fills the canvas (iOS rounds the corners).
- icon.svg: the same as icon-512, as a vector, for other uses.
- favicon.svg / favicon-32.png: the icon, small: case, window and rim, and
  the mark solid (too small for pixels); the same on light and dark tabs.
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
WINDOW = 0.70  # the LCD's side as a share of the case's
CASE = [(0, "#fdfcf9"), (1, "#dedbd4")]  # matte white, lit from above
LCD = ("#c4cbb2", "#a9b195")  # the reflector, lighter in the middle
PIXEL = ("#2b3328", "#1b2219")  # a dark pixel, a little lighter at the top


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


def squircle(x: float, y: float, w: float, h: float, n: float = 5.0, steps: int = 240) -> str:
    """A superellipse path, close to the iOS icon shape (continuous corners)."""
    cx, cy, a, b = x + w / 2, y + h / 2, w / 2, h / 2
    points = []
    for k in range(steps):
        t = 2 * math.pi * k / steps
        c, s = math.cos(t), math.sin(t)
        points.append(f"{cx + a * math.copysign(abs(c) ** (2 / n), c):.2f},{cy + b * math.copysign(abs(s) ** (2 / n), s):.2f}")
    return "M" + " L".join(points) + " Z"


def icon(size: int, bleed: bool, window: float) -> str:
    """bleed: the case fills the square canvas, without shadow (the platform
    crops it to its own shape); otherwise a squircle case with a margin for its
    shadow. window: the LCD's side as a share of the case's. The window has
    the case's shape, so it sits in the iOS icon like a smaller icon; its lip
    and inner shadow are wide enough to read at home-screen size."""
    if bleed:
        bx, by, bw = 0.0, 0.0, float(size)
    else:
        k = size / 512
        bx, by, bw = 28 * k, 22 * k, 456 * k
    u = bw / 1024  # the design's unit: drawn on a 1024 case
    dw = bw * window
    dx, dy = bx + (bw - dw) / 2, by + (bw - dw) / 2
    case_path = squircle(bx, by, bw, bw)
    win = squircle(dx, dy, dw, dw)
    lip = 31 * u
    lit = mark(LCD_GRID)
    pad = dw * 0.08
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
        f'<circle cx="{rnd.uniform(bx, bx + bw):.1f}" cy="{rnd.uniform(by, by + bw):.1f}" r="{1.6 * u:.2f}" '
        f'fill="{rnd.choice(("#000", "#fff"))}" opacity=".05"/>'
        for _ in range(2500)
    )
    defs = [
        grad("case", CASE),
        f'<radialGradient id="lcd" cx=".5" cy=".45" r=".8"><stop offset="0" stop-color="{LCD[0]}"/>'
        f'<stop offset="1" stop-color="{LCD[1]}"/></radialGradient>',
        grad("pixel", [(0, PIXEL[0]), (1, PIXEL[1])]),
        # The lip milled around the window: in shadow at the top, lit at the bottom.
        grad("lip", [(0, "rgba(0,0,0,.5)"), (0.55, "rgba(0,0,0,.07)"), (1, "rgba(255,255,255,1)")]),
        grad("sheen", [(0, "rgba(255,255,255,.28)"), (0.5, "rgba(255,255,255,0)")]),
        f'<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="{18 * u:.2f}"/></filter>',
        f'<filter id="drop" x="-15%" y="-15%" width="130%" height="135%"><feGaussianBlur in="SourceAlpha" stdDeviation="{20 * u:.2f}"/>'
        f'<feOffset dy="{18 * u:.2f}"/><feComponentTransfer><feFuncA type="linear" slope=".32"/></feComponentTransfer>'
        "<feMerge><feMergeNode/><feMergeNode in=\"SourceGraphic\"/></feMerge></filter>",
        f'<clipPath id="body"><path d="{case_path}"/></clipPath>',
        f'<clipPath id="win"><path d="{win}"/></clipPath>',
    ]
    if bleed:
        case = f'<rect width="{size}" height="{size}" fill="url(#case)"/>'
        parts = [case, grain]
    else:
        case = f'<path d="{case_path}" fill="url(#case)"/>'
        parts = [
            f'<g filter="url(#drop)">{case}</g>',
            f'<g clip-path="url(#body)">{grain}</g>',
            f'<path d="{case_path}" fill="none" stroke="#000" stroke-opacity=".16" stroke-width="{2 * u:.2f}"/>',
        ]
    parts += [
        f'<path d="{squircle(dx - lip, dy - lip, dw + 2 * lip, dw + 2 * lip)}" fill="url(#lip)"/>',
        f'<path d="{win}" fill="url(#lcd)"/>',
        '<g clip-path="url(#win)">',
        f'<g fill="{PIXEL[1]}" opacity=".08">{pixels(False)}</g>',
        f'<g fill="#000" opacity=".2" transform="translate({4 * u:.2f} {6 * u:.2f})">{pixels(True)}</g>',
        f'<g fill="url(#pixel)">{pixels(True)}</g>',
        # The case's shadow falling inside the window, deeper at the top.
        f'<path d="{win}" fill="none" stroke="#000" stroke-opacity=".66" stroke-width="{72 * u:.2f}" '
        f'filter="url(#soft)" transform="translate(0 {12 * u:.2f})"/>',
        f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dw}" fill="url(#sheen)"/>',
        "</g>",
        f'<path d="{win}" fill="none" stroke="#000" stroke-opacity=".35" stroke-width="{3 * u:.2f}"/>',
    ]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">'
        f'<defs>{"".join(defs)}</defs>{"".join(parts)}</svg>\n'
    )


def favicon_svg() -> str:
    """The icon, small: the white case and its squircle window, the lip as a
    thin rim (dark at the top, light at the bottom), and the mark as solid
    squares on the LCD (pixels would blur at 16px). On a 32 grid, one square
    per pixel at 32px. Readable on light and dark tabs alike."""
    lit = mark(GRID)
    shift = 4  # the mark (18 x 16 squares) centred in the 26-wide window at 3
    rects = []
    for j in range(GRID):
        i = 0
        while i < GRID:
            if (i, j) in lit:
                start = i
                while (i, j) in lit:
                    i += 1
                rects.append(f'<rect x="{start + shift}" y="{j + shift}" width="{i - start}" height="1"/>')
            else:
                i += 1
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        "<defs>"
        + grad("c", CASE)
        + grad("l", [(0, "#5f6457"), (0.5, "#b7b9b0"), (1, "#ffffff")])
        + f'<radialGradient id="s" cx=".5" cy=".4" r=".8"><stop offset="0" stop-color="{LCD[0]}"/>'
        f'<stop offset="1" stop-color="{LCD[1]}"/></radialGradient>'
        "</defs>"
        f'<path d="{squircle(0.5, 0.5, 31, 31, steps=96)}" fill="url(#c)" stroke="#000" stroke-opacity=".3"/>'
        f'<path d="{squircle(2, 2, 28, 28, steps=96)}" fill="url(#l)"/>'
        f'<path d="{squircle(3, 3, 26, 26, steps=96)}" fill="url(#s)"/>'
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
        "icon-192.png": icon(192, bleed=False, window=WINDOW),
        "icon-512.png": icon(512, bleed=False, window=WINDOW),
        # The LCD and its lip inside the central 80% circle (a squircle's
        # corner reaches 1.23 times its half side from the centre).
        "maskable-512.png": icon(512, bleed=True, window=0.56),
        # iOS crops it to its own shape: a full-bleed square.
        "apple-touch-icon.png": icon(180, bleed=True, window=WINDOW),
        "favicon-32.png": favicon_svg().replace('viewBox="0 0 32 32"', 'viewBox="0 0 32 32" width="32" height="32"'),
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
    (out / "icon.svg").write_text(icon(512, bleed=False, window=WINDOW))
    print("wrote", out / "icon.svg")
    (out / "favicon.svg").write_text(favicon_svg())
    print("wrote", out / "favicon.svg")


if __name__ == "__main__":
    main()
