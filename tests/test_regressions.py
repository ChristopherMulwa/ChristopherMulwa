"""Regressions from the adversarial review of this pipeline.

Each test here corresponds to a bug that was found by attacking the code
rather than by reading it. They stay as tests so the same mistake cannot be
reintroduced quietly.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generator import __main__ as entry  # noqa: E402
from generator.sanitize import md_cell, md_code, md_text  # noqa: E402
from generator.sources.github import Snapshot, save_cache  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
import audit_output  # noqa: E402


class CodeSpanEscape(unittest.TestCase):
    """A newline inside a code span terminates it, after which the rest of the
    value is emitted as raw Markdown -- and code spans do no HTML encoding."""

    def test_newlines_collapse(self):
        self.assertEqual(md_code("a\n\n<img src=x>"), "a <img src=x>")

    def test_all_whitespace_collapses(self):
        self.assertEqual(md_code("a\t\t b\n c"), "a b c")

    def test_backticks_are_removed(self):
        self.assertNotIn("`", md_code("a`b``c"))

    def test_empty_value_yields_a_placeholder(self):
        self.assertEqual(md_code("```"), "—")


class AttributeEscape(unittest.TestCase):
    """md_text output is interpolated into HTML attributes, so encoding angle
    brackets alone is not enough -- a value can close the attribute and add a
    second src= to the existing <img>, which HTML resolves to the first one."""

    def test_double_quote_is_encoded(self):
        out = md_text('Chris" src="https://evil.example/x.svg')
        self.assertNotIn('"', out)
        self.assertIn("&quot;", out)

    def test_single_quote_is_encoded(self):
        self.assertNotIn("'", md_text("it's"))

    def test_attribute_cannot_be_closed_in_rendered_output(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            config = json.loads((ROOT / "profile.json").read_text("utf-8"))
            config["displayName"] = 'Chris" src="https://raw.githubusercontent.com/e/x/a.svg'
            (tmp / "profile.json").write_text(json.dumps(config), encoding="utf-8")
            (tmp / "data").mkdir()
            self.assertEqual(entry.main(["--root", str(tmp), "--offline"]), 0)

            readme = (tmp / "README.md").read_text("utf-8")
            tags = re.findall(r"<img\b[^>]*>", readme)
            self.assertTrue(tags)
            for tag in tags:
                self.assertEqual(tag.count(' src="'), 1, tag)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TableCellEscape(unittest.TestCase):
    """Escaping the pipe twice produces an escaped backslash followed by a
    live delimiter, which splits the row rather than protecting it."""

    def test_pipe_is_escaped_exactly_once(self):
        self.assertEqual(md_cell("a|b"), "a\\|b")
        self.assertNotIn("\\\\", md_cell("a|b"))

    def test_cell_matches_inline_escaping(self):
        for value in ("a|b", "a*b", "a_b", "plain"):
            self.assertEqual(md_cell(value), md_text(value))


class AuditFalsePositives(unittest.TestCase):
    """The audit must fail on active markup and pass on escaped text that
    merely looks alarming. A build that goes red on the word 'JavaScript' is
    a build nobody trusts."""

    def test_escaped_text_mentioning_a_scheme_is_allowed(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" role="img">'
            "<title>t</title><desc>JavaScript: Python, TypeScript</desc>"
            "<text>javascript: is just a word here</text></svg>"
        )
        self.assertEqual(audit_output._audit_svg(svg), [])

    def test_escaped_angle_brackets_in_text_are_allowed(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" role="img">'
            "<title>t</title><desc>d</desc>"
            "<text>&lt;g onload=&quot;x&quot;&gt;</text></svg>"
        )
        self.assertEqual(audit_output._audit_svg(svg), [])

    def test_script_element_is_caught(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
        self.assertTrue(any("script" in p for p in audit_output._audit_svg(svg)))

    def test_event_handler_attribute_is_caught(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect onload="alert(1)"/></svg>'
        self.assertTrue(any("event handler" in p for p in audit_output._audit_svg(svg)))

    def test_external_reference_is_caught(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<rect fill="url(https://evil.example/x)"/></svg>'
        )
        self.assertTrue(audit_output._audit_svg(svg))

    def test_malformed_svg_is_caught(self):
        self.assertTrue(audit_output._audit_svg("<svg><rect></svg>"))

    def test_real_output_passes(self):
        self.assertEqual(audit_output.audit(ROOT, strict=True), [])


class SnapshotAlwaysExists(unittest.TestCase):
    """Without a committed snapshot, timestamps fall back to the wall clock:
    `--check` then only passes inside the same minute as the last build, and
    the publish step stages a path that does not exist."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(ROOT / "profile.json", self.tmp / "profile.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_creates_the_snapshot(self):
        cache = self.tmp / "data" / "cache.json"
        self.assertFalse(cache.exists())
        entry.main(["--root", str(self.tmp), "--offline"])
        self.assertTrue(cache.exists())

    def test_check_passes_regardless_of_elapsed_time(self):
        entry.main(["--root", str(self.tmp), "--offline"])
        stamp = json.loads((self.tmp / "data" / "cache.json").read_text("utf-8"))
        self.assertTrue(stamp["generated_at"])
        # Re-running much later must still agree, because every timestamp in
        # the output derives from the snapshot rather than the clock.
        self.assertEqual(entry.main(["--root", str(self.tmp), "--check"]), 0)

    def test_committed_repository_has_a_snapshot(self):
        self.assertTrue((ROOT / "data" / "cache.json").exists(),
                        "data/cache.json must be committed")


class PublishStepPathspec(unittest.TestCase):
    """`git add` exits non-zero if a pathspec matches nothing -- including
    `-A` against a directory that does not exist -- and under `set -e` that
    aborts the publish step instead of reaching the intended no-op."""

    STAGING = (
        'for target in README.md assets data; do\n'
        '  if [ -e "$target" ]; then\n'
        '    git add -A -- "$target"\n'
        '  fi\n'
        'done\n'
    )

    def test_workflow_stages_only_paths_that_exist(self):
        workflow = (ROOT / ".github/workflows/build-profile.yml").read_text("utf-8")
        self.assertIn('for target in README.md assets data; do', workflow)
        self.assertIn('if [ -e "$target" ]; then', workflow)
        # The naive forms both abort the step when assets/ or data/ is absent.
        self.assertNotIn("git add -- README.md assets data/cache.json", workflow)
        self.assertNotIn("git add -A -- README.md assets data\n", workflow)

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_naive_add_really_does_abort(self):
        """Guard against 'fixing' this back to a single git add."""
        with self._repo() as tmp:
            result = subprocess.run(
                ["bash", "-c",
                 "set -euo pipefail; git add -A -- README.md assets data; echo REACHED"],
                cwd=tmp, capture_output=True, text=True,
            )
            self.assertNotIn("REACHED", result.stdout)
            self.assertNotEqual(result.returncode, 0)

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_staging_snippet_survives_a_missing_path(self):
        with self._repo() as tmp:
            result = subprocess.run(
                ["bash", "-c", "set -euo pipefail\n" + self.STAGING + "echo REACHED"],
                cwd=tmp, capture_output=True, text=True,
            )
            self.assertIn("REACHED", result.stdout, result.stderr)
            self.assertEqual(result.returncode, 0)

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_staging_snippet_stages_what_is_there(self):
        with self._repo() as tmp:
            (tmp / "assets").mkdir()
            (tmp / "assets" / "a.svg").write_text("<svg/>", encoding="utf-8")
            subprocess.run(["bash", "-c", "set -euo pipefail\n" + self.STAGING],
                           cwd=tmp, check=True)
            staged = subprocess.run(["git", "diff", "--cached", "--name-only"],
                                    cwd=tmp, capture_output=True, text=True).stdout
            self.assertIn("README.md", staged)
            self.assertIn("assets/a.svg", staged)

    @contextlib.contextmanager
    def _repo(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            subprocess.run(["git", "init", "-q", str(tmp)], check=True)
            (tmp / "README.md").write_text("x", encoding="utf-8")
            yield tmp
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class AuditSeesTheToken(unittest.TestCase):
    """Step-level env does not propagate, so the audit step must declare the
    token explicitly or its 'no live secret in output' check is a no-op."""

    def test_workflow_passes_the_token_to_the_audit_step(self):
        workflow = (ROOT / ".github/workflows/build-profile.yml").read_text("utf-8")
        audit_block = workflow.split("- name: Audit generated output", 1)[1]
        audit_block = audit_block.split("- name:", 1)[0]
        self.assertIn("GITHUB_TOKEN", audit_block)

    def test_a_leaked_environment_secret_fails_the_audit(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copy(ROOT / "profile.json", tmp / "profile.json")
            (tmp / "data").mkdir()
            (tmp / "assets").mkdir()
            secret = "ghs_" + "A" * 36
            (tmp / "README.md").write_text(f"oops {secret}\n", encoding="utf-8")
            os.environ["FAKE_TEST_TOKEN"] = secret
            try:
                failures = audit_output.audit(tmp, strict=False)
            finally:
                del os.environ["FAKE_TEST_TOKEN"]
            self.assertTrue(failures)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class HostileConfigEndToEnd(unittest.TestCase):
    """The full attack surface, exercised through the real entry point."""

    def test_hostile_config_still_produces_inert_output(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            config = json.loads((ROOT / "profile.json").read_text("utf-8"))
            config["projects"][0]["stack"] = ["a\n\n<img src=x>", "b`c", '"><script>']
            config["headline"] = '</title><script>alert(1)</script>'
            config["projects"][0]["name"] = "| x | y |"
            (tmp / "profile.json").write_text(json.dumps(config), encoding="utf-8")
            (tmp / "data").mkdir()
            save_cache(tmp / "data" / "cache.json",
                       Snapshot(generated_at="2026-01-02T03:04:05Z", live=True,
                                languages=[{"name": "C|x", "share": 1.0}],
                                activity=[1] * 52, activity_total=52))

            self.assertEqual(entry.main(["--root", str(tmp), "--offline"]), 0)
            self.assertEqual(audit_output.audit(tmp, strict=True), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ContentDoesNotDependOnAnimation(unittest.TestCase):
    """No card may rely on a running animation to display content.

    GitHub renders these files with `<img>` on the profile page, and the
    animation does not start in that context: the four role lines sat at
    opacity 0 for a full cycle on the published page, so the ticker showed
    nothing at all to any visitor, while the same file opened directly as a
    document animated correctly. The reduced-motion fallback already had the
    right idea; it was just scoped to a media query that was not matching.
    """

    def _base_style(self, svg: str) -> str:
        """The stylesheet with the reduced-motion block removed."""
        style = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", svg, re.S))
        return re.sub(r"@media[^{]*\{.*?\}\}", "", style, flags=re.S)

    def test_a_role_is_visible_without_animation(self):
        for name in ("hero-dark", "hero-light"):
            svg = (ROOT / "assets" / f"{name}.svg").read_text("utf-8")
            base = self._base_style(svg)
            self.assertRegex(
                base.replace(" ", ""),
                r"\.role:first-of-type\{opacity:1\}",
                f"{name}: no static fallback, so the ticker is blank wherever "
                "CSS animation does not run",
            )

    def test_every_animated_class_is_either_decorative_or_has_a_fallback(self):
        """Flag any *new* class that is invisible until an animation runs."""
        for path in sorted((ROOT / "assets").glob("*.svg")):
            svg = path.read_text("utf-8")
            base = self._base_style(svg).replace(" ", "")
            for sel, body in re.findall(r"(\.[\w-]+)\{([^}]*)\}", base):
                if "opacity:0" in body and "animation:" in body:
                    fallback = f"{sel}:first-of-type{{opacity:1}}" in base
                    self.assertTrue(
                        fallback,
                        f"{path.name}: {sel} is invisible without animation and "
                        "has no static fallback",
                    )


class RadarPlotsRealData(unittest.TestCase):
    """The radar showed five invented contacts and overlapped the build stamp.

    The blips were hardcoded ``(angle, distance, colour)`` tuples: they looked
    like readings and encoded nothing. And at r=104 centred on y=131 the outer
    ring cut through the timestamp above it for ~100px, overlapping the glyphs
    by up to 13px.
    """

    def test_outer_ring_clears_the_build_stamp(self):
        from generator.cards.hero import PAD, RADAR_CY, RADAR_R

        stamp_baseline = PAD + 4          # where the build stamp is drawn
        stamp_bottom = stamp_baseline + 9.5 * 0.2
        self.assertGreater(
            RADAR_CY - RADAR_R, stamp_bottom + 5,
            "the radar's outer ring is back inside the build stamp",
        )

    def test_radar_fits_inside_the_card(self):
        from generator.cards.hero import H, W, RADAR_CX, RADAR_CY, RADAR_R

        self.assertGreaterEqual(RADAR_CY + RADAR_R, 0)
        self.assertLessEqual(RADAR_CY + RADAR_R, H - 4, "ring clipped at the bottom")
        self.assertLessEqual(RADAR_CX + RADAR_R, W, "ring clipped at the right")

    def test_blips_come_from_the_snapshot_not_from_constants(self):
        """Different repositories must produce a different dial."""
        from generator.cards.hero import contacts
        from generator.design import PALETTES

        p = PALETTES[0]
        a = contacts((("alpha", "2026-01-01"), ("beta", "2025-01-01")), 1767225600.0, p)
        b = contacts((("gamma", "2026-01-01"), ("delta", "2025-01-01")), 1767225600.0, p)
        self.assertEqual(len(a), 2)
        self.assertNotEqual([x[0] for x in a], [x[0] for x in b], "bearing ignores the name")
        # A repository keeps its bearing between builds.
        self.assertEqual(a[0][0], contacts((("alpha", "2020-05-05"),), 1767225600.0, p)[0][0])
        # Recent work plots nearer the centre than dormant work.
        self.assertLess(a[0][1], a[1][1])

    def test_no_blips_when_the_snapshot_has_no_repositories(self):
        from generator.cards.hero import contacts
        from generator.design import PALETTES

        self.assertEqual(contacts((), 0.0, PALETTES[0]), ())

    def test_a_hostile_repository_name_cannot_escape_the_blip_title(self):
        """Repository names are API data and the radar renders them as markup.

        The <title> on each blip was first written by hand, straight into the
        f-string, so a repository named `</title><script>alert(1)</script>`
        closed the element and injected a live script element into an SVG
        served from raw.githubusercontent.com -- which is not passed through
        GitHub's HTML sanitiser. document() escapes the title and desc it is
        handed; hand-rolled markup does not inherit that.
        """
        payloads = (
            "</title><script>alert(1)</script>",
            '"><script>alert(1)</script>',
            "<foreignObject><body>x</body></foreignObject>",
            "&lt;script&gt;",
            "]]><script>alert(1)</script>",
        )
        for payload in payloads:
            tmp = Path(tempfile.mkdtemp())
            try:
                shutil.copy(ROOT / "profile.json", tmp / "profile.json")
                (tmp / "data").mkdir()
                save_cache(tmp / "data" / "cache.json", Snapshot(
                    generated_at="2026-01-02T03:04:05Z", live=True,
                    top_repos=[{"name": payload, "pushed": "2026-01-01"}],
                    languages=[{"name": "C", "share": 1.0}],
                    activity=[1] * 52, activity_total=52))
                self.assertEqual(entry.main(["--root", str(tmp), "--offline"]), 0)

                svg = (tmp / "assets" / "hero-dark.svg").read_text("utf-8")
                # Parse it. Escaped text in a text node is inert; only markup
                # can be active, and only a parser can tell the difference.
                root = ElementTree.fromstring(svg)
                tags = {e.tag.rsplit("}", 1)[-1] for e in root.iter()}
                self.assertNotIn("script", tags, f"script element from {payload!r}")
                self.assertNotIn("foreignObject", tags, f"foreignObject from {payload!r}")
                self.assertEqual(audit_output.audit(tmp, strict=True), [])
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    def test_the_dial_is_explained_in_the_description(self):
        """A plot that means something has to say so, or it is still decoration."""
        for name in ("hero-dark", "hero-light"):
            svg = (ROOT / "assets" / f"{name}.svg").read_text("utf-8")
            desc = re.search(r"<desc[^>]*>(.*?)</desc>", svg, re.S).group(1)
            self.assertIn("how recently", desc, f"{name}: dial not explained")


class LiveRenderIsReproducible(unittest.TestCase):
    """A live build's output must survive the reproducibility gate.

    ``load_cache`` used to force ``live=False``, so the freshness badge was the
    one thing in the document that was not a function of the committed
    snapshot: `make live` rendered LIVE TELEMETRY, and the `--check` re-render
    produced CACHED SNAPSHOT and failed. The gate was unpassable after any
    live build, and the published tree was one CI could not verify.

    This is the end-to-end assertion the unit tests missed: render from a
    snapshot marked live, then run the gate against that output.
    """

    def _workspace(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        shutil.copy(ROOT / "profile.json", tmp / "profile.json")
        (tmp / "data").mkdir()
        return tmp

    def _snapshot(self, *, live: bool) -> Snapshot:
        return Snapshot(
            generated_at="2026-01-02T03:04:05Z",
            live=live,
            followers=4,
            public_repos=6,
            own_repos=5,
            total_stars=11,
            account_age_years=2.5,
            languages=[{"name": "TypeScript", "share": 1.0}],
            activity=[1] * 52,
            activity_total=52,
            last_push="2026-01-01",
        )

    def test_live_output_passes_the_check_gate(self):
        tmp = self._workspace()
        try:
            save_cache(tmp / "data" / "cache.json", self._snapshot(live=True))
            self.assertEqual(entry.main(["--root", str(tmp), "--offline"]), 0)
            self.assertIn("LIVE TELEMETRY", (tmp / "assets" / "hero-dark.svg").read_text("utf-8"))
            # The gate must pass against output rendered from a live snapshot.
            self.assertEqual(entry.main(["--root", str(tmp), "--check"]), 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_cached_output_passes_the_check_gate_too(self):
        """The degraded path has to be reproducible as well, not just the happy one."""
        tmp = self._workspace()
        try:
            save_cache(tmp / "data" / "cache.json", self._snapshot(live=False))
            self.assertEqual(entry.main(["--root", str(tmp), "--offline"]), 0)
            self.assertIn("CACHED SNAPSHOT", (tmp / "assets" / "hero-dark.svg").read_text("utf-8"))
            self.assertEqual(entry.main(["--root", str(tmp), "--check"]), 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_badge_actually_differs_between_the_two(self):
        """Guard against the gate passing because the flag stopped mattering."""
        rendered = {}
        for live in (True, False):
            tmp = self._workspace()
            try:
                save_cache(tmp / "data" / "cache.json", self._snapshot(live=live))
                self.assertEqual(entry.main(["--root", str(tmp), "--offline"]), 0)
                rendered[live] = (tmp / "README.md").read_text("utf-8")
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        self.assertNotEqual(rendered[True], rendered[False])
        self.assertIn("live snapshot", rendered[True])
        self.assertIn("cached snapshot", rendered[False])


if __name__ == "__main__":
    unittest.main()
