"""Entry point.

    python3 -m generator                # fetch live data, write README + assets
    python3 -m generator --offline      # render from the cached snapshot only
    python3 -m generator --check        # render to memory and fail if output differs

``--check`` is what pull requests run: it proves the committed output matches
what the current code produces, so a change to the generator cannot silently
diverge from the published page.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import os
import sys
import time
from pathlib import Path

from . import readme as readme_builder
from .cards import hero, pill, stack, telemetry
from .config import ConfigError, load
from .design import PALETTES
from .sanitize import slug
from .sources import github

GLYPH_BY_HOST = {
    "devsirchhub.co.ke": "globe",
    "www.devsirchhub.co.ke": "globe",
    "linkedin.com": "linkedin",
    "www.linkedin.com": "linkedin",
    "tryhackme.com": "shield",
    "hackerone.com": "shield",
    "github.com": "terminal",
    "www.github.com": "terminal",
}
ACCENT_BY_GLYPH = {
    "globe": "accent",
    "linkedin": "cyan",
    "shield": "violet",
    "terminal": "amber",
}


def _host(url: str) -> str:
    return url[len("https://"):].split("/", 1)[0].split(":", 1)[0].lower()


def _version(content: str) -> str:
    """Short content hash used to bust GitHub's image cache."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:10]


def _write(path: Path, content: str) -> bool:
    """Write only if the bytes changed. Returns True when the file was touched."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = content if content.endswith("\n") else content + "\n"
    try:
        if path.read_text("utf-8") == payload:
            return False
    except OSError:
        pass
    # Write via a temporary file in the same directory, then rename, so an
    # interrupted build cannot leave a half-written asset in the repository.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generator", description="Build the profile README.")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--offline", action="store_true",
                        help="skip the network and render from data/cache.json")
    parser.add_argument("--check", action="store_true",
                        help="verify committed output matches a fresh render")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    config_path = root / "profile.json"
    cache_path = root / "data" / "cache.json"
    assets = root / "assets"

    try:
        cfg = load(config_path)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    # The owner of the repository wins over the config file when running in
    # Actions, so a fork builds its own profile rather than someone else's.
    env_user = os.environ.get("PROFILE_USER", "").strip()
    username = cfg.username
    if env_user and env_user.replace("-", "").isalnum() and len(env_user) <= 39:
        username = env_user

    print(f"· building profile for {username}")
    snap = github.resolve(username, cache_path, offline=args.offline or args.check)

    # Guarantee the snapshot exists on disk. Without it the timestamps in
    # the output would come from the wall clock, `--check` could only pass
    # within the same minute as the last build, and the publish step would
    # stage a path that is not there.
    if not args.check and not cache_path.exists():
        github.save_cache(cache_path, snap)

    # Every timestamp in the output derives from the snapshot, never from the
    # wall clock. That makes the build reproducible: re-running the generator
    # against the same committed cache produces byte-identical output, which
    # is what lets `--check` be a meaningful CI gate. It also means the date
    # on the page is the date the data was collected, which is the honest
    # thing to display when a build falls back to cache.
    now_epoch = time.time()
    try:
        parsed = time.strptime((snap.generated_at or "")[:19], "%Y-%m-%dT%H:%M:%S")
        now_epoch = calendar.timegm(parsed)
    except (ValueError, TypeError):
        pass
    built = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(now_epoch))

    # ---- render every asset, for both themes ---------------------------
    rendered: dict[str, str] = {}
    pill_slugs: list[tuple[str, object]] = []

    for p in PALETTES:
        rendered[f"hero-{p.name}"] = hero.render(
            p,
            name=username,
            display_name=cfg.display_name,
            headline=cfg.headline,
            roles=cfg.roles,
            location=cfg.location,
            stars=snap.total_stars,
            repos=snap.own_repos or snap.public_repos,
            followers=snap.followers,
            built=built,
            live=snap.live,
        )
        rendered[f"telemetry-{p.name}"] = telemetry.render(
            p, snap=snap, built=built, now_epoch=now_epoch
        )
        rendered[f"stack-{p.name}"] = stack.render(
            p, groups=cfg.stack, note=f"{sum(len(g.items) for g in cfg.stack)} tools tracked"
        )
        # The pipeline card is not rendered: the README section that carried it
        # was removed. `generator.cards.pipeline` is kept intact -- restore the
        # three lines here and the _picture() call in readme.py to bring it back.
        # Nothing unreferenced is written, so `assets/` has no orphans.

    seen: set[str] = set()
    for link in cfg.links:
        name = slug(link.label, 24)
        while name in seen:
            name += "x"
        seen.add(name)
        pill_slugs.append((name, link))
        glyph = GLYPH_BY_HOST.get(_host(link.url), "globe")
        accent = ACCENT_BY_GLYPH.get(glyph, "accent")
        for p in PALETTES:
            rendered[f"pill-{name}-{p.name}"] = pill.render(
                p, label=link.label, glyph=glyph, accent=accent
            )

    versions = {key: _version(value) for key, value in rendered.items()}
    document = readme_builder.build(cfg, snap, versions, pill_slugs, built)

    # ---- compare or commit ---------------------------------------------
    if args.check:
        stale = []
        for key, content in rendered.items():
            path = assets / f"{key}.svg"
            expected = content if content.endswith("\n") else content + "\n"
            if not path.exists() or path.read_text("utf-8") != expected:
                stale.append(f"assets/{key}.svg")
        readme_path = root / "README.md"
        expected_readme = document if document.endswith("\n") else document + "\n"
        if not readme_path.exists() or readme_path.read_text("utf-8") != expected_readme:
            stale.append("README.md")
        if stale:
            print("out of date, run `make build` and commit the result:", file=sys.stderr)
            for name in stale:
                print(f"  - {name}", file=sys.stderr)
            return 1
        print("· output is up to date")
        return 0

    changed = [key for key, content in rendered.items()
               if _write(assets / f"{key}.svg", content)]
    if _write(root / "README.md", document):
        changed.append("README.md")

    print(f"· {len(rendered)} assets rendered, {len(changed)} file(s) changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
