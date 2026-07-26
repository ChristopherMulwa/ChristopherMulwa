"""Telemetry panel: headline counters, 52-week commit activity, language mix.

This replaces the third-party stat-card services most profiles embed. Those
services are convenient, but each one is an uncontrolled external dependency
that sees a request for every page view, can change what it renders without
notice, and occasionally goes down and leaves a broken image on your profile.
Rendering locally costs a few hundred lines and removes all three problems.
"""

from __future__ import annotations

import time

from ..design import (
    SANS,
    Palette,
    document,
    group,
    line,
    mono_width,
    panel,
    rect,
    text,
)
from ..sanitize import clamp, human_count

W = 920
PAD = 26
TILE_H = 74
TILE_GAP = 12
CHART_Y = 142
CHART_H = 148
H = CHART_Y + CHART_H + 30

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def _month_ticks(now_epoch: float) -> list[tuple[int, str]]:
    """Label the first plotted week of each calendar month.

    Bar ``i`` covers the week ending ``51 - i`` weeks before the build, so the
    axis is anchored to the actual build date rather than a fixed offset.
    """
    ticks: list[tuple[int, str]] = []
    previous = -1
    for i in range(52):
        month = time.gmtime(now_epoch - (51 - i) * 7 * 86400).tm_mon
        if month != previous:
            ticks.append((i, MONTHS[month - 1]))
            previous = month
    return ticks


def _tile(x: float, y: float, w: float, p: Palette, *, value: str, label: str,
          note: str, accent: str) -> str:
    out = [
        rect(x, y, w, TILE_H, fill=p.surface_alt, stroke=p.border, rx=8),
        rect(x, y, 3, TILE_H, fill=accent, rx=1.5),
        text(value, x + 14, y + 32, size=23, fill=p.text, family=SANS, weight="700"),
        text(label.upper(), x + 14, y + 49, size=8.5, fill=p.muted, letter_spacing=1.3,
             weight="600"),
        text(note, x + 14, y + 63, size=9, fill=p.faint),
    ]
    return "".join(out)


def _activity(x: float, y: float, w: float, h: float, p: Palette,
              weeks: list[int], now_epoch: float) -> str:
    series = [int(clamp(v, 0, 5000)) for v in (weeks or [])][-52:]
    if len(series) < 52:
        series = [0] * (52 - len(series)) + series
    peak = max(series) or 1

    inner_x = x + 14
    inner_w = w - 28
    base_y = y + h - 30
    plot_h = h - 62
    pitch = inner_w / 52
    bar_w = max(3.0, pitch - 3)

    out = [
        panel(x, y, w, h, p, label="commit activity · 52w", accent=p.accent),
        text("weekly commits across public repositories", inner_x, y + 30,
             size=9.5, fill=p.faint),
        text(f"peak {peak}", x + w - 14, y + 30, size=9.5, fill=p.muted, anchor="end"),
    ]

    # Reference grid
    for frac in (0.25, 0.5, 0.75, 1.0):
        gy = base_y - plot_h * frac
        out.append(line(inner_x, gy, inner_x + inner_w, gy, stroke=p.border,
                        opacity=0.45, dash="2 4"))

    for i, value in enumerate(series):
        bx = inner_x + i * pitch
        bh = (value / peak) * plot_h
        if bh < 1.6:
            # Zero weeks still get a tick so the axis reads as continuous.
            out.append(rect(bx, base_y - 1.6, bar_w, 1.6, fill=p.border, rx=0.8))
            continue
        intensity = value / peak
        idx = 1 + min(3, int(intensity * 4))
        out.append(rect(bx, base_y - bh, bar_w, bh, fill=p.heat[idx], rx=1.5))

    out.append(line(inner_x, base_y, inner_x + inner_w, base_y, stroke=p.border))

    # Month ticks, anchored to the build date. Labels are dropped rather than
    # overlapped when the pitch is too tight to fit them.
    last_label_x = -999.0
    for index, label in _month_ticks(now_epoch):
        lx = inner_x + index * pitch + bar_w / 2
        if lx - last_label_x < 44:
            continue
        if lx > inner_x + inner_w - 12:
            break
        out.append(line(lx - bar_w / 2 - 1.5, base_y, lx - bar_w / 2 - 1.5,
                        base_y + 4, stroke=p.border))
        out.append(text(label, lx - bar_w / 2 - 1.5, base_y + 16, size=8.5,
                        fill=p.faint, anchor="middle", letter_spacing=0.6))
        last_label_x = lx
    return "".join(out)


def _languages(x: float, y: float, w: float, h: float, p: Palette,
               languages: list[dict]) -> str:
    ramp = (p.accent, p.cyan, p.violet, p.amber, p.rose, p.muted, p.faint)
    entries = []
    for i, item in enumerate(languages[:5]):
        name = str(item.get("name", ""))[:24]
        share = clamp(item.get("share"), 0.0, 1.0)
        if name and share > 0.004:
            entries.append((name, share, ramp[i % len(ramp)]))

    out = [panel(x, y, w, h, p, label="language mix", accent=p.cyan)]

    if not entries:
        out.append(text("no data", x + 14, y + h / 2, size=11, fill=p.faint))
        return "".join(out)

    total = sum(e[1] for e in entries) or 1.0
    bar_x, bar_y, bar_w, bar_h = x + 14, y + 34, w - 28, 10

    # Stacked bar, clipped to a pill so the ends stay rounded.
    clip_id = f"lang-clip-{p.name}"
    out.append(
        f'<clipPath id="{clip_id}"><rect x="{bar_x:g}" y="{bar_y:g}" '
        f'width="{bar_w:g}" height="{bar_h:g}" rx="{bar_h / 2:g}"/></clipPath>'
    )
    seg = []
    cursor = bar_x
    for _, share, color in entries:
        seg_w = bar_w * (share / total)
        seg.append(rect(cursor, bar_y, seg_w + 0.5, bar_h, fill=color))
        cursor += seg_w
    out.append(f'<g clip-path="url(#{clip_id})">{"".join(seg)}</g>')

    # Legend
    ly = bar_y + 32
    for name, share, color in entries:
        pct = f"{share / total * 100:.0f}%"
        out.append(f'<rect x="{bar_x:g}" y="{ly - 7:g}" width="8" height="8" rx="2" fill="{color}"/>')
        out.append(text(name, bar_x + 15, ly, size=10.5, fill=p.text))
        out.append(text(pct, x + w - 14, ly, size=10.5, fill=p.muted, anchor="end"))
        ly += 16.5
    return "".join(out)


def render(p: Palette, *, snap, built: str, now_epoch: float) -> str:
    tiles = (
        (human_count(snap.own_repos or snap.public_repos), "repositories", "public, non-fork", p.accent),
        (human_count(snap.total_stars), "stars earned", "across own repos", p.amber),
        (human_count(snap.activity_total), "commits", "trailing 52 weeks", p.cyan),
        (human_count(snap.followers), "followers", f"following {human_count(snap.following)}", p.violet),
        (f"{snap.account_age_years:g}y", "on github", f"last push {snap.last_push or '—'}", p.rose),
    )

    tile_w = (W - PAD * 2 - TILE_GAP * (len(tiles) - 1)) / len(tiles)
    body = [rect(0, 0, W, H, fill=p.canvas, rx=12, stroke=p.border)]

    body.append(text("TELEMETRY", PAD, 30, size=10, fill=p.muted, weight="600",
                     letter_spacing=1.8))
    label = "live" if snap.live else "cached"
    body.append(text(f"generated {built} · {label}", W - PAD, 30, size=9.5,
                     fill=p.faint, anchor="end"))

    for i, (value, name, note, accent) in enumerate(tiles):
        body.append(
            _tile(PAD + i * (tile_w + TILE_GAP), 44, tile_w, p,
                  value=value, label=name, note=note, accent=accent)
        )

    left_w = 566
    body.append(_activity(PAD, CHART_Y, left_w, CHART_H, p, snap.activity, now_epoch))
    body.append(
        _languages(PAD + left_w + 16, CHART_Y, W - PAD * 2 - left_w - 16, CHART_H, p,
                   snap.languages)
    )

    langs = ", ".join(
        f"{item.get('name')} {clamp(item.get('share'), 0, 1) * 100:.0f}%"
        for item in (snap.languages or [])[:5]
    )
    return document(
        width=W,
        height=H,
        title="GitHub telemetry",
        desc=(
            f"{snap.own_repos} public repositories, {snap.total_stars} stars, "
            f"{snap.activity_total} commits in the last 52 weeks, "
            f"{snap.followers} followers. Language mix: {langs or 'unavailable'}. "
            f"Snapshot generated {built}."
        ),
        body="".join(body),
    )
