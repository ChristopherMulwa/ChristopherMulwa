"""Link pills.

An SVG embedded with ``<img>`` cannot contain a working hyperlink, so each
pill is its own small asset wrapped in a Markdown link. That keeps the badge
look without handing a third-party badge service a request -- and a view
count -- every time someone opens the profile.
"""

from __future__ import annotations

from ..design import Palette, document, mono_width, rect, text

FONT = 11.5
HEIGHT = 32
PAD_X = 16
GLYPH_W = 16


def _glyph(kind: str, x: float, y: float, colour: str) -> str:
    """Simple stroked marks. Drawn as paths so no icon font is needed."""
    s = 5.6
    if kind == "globe":
        return (
            f'<g stroke="{colour}" stroke-width="1.4" fill="none" '
            f'stroke-linecap="round">'
            f'<circle cx="{x:g}" cy="{y:g}" r="{s:g}"/>'
            f'<ellipse cx="{x:g}" cy="{y:g}" rx="{s * 0.5:g}" ry="{s:g}"/>'
            f'<path d="M {x - s:g} {y:g} H {x + s:g}"/></g>'
        )
    if kind == "linkedin":
        return (
            f'<g fill="{colour}">'
            f'<rect x="{x - s:g}" y="{y - s:g}" width="{s * 2:g}" height="{s * 2:g}" '
            f'rx="1.6" fill="none" stroke="{colour}" stroke-width="1.4"/>'
            f'<rect x="{x - 3.2:g}" y="{y - 1.2:g}" width="1.6" height="4"/>'
            f'<rect x="{x - 3.2:g}" y="{y - 3.6:g}" width="1.6" height="1.6"/>'
            f'<path d="M {x - 0.2:g} {y + 2.8:g} v -4 h 1.5 v .7 a 1.9 1.9 0 0 1 3 1.5 '
            f'v 1.8 h -1.5 v -1.6 a .8 .8 0 0 0 -1.5 0 v 1.6 z"/></g>'
        )
    if kind == "shield":
        return (
            f'<path d="M {x:g} {y - s:g} l {s * 0.9:g} {s * 0.4:g} '
            f'v {s * 0.7:g} c 0 {s * 0.7:g} -{s * 0.5:g} {s * 0.9:g} -{s * 0.9:g} {s:g} '
            f'c -{s * 0.4:g} -{s * 0.1:g} -{s * 0.9:g} -{s * 0.3:g} -{s * 0.9:g} -{s:g} '
            f'v -{s * 0.7:g} z" fill="none" stroke="{colour}" stroke-width="1.4" '
            f'stroke-linejoin="round"/>'
        )
    if kind == "terminal":
        return (
            f'<g stroke="{colour}" stroke-width="1.4" fill="none" '
            f'stroke-linecap="round" stroke-linejoin="round">'
            f'<rect x="{x - s:g}" y="{y - s * 0.8:g}" width="{s * 2:g}" '
            f'height="{s * 1.6:g}" rx="1.6"/>'
            f'<path d="M {x - 2.8:g} {y - 1.6:g} l 2 1.6 l -2 1.6"/>'
            f'<path d="M {x + 1.4:g} {y + 2:g} h 2.4"/></g>'
        )
    # Default: a filled dot.
    return f'<circle cx="{x:g}" cy="{y:g}" r="3.4" fill="{colour}"/>'


def render(p: Palette, *, label: str, glyph: str, accent: str) -> str:
    width = PAD_X * 2 + GLYPH_W + mono_width(label, FONT)
    colour = {"accent": p.accent, "cyan": p.cyan, "violet": p.violet,
              "amber": p.amber, "rose": p.rose}.get(accent, p.accent)
    body = (
        rect(0.5, 0.5, width - 1, HEIGHT - 1, fill=p.surface, stroke=p.border,
             rx=(HEIGHT - 1) / 2)
        + _glyph(glyph, PAD_X - 2, HEIGHT / 2, colour)
        + text(label, PAD_X + GLYPH_W - 4, HEIGHT / 2 + FONT * 0.35, size=FONT,
               fill=p.text)
    )
    return document(
        width=width,
        height=HEIGHT,
        title=label,
        desc=f"Link to {label}",
        body=body,
    )
