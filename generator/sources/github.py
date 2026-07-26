"""GitHub data acquisition.

Design rules for this module:

* **stdlib only.** ``urllib.request`` instead of ``requests``. The generator
  has zero third-party runtime dependencies, so the profile's supply chain is
  the Python standard library and nothing else. There is no ``pip install``
  step in CI that an attacker can poison.
* **Egress allow-list.** Exactly one host is contactable. The URL is built
  from validated components; no caller-supplied string is concatenated into a
  path without passing the username allow-list first.
* **Bounded everything.** Connect/read timeouts, a response size ceiling, a
  redirect ban, and a cap on pagination. A hostile or malfunctioning endpoint
  cannot hang the build or exhaust the runner.
* **Never fatal.** Any failure returns the last-known-good snapshot from
  ``data/cache.json``. A rate limit or an outage must degrade the freshness of
  the profile, never its correctness or its availability.
* **No token in output.** The token is read from the environment, used for the
  ``Authorization`` header, and never stored, logged, or rendered.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

API_HOST = "api.github.com"
API_ROOT = f"https://{API_HOST}"
USER_AGENT = "profile-generator (+https://github.com/features/actions)"

CONNECT_TIMEOUT = 10          # seconds
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_PAGES = 4                 # 4 x 100 repositories is well past what we render
MAX_RETRIES = 2
RETRY_BACKOFF = 2.0           # seconds, doubled per attempt

# Languages that describe packaging or markup rather than authored work.
# Excluded from the language mix so the chart reflects engineering, not
# whatever a framework generated.
LANGUAGE_NOISE = frozenset({"HTML", "CSS", "SCSS", "Dockerfile", "Makefile", "Shell", "Procfile"})


@dataclass
class Snapshot:
    """Everything the renderer needs, in a form that survives a JSON round-trip."""

    generated_at: str = ""
    live: bool = False
    followers: int = 0
    following: int = 0
    public_repos: int = 0
    total_stars: int = 0
    total_forks: int = 0
    own_repos: int = 0
    account_age_years: float = 0.0
    languages: list[dict[str, Any]] = field(default_factory=list)
    top_repos: list[dict[str, Any]] = field(default_factory=list)
    activity: list[int] = field(default_factory=list)   # commits per week, oldest first
    activity_total: int = 0
    last_push: str = ""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects.

    A 302 from the API host is not expected. Following one would let a
    misconfigured or hijacked response move the request off the allow-listed
    host, so it is treated as an error instead.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


_opener = urllib.request.build_opener(_NoRedirect)
_opener.addheaders = []


def _get(path: str, token: str) -> Any | None:
    """GET a repository- or user-scoped API path. Returns parsed JSON or ``None``.

    ``path`` must already be composed of validated components -- see
    :func:`generator.config._username`.
    """
    url = f"{API_ROOT}{path}"
    if not url.startswith(f"https://{API_HOST}/"):
        # Belt and braces: refuse to issue a request that escaped the host.
        return None

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for attempt in range(MAX_RETRIES + 1):
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with _opener.open(request, timeout=CONNECT_TIMEOUT) as response:
                if response.status != 200:
                    return None
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                if len(payload) > MAX_RESPONSE_BYTES:
                    print(f"  ! response from {path} exceeded size cap; ignoring")
                    return None
                return json.loads(payload.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # 403/429 with a rate-limit header is worth one backoff; a 404 is not.
            if exc.code in (403, 429) and attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * (attempt + 1))
                continue
            print(f"  ! {path} -> HTTP {exc.code}")
            return None
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * (attempt + 1))
                continue
            print(f"  ! {path} -> {type(exc).__name__}")
            return None
    return None


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _years_since(iso: str) -> float:
    try:
        created = time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError):
        return 0.0
    return max(0.0, (time.time() - time.mktime(created)) / (365.25 * 24 * 3600))


def _collect_repos(username: str, token: str) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        batch = _get(
            f"/users/{username}/repos?per_page=100&page={page}&sort=pushed&type=owner",
            token,
        )
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < 100:
            break
    return repos


def _weekly_activity(username: str, token: str, repos: list[dict[str, Any]]) -> list[int]:
    """Commit activity for the last 52 weeks.

    The contributions calendar lives behind the GraphQL API and needs a token
    with ``read:user``; the automatic ``GITHUB_TOKEN`` often does not have it.
    Rather than asking for a long-lived personal access token -- a credential
    that would sit in the repository's secrets with far more power than this
    job needs -- activity is reconstructed from the per-repository commit
    statistics available to a read-only token.

    This under-counts private and organisation work, which is the honest
    trade: fewer numbers, no over-privileged secret.
    """
    weeks = [0] * 52
    considered = 0
    for repo in sorted(repos, key=lambda r: r.get("pushed_at") or "", reverse=True):
        if considered >= 12:
            break
        name = repo.get("name")
        if not isinstance(name, str) or repo.get("fork"):
            continue
        # Repository names are echoed from the API; constrain before use in a path.
        if not name.replace("-", "").replace("_", "").replace(".", "").isalnum():
            continue
        considered += 1
        stats = _get(f"/repos/{username}/{name}/stats/participation", token)
        if not isinstance(stats, dict):
            continue
        series = stats.get("owner")
        if not isinstance(series, list):
            continue
        tail = [int(v) for v in series[-52:] if isinstance(v, (int, float))]
        offset = 52 - len(tail)
        for i, value in enumerate(tail):
            weeks[offset + i] += max(0, min(value, 500))
    return weeks


def fetch(username: str, token: str) -> Snapshot:
    """Build a fresh snapshot. Returns ``live=False`` if the API was unreachable."""
    snap = Snapshot(generated_at=_iso_now())

    user = _get(f"/users/{username}", token)
    repos = _collect_repos(username, token)

    if not isinstance(user, dict) and not repos:
        return snap  # live stays False; caller falls back to cache

    if isinstance(user, dict):
        snap.followers = max(0, int(user.get("followers") or 0))
        snap.following = max(0, int(user.get("following") or 0))
        snap.public_repos = max(0, int(user.get("public_repos") or 0))
        snap.account_age_years = round(_years_since(str(user.get("created_at") or "")), 1)

    own = [r for r in repos if not r.get("fork")]
    snap.own_repos = len(own)
    snap.total_stars = sum(max(0, int(r.get("stargazers_count") or 0)) for r in own)
    snap.total_forks = sum(max(0, int(r.get("forks_count") or 0)) for r in own)
    snap.last_push = str((own[0].get("pushed_at") if own else "") or "")[:10]

    tally: dict[str, int] = {}
    for repo in own:
        language = repo.get("language")
        if not isinstance(language, str) or language in LANGUAGE_NOISE:
            continue
        # Weight by repository size so a one-file experiment does not outrank
        # a real codebase, but compress it so one large repo cannot dominate.
        size = max(1, int(repo.get("size") or 1))
        tally[language] = tally.get(language, 0) + int(size ** 0.5) + 8
    total = sum(tally.values()) or 1
    snap.languages = [
        {"name": name, "share": round(count / total, 4)}
        for name, count in sorted(tally.items(), key=lambda kv: kv[1], reverse=True)[:7]
    ]

    snap.top_repos = [
        {
            "name": str(r.get("name") or "")[:60],
            "description": str(r.get("description") or "")[:160],
            "language": str(r.get("language") or "")[:30],
            "stars": max(0, int(r.get("stargazers_count") or 0)),
            "pushed": str(r.get("pushed_at") or "")[:10],
            "url": str(r.get("html_url") or "")[:200],
        }
        for r in sorted(own, key=lambda r: (r.get("stargazers_count") or 0, r.get("pushed_at") or ""), reverse=True)[:6]
    ]

    snap.activity = _weekly_activity(username, token, own)
    snap.activity_total = sum(snap.activity)
    snap.live = True
    return snap


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------


def load_cache(path: Path) -> Snapshot:
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return Snapshot(generated_at=_iso_now())
    if not isinstance(data, dict):
        return Snapshot(generated_at=_iso_now())
    snap = Snapshot()
    for key, value in data.items():
        if hasattr(snap, key) and type(value) is type(getattr(snap, key)):
            setattr(snap, key, value)
    # ``live`` round-trips like every other field. It records how *this
    # snapshot* was obtained, not whether the current process reached the
    # network, so loading it back must not change it: `--check` re-renders from
    # this file and compares byte-for-byte against the committed output, and a
    # flag that flipped on load would make every live build unreproducible.
    # Degrading the flag is the job of `resolve()`, which is the only place
    # that knows a fetch was attempted and failed.
    return snap


def save_cache(path: Path, snap: Snapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(snap), indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(payload + "\n", encoding="utf-8")


def _degraded(cache_path: Path) -> Snapshot:
    """Load the cache for a build whose fetch failed, and record that it failed.

    The page must not claim live telemetry when the API could not be reached,
    so the flag is cleared here. It is also written back, because the rendered
    output and ``data/cache.json`` are published together and have to agree:
    anything else leaves a committed page that a later ``--check`` cannot
    reproduce from the committed snapshot.
    """
    snap = load_cache(cache_path)
    snap.live = False
    save_cache(cache_path, snap)
    return snap


def resolve(username: str, cache_path: Path, *, offline: bool = False) -> Snapshot:
    """Fetch if possible, otherwise fall back to cache. Never raises."""
    if offline:
        # Deliberately *not* degraded: offline is how `--check` and `make build`
        # re-render, and both must reproduce the committed bytes exactly.
        print("  · offline mode: using cached snapshot")
        return load_cache(cache_path)

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    try:
        fresh = fetch(username, token)
    except Exception as exc:  # noqa: BLE001 - a build must not fail on telemetry
        print(f"  ! fetch failed unexpectedly ({type(exc).__name__}); using cache")
        return _degraded(cache_path)

    if fresh.live:
        save_cache(cache_path, fresh)
        return fresh

    print("  ! GitHub API unavailable; falling back to cached snapshot")
    return _degraded(cache_path)
