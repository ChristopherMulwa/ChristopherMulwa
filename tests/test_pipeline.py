"""End-to-end tests: config validation, rendering, determinism, and the
behaviour of the generator when the GitHub API returns hostile data.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generator import __main__ as entry  # noqa: E402
from generator.config import ConfigError, load  # noqa: E402
from generator.design import PALETTES  # noqa: E402
from generator.sources import github  # noqa: E402
from generator.sources.github import Snapshot, load_cache, save_cache  # noqa: E402


def _workspace() -> Path:
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(ROOT / "profile.json", tmp / "profile.json")
    (tmp / "data").mkdir()
    return tmp


class ConfigValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.base = json.loads((ROOT / "profile.json").read_text("utf-8"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, data) -> Path:
        path = self.tmp / "profile.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_real_config_is_valid(self):
        cfg = load(ROOT / "profile.json")
        self.assertTrue(cfg.username)
        self.assertTrue(cfg.projects)

    def test_unknown_top_level_key_is_rejected(self):
        data = dict(self.base, surprise=1)
        with self.assertRaises(ConfigError):
            load(self._write(data))

    def test_unknown_nested_key_is_rejected(self):
        data = json.loads(json.dumps(self.base))
        data["projects"][0]["onerror"] = "alert(1)"
        with self.assertRaises(ConfigError):
            load(self._write(data))

    def test_bad_username_is_rejected(self):
        for bad in ("../etc", "a/b", "x" * 40, "", "-lead", "a b", "a?b=1"):
            data = dict(self.base, username=bad)
            with self.assertRaises(ConfigError, msg=bad):
                load(self._write(data))

    def test_off_allowlist_link_is_rejected(self):
        data = json.loads(json.dumps(self.base))
        data["links"][0]["url"] = "https://evil.example"
        with self.assertRaises(ConfigError):
            load(self._write(data))

    def test_javascript_url_is_rejected(self):
        data = json.loads(json.dumps(self.base))
        data["links"][0]["url"] = "javascript:alert(1)"
        with self.assertRaises(ConfigError):
            load(self._write(data))

    def test_unknown_status_is_rejected(self):
        data = json.loads(json.dumps(self.base))
        data["projects"][0]["status"] = "totally-shipped"
        with self.assertRaises(ConfigError):
            load(self._write(data))

    def test_malformed_json_is_rejected(self):
        path = self.tmp / "profile.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ConfigError):
            load(path)

    def test_oversized_config_is_rejected(self):
        path = self.tmp / "profile.json"
        path.write_text("{" + '"x":"' + "a" * 400_000 + '"}', encoding="utf-8")
        with self.assertRaises(ConfigError):
            load(path)


class Rendering(unittest.TestCase):
    def setUp(self):
        self.tmp = _workspace()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_offline_build_succeeds_with_no_cache(self):
        self.assertEqual(entry.main(["--root", str(self.tmp), "--offline"]), 0)
        self.assertTrue((self.tmp / "README.md").exists())
        self.assertTrue(list((self.tmp / "assets").glob("*.svg")))

    def test_every_asset_is_well_formed_xml(self):
        entry.main(["--root", str(self.tmp), "--offline"])
        for svg in (self.tmp / "assets").glob("*.svg"):
            ElementTree.fromstring(svg.read_text("utf-8"))

    def test_every_asset_is_accessible(self):
        entry.main(["--root", str(self.tmp), "--offline"])
        ns = "{http://www.w3.org/2000/svg}"
        for svg in (self.tmp / "assets").glob("*.svg"):
            root = ElementTree.fromstring(svg.read_text("utf-8"))
            self.assertEqual(root.get("role"), "img", svg.name)
            self.assertIsNotNone(root.find(f"{ns}title"), svg.name)
            desc = root.find(f"{ns}desc")
            self.assertIsNotNone(desc, svg.name)
            self.assertGreater(len((desc.text or "").strip()), 10, svg.name)

    def test_build_is_deterministic(self):
        entry.main(["--root", str(self.tmp), "--offline"])
        first = {p.name: p.read_bytes() for p in (self.tmp / "assets").glob("*.svg")}
        first["README.md"] = (self.tmp / "README.md").read_bytes()

        entry.main(["--root", str(self.tmp), "--offline"])
        second = {p.name: p.read_bytes() for p in (self.tmp / "assets").glob("*.svg")}
        second["README.md"] = (self.tmp / "README.md").read_bytes()

        self.assertEqual(first, second)

    def test_check_passes_on_fresh_build(self):
        entry.main(["--root", str(self.tmp), "--offline"])
        self.assertEqual(entry.main(["--root", str(self.tmp), "--check"]), 0)

    def test_check_fails_when_output_is_edited(self):
        entry.main(["--root", str(self.tmp), "--offline"])
        readme = self.tmp / "README.md"
        readme.write_text(readme.read_text("utf-8") + "\ntampered\n", encoding="utf-8")
        self.assertEqual(entry.main(["--root", str(self.tmp), "--check"]), 1)

    def test_hostile_api_data_cannot_escape_a_sink(self):
        """The realistic attack: a repository name or language string that
        contains markup. It reaches the SVG and the README, and must not
        break either."""
        payload = '</text><script>alert(1)</script><text x="0"'
        snap = Snapshot(
            generated_at="2026-01-02T03:04:05Z",
            live=True,
            followers=3,
            public_repos=4,
            own_repos=4,
            total_stars=5,
            account_age_years=2.0,
            languages=[{"name": payload, "share": 0.5},
                       {"name": "<img src=x onerror=alert(1)>", "share": 0.5}],
            activity=[1] * 52,
            activity_total=52,
            last_push=payload,
        )
        save_cache(self.tmp / "data" / "cache.json", snap)
        self.assertEqual(entry.main(["--root", str(self.tmp), "--offline"]), 0)

        for svg in (self.tmp / "assets").glob("*.svg"):
            content = svg.read_text("utf-8")
            ElementTree.fromstring(content)
            self.assertNotIn("<script", content.lower(), svg.name)

        readme = (self.tmp / "README.md").read_text("utf-8")
        self.assertNotIn("<script", readme.lower())

    def test_absurd_numbers_do_not_break_geometry(self):
        snap = Snapshot(
            generated_at="2026-01-02T03:04:05Z",
            live=True,
            followers=-99999,
            total_stars=10**12,
            own_repos=-1,
            account_age_years=-5.0,
            languages=[{"name": "X", "share": 99.0}, {"name": "Y", "share": -3.0}],
            activity=[-100] * 52,
            activity_total=-1,
        )
        save_cache(self.tmp / "data" / "cache.json", snap)
        self.assertEqual(entry.main(["--root", str(self.tmp), "--offline"]), 0)
        for svg in (self.tmp / "assets").glob("*.svg"):
            ElementTree.fromstring(svg.read_text("utf-8"))

    def test_both_themes_are_emitted(self):
        entry.main(["--root", str(self.tmp), "--offline"])
        names = {p.name for p in (self.tmp / "assets").glob("*.svg")}
        for base in ("hero", "telemetry", "stack", "pipeline"):
            self.assertIn(f"{base}-dark.svg", names)
            self.assertIn(f"{base}-light.svg", names)

    def test_themes_actually_differ(self):
        entry.main(["--root", str(self.tmp), "--offline"])
        for base in ("hero", "telemetry", "stack", "pipeline"):
            dark = (self.tmp / "assets" / f"{base}-dark.svg").read_text("utf-8")
            light = (self.tmp / "assets" / f"{base}-light.svg").read_text("utf-8")
            self.assertNotEqual(dark, light, base)


class CacheBehaviour(unittest.TestCase):
    def setUp(self):
        self.tmp = _workspace()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_corrupt_cache_does_not_crash(self):
        (self.tmp / "data" / "cache.json").write_text("{{{", encoding="utf-8")
        self.assertEqual(entry.main(["--root", str(self.tmp), "--offline"]), 0)

    def test_cache_with_wrong_types_is_ignored_field_by_field(self):
        (self.tmp / "data" / "cache.json").write_text(
            json.dumps({"followers": "many", "total_stars": 12, "activity": "nope"}),
            encoding="utf-8",
        )
        snap = load_cache(self.tmp / "data" / "cache.json")
        self.assertEqual(snap.followers, 0)      # wrong type -> default
        self.assertEqual(snap.total_stars, 12)   # right type -> kept
        self.assertEqual(snap.activity, [])

    def test_cache_round_trips_the_live_flag(self):
        """``live`` describes the snapshot, so it must survive the round-trip.

        It used to be forced to False on load, which meant a live build could
        never be re-rendered from its own committed cache: the reproducibility
        gate compared a LIVE page against a CACHED re-render and always failed.
        """
        path = self.tmp / "data" / "cache.json"
        save_cache(path, Snapshot(live=True, followers=1))
        self.assertTrue(load_cache(path).live)
        save_cache(path, Snapshot(live=False, followers=1))
        self.assertFalse(load_cache(path).live)

    def test_failed_fetch_degrades_the_flag_and_persists_it(self):
        """A build that cannot reach the API must not publish a LIVE page.

        ``_degraded`` clears the flag *and* writes it back, so the committed
        snapshot still explains the committed output.
        """
        path = self.tmp / "data" / "cache.json"
        save_cache(path, Snapshot(live=True, followers=3, total_stars=9))
        snap = github._degraded(path)
        self.assertFalse(snap.live)
        self.assertEqual(snap.followers, 3)      # data preserved
        self.assertEqual(snap.total_stars, 9)
        self.assertFalse(load_cache(path).live)  # and the change is on disk

    def test_offline_resolve_does_not_degrade_the_flag(self):
        """`--check` and `make build` resolve offline and must not mutate state."""
        path = self.tmp / "data" / "cache.json"
        save_cache(path, Snapshot(live=True, followers=1))
        before = path.read_text("utf-8")
        self.assertTrue(github.resolve("ChristopherMulwa", path, offline=True).live)
        self.assertEqual(path.read_text("utf-8"), before)

    def test_unknown_cache_keys_are_dropped(self):
        (self.tmp / "data" / "cache.json").write_text(
            json.dumps({"__class__": "evil", "followers": 7}), encoding="utf-8"
        )
        snap = load_cache(self.tmp / "data" / "cache.json")
        self.assertEqual(snap.followers, 7)
        self.assertFalse(hasattr(snap, "__evil__"))


class Palettes(unittest.TestCase):
    def test_every_palette_defines_every_token(self):
        for p in PALETTES:
            for field in ("canvas", "surface", "border", "text", "muted", "accent"):
                value = getattr(p, field)
                self.assertRegex(value, r"^#[0-9A-Fa-f]{6}$", f"{p.name}.{field}")
            self.assertEqual(len(p.heat), 5, p.name)


if __name__ == "__main__":
    unittest.main()
