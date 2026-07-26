"""Tech-stack matrix.

Drawn rather than assembled from shields.io badges. Badge services mean dozens
of external requests per page view and a layout that reflows whenever someone
else's CDN is slow. Here the whole grid is measured and laid out in one pass,
so it renders identically every time and costs a single request.
"""

from __future__ import annotations

from ..design import MONO, Palette, document, mono_width, rect, text

W = 920
PAD = 24
LABEL_W = 158
CHIP_H = 27
CHIP_GAP = 7
ROW_GAP = 9
GROUP_GAP = 20
CHIP_FONT = 11.0
CHIP_PAD = 11


def _accent(p: Palette, key: str) -> str:
    return {
        "accent": p.accent,
        "cyan": p.cyan,
        "violet": p.violet,
        "amber": p.amber,
        "rose": p.rose,
    }.get(key, p.accent)


def _wrap(items: tuple[str, ...], width: float) -> list[list[tuple[str, float]]]:
    """Greedy line-breaking over measured chip widths."""
    rows: list[list[tuple[str, float]]] = [[]]
    used = 0.0
    for item in items:
        chip_w = mono_width(item, CHIP_FONT) + CHIP_PAD * 2
        need = chip_w + (CHIP_GAP if rows[-1] else 0)
        if used + need > width and rows[-1]:
            rows.append([])
            used = 0.0
            need = chip_w
        rows[-1].append((item, chip_w))
        used += need
    return [row for row in rows if row]


def measure(groups) -> float:
    chip_area = W - PAD * 2 - LABEL_W
    height = 52.0
    for grp in groups:
        rows = _wrap(grp.items, chip_area)
        block = len(rows) * CHIP_H + (len(rows) - 1) * ROW_GAP
        height += max(block, 30) + GROUP_GAP
    return height - GROUP_GAP + PAD + 6


def render(p: Palette, *, groups, note: str) -> str:
    height = measure(groups)
    chip_area = W - PAD * 2 - LABEL_W

    body = [
        rect(0, 0, W, height, fill=p.canvas, stroke=p.border, rx=12),
        text("BUILD SURFACE", PAD, 30, size=10, fill=p.muted, weight="600",
             letter_spacing=1.8),
        text(note, W - PAD, 30, size=9.5, fill=p.faint, anchor="end"),
    ]

    y = 52.0
    for gi, grp in enumerate(groups):
        colour = _accent(p, grp.accent)
        rows = _wrap(grp.items, chip_area)
        block = len(rows) * CHIP_H + (len(rows) - 1) * ROW_GAP

        # Label column: accent rule + name, vertically centred against the block.
        body.append(rect(PAD, y + 4, 2, max(block - 8, 14), fill=colour, rx=1))
        body.append(text(grp.label.upper(), PAD + 12, y + 17, size=10, fill=p.text,
                         weight="600", letter_spacing=1.1))
        body.append(text(f"{len(grp.items):02d}", PAD + 12, y + 32, size=9,
                         fill=p.faint))

        cy = y
        for row in rows:
            cx = PAD + LABEL_W
            for label, chip_w in row:
                body.append(
                    rect(cx, cy, chip_w, CHIP_H, fill=p.surface, stroke=p.border,
                         rx=6)
                )
                body.append(rect(cx, cy, 2, CHIP_H, fill=colour, rx=1, opacity=0.85))
                body.append(
                    text(label, cx + CHIP_PAD, cy + CHIP_H / 2 + CHIP_FONT * 0.35,
                         size=CHIP_FONT, fill=p.text)
                )
                cx += chip_w + CHIP_GAP
            cy += CHIP_H + ROW_GAP

        y += max(block, 30) + GROUP_GAP

        if gi < len(groups) - 1:
            body.append(
                rect(PAD, y - GROUP_GAP / 2 - 1, W - PAD * 2, 1, fill=p.border,
                     opacity=0.6)
            )

    flat = "; ".join(f"{g.label}: {', '.join(g.items)}" for g in groups)
    return document(
        width=W,
        height=height,
        title="Technology stack",
        desc=f"Tools and technologies grouped by domain. {flat}",
        body="".join(body),
    )
