#!/usr/bin/env python3
"""Post-build audit of everything the generator is about to publish.

The generator is careful, but "careful" is a property you assert and then
verify. This runs after rendering and fails the build if the artefacts contain
anything they should not, so a mistake in the renderer becomes a red build
rather than a published secret.

Checks:

  1. No credential-shaped strings in any generated file.
  2. No live token value from the environment appears in the output.
  3. No script, event handler, or foreign-object element in any SVG.
  4. No off-allow-list external reference in any generated file.
  5. No active content in the README's own HTML.

Every SVG is parsed as XML regardless of flags; ``--strict`` additionally
requires that at least one asset exists, so an empty assets/ directory cannot
pass silently.

Usage:  python3 tools/audit_output.py [--strict] [--root .]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

# Credential shapes worth failing on. GitHub's own token formats plus the
# generic "looks like a bearer header" case.
SECRET_PATTERNS = (
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("GitHub fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("Authorization header", re.compile(r"(?i)authorization\s*:\s*(bearer|basic)\s+\S+")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Slack token", re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}")),
)

# Active content that must never appear in a generated SVG. An asset is served
# raw from raw.githubusercontent.com, where GitHub's HTML sanitiser does not
# apply, so the SVG has to be inert on its own merits.
#
# These checks run against the *parsed* document -- element names, attribute
# names, attribute values -- and never against the serialised bytes. Regexing
# the bytes would flag correctly-escaped text content: a stack group labelled
# "JavaScript" renders `JavaScript: Python, ...` inside a <desc>, which a naive
# /javascript:/ pattern reads as a URI scheme and fails the build on. Escaped
# text in a text node is inert by construction; only markup can be active.

# Allow-list, not a block-list. A renderer that starts emitting a new element
# has to come through here first, which is the intended friction.
SVG_ALLOWED_TAGS = frozenset(
    {
        "svg", "title", "desc", "defs", "style", "g", "rect", "circle",
        "ellipse", "line", "path", "polyline", "polygon", "text", "tspan",
        "linearGradient", "radialGradient", "stop", "pattern", "clipPath",
        "mask",
    }
)

# Attribute values that may reference something. Anything else with a scheme
# is an external fetch we did not intend.
SVG_LOCAL_REF = re.compile(r"^(#|url\(#)")
# url(...) may only ever point at a gradient or clip path defined in the
# same document. Anything else is an outbound fetch.
SVG_URL_FUNC = re.compile(r"(?i)url\(\s*[\"']?\s*(?!#)")

# Inline code spans in the README. Markdown escapes their contents on
# render, so scanning the raw bytes flags text that is provably inert --
# the same mistake as regexing an SVG instead of parsing it.
MD_CODE_SPAN = re.compile(r"`[^`\n]*`")
MD_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
CSS_FORBIDDEN = re.compile(r"(?i)@import|url\s*\(\s*[\"']?\s*(?!#)[a-z]+:")

# Hosts a generated file may reference. The SVG namespace URL is a declaration
# rather than a fetch, and the noreply address is the commit identity.
ALLOWED_REFERENCES = (
    "http://www.w3.org/2000/svg",
    "https://github.com/features/actions",
)

URL_IN_TEXT = re.compile(r"https?://[^\s\"'()<>\\]+")

# Hosts the README is allowed to link to. Kept in step with
# generator/sanitize.py -- if they drift, this audit is the thing that notices.
ALLOWED_LINK_HOSTS = {
    "github.com", "www.github.com", "gist.github.com", "raw.githubusercontent.com",
    "linkedin.com", "www.linkedin.com", "tryhackme.com", "hackerone.com",
    "devsirchhub.co.ke", "www.devsirchhub.co.ke",
    "challengeme.africa", "www.challengeme.africa",
    "www.w3.org",
}


def _host(url: str) -> str:
    rest = url.split("://", 1)[-1]
    return rest.split("/", 1)[0].split(":", 1)[0].split("@")[-1].lower()


def _audit_svg(content: str) -> list[str]:
    """Parse an SVG and report any element or attribute that could be active."""
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        return [f"not well-formed XML ({exc})"]

    problems: list[str] = []
    for element in root.iter():
        tag = element.tag.split("}")[-1]
        if tag not in SVG_ALLOWED_TAGS:
            problems.append(f"element <{tag}> is not on the allow-list")

        for name, value in element.attrib.items():
            local = name.split("}")[-1]
            if local.lower().startswith("on"):
                problems.append(f"event handler attribute {local!r} on <{tag}>")
                continue
            if local in ("href", "xlink:href", "src") and not SVG_LOCAL_REF.match(value):
                problems.append(f"external reference in {local!r} on <{tag}>")
                continue
            # Any attribute value carrying a scheme, or a url() pointing
            # somewhere other than a local id, is a fetch we did not mean to
            # make. Fill and stroke legitimately use url(#local-id) only.
            if re.match(r"(?i)^\s*(javascript|data|vbscript|file|http)s?\s*:", value):
                problems.append(f"scheme URI in attribute {local!r} on <{tag}>")
            elif SVG_URL_FUNC.search(value):
                problems.append(f"non-local url() in attribute {local!r} on <{tag}>")

        if tag == "style" and element.text and CSS_FORBIDDEN.search(element.text):
            problems.append("stylesheet loads an external resource")

    return problems


def audit(root: Path, strict: bool) -> list[str]:
    failures: list[str] = []

    targets = [root / "README.md"]
    targets += sorted((root / "assets").glob("*.svg"))
    cache = root / "data" / "cache.json"
    if cache.exists():
        targets.append(cache)

    # Any token present in this process's environment must not survive into a
    # generated file. This catches the whole class of "accidentally rendered a
    # variable I should not have" bugs, not just known token shapes.
    live_secrets = [
        value
        for key, value in os.environ.items()
        if ("TOKEN" in key or "SECRET" in key or "PASSWORD" in key or "KEY" in key)
        and isinstance(value, str)
        and len(value) >= 12
    ]

    for path in targets:
        try:
            content = path.read_text("utf-8")
        except OSError as exc:
            failures.append(f"{path.name}: unreadable ({exc})")
            continue

        rel = path.relative_to(root)

        for label, pattern in SECRET_PATTERNS:
            if pattern.search(content):
                failures.append(f"{rel}: contains something shaped like a {label}")

        for secret in live_secrets:
            if secret in content:
                failures.append(f"{rel}: contains a value from a secret environment variable")

        if path.suffix == ".svg":
            failures.extend(f"{rel}: {problem}" for problem in _audit_svg(content))

        if path.suffix == ".md":
            # Code spans and HTML comments are rendered as literal text, so
            # they are removed before scanning. What remains is markup GitHub
            # will actually interpret.
            live = MD_COMMENT.sub(" ", MD_CODE_SPAN.sub(" ", content)).lower()
            for token in ("<script", "<iframe", "<object", "<embed", "javascript:"):
                if token in live:
                    failures.append(f"{rel}: contains live {token!r}")

        for url in URL_IN_TEXT.findall(content):
            if url.rstrip("/,.)\"'") in ALLOWED_REFERENCES:
                continue
            if url.startswith("http://") and url not in ALLOWED_REFERENCES:
                failures.append(f"{rel}: plaintext http reference {url}")
                continue
            host = _host(url)
            if host not in ALLOWED_LINK_HOSTS:
                failures.append(f"{rel}: reference to non-allow-listed host {host}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--strict", action="store_true",
                        help="also fail if there is nothing to audit")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    failures = audit(root, args.strict)

    if args.strict and not list((root / "assets").glob("*.svg")):
        failures.append("assets/: no SVG assets to audit")

    if failures:
        print("output audit FAILED:", file=sys.stderr)
        for item in sorted(set(failures)):
            print(f"  ✗ {item}", file=sys.stderr)
        return 1

    print("· output audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
