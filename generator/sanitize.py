"""Trust boundary.

Everything the generator receives from the GitHub API, from the environment,
or from ``profile.json`` is untrusted input. It ends up in two sinks:

  1. Markdown  (README.md)  -- rendered as HTML by GitHub
  2. SVG/XML   (assets/*)   -- rendered as an image by the browser

Both sinks are escaped here, at the boundary, with an allow-list mindset:
we do not try to strip "bad" characters, we constrain values to the shape we
expect and encode whatever survives.

No value from an untrusted source is ever passed to a shell, a template
compiler, ``eval``, ``exec``, ``pickle``, or a filesystem path.
"""

from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------------------
# Limits. Every untrusted string is length-capped before it reaches a sink so
# that a hostile or accidental megabyte cannot blow up the README or the SVG.
# --------------------------------------------------------------------------
MAX_SHORT = 120
MAX_TEXT = 600
MAX_URL = 400

# Characters that are legal in XML 1.0. Anything outside this set is dropped
# rather than escaped -- an SVG containing a raw control byte is invalid XML
# and will silently fail to render.
_XML_ILLEGAL = re.compile(
    "[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD"
    "\U00010000-\U0010FFFF]"
)

# Bidirectional control characters. These are invisible and can be used to
# make displayed text differ from its logical order ("Trojan Source",
# CVE-2021-42574). A profile page is a low-stakes target for that trick, but
# the cost of removing them is zero.
_BIDI = re.compile("[\u061C\u200E\u200F\u202A-\u202E\u2066-\u2069]")

# Zero-width and other invisible formatting characters, used for homograph
# and watermark tricks.
_INVISIBLE = re.compile("[\u200B\u200C\u200D\u2060\uFEFF]")

# Inline Markdown metacharacters. Backslash-escaped rather than stripped, so a
# repository genuinely named "foo_bar_baz" still displays correctly.
#
# Notably absent: ``. - ! # +`` and parentheses. Those are only meaningful at
# the start of a line or as part of a link construct, and escaping them inline
# produces visible backslash litter in the rendered page for no security gain.
# Line-start ambiguity is handled separately, below.
_MD_INLINE = "\\`*_[]~|"

# Block markers. A value that begins with one of these could otherwise turn
# into a heading, a list item, or a blockquote when interpolated at the start
# of a line.
_MD_BLOCK_START = ("#", ">", "-", "+", "=", "|", "*", "_", "~")

# Characters that must be HTML-encoded rather than backslash-escaped. GitHub
# renders raw HTML inside Markdown, so these are the actual injection vector.
# Quotes are included because md_text output is interpolated into HTML
# attributes (the alt= on generated <img> tags). Without them a value can
# close the attribute and inject a second src= into the existing element --
# no new tag required, so encoding < and > alone is not enough.
_HTML_ENCODE = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
}

# URL schemes that may appear in a generated link. Everything else -- most
# importantly ``javascript:``, ``data:`` and ``vbscript:`` -- is rejected.
# GitHub's own sanitiser would also catch these; this is defence in depth,
# not a substitute for it.
_ALLOWED_SCHEMES = ("https://",)

_URL_SAFE = re.compile(r"^https://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")

# Hostnames we are willing to emit as image or link targets. Keeping this
# closed means a compromised or mistaken config cannot turn the profile into
# a redirector or a tracking beacon for a third party.
ALLOWED_LINK_HOSTS = frozenset(
    {
        "github.com",
        "www.github.com",
        "gist.github.com",
        "raw.githubusercontent.com",
        "linkedin.com",
        "www.linkedin.com",
        "tryhackme.com",
        "hackerone.com",
        "devsirchhub.co.ke",
        "www.devsirchhub.co.ke",
        "challengeme.africa",
        "www.challengeme.africa",
    }
)


class UnsafeValue(ValueError):
    """Raised when a value cannot be made safe and must not be emitted."""


def _normalise(value: object, limit: int) -> str:
    """Coerce to a bounded, NFC-normalised, control-free string.

    Unicode normalisation happens *before* escaping so that a decomposed
    sequence cannot reassemble into a metacharacter after we have escaped.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (int, float)):
        text = str(value)
    elif isinstance(value, str):
        text = value
    else:
        raise UnsafeValue(f"refusing to render value of type {type(value).__name__}")

    text = unicodedata.normalize("NFC", text)
    text = _BIDI.sub("", text)
    text = _INVISIBLE.sub("", text)
    text = _XML_ILLEGAL.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.strip()

    if len(text) > limit:
        # Cut on a character boundary and mark the truncation so a reader can
        # tell the difference between "short" and "trimmed".
        text = text[: limit - 1].rstrip() + "…"
    return text


def xml_text(value: object, limit: int = MAX_TEXT) -> str:
    """Escape a value for an SVG/XML *text node*."""
    text = _normalise(value, limit)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def xml_attr(value: object, limit: int = MAX_TEXT) -> str:
    """Escape a value for an SVG/XML *attribute value* (double-quoted)."""
    return (
        xml_text(value, limit)
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def md_text(value: object, limit: int = MAX_TEXT) -> str:
    """Escape a value for inline Markdown.

    Angle brackets and ampersands are HTML-encoded, because GitHub renders raw
    HTML inside Markdown and that is where the injection risk actually lives.
    Emphasis and code metacharacters are backslash-escaped. Newlines collapse
    to spaces so a multi-line value cannot break out of a table row or a list
    item.
    """
    text = _normalise(value, limit)
    out = []
    for ch in text:
        if ch in _HTML_ENCODE:
            out.append(_HTML_ENCODE[ch])
        elif ch in _MD_INLINE:
            out.append("\\" + ch)
        elif ch == "\n":
            out.append(" ")
        else:
            out.append(ch)
    result = "".join(out)

    # A value interpolated at the start of a line must not read as a block
    # marker. ``1.`` and ``1)`` start ordered lists, so guard those too.
    if result[:1] in _MD_BLOCK_START:
        result = "\\" + result
    elif len(result) > 1 and result[0].isdigit():
        head = result.lstrip("0123456789")
        if head[:1] in (".", ")"):
            digits = len(result) - len(head)
            result = result[:digits] + "\\" + head
    return result


def md_cell(value: object, limit: int = MAX_SHORT) -> str:
    """Escape a value for a Markdown *table cell*.

    ``|`` is already in the inline escape set, so this only exists to make the
    call site read correctly. Escaping the pipe a second time here would
    produce ``\\\\|`` -- an escaped backslash followed by a *live* delimiter,
    which splits the row instead of protecting it.
    """
    return md_text(value, limit)


def md_code(value: object, limit: int = MAX_SHORT) -> str:
    """Render a value inside a code span.

    Backslash escapes are *literal* inside a code span, so escaping here would
    put visible backslashes on the page. Backticks are stripped instead, since
    they are the only character that can terminate the span, and a leading or
    trailing space would be eaten by the span itself.
    """
    # All whitespace collapses to a single space: a newline inside a code span
    # terminates the span, after which the remainder of the value would be
    # emitted as raw Markdown -- and code spans do no HTML encoding at all.
    text = re.sub(r"\s+", " ", _normalise(value, limit)).replace("`", "").strip()
    return text or "—"


def safe_url(value: object, *, hosts: frozenset[str] | None = None) -> str:
    """Validate a URL against the scheme and host allow-lists.

    Returns ``""`` for anything that does not pass, so a bad link degrades to
    plain text rather than becoming an unexpected navigation target.
    """
    text = _normalise(value, MAX_URL)
    if not text:
        return ""
    if not text.startswith(_ALLOWED_SCHEMES):
        return ""
    if not _URL_SAFE.match(text):
        return ""

    remainder = text[len("https://") :]
    authority = remainder.split("/", 1)[0]
    # Reject embedded credentials (https://user:pass@evil.example) outright.
    if "@" in authority:
        return ""
    host = authority.split(":", 1)[0].lower()

    allowed = ALLOWED_LINK_HOSTS if hosts is None else hosts
    if host not in allowed:
        return ""
    return text


def md_link(label: object, url: object, *, hosts: frozenset[str] | None = None) -> str:
    """Render a Markdown link, falling back to bare text if the URL is unsafe."""
    text = md_text(label, MAX_SHORT)
    target = safe_url(url, hosts=hosts)
    if not target:
        return text
    # Parentheses inside a Markdown destination terminate it early; the URL
    # regex permits them, so encode them here.
    target = target.replace("(", "%28").replace(")", "%29")
    return f"[{text}]({target})"


def slug(value: object, limit: int = 64) -> str:
    """Reduce a value to ``[a-z0-9-]``.

    Used for anything that becomes an id, a filename fragment, or a CSS class
    -- contexts where escaping is not enough and only an allow-list will do.
    """
    text = _normalise(value, limit).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "x"


def clamp(value: object, low: float, high: float, default: float = 0.0) -> float:
    """Coerce an untrusted numeric to a bounded float.

    Guards the SVG geometry: a negative or absurd count from the API becomes
    a malformed path, not a crash and not a distorted card.
    """
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if number != number or number in (float("inf"), float("-inf")):  # NaN / inf
        return default
    return max(low, min(high, number))


def human_count(value: object) -> str:
    """Format a count compactly (1200 -> ``1.2k``) with a hard upper bound."""
    number = int(clamp(value, 0, 10**9))
    if number < 1000:
        return str(number)
    if number < 1_000_000:
        trimmed = number / 1000
        return f"{trimmed:.1f}k".replace(".0k", "k")
    trimmed = number / 1_000_000
    return f"{trimmed:.1f}M".replace(".0M", "M")
