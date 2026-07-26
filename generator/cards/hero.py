"""Hero banner.

A masthead that reads as an instrument panel rather than a badge collection:
identity on the left, a rotating role ticker, and on the right a radar sweep
standing in for attack-surface monitoring. Both are CSS-animated inside the
SVG.

Do not rely on that animation to display anything. Measured on the published
profile page: GitHub embeds this file with ``<img>``, and the animation does
not run there -- the roles stayed blank and the sweep static across a full
cycle, while the same file opened as a document animates correctly. So every
element must be legible in its unanimated state, and animation is decoration
on top of that. `.role:first-of-type` carries the static fallback.
"""

from __future__ import annotations

import calendar
import hashlib
import math
import time

from ..design import (
    MONO,
    SANS,
    Palette,
    document,
    grid_backdrop,
    group,
    line,
    mono_width,
    rect,
    text,
)
from ..sanitize import clamp, human_count

W, H = 920, 250
PAD = 34
ROLE_SECONDS = 3.4

# Radar placement. Kept as constants because the clearance above the ring is
# load-bearing: the build stamp sits on the baseline at y=38, so anything that
# lifts the ring above y≈46 puts it back through the text.
RADAR_CX = W - 148
RADAR_CY = 145
RADAR_R = 96


def contacts(plots: tuple[tuple[str, str], ...], now_epoch: float,
             p: Palette) -> tuple[tuple[float, float, str, str], ...]:
    """Turn repositories into radar contacts: (degrees, distance, colour, name).

    The blips used to be five hardcoded ``(angle, distance, colour)`` tuples.
    They looked like readings and meant nothing, which is the one thing this
    page should not do. They are now derived from the snapshot:

    * **Bearing** is a stable hash of the repository name, so a repository
      keeps the same position on the dial from one build to the next and the
      dial does not reshuffle itself every night.
    * **Range** is how long ago it was last pushed -- recent work sits near
      the centre, dormant work drifts out to the rim.

    Both are pure functions of ``data/cache.json``, so the render stays
    byte-reproducible and ``--check`` still means something. Colour is
    rotation only; it is not asked to carry meaning.
    """
    wheel = (p.accent, p.cyan, p.violet, p.amber, p.rose)
    out = []
    for i, (name, pushed) in enumerate(plots):
        digest = hashlib.sha256(name.encode("utf-8")).digest()
        degrees = ((digest[0] << 8) | digest[1]) % 360
        age_days = 365.0
        try:
            pushed_at = calendar.timegm(time.strptime(str(pushed)[:10], "%Y-%m-%d"))
            age_days = clamp((now_epoch - pushed_at) / 86400.0, 0.0, 365.0)
        except (ValueError, TypeError):
            pass  # unparseable date -> plotted at the rim, which is honest
        out.append((float(degrees), 0.30 + 0.62 * (age_days / 365.0),
                    wheel[i % len(wheel)], name))
    return tuple(out)


def _radar(cx: float, cy: float, r: float, p: Palette,
           blips: tuple[tuple[float, float, str, str], ...] = ()) -> str:
    """Concentric rings, plotted repositories, and a rotating sweep."""
    out = [
        # Rings
        *[
            f'<circle cx="{cx:g}" cy="{cy:g}" r="{r * f:g}" fill="none" '
            f'stroke="{p.border}" stroke-width="1" opacity="{0.9 - i * 0.16:.2f}"/>'
            for i, f in enumerate((1.0, 0.72, 0.46, 0.22))
        ],
        # Cross hairs
        line(cx - r, cy, cx + r, cy, stroke=p.border, opacity=0.5),
        line(cx, cy - r, cx, cy + r, stroke=p.border, opacity=0.5),
    ]

    for i, (deg, dist, color, name) in enumerate(blips):
        rad = math.radians(deg)
        x = cx + math.cos(rad) * r * dist
        y = cy + math.sin(rad) * r * dist
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" '
            f'class="ping" style="animation-delay:{i * 0.9:.1f}s"><title>{name}</title></circle>'
        )
        # The halo is drawn wider than the dot it surrounds. At r=3 it sat
        # exactly on the dot, so wherever the expand animation does not run
        # the pair rendered as one thick blob rather than a contact.
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="none" stroke="{color}" '
            f'stroke-width="1" opacity="0.55" class="ping-ring" '
            f'style="animation-delay:{i * 0.9:.1f}s"/>'
        )

    # Sweep: a wedge that rotates about the centre.
    sweep = (
        f'<path d="M {cx:g} {cy:g} L {cx + r:g} {cy:g} '
        f'A {r:g} {r:g} 0 0 0 {cx + r * math.cos(math.radians(-52)):.1f} '
        f'{cy + r * math.sin(math.radians(-52)):.1f} Z" '
        f'fill="url(#sweep-{p.name})" class="sweep" '
        f'style="transform-origin:{cx:g}px {cy:g}px"/>'
    )
    out.append(sweep)
    out.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="2.5" fill="{p.accent}"/>')
    return "".join(out)


def render(
    p: Palette,
    *,
    name: str,
    display_name: str,
    headline: str,
    roles: tuple[str, ...],
    location: str,
    stars: int,
    repos: int,
    followers: int,
    built: str,
    live: bool,
    plots: tuple[tuple[str, str], ...] = (),
    now_epoch: float = 0.0,
) -> str:
    roles = roles or ("Engineer",)
    cycle = len(roles) * ROLE_SECONDS
    window = 100.0 / len(roles)

    pattern, backdrop = grid_backdrop(0, 0, W, H, p, step=23)

    defs = (
        pattern
        + f'<linearGradient id="fade-{p.name}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{p.canvas}" stop-opacity="1"/>'
        f'<stop offset="0.62" stop-color="{p.canvas}" stop-opacity="0.55"/>'
        f'<stop offset="1" stop-color="{p.canvas}" stop-opacity="0"/></linearGradient>'
        + f'<linearGradient id="sweep-{p.name}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{p.accent}" stop-opacity="0.34"/>'
        f'<stop offset="1" stop-color="{p.accent}" stop-opacity="0"/></linearGradient>'
        + f'<linearGradient id="rule-{p.name}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{p.accent}"/>'
        f'<stop offset="1" stop-color="{p.accent}" stop-opacity="0"/></linearGradient>'
    )

    style = f"""
.role{{opacity:0;animation:roll {cycle:g}s linear infinite}}
/* The ticker must never be the only way to read a role. Where the animation
   does not run, every .role stays at opacity 0 and the line renders blank --
   which is what happens on the profile page itself, because GitHub embeds
   this file with <img> and the animation does not start there. Keeping the
   first role visible by default costs nothing where the animation does run:
   an infinite animation is always in its active phase, so the animated value
   wins and role one still takes its turn in the cycle. */
.role:first-of-type{{opacity:1}}
@keyframes roll{{
0%{{opacity:0;transform:translateY(5px)}}
{window * 0.09:.2f}%{{opacity:1;transform:translateY(0)}}
{window * 0.82:.2f}%{{opacity:1;transform:translateY(0)}}
{window:.2f}%{{opacity:0;transform:translateY(-5px)}}
100%{{opacity:0}}}}
.sweep{{animation:spin 5.5s linear infinite}}
@keyframes spin{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}
.ping{{animation:pulse 3.6s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}
.ping-ring{{animation:expand 3.6s ease-out infinite;transform-box:fill-box;transform-origin:center}}
@keyframes expand{{0%{{transform:scale(1);opacity:.9}}70%,100%{{transform:scale(3.4);opacity:0}}}}
.beam{{animation:scan 7s ease-in-out infinite}}
@keyframes scan{{0%,100%{{opacity:0}}45%{{opacity:.5}}55%{{opacity:.5}}}}
@media (prefers-reduced-motion:reduce){{
.role,.sweep,.ping,.ping-ring,.beam{{animation:none}}
.role:first-of-type{{opacity:1}}}}
"""

    # Radius and centre are chosen so the outer ring clears the build stamp
    # above it. At r=104 centred on y=131 the ring cut through the timestamp
    # for ~100px of its width, overlapping the glyphs by up to 13px.
    #   ring top    = RADAR_CY - RADAR_R = 49   (stamp ends at y=40)
    #   ring bottom = RADAR_CY + RADAR_R = 241  (card is 250 tall)
    blips = contacts(plots, now_epoch, p)
    body = [
        rect(0, 0, W, H, fill=p.canvas),
        backdrop,
        _radar(RADAR_CX, RADAR_CY, RADAR_R, p, blips),
        rect(0, 0, W, H, fill=f"url(#fade-{p.name})"),
    ]

    # Status strip
    y = PAD + 4
    dot = p.accent if live else p.amber
    body.append(f'<circle cx="{PAD + 3:g}" cy="{y - 4:g}" r="3.5" fill="{dot}"/>')
    body.append(
        f'<circle cx="{PAD + 3:g}" cy="{y - 4:g}" r="3.5" fill="none" stroke="{dot}" '
        f'stroke-width="1" class="ping-ring"/>'
    )
    status = "LIVE TELEMETRY" if live else "CACHED SNAPSHOT"
    body.append(text(status, PAD + 14, y, size=9.5, fill=p.muted, weight="600", letter_spacing=1.6))
    stamp = f"BUILD {built}"
    body.append(
        text(stamp, W - PAD, y, size=9.5, fill=p.faint, anchor="end", letter_spacing=1.4)
    )

    # Name
    body.append(text(f"~/{name}", PAD, y + 38, size=13, fill=p.faint, opacity=0.85))
    body.append(
        text(display_name, PAD, y + 74, size=33, fill=p.text, family=SANS,
             weight="700", letter_spacing=-0.6)
    )

    # Accent rule
    body.append(rect(PAD, y + 88, 190, 2, fill=f"url(#rule-{p.name})"))

    # Role ticker
    for i, role in enumerate(roles):
        body.append(
            group(
                text(role, PAD, y + 118, size=15, fill=p.accent, weight="500"),
                cls="role",
                style=f"animation-delay:{i * ROLE_SECONDS:g}s",
            )
        )

    # Standing tagline, under the rotating roles.
    body.append(
        text(headline, PAD, y + 152, size=14.5, fill=p.muted, family=SANS,
             weight="400")
    )

    # Footer facts
    facts = (
        (location, p.muted),
        (f"{human_count(repos)} public repos", p.muted),
        (f"{human_count(stars)} stars earned", p.muted),
        (f"{human_count(followers)} followers", p.muted),
    )
    x = PAD
    fy = H - PAD + 6
    for i, (label, color) in enumerate(facts):
        if i:
            body.append(text("·", x - 11, fy, size=12, fill=p.faint))
        body.append(text(label, x, fy, size=11.5, fill=color))
        x += mono_width(label, 11.5) + 22

    # Scan beam across the whole banner
    body.append(
        f'<rect x="0" y="{H - 1:g}" width="{W}" height="1" fill="{p.accent}" class="beam"/>'
    )
    body.append(rect(0, 0, W, H, stroke=p.border, rx=12))

    return document(
        width=W,
        height=H,
        title=f"{display_name} — {headline}",
        desc=(
            f"Banner for {display_name}. {', '.join(roles)}. Based in {location}. "
            f"{repos} public repositories, {stars} stars, {followers} followers. "
            + (
                f"The dial plots {len(blips)} public "
                f"{'repository' if len(blips) == 1 else 'repositories'} by how "
                "recently each was pushed: recent work near the centre, dormant "
                f"work toward the rim ({', '.join(b[3] for b in blips)}). "
                if blips else ""
            )
            + f"Generated {built}."
        ),
        defs=defs,
        style=style,
        body="".join(body),
    )
