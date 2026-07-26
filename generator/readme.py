"""README assembly.

The document is built by string composition rather than a template engine.
That is a deliberate reduction of moving parts: there is no template syntax to
get wrong, no autoescape setting to forget, and no third-party dependency in
the path between untrusted API data and published Markdown. Every interpolated
value goes through :mod:`generator.sanitize` first.
"""

from __future__ import annotations

from .sanitize import (
    clamp,
    human_count,
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


def build(cfg, snap, versions: dict[str, str], pill_slugs: list[tuple[str, object]],
          built: str) -> str:
    out: list[str] = [MARKER, ""]

    # ---- masthead -------------------------------------------------------
    out.append('<div align="center">')
    out.append("")
    out.append(
        _picture(
            "hero",
            f"{md_text(cfg.display_name, 80)} — {md_text(cfg.headline, 80)}",
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
        out.append(f"- {md_text(item, 200)}")
    out.append("")

    # ---- telemetry ------------------------------------------------------
    out.append("## Telemetry")
    out.append("")
    out.append(
        _picture(
            "telemetry",
            "GitHub telemetry: repositories, stars, commit activity and language mix",
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
    rows = (
        ("Public repositories (non-fork)", human_count(snap.own_repos or snap.public_repos)),
        ("Stars earned", human_count(snap.total_stars)),
        ("Commits, trailing 52 weeks", human_count(snap.activity_total)),
        ("Followers", human_count(snap.followers)),
        ("Years on GitHub", f"{snap.account_age_years:g}"),
        ("Last public push", snap.last_push or "unknown"),
        ("Snapshot", f"{built} ({'live' if snap.live else 'cached'})"),
    )
    for label, value in rows:
        out.append(f"| {md_cell(label)} | {md_cell(value)} |")
    if snap.languages:
        out.append("")
        out.append("| Language | Share |")
        out.append("| --- | --- |")
        total = sum(clamp(item.get("share"), 0, 1) for item in snap.languages) or 1.0
        for item in snap.languages[:5]:
            share = clamp(item.get("share"), 0, 1) / total * 100
            out.append(f"| {md_cell(item.get('name'))} | {share:.0f}% |")
    out.append("")
    out.append("</details>")
    out.append("")

    # ---- stack ----------------------------------------------------------
    out.append("## Build surface")
    out.append("")
    out.append(_picture("stack", "Technology stack grouped by domain", versions))
    out.append("")

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

    # ---- security practice ---------------------------------------------
    out.append("## Security practice")
    out.append("")
    for practice in cfg.practices:
        out.append(f"**{md_text(practice.label, 120)}** — {md_text(practice.detail, 400)}")
        out.append("")

    # ---- the pipeline ---------------------------------------------------
    out.append("## How this page builds itself")
    out.append("")
    out.append(
        "This README is not hand-written. A scheduled workflow queries the GitHub "
        "API, renders every image in this repository, and commits the result only "
        "if the bytes changed."
    )
    out.append("")
    out.append(
        _picture("pipeline", "Build pipeline and the security controls at each stage", versions)
    )
    out.append("")
    out.append(
        "A profile README is a program with write access to a repository, so it is "
        "worth treating like one:"
    )
    out.append("")
    out.append(
        "- **No untrusted trigger.** The workflow runs on `schedule`, on manual "
        "dispatch, and on pushes to `main`. It never runs on `pull_request_target` "
        "or `issue_comment`, the two triggers behind most Actions token-theft "
        "incidents."
    )
    out.append(
        "- **No third-party runtime dependencies.** The generator is standard "
        "library Python. There is no `pip install` step in CI, so there is no "
        "package to typosquat or compromise."
    )
    out.append(
        "- **Least privilege.** Default permissions are empty; the single job that "
        "publishes is granted `contents: write` and nothing else. No personal "
        "access token is stored."
    )
    out.append(
        "- **Everything escaped at the boundary.** Repository names and "
        "descriptions come back from the API as untrusted strings and are encoded "
        "for their sink — Markdown or XML — before they reach it."
    )
    out.append(
        "- **Bounded egress.** Exactly one host is reachable, redirects are "
        "refused, and responses are capped and timed out."
    )
    out.append("")
    out.append(
        "The full write-up, including the residual risks I chose to accept and why, "
        "is in [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md). The workflow itself is "
        "[here](.github/workflows/build-profile.yml)."
    )
    out.append("")

    # ---- footer ---------------------------------------------------------
    out.append("---")
    out.append("")
    out.append(
        f'<sub>Generated {md_text(built, 40)} · '
        f"{'live snapshot' if snap.live else 'cached snapshot — the API was unreachable at build time'} · "
        f"no third-party trackers, badge services, or analytics on this page.</sub>"
    )
    out.append("")

    return "\n".join(out)
