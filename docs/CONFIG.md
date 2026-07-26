# Editing the profile

Everything you would want to change day-to-day lives in `profile.json`. The
README itself is generated output — editing it directly works until the next
scheduled build overwrites it.

```
profile.json                 <- content: bio, links, stack, projects
generator/                   <- layout: how the content becomes SVG + Markdown
  sanitize.py                <- the trust boundary; read this one first
  config.py                  <- schema validation for profile.json
  design.py                  <- palette, type scale, SVG primitives
  cards/                     <- one module per generated image
  sources/github.py          <- API client, cache, graceful degradation
  readme.py                  <- assembles the Markdown document
tools/audit_output.py        <- post-build secret and active-content scan
tests/                       <- unit tests, run by CI on every pull request
assets/                      <- generated. do not edit.
data/cache.json              <- last-known-good API snapshot. generated.
README.md                    <- generated.
```

## Workflow

```sh
make build      # re-render from the committed snapshot (no network)
make live       # fetch fresh data from the API, then render
make test       # run the test suite
make check      # assert committed output matches a fresh render (what CI runs)
make preview    # build, then print what changed
```

Edit `profile.json`, run `make build`, look at the result, commit. The
scheduled workflow does the same thing every day at 04:17 UTC and only commits
when bytes actually change.

## The config schema

Validation is strict on purpose: **unknown keys are rejected**, not ignored. A
typo fails the build loudly instead of silently dropping a section.

### Top level

| Key | Type | Notes |
| --- | --- | --- |
| `username` | string | GitHub username. `[A-Za-z0-9-]`, max 39. Validated against an allow-list because it is interpolated into API paths. |
| `displayName` | string | The large name in the banner. |
| `headline` | string | One line under the role ticker. Keep it short. |
| `location` | string | Shown in the banner footer. |
| `roles` | string[] | Up to 8. These rotate in the banner, one every 3.4 seconds. |
| `summary` | string | The `whoami` paragraph. Up to 1200 characters. |
| `focus` | string[] | Up to 8 bullets under the summary. |
| `links` | object[] | `{label, url}`. At least one. |
| `stack` | object[] | `{label, accent, items}`. |
| `projects` | object[] | See below. |
| `practices` | object[] | `{label, detail}`. |

### `links[]`

`url` **must** be `https` and its host **must** be in `ALLOWED_LINK_HOSTS` in
`generator/sanitize.py`. Adding a new destination is a deliberate two-line
change to that allow-list — that friction is the point. A config file should
not be able to turn the profile into a redirector.

### `stack[]`

`accent` is one of `accent` (green), `cyan`, `violet`, `amber`, `rose`. Items
wrap automatically; the card grows to fit.

### `projects[]`

| Key | Notes |
| --- | --- |
| `name` | Heading. |
| `tagline` | One bold line. |
| `detail` | Two or three sentences. Say what was hard, not what it does. |
| `stack` | Up to 12 short strings, rendered as code spans. |
| `status` | One of `live`, `building`, `design`, `archived`, `private`. |
| `url` | Optional, allow-listed like `links[]`. |

## Adding a new card

1. Write `generator/cards/yours.py` exposing
   `render(palette, **data) -> str`. Build it from the primitives in
   `design.py` so it inherits the palette, the type scale, and the accessible
   `<svg role="img">` wrapper.
2. Render it for both palettes in `generator/__main__.py`.
3. Place it in the document in `generator/readme.py`.
4. Run `make test` — the suite asserts every asset is well-formed XML, carries
   a non-trivial `<desc>`, and differs between themes.

Anything you interpolate must go through `sanitize.py` first. `text()` and the
other primitives escape their arguments, so pass raw values in and do not
pre-escape.

## Colours and motion

Both themes are generated from the `Palette` dataclasses in `design.py`. Change
a token there and every card follows.

All animation is CSS `@keyframes` inside the SVG, and every animated card
carries a `prefers-reduced-motion: reduce` block that stops it. If you add
motion, add it to that block too.

## First run

`data/cache.json` starts empty, so the first `make build` renders a page with
zeroes and a "cached snapshot" badge. Run `make live` with a token, or just
push and let the scheduled workflow fill it in:

```sh
GITHUB_TOKEN=$(gh auth token) make live
```

Run `make live` twice, a minute apart. `/stats/participation` answers `202
Accepted` the first time GitHub is asked for a repository's statistics while it
computes them; the generator treats any non-200 as "no data" and falls back, so
the first run produces a flat commit-activity chart and the second gets the
real series.

## Freshness

`data/cache.json` carries a `live` flag recording how the snapshot was
obtained, and the badge in the banner reads from it — `LIVE TELEMETRY` when the
API answered, `CACHED SNAPSHOT` when the build fell back. The flag survives a
round-trip through the cache on purpose: `make check` re-renders from the
committed snapshot and compares byte-for-byte, so a value that changed on load
would make every live build fail the gate. Only a failed fetch clears it, and
that write is persisted, so the committed page and the committed snapshot never
disagree. Do not "helpfully" reset it in `load_cache()` — see
[THREAT-MODEL.md](THREAT-MODEL.md) §6.
