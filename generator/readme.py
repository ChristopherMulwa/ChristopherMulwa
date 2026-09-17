"""README assembly.

The document is built by string composition rather than a template engine.
That is a deliberate reduction of moving parts: there is no template syntax to
get wrong, no autoescape setting to forget, and no third-party dependency in
the path between untrusted API data and published Markdown. Every interpolated
value goes through :mod:`generator.sanitize` first.
"""

from __future__ import annotations

from .cards.telemetry import telemetry_rows
from .sanitize import (
    md_cell,
    md_code,
    md_link,
    md_text,
    safe_url,
)

MARKER = (
    "<!--\n"
    "  This file is generated. Do not edit it directly -- the next scheduled\n"
    "  build will overwrite your changes.\n"
    "\n"
    "    content   ->  profile.json\n"
    "    layout    ->  generator/\n"
    "    schedule  ->  .github/workflows/build-profile.yml\n"
    "\n"
    "  Regenerate locally with:  make build   (or: python3 -m generator --offline)\n"
    "-->"
)

STATUS_LABEL = {
    "live": "live",
    "building": "in build",
    "paused": "paused",
    "design": "in design",
    "archived": "archived",
    "private": "private",
}


def _picture(name: str, alt: str, versions: dict[str, str], width: str = "100%") -> str:
    """Dark/light responsive image.

    GitHub honours ``<picture>`` with a ``prefers-color-scheme`` media query,
    which is the only reliable way to serve different assets per theme; the
    older ``#gh-dark-mode-only`` fragment trick no longer works.

    The ``?v=`` query carries a content hash. GitHub proxies images through a
    caching layer keyed on URL, so without it a regenerated asset can stay
    stale for hours.
    """
    dark = f"assets/{name}-dark.svg?v={versions[f'{name}-dark']}"
    light = f"assets/{name}-light.svg?v={versions[f'{name}-light']}"
    return (
        "<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" srcset="{dark}">\n'
        f'  <source media="(prefers-color-scheme: light)" srcset="{light}">\n'
        f'  <img alt="{alt}" src="{dark}" width="{width}">\n'
        "</picture>"
    )


def _pill(slug_name: str, link, versions: dict[str, str]) -> str:
    dark = f"assets/pill-{slug_name}-dark.svg?v={versions[f'pill-{slug_name}-dark']}"
    light = f"assets/pill-{slug_name}-light.svg?v={versions[f'pill-{slug_name}-light']}"
    alt = md_text(link.label, 60).replace('"', "")
    url = safe_url(link.url)
    inner = (
        "<picture>"
        f'<source media="(prefers-color-scheme: dark)" srcset="{dark}">'
        f'<source media="(prefers-color-scheme: light)" srcset="{light}">'
        f'<img alt="{alt}" src="{dark}" height="32">'
        "</picture>"
    )
    return f'<a href="{url}">{inner}</a>' if url else inner


def _practice_block(out: list[str], items) -> None:
    """Bold lead-in, then the detail. The lead-in ends in a period rather than
    a dash so it reads as a sentence, not a form field."""
    for item in items:
        line = md_text(item.detail, 600)
        if item.label.strip():
            label = md_text(item.label, 120).rstrip(".")
            line = f"**{label}.** {line}"
        if item.url:
            line += " " + md_link(item.url_label or item.url.replace("https://", ""), item.url)
        out.append(line)
        out.append("")


def build(cfg, snap, versions: dict[str, str], pill_slugs: list[tuple[str, object]],
          built: str) -> str:
    out: list[str] = [MARKER, ""]

    # ---- masthead -------------------------------------------------------
    out.append('<div align="center">')
    out.append("")
    out.append(
        _picture(
            "hero",
            md_text(cfg.display_name, 80)
            + (f": {md_text(cfg.headline, 80)}" if cfg.headline.strip() else ""),
            versions,
        )
    )
    out.append("")
    out.append("&nbsp;")
    out.append("")
    out.append("".join(_pill(s, link, versions) for s, link in pill_slugs))
    out.append("")
    out.append("</div>")
    out.append("")

    # ---- whoami ---------------------------------------------------------
    out.append("## whoami")
    out.append("")
    out.append(md_text(cfg.summary, 1200))
    out.append("")
    for item in cfg.focus:
        out.append(f"- {md_text(item, 280)}")
    out.append("")
    if cfg.aside:
        out.append(f"> {md_text(cfg.aside, 600)}")
        out.append("")

    # ---- telemetry ------------------------------------------------------
    out.append("## Activity")
    out.append("")
    out.append(
        _picture(
            "telemetry",
            "GitHub telemetry: contributions across public and private repositories, "
            "weekly activity, and work by type",
            versions,
        )
    )
    out.append("")
    out.append("<details>")
    out.append(
        "<summary>Same numbers as text "
        "(for screen readers, and for when images are blocked)</summary>"
    )
    out.append("")
    out.append("| Metric | Value |")
    out.append("| --- | --- |")
    for label, value in telemetry_rows(snap, built):
        out.append(f"| {md_cell(label)} | {md_cell(value)} |")
    out.append("")
    out.append("</details>")
    out.append("")

    # ---- security practice ---------------------------------------------
    out.append("## Security practice")
    out.append("")
    _practice_block(out, cfg.practices)

    # ---- working method -------------------------------------------------
    if cfg.workflow:
        out.append("## How I work")
        out.append("")
        _practice_block(out, cfg.workflow)

    # ---- projects -------------------------------------------------------
    out.append("## Shipping")
    out.append("")
    for project in cfg.projects:
        status = STATUS_LABEL.get(project.status, project.status)
        heading = md_text(project.name, 80)
        out.append(f"### {heading} &nbsp;·&nbsp; `{md_code(status, 20)}`")
        out.append("")
        out.append(f"**{md_text(project.tagline, 160)}**")
        out.append("")
        out.append(md_text(project.detail, 600))
        out.append("")
        if project.stack:
            out.append(" ".join(f"`{md_code(item, 32)}`" for item in project.stack))
            out.append("")
        if project.url:
            out.append(md_link(project.url.replace("https://", ""), project.url))
            out.append("")

    # ---- stack ----------------------------------------------------------
    out.append("## Stack")
    out.append("")
    out.append(_picture("stack", "Technology stack grouped by domain", versions))
    out.append("")

    # ---- learning -------------------------------------------------------
    if cfg.learning:
        out.append("## Learning")
        out.append("")
        for item in cfg.learning:
            out.append(f"- {md_text(item, 280)}")
        out.append("")

    # ---- no self-description --------------------------------------------
    # There was a "How this page builds itself" section here: the pipeline
    # diagram, five prose bullets restating it, and a link to the threat model.
    # Removed deliberately. It was the largest block of prose on the page --
    # more words than all four shipped products combined -- and it described
    # the build system rather than the work. The repository documents itself
    # for anyone who looks; the page does not need to argue the case.
    #
    # The footer still records that the document is generated and when. To
    # reinstate the card, render `pipeline` in __main__.py and place it here
    # with _picture(); generator/cards/pipeline.py is untouched.

    # ---- footer ---------------------------------------------------------
    out.append("---")
    out.append("")
    out.append(
        f'<sub>Generated {md_text(built, 40)} · '
        f"{'live snapshot' if snap.live else 'cached snapshot, the API was unreachable at build time'} · "
        f"no third-party trackers, badge services, or analytics on this page.</sub>"
    )
    out.append("")

    return "\n".join(out)
