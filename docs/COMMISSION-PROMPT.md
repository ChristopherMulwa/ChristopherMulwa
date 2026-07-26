# Prompt: commission the self-building profile pipeline

Copy everything below the line into Claude Code, run from `~/ChristopherMulwa`.

---

You are commissioning a build pipeline into production. The repository is
`~/ChristopherMulwa` — my GitHub profile repository
(`github.com/ChristopherMulwa/ChristopherMulwa`). Work through this in order,
verifying as you go. Do not skip ahead, and do not push anything until Phase 2
passes cleanly.

## What this repository is

The `README.md` shown on my GitHub profile is **generated output**, not a
hand-written file. A scheduled GitHub Actions workflow queries the GitHub API,
renders every image in `assets/` as SVG, rebuilds `README.md`, and commits the
result only when the bytes change.

```
profile.json                     content: bio, links, stack, projects
generator/                       the renderer (stdlib Python only)
  sanitize.py                    the trust boundary — read this first
  config.py                      strict schema validation for profile.json
  design.py                      palette, type scale, SVG primitives
  cards/                         one module per generated image
  sources/github.py              API client, cache, graceful degradation
  readme.py                      assembles the Markdown
tools/audit_output.py            post-build secret + active-content scan
tests/                           76 tests, incl. an injection suite
.github/workflows/
  build-profile.yml              the scheduled build (holds contents: write)
  verify.yml                     PR gate: tests + reproducibility + audit
docs/THREAT-MODEL.md             why the pipeline is built the way it is
assets/  data/cache.json  README.md      all generated — never hand-edit
```

Read `docs/CONFIG.md` and `docs/THREAT-MODEL.md` before you change anything.

## Non-negotiable constraints

This repository is public, and the workflow runs with a write-capable token.
The security properties below are the point of the design, not incidental. **If
making something pass would require weakening any of these, stop and report
instead of doing it.**

1. **No `uses:` in any workflow.** Zero third-party Actions, deliberately —
   including `actions/checkout`. Four `git` commands replace it.
2. **No third-party Python packages.** Stdlib only. No `requirements.txt`, no
   `pip install` step. If you think you need a library, you need a different
   approach.
3. **No new workflow triggers.** Never add `pull_request_target`,
   `issue_comment`, or `workflow_run`.
4. **Never interpolate `${{ }}` inside a `run:` block.** Pass values through
   `env:` and reference them as shell variables.
5. **Never widen `ALLOWED_LINK_HOSTS`** in `generator/sanitize.py` without
   asking me first.
6. **Never hand-edit** `README.md`, `assets/*.svg`, or `data/cache.json`.
   Change `profile.json` or the generator and re-render.

## Phase 1 — Understand and verify locally

```sh
cd ~/ChristopherMulwa
make help
make test        # expect: Ran 76 tests ... OK
make build       # render from the committed snapshot, no network
make check       # expect: "output is up to date"
make audit       # expect: "output audit passed"
```

`make check` is the reproducibility gate: it re-renders and fails if a single
byte differs from what is committed. If it fails, `make build` and inspect the
diff — a change to the generator that was never re-rendered is exactly what it
exists to catch.

Report the results of all four before continuing. If anything fails, diagnose
it and tell me what you found — do not paper over it.

## Phase 2 — Populate real data

The committed `data/cache.json` is a zero snapshot, so the page currently shows
zeroes and a "cached snapshot" badge. Fetch the real numbers:

```sh
GITHUB_TOKEN=$(gh auth token) make live
```

**Run `make live` twice, about 60 seconds apart.** The
`/repos/{owner}/{repo}/stats/participation` endpoint returns `202 Accepted` the
first time it is asked, while GitHub computes the statistics. The generator
treats a non-200 as "no data" and falls back, so the first run produces a flat
commit-activity chart and the second run gets the real series.

Then confirm:

- The hero badge reads **LIVE TELEMETRY**, not `CACHED SNAPSHOT`
  (`grep -o 'LIVE TELEMETRY\|CACHED SNAPSHOT' assets/hero-dark.svg`).
- `data/cache.json` has a non-zero `activity_total` and a populated
  `languages` array.
- The numbers in the `<details>` fallback table in `README.md` match
  `data/cache.json`.
- `make audit` still passes, and `make check` passes.

Open `README.md` and read it. Tell me anything that looks wrong, thin, or
overstated — especially in the project descriptions, which were drafted partly
by inference from my repositories rather than from my own words. Flag anything
you would not stand behind; do not silently "improve" my copy.

## Phase 3 — Configure the repository

The workflow declares `permissions: contents: write`, but a job cannot exceed
the repository default. Check it:

```sh
gh api repos/ChristopherMulwa/ChristopherMulwa/actions/permissions/workflow
```

If `default_workflow_permissions` is `read`, set it:

```sh
gh api -X PUT repos/ChristopherMulwa/ChristopherMulwa/actions/permissions/workflow \
  -f default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=false
```

Also confirm Actions is enabled for the repository, and tell me if `main` has
branch protection that would block the bot's push.

## Phase 4 — Push

Show me `git status` and a summary of the diff **before** committing. Then:

```sh
git add -A
git commit -m "feat: self-building profile with hardened generation pipeline"
git push origin main
```

Note for your own awareness: this push matches the workflow's `paths` filter,
so it will trigger a build. The bot's own commit carries `[skip ci]`, so it
does not loop.

If `_to_delete/` is still present, ask me before removing it — it holds my
previous README.

## Phase 5 — Verify the automation actually works

This is the part I care most about. Do not report success until you have
observed the workflow complete.

```sh
gh run list --workflow="build profile" --limit 5
gh run watch                      # follow the triggered run
```

If it did not trigger, dispatch it manually:

```sh
gh workflow run "build profile"
```

Then verify, concretely:

1. **The run succeeded.** If not, `gh run view --log-failed` and diagnose.
   Report the actual error, not a guess.
2. **Every step behaved.** In the log, confirm the fetch step checked out,
   the render step reported assets rendered, the audit printed
   "output audit passed", and the commit step either published or said
   "no change; nothing to publish".
3. **Nothing leaked.** Search the run log for anything token-shaped
   (`ghs_`, `ghp_`, `x-access-token:`, a bare `Authorization:` value). The
   token appears in a remote URL by design — confirm Actions **masked** it as
   `***` rather than printing it.
4. **The published output is reproducible.** This is the real proof:
   ```sh
   git pull --ff-only
   make check          # must pass against the bot's own commit
   make audit
   ```
5. **Every asset resolves over HTTP.** Relative image paths must actually
   serve. For each of `hero`, `telemetry`, `stack`, `pipeline` in both `-dark`
   and `-light`, plus the three `pill-*` pairs:
   ```sh
   for f in assets/*.svg; do
     printf '%s ' "$f"
     curl -s -o /dev/null -w '%{http_code} %{content_type}\n' \
       "https://raw.githubusercontent.com/ChristopherMulwa/ChristopherMulwa/main/$f"
   done
   ```
   Expect `200` for all fourteen. A `404` means an asset was not committed.
6. **The cache-busting hashes are correct.** Each `?v=` query in `README.md`
   is the first 10 hex characters of the SHA-256 of that asset's file
   contents. Verify a couple by hand — a stale hash means GitHub's image proxy
   will keep serving an old render.
7. **The page renders.** Open `https://github.com/ChristopherMulwa` and check
   it in both light and dark mode. The `<picture>` elements must swap themes,
   the role ticker in the banner must cycle, and the radar sweep must animate.
   Tell me if any image is broken, clipped, or unreadable in either theme.
8. **The fallback works.** Confirm the `<details>` block expands and the
   numbers are legible with images disabled.

## Phase 6 — Report

Give me:

- A pass/fail line for each phase.
- Anything that failed, with the actual error and what you did about it.
- Anything you noticed that is not broken but is worth fixing — layout,
  wording, a control that reads stronger in the docs than it is in the code.
- Confirmation of the next scheduled run time (cron is `17 4 * * *` UTC;
  I am in `Africa/Nairobi`, UTC+3).

## If you need to roll back

My previous profile README is in history:

```sh
git show 850bc38:README.md > README.md.old      # inspect
```

Do not roll back unilaterally. Show me the problem and ask.

## Working style

- Read before you write. `sanitize.py` and `THREAT-MODEL.md` explain why
  things are shaped the way they are.
- Verify with commands, not assumptions. If you claim something works, show
  me the output that proves it.
- When a fix would trade away a security property for convenience, stop and
  give me the trade-off in one paragraph. Let me decide.
- Tell me when something is wrong even if I seem invested in it.
