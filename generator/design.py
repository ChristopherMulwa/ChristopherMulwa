"""Design tokens and SVG primitives.

Every asset in ``assets/`` is generated here. Nothing is fetched from a
third-party image service at render time, which means:

  * no external host sees a request every time someone loads the profile
  * the page cannot break, or change content, because someone else's service
    changed
  * the bytes GitHub serves are the bytes in this repository

Constraints the renderer works under, because SVGs embedded via ``<img>`` are
loaded in a restricted context by the browser:

  * no ``<script>``  -- it will not execute, and GitHub strips it anyway
  * no external references (fonts, images, stylesheets) -- they will not load
  * CSS ``@keyframes`` inside an inline ``<style>`` *do* animate

Text is laid out without a font metrics engine, so the type scale is
monospace-first and widths are computed from a fixed advance ratio. Anywhere a
proportional face is used, the layout is centred or left-aligned with slack so
a metric mismatch degrades gracefully.
"""

from __future__ import annotations

from dataclasses import dataclass

from .sanitize import xml_attr, xml_text

# ---------------------------------------------------------------------------
# Type
# ---------------------------------------------------------------------------
# System stacks only. A web font would require an external fetch that an
# <img>-embedded SVG is not permitted to make.
MONO = (
    "ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,"
    "'DejaVu Sans Mono','Liberation Mono',monospace"
)
SANS = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,"
    "'Helvetica Neue',Arial,sans-serif"
)

# Advance width of a monospace glyph as a fraction of font-size. Near-universal
# across the stack above; layout tolerances assume +/-4%.
MONO_ADVANCE = 0.6


def mono_width(text: str, size: float) -> float:
    """Width in user units of ``text`` set in the monospace stack."""
    return len(text) * size * MONO_ADVANCE


# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Palette:
    name: str
    canvas: str
    surface: str
    surface_alt: str
    border: str
    grid: str
    text: str
    muted: str
    faint: str
    accent: str
    accent_soft: str
    cyan: str
    violet: str
    amber: str
    rose: str
    # Five-stop ramp for the contribution heat map, coldest first.
    heat: tuple[str, str, str, str, str]


DARK = Palette(
    name="dark",
    canvas="#0A0E14",
    surface="#10151D",
    surface_alt="#161C26",
    border="#212A36",
    grid="#141A23",
    text="#E6EDF3",
    muted="#8695A8",
    faint="#5A6675",
    accent="#22C55E",
    accent_soft="#134E2A",
    cyan="#22D3EE",
    violet="#A78BFA",
    amber="#F59E0B",
    rose="#FB7185",
    heat=("#161C26", "#134E2A", "#166F3C", "#22A34E", "#4ADE80"),
)

LIGHT = Palette(
    name="light",
    canvas="#FFFFFF",
    surface="#F7F9FB",
    surface_alt="#EDF1F6",
    border="#D5DDE6",
    grid="#E7ECF2",
    text="#0B1117",
    muted="#5A6675",
    faint="#8695A8",
    accent="#15803D",
    accent_soft="#BBF7D0",
    cyan="#0E7490",
    violet="#6D28D9",
    amber="#B45309",
    rose="#BE123C",
    heat=("#EBEFF4", "#BBF7D0", "#6EE7A8", "#22A34E", "#15803D"),
)

PALETTES = (DARK, LIGHT)


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


def document(
    *,
    width: float,
    height: float,
    title: str,
    desc: str,
    body: str,
    defs: str = "",
    style: str = "",
) -> str:
    """Wrap rendered content in a complete, accessible SVG document.

    ``role="img"`` plus ``<title>``/``<desc>`` give assistive technology
    something to read when the SVG is embedded directly; the Markdown ``alt``
    attribute covers the ``<img>`` case. Both are populated -- an image-heavy
    profile that is opaque to a screen reader is a broken profile.
    """
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width:g}" height="{height:g}" '
        f'viewBox="0 0 {width:g} {height:g}" '
        f'role="img" aria-labelledby="t d" font-family="{MONO}">',
        f'<title id="t">{xml_text(title)}</title>',
        f'<desc id="d">{xml_text(desc)}</desc>',
    ]
    if defs:
        parts.append(f"<defs>{defs}</defs>")
    if style:
        # CDATA keeps ">" and "&" in selectors from breaking XML parsing.
        parts.append(f"<style>/*<![CDATA[*/{style}/*]]>*/</style>")
    parts.append(body)
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def rect(
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: str = "none",
    stroke: str = "",
    rx: float = 0,
    opacity: float = 1.0,
    stroke_width: float = 1,
    extra: str = "",
) -> str:
    bits = [f'<rect x="{x:g}" y="{y:g}" width="{max(w, 0):g}" height="{max(h, 0):g}"']
    if rx:
        bits.append(f'rx="{rx:g}"')
    bits.append(f'fill="{xml_attr(fill)}"')
    if stroke:
        bits.append(f'stroke="{xml_attr(stroke)}" stroke-width="{stroke_width:g}"')
    if opacity != 1.0:
        bits.append(f'opacity="{opacity:g}"')
    if extra:
        bits.append(extra)
    return " ".join(bits) + "/>"


def text(
    content: str,
    x: float,
    y: float,
    *,
    size: float = 12,
    fill: str = "#fff",
    family: str = MONO,
    weight: str = "400",
    anchor: str = "start",
    opacity: float = 1.0,
    letter_spacing: float = 0,
    extra: str = "",
) -> str:
    bits = [
        f'<text x="{x:g}" y="{y:g}" font-size="{size:g}"',
        f'fill="{xml_attr(fill)}" font-family="{family}"',
    ]
    if weight != "400":
        bits.append(f'font-weight="{xml_attr(weight)}"')
    if anchor != "start":
        bits.append(f'text-anchor="{anchor}"')
    if opacity != 1.0:
        bits.append(f'opacity="{opacity:g}"')
    if letter_spacing:
        bits.append(f'letter-spacing="{letter_spacing:g}"')
    if extra:
        bits.append(extra)
    # xml_text escapes the caller's content; callers must not pre-escape.
    return " ".join(bits) + f">{xml_text(content)}</text>"


def line(
    x1: float, y1: float, x2: float, y2: float, *, stroke: str, width: float = 1,
    opacity: float = 1.0, dash: str = "",
) -> str:
    bits = [
        f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}"',
        f'stroke="{xml_attr(stroke)}" stroke-width="{width:g}"',
    ]
    if opacity != 1.0:
        bits.append(f'opacity="{opacity:g}"')
    if dash:
        bits.append(f'stroke-dasharray="{xml_attr(dash)}"')
    return " ".join(bits) + "/>"


def group(
    content: str,
    *,
    transform: str = "",
    opacity: float = 1.0,
    cls: str = "",
    style: str = "",
) -> str:
    bits = ["<g"]
    if transform:
        bits.append(f'transform="{xml_attr(transform)}"')
    if opacity != 1.0:
        bits.append(f'opacity="{opacity:g}"')
    if cls:
        bits.append(f'class="{xml_attr(cls)}"')
    if style:
        bits.append(f'style="{xml_attr(style)}"')
    return " ".join(bits) + f">{content}</g>"


# ---------------------------------------------------------------------------
# Composites
# ---------------------------------------------------------------------------


def panel(
    x: float,
    y: float,
    w: float,
    h: float,
    p: Palette,
    *,
    label: str = "",
    accent: str = "",
    radius: float = 10,
) -> str:
    """A bordered surface with an optional small-caps label notched into the top edge."""
    accent = accent or p.accent
    out = [
        rect(x, y, w, h, fill=p.surface, stroke=p.border, rx=radius),
        # 2px accent tick in the top-left corner, the recurring motif.
        rect(x + radius, y, 26, 2, fill=accent, opacity=0.9),
    ]
    if label:
        size = 9.5
        pad = 6
        tw = mono_width(label.upper(), size) + pad * 2 + 1.2 * len(label)
        out.append(rect(x + radius + 34, y - 7, tw, 15, fill=p.canvas, rx=4))
        out.append(
            text(
                label.upper(),
                x + radius + 34 + pad,
                y + 3.5,
                size=size,
                fill=p.muted,
                letter_spacing=1.2,
                weight="600",
            )
        )
    return "".join(out)


def grid_backdrop(
    x: float, y: float, w: float, h: float, p: Palette, *, step: float = 22
) -> str:
    """Faint engineering grid. Drawn as a tiled pattern so the file stays small."""
    pid = f"grid-{p.name}"
    pattern = (
        f'<pattern id="{pid}" width="{step:g}" height="{step:g}" '
        f'patternUnits="userSpaceOnUse">'
        f'<path d="M {step:g} 0 L 0 0 0 {step:g}" fill="none" '
        f'stroke="{xml_attr(p.grid)}" stroke-width="1"/></pattern>'
    )
    return pattern, rect(x, y, w, h, fill=f"url(#{pid})")


def chip(
    label: str,
    x: float,
    y: float,
    p: Palette,
    *,
    size: float = 11,
    fill: str = "",
    color: str = "",
    height: float = 24,
    pad: float = 10,
) -> tuple[str, float]:
    """A rounded label. Returns the markup and the width consumed."""
    w = mono_width(label, size) + pad * 2
    out = rect(
        x, y, w, height, fill=fill or p.surface_alt, stroke=p.border, rx=height / 2
    ) + text(
        label,
        x + pad,
        y + height / 2 + size * 0.36,
        size=size,
        fill=color or p.text,
    )
    return out, w


def meter(
    x: float,
    y: float,
    w: float,
    p: Palette,
    *,
    fraction: float,
    color: str = "",
    height: float = 6,
) -> str:
    """A horizontal progress track. ``fraction`` is clamped by the caller."""
    filled = max(0.0, min(1.0, fraction)) * w
    return rect(x, y, w, height, fill=p.surface_alt, rx=height / 2) + rect(
        x, y, filled, height, fill=color or p.accent, rx=height / 2
    )
