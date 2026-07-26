"""Supply-chain diagram for the build that produces this profile.

A profile README is an odd artefact: it is marketing copy that also happens to
be a program running on GitHub's infrastructure with write access to a
repository. Plenty of them are built by workflows that trigger on
``pull_request_target`` or ``issue_comment`` and interpolate attacker-supplied
strings straight into a ``run:`` block -- which is command execution on the
runner, with the repository token in the environment.

This card documents the controls that keep that from being true here. It is
generated from the same constants the workflow is written against, so it is a
description of the pipeline rather than a claim about it.
"""

from __future__ import annotations

from ..design import SANS, Palette, document, mono_width, rect, text

W = 920
PAD = 24
NODE_Y = 58
NODE_H = 116
NODE_GAP = 14

STAGES = (
    (
        "TRIGGER",
        "accent",
        ("schedule + manual only", "no fork-PR triggers", "concurrency guarded"),
    ),
    (
        "FETCH",
        "cyan",
        ("api.github.com only", "redirects refused", "timeout + size ceiling"),
    ),
    (
        "VALIDATE",
        "violet",
        ("schema-checked config", "unknown keys rejected", "URL host allow-list"),
    ),
    (
        "RENDER",
        "amber",
        ("escaped at every sink", "no eval / no shell", "deterministic output"),
    ),
    (
        "PUBLISH",
        "rose",
        ("contents:write, 1 job", "diff-gated commit", "no secret in artefact"),
    ),
)

CONTROLS = (
    "0 third-party runtime deps",
    "0 third-party actions",
    "default permissions: {}",
    "GITHUB_TOKEN only, no PAT",
    "reproducible byte-for-byte",
    "output audited before publish",
    "threat model in docs/",
)


def _accent(p: Palette, key: str) -> str:
    return {"accent": p.accent, "cyan": p.cyan, "violet": p.violet,
            "amber": p.amber, "rose": p.rose}.get(key, p.accent)


CHIP_FONT = 10.0
CHIP_H = 24
CHIP_PAD = 10
CHIP_GAP = 8
CHIP_ROW_GAP = 8
CONTROLS_Y = NODE_Y + NODE_H + 30


def _chip_rows() -> list[list[tuple[str, float]]]:
    """Lay the control chips out across as many rows as they need.

    Measured up front so nothing is silently dropped off the right edge --
    a card that quietly truncates its own claims would rather undercut the
    point it is making.
    """
    available = W - PAD * 2
    rows: list[list[tuple[str, float]]] = [[]]
    used = 0.0
    for control in CONTROLS:
        chip_w = mono_width(control, CHIP_FONT) + CHIP_PAD * 2 + 12
        need = chip_w + (CHIP_GAP if rows[-1] else 0)
        if used + need > available and rows[-1]:
            rows.append([])
            used = 0.0
            need = chip_w
        rows[-1].append((control, chip_w))
        used += need
    return rows


_ROWS = _chip_rows()
H = CONTROLS_Y + len(_ROWS) * CHIP_H + (len(_ROWS) - 1) * CHIP_ROW_GAP + 26


def render(p: Palette, *, subtitle: str) -> str:
    node_w = (W - PAD * 2 - NODE_GAP * (len(STAGES) - 1)) / len(STAGES)

    body = [
        rect(0, 0, W, H, fill=p.canvas, stroke=p.border, rx=12),
        text("SUPPLY CHAIN", PAD, 30, size=10, fill=p.muted, weight="600",
             letter_spacing=1.8),
        text(subtitle, W - PAD, 30, size=9.5, fill=p.faint, anchor="end"),
        text("how this page rebuilds itself, and what stops it becoming a foothold",
             PAD, 46, size=9.5, fill=p.faint),
    ]

    for i, (name, accent_key, controls) in enumerate(STAGES):
        colour = _accent(p, accent_key)
        x = PAD + i * (node_w + NODE_GAP)

        body.append(rect(x, NODE_Y, node_w, NODE_H, fill=p.surface, stroke=p.border, rx=9))
        body.append(rect(x, NODE_Y, node_w, 2.5, fill=colour, rx=1.25))
        body.append(text(f"{i + 1:02d}", x + node_w - 12, NODE_Y + 24, size=9.5,
                         fill=p.faint, anchor="end"))
        body.append(text(name, x + 12, NODE_Y + 25, size=11.5, fill=p.text,
                         weight="700", letter_spacing=0.9))
        body.append(rect(x + 12, NODE_Y + 33, 22, 1.5, fill=colour, opacity=0.8))

        cy = NODE_Y + 53
        for control in controls:
            body.append(rect(x + 12, cy - 3.6, 3.4, 3.4, fill=colour, rx=0.6))
            body.append(text(control, x + 21, cy, size=8.6, fill=p.muted))
            cy += 15

        if i < len(STAGES) - 1:
            ax = x + node_w + NODE_GAP / 2
            ay = NODE_Y + NODE_H / 2
            body.append(
                f'<path d="M {ax - 4.5:g} {ay - 4:g} L {ax + 2.5:g} {ay:g} '
                f'L {ax - 4.5:g} {ay + 4:g}" fill="none" stroke="{p.faint}" '
                f'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
            )

    body.append(text("CONTROLS IN FORCE", PAD, CONTROLS_Y - 10, size=8.5,
                     fill=p.faint, letter_spacing=1.4, weight="600"))

    row_y = CONTROLS_Y
    for row in _ROWS:
        x = PAD
        for control, chip_w in row:
            body.append(rect(x, row_y, chip_w, CHIP_H, fill=p.surface_alt,
                             stroke=p.border, rx=CHIP_H / 2))
            # Check glyph drawn as a path, so it cannot depend on a font that
            # may not exist on the reader's machine.
            cx, cy = x + CHIP_PAD + 1, row_y + CHIP_H / 2
            body.append(
                f'<path d="M {cx:g} {cy:g} l 2.6 2.8 l 5 -6" fill="none" '
                f'stroke="{p.accent}" stroke-width="1.6" stroke-linecap="round" '
                f'stroke-linejoin="round"/>'
            )
            body.append(text(control, x + CHIP_PAD + 12, cy + CHIP_FONT * 0.35,
                             size=CHIP_FONT, fill=p.text))
            x += chip_w + CHIP_GAP
        row_y += CHIP_H + CHIP_ROW_GAP

    flat = "; ".join(f"{name}: {', '.join(c)}" for name, _, c in STAGES)
    return document(
        width=W,
        height=H,
        title="Build pipeline and its security controls",
        desc=(
            "Five-stage pipeline that regenerates this profile. " + flat +
            ". Controls in force: " + ", ".join(CONTROLS) + "."
        ),
        body="".join(body),
    )
