"""Injection tests for the trust boundary.

These are the tests that matter. Everything else in this repository is
cosmetic; a failure here means hostile input from the GitHub API could reach a
rendering sink intact.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generator.sanitize import (  # noqa: E402
    ALLOWED_LINK_HOSTS,
    UnsafeValue,
    clamp,
    human_count,
    md_cell,
    md_link,
    md_text,
    safe_url,
    slug,
    xml_attr,
    xml_text,
)

# Payloads modelled on what an attacker could actually put in front of this
# generator: a repository name, a repository description, or a bio. All of
# those are free text controlled by whoever owns the account.
HOSTILE = [
    '<script>alert(1)</script>',
    '"><script>alert(1)</script>',
    "<img src=x onerror=alert(1)>",
    "]]><script>alert(1)</script><![CDATA[",
    "</text><script>alert(1)</script><text>",
    "'; DROP TABLE users;--",
    "$(id)",
    "`id`",
    "${IFS}cat${IFS}/etc/passwd",
    "../../../../etc/passwd",
    "\x00\x01\x02truncated",
    "a" * 5000,
    "‮evil‬",
    "​​hidden",
    "javascript:alert(1)",
    "&lt;already&gt;escaped",
    "line1\r\nline2\rline3",
    "emoji 🔐 and ünïcödé",
]


class XmlSink(unittest.TestCase):
    def test_no_raw_angle_brackets_survive(self):
        for payload in HOSTILE:
            out = xml_text(payload)
            self.assertNotIn("<", out, payload[:40])
            self.assertNotIn(">", out, payload[:40])

    def test_attribute_quotes_are_encoded(self):
        for payload in HOSTILE + ['" onload="alert(1)', "' onload='alert(1)"]:
            out = xml_attr(payload)
            self.assertNotIn('"', out)
            self.assertNotIn("'", out)

    def test_ampersand_escaped_once(self):
        self.assertEqual(xml_text("a & b"), "a &amp; b")
        # Pre-escaped input must not be double-decoded into a live entity.
        self.assertEqual(xml_text("&lt;b&gt;"), "&amp;lt;b&amp;gt;")

    def test_control_characters_removed(self):
        self.assertEqual(xml_text("\x00\x08ok\x1f"), "ok")

    def test_bidi_and_zero_width_removed(self):
        self.assertEqual(xml_text("‮reversed‬"), "reversed")
        self.assertEqual(xml_text("a​b﻿c"), "abc")

    def test_output_is_well_formed_when_embedded(self):
        from xml.etree import ElementTree
        for payload in HOSTILE:
            doc = f'<svg xmlns="http://www.w3.org/2000/svg"><text x="{xml_attr(payload)}">{xml_text(payload)}</text></svg>'
            ElementTree.fromstring(doc)  # raises on malformed output

    def test_length_is_bounded(self):
        self.assertLessEqual(len(xml_text("a" * 100_000)), 600)

    def test_non_scalar_input_is_refused(self):
        with self.assertRaises(UnsafeValue):
            xml_text({"a": 1})
        with self.assertRaises(UnsafeValue):
            xml_text(["a"])


class MarkdownSink(unittest.TestCase):
    def test_html_cannot_be_injected(self):
        for payload in HOSTILE:
            out = md_text(payload)
            # Angle brackets are HTML-encoded, so no tag can ever form.
            self.assertNotIn("<", out, payload[:40])
            self.assertNotIn(">", out, payload[:40])

    def test_block_markers_at_line_start_are_neutralised(self):
        """A value interpolated at the start of a line must not become a
        heading, list item, blockquote, table row, or setext rule."""
        for payload in ("# heading", "- item", "> quote", "1. item", "1) item",
                        "=== rule", "| a | b |", "* item", "+ item"):
            out = md_text(payload)
            self.assertNotIn(out[0], "#-+=|*_~>", f"{payload!r} -> {out!r}")

    def test_ordered_list_marker_is_broken(self):
        self.assertEqual(md_text("1. item"), "1\\. item")
        self.assertEqual(md_text("12) item"), "12\\) item")

    def test_table_cells_cannot_break_the_row(self):
        self.assertNotIn("|", md_cell("a | b").replace("\\|", ""))

    def test_image_and_link_syntax_is_neutralised(self):
        """Brackets are escaped, so neither a link nor an image can form
        around an attacker-chosen destination."""
        out = md_text("![x](javascript:alert(1))")
        self.assertNotIn("[", out.replace("\\[", ""))
        self.assertNotIn("]", out.replace("\\]", ""))
        self.assertIn("\\[", out)

    def test_newlines_do_not_escape_the_construct(self):
        self.assertNotIn("\n", md_text("a\nb\r\nc"))


class UrlAllowList(unittest.TestCase):
    def test_dangerous_schemes_rejected(self):
        for url in (
            "javascript:alert(1)",
            "JavaScript:alert(1)",
            "data:text/html;base64,PHNjcmlwdD4=",
            "vbscript:msgbox(1)",
            "file:///etc/passwd",
            "http://github.com/x",          # plaintext
            "//github.com/x",
            " javascript:alert(1)",
        ):
            self.assertEqual(safe_url(url), "", url)

    def test_off_allowlist_hosts_rejected(self):
        for url in (
            "https://evil.example/x",
            "https://github.com.evil.example/x",
            "https://evilgithub.com/x",
            "https://user:pass@github.com/x",
            "https://github.com@evil.example/x",
        ):
            self.assertEqual(safe_url(url), "", url)

    def test_allow_listed_hosts_pass(self):
        for host in sorted(ALLOWED_LINK_HOSTS):
            self.assertTrue(safe_url(f"https://{host}/path?a=1#b"), host)

    def test_case_insensitive_host_matching(self):
        self.assertTrue(safe_url("https://GitHub.com/x"))

    def test_link_degrades_to_text_when_url_is_unsafe(self):
        out = md_link("click", "javascript:alert(1)")
        self.assertNotIn("(", out.replace("\\(", ""))
        self.assertIn("click", out)

    def test_parentheses_in_destination_are_encoded(self):
        out = md_link("x", "https://github.com/a(b)c")
        self.assertIn("%28", out)
        self.assertIn("%29", out)


class Numerics(unittest.TestCase):
    def test_clamp_handles_garbage(self):
        for value in (None, "abc", [], {}, float("nan"), float("inf"), -float("inf")):
            self.assertEqual(clamp(value, 0, 10, default=3.0), 3.0)

    def test_clamp_bounds(self):
        self.assertEqual(clamp(-5, 0, 10), 0)
        self.assertEqual(clamp(99, 0, 10), 10)

    def test_human_count_never_negative_or_unbounded(self):
        self.assertEqual(human_count(-10), "0")
        self.assertEqual(human_count(999), "999")
        self.assertEqual(human_count(1500), "1.5k")
        self.assertEqual(human_count(2_400_000), "2.4M")
        self.assertEqual(human_count("garbage"), "0")


class Slugs(unittest.TestCase):
    def test_slug_is_allow_listed(self):
        for payload in HOSTILE:
            out = slug(payload)
            self.assertRegex(out, r"^[a-z0-9-]+$", payload[:40])

    def test_slug_never_empty(self):
        self.assertTrue(slug(""))
        self.assertTrue(slug("!!!"))

    def test_slug_cannot_traverse(self):
        self.assertNotIn("/", slug("../../etc/passwd"))
        self.assertNotIn(".", slug("../../etc/passwd"))


if __name__ == "__main__":
    unittest.main()
