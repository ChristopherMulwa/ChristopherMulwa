"""Configuration loading and validation.

The editable content of the profile lives in ``profile.json``. It is loaded
with :func:`json.load` rather than a YAML parser on purpose: ``yaml.load``
without an explicit safe loader is a remote-code-execution primitive, and the
convenience of YAML is not worth carrying that footgun -- or the dependency --
in a repository whose whole point is that it is publicly readable.

The schema is checked by hand against an explicit shape. Unknown keys are
rejected rather than ignored, so a typo fails loudly at build time instead of
silently dropping a section from the rendered page.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .sanitize import MAX_SHORT, MAX_TEXT, UnsafeValue, safe_url

MAX_CONFIG_BYTES = 256 * 1024


class ConfigError(ValueError):
    """The configuration file is missing, malformed, or fails validation."""


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True)
class Project:
    name: str
    tagline: str
    detail: str
    stack: tuple[str, ...]
    status: str
    url: str = ""
    repo: str = ""


@dataclass(frozen=True)
class StackGroup:
    label: str
    accent: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class Practice:
    label: str
    detail: str


@dataclass(frozen=True)
class Config:
    username: str
    display_name: str
    headline: str
    roles: tuple[str, ...]
    location: str
    summary: str
    focus: tuple[str, ...]
    links: tuple[Link, ...]
    stack: tuple[StackGroup, ...]
    projects: tuple[Project, ...]
    practices: tuple[Practice, ...]
    accent_rotation: tuple[str, ...] = field(default=("accent", "cyan", "violet", "amber"))


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------


def _require(node: Any, key: str, kind: type, where: str) -> Any:
    if not isinstance(node, dict):
        raise ConfigError(f"{where}: expected an object")
    if key not in node:
        raise ConfigError(f"{where}: missing required key {key!r}")
    value = node[key]
    if not isinstance(value, kind):
        raise ConfigError(
            f"{where}.{key}: expected {kind.__name__}, got {type(value).__name__}"
        )
    return value


def _reject_unknown(node: dict[str, Any], allowed: set[str], where: str) -> None:
    extra = set(node) - allowed
    if extra:
        raise ConfigError(f"{where}: unexpected key(s) {sorted(extra)}")


def _string(node: dict, key: str, where: str, *, limit: int = MAX_TEXT,
            required: bool = True, default: str = "") -> str:
    if key not in node and not required:
        return default
    value = _require(node, key, str, where)
    if required and not value.strip():
        raise ConfigError(f"{where}.{key}: must not be empty")
    if len(value) > limit:
        raise ConfigError(f"{where}.{key}: exceeds {limit} characters")
    return value


def _string_list(node: dict, key: str, where: str, *, limit: int = MAX_SHORT,
                 max_items: int = 32, required: bool = True) -> tuple[str, ...]:
    if key not in node and not required:
        return ()
    raw = _require(node, key, list, where)
    if len(raw) > max_items:
        raise ConfigError(f"{where}.{key}: at most {max_items} entries")
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, str):
            raise ConfigError(f"{where}.{key}[{i}]: expected string")
        if len(item) > limit:
            raise ConfigError(f"{where}.{key}[{i}]: exceeds {limit} characters")
        if item.strip():
            out.append(item)
    return tuple(out)


_USERNAME_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")


def _username(value: str) -> str:
    """GitHub usernames are ``[A-Za-z0-9-]`` up to 39 characters.

    This value is interpolated into API paths, so it is validated against an
    allow-list rather than escaped. A username containing ``../`` or a query
    separator would otherwise let config content redirect an API call.
    """
    value = value.strip()
    if not value or len(value) > 39:
        raise ConfigError("username: must be 1-39 characters")
    if not set(value) <= _USERNAME_OK:
        raise ConfigError("username: may only contain letters, digits and hyphens")
    if value.startswith("-") or value.endswith("-") or "--" in value:
        raise ConfigError("username: malformed")
    return value


_ACCENTS = {"accent", "cyan", "violet", "amber", "rose"}
_STATUSES = {"live", "building", "design", "archived", "private"}


# --------------------------------------------------------------------------
# Loader
# --------------------------------------------------------------------------


def load(path: Path) -> Config:
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc

    if len(raw_bytes) > MAX_CONFIG_BYTES:
        raise ConfigError(f"{path}: larger than {MAX_CONFIG_BYTES} bytes")

    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"{path}: not valid UTF-8 JSON ({exc})") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be an object")

    _reject_unknown(
        data,
        {
            "$schema", "username", "displayName", "headline", "roles", "location",
            "summary", "focus", "links", "stack", "projects", "practices",
        },
        "profile",
    )

    username = _username(_string(data, "username", "profile", limit=39))

    links = []
    for i, item in enumerate(_require(data, "links", list, "profile")):
        where = f"profile.links[{i}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{where}: expected an object")
        _reject_unknown(item, {"label", "url"}, where)
        url = safe_url(_string(item, "url", where))
        if not url:
            raise ConfigError(
                f"{where}.url: rejected. Must be https and on the host allow-list "
                f"in generator/sanitize.py"
            )
        links.append(Link(label=_string(item, "label", where, limit=MAX_SHORT), url=url))
    if not links:
        raise ConfigError("profile.links: at least one link is required")

    stack = []
    for i, item in enumerate(_require(data, "stack", list, "profile")):
        where = f"profile.stack[{i}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{where}: expected an object")
        _reject_unknown(item, {"label", "accent", "items"}, where)
        accent = _string(item, "accent", where, limit=16, required=False, default="accent")
        if accent not in _ACCENTS:
            raise ConfigError(f"{where}.accent: must be one of {sorted(_ACCENTS)}")
        stack.append(
            StackGroup(
                label=_string(item, "label", where, limit=MAX_SHORT),
                accent=accent,
                items=_string_list(item, "items", where, limit=32, max_items=24),
            )
        )

    projects = []
    for i, item in enumerate(_require(data, "projects", list, "profile")):
        where = f"profile.projects[{i}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{where}: expected an object")
        _reject_unknown(item, {"name", "tagline", "detail", "stack", "status", "url", "repo"}, where)
        status = _string(item, "status", where, limit=16)
        if status not in _STATUSES:
            raise ConfigError(f"{where}.status: must be one of {sorted(_STATUSES)}")
        url_in = _string(item, "url", where, required=False)
        url = safe_url(url_in) if url_in else ""
        if url_in and not url:
            raise ConfigError(f"{where}.url: rejected by the URL allow-list")
        projects.append(
            Project(
                name=_string(item, "name", where, limit=MAX_SHORT),
                tagline=_string(item, "tagline", where, limit=MAX_SHORT),
                detail=_string(item, "detail", where),
                stack=_string_list(item, "stack", where, limit=32, max_items=12),
                status=status,
                url=url,
                repo=_string(item, "repo", where, limit=MAX_SHORT, required=False),
            )
        )

    practices = []
    for i, item in enumerate(_require(data, "practices", list, "profile")):
        where = f"profile.practices[{i}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{where}: expected an object")
        _reject_unknown(item, {"label", "detail"}, where)
        practices.append(
            Practice(
                label=_string(item, "label", where, limit=MAX_SHORT),
                detail=_string(item, "detail", where),
            )
        )

    return Config(
        username=username,
        display_name=_string(data, "displayName", "profile", limit=MAX_SHORT),
        headline=_string(data, "headline", "profile", limit=MAX_SHORT),
        roles=_string_list(data, "roles", "profile", limit=64, max_items=8),
        location=_string(data, "location", "profile", limit=MAX_SHORT),
        summary=_string(data, "summary", "profile", limit=1200),
        focus=_string_list(data, "focus", "profile", limit=280, max_items=8),
        links=tuple(links),
        stack=tuple(stack),
        projects=tuple(projects),
        practices=tuple(practices),
    )
