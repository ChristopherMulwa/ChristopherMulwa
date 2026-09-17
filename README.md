<!--
  This file is generated. Do not edit it directly -- the next scheduled
  build will overwrite your changes.

    content   ->  profile.json
    layout    ->  generator/
    schedule  ->  .github/workflows/build-profile.yml

  Regenerate locally with:  make build   (or: python3 -m generator --offline)
-->

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg?v=ae9c765fdf">
  <source media="(prefers-color-scheme: light)" srcset="assets/hero-light.svg?v=ed6f91b830">
  <img alt="Christopher Mulwa" src="assets/hero-dark.svg?v=ae9c765fdf" width="100%">
</picture>

&nbsp;

<a href="https://devsirchhub.co.ke"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-devsirchhub-co-ke-dark.svg?v=c0556a46cf"><source media="(prefers-color-scheme: light)" srcset="assets/pill-devsirchhub-co-ke-light.svg?v=8b0575b505"><img alt="devsirchhub.co.ke" src="assets/pill-devsirchhub-co-ke-dark.svg?v=c0556a46cf" height="32"></picture></a><a href="https://www.linkedin.com/in/christophermulwa"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-linkedin-dark.svg?v=01dacb6356"><source media="(prefers-color-scheme: light)" srcset="assets/pill-linkedin-light.svg?v=f3da5a227f"><img alt="LinkedIn" src="assets/pill-linkedin-dark.svg?v=01dacb6356" height="32"></picture></a><a href="https://challengeme.africa"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-challengeme-africa-dark.svg?v=70a2efc4dd"><source media="(prefers-color-scheme: light)" srcset="assets/pill-challengeme-africa-light.svg?v=f4f5d8f833"><img alt="challengeme.africa" src="assets/pill-challengeme-africa-dark.svg?v=70a2efc4dd" height="32"></picture></a>

</div>

## whoami

Security engineer who builds. BSc Information Security and Forensics, 2019 to 2023, then a self-taught full-stack and mobile practice on top. Founder of Devsirch Hub in Nairobi, a security-first firm that also builds, on its way to being the cybersecurity company Kenya trusts first. I ship software that handles money, and I attack it before anyone else can.


> Nearly all of my commits are client work in private repositories, so the public repositories here are a poor sample. The activity card counts the private ones too.

## Activity

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/telemetry-dark.svg?v=28566a0025">
  <source media="(prefers-color-scheme: light)" srcset="assets/telemetry-light.svg?v=f858c0e17b">
  <img alt="GitHub telemetry: contributions across public and private repositories, weekly activity, and work by type" src="assets/telemetry-dark.svg?v=28566a0025" width="100%">
</picture>

<details>
<summary>Same numbers as text (for screen readers, and for when images are blocked)</summary>

| Metric | Value |
| --- | --- |
| Contributions, trailing 12 months | 3\.5k |
| In private repositories | 3\.5k |
| Public commits | 19 |
| Public pull requests | 2 |
| Public reviews and issues | 0 |
| Public repositories (non-fork) | 4 |
| Years on GitHub | 2\.7 |
| Snapshot | 2026-09-17 11:13 UTC (live) |

</details>

## Security practice

**Authentication is a boundary, not a form.** Argon2id for anything a person types, device binding for anything a person carries, a second factor before a privileged action, and short-lived signed tokens between services. A session that loses the network is not a session that has lost its rights.

**Authorisation on every object, every time.** Every ID a request carries is checked for ownership in the handler, then again by row-level security in the database. Broken object-level authorisation is the bug I hunt first, because it is the one that turns one user&#39;s data into everyone&#39;s.

**Least privilege, by named role.** Roles are named, permissions are enumerated, and a service can only do the one thing it exists for. A credential that can only do one thing turns a leak into an incident instead of a catastrophe.

**Confidentiality, integrity, availability, in that order of paranoia.** Sensitive fields encrypted at rest and bound to their own row. Audit logs append-only and hash-chained, tamper-evident rather than tamper-proof. Money state machines enforced by the database, not the application. Rate limits that survive an outage of the store that holds them.

**Input is hostile until proven otherwise.** Strict schemas at every boundary, including the environment at boot, my own config, and this page: every string from the GitHub API or profile.json passes one sanitiser before it reaches Markdown or SVG. [Threat model](https://github.com/ChristopherMulwa/ChristopherMulwa/blob/main/docs/THREAT-MODEL.md)

**If it is not observed, it is not running.** Metrics, traces and logs go through one collector to one place, and every alert maps to a severity with a fixed set of sinks. An event nobody mapped defaults to the middle severity, so a forgotten mapping shows up as noise rather than silence. A failed webhook signature pages as an attack, not a bug; a mismatch between a provider&#39;s balance and the ledger pages as an incident. Every alert has a runbook, and by the time a log line leaves the process it carries no personal data.

**I test my own work first.** OWASP API Security Top 10 and MASVS before a launch, findings in one register that closes only on a merged and re-tested fix. That is self-review with tools, and I label it as such.

## How I work

**Spec first.** I agree the design, then the agent builds. Anything the spec did not settle goes into the PR as an assumption, and merging waits for me.

**Nothing merges unreviewed.** Two review agents with different questions, then me. I act first on the finding they disagree about.

**Every incident becomes a check.** Post-mortems become dated lessons. Where a grep can enforce one, it becomes a CI gate.

**Handsets, not simulators.** A mobile change ships after it has run on a physical device.

## Shipping

### ChallengeMe &nbsp;·&nbsp; `live`

**Side-competitions platform for golf clubs, live in Kenya.**

Players pay entry fees by mobile money, club admins run events and payouts from a real-time dashboard, and every entry keeps the fee rate that applied to it. Webhooks are idempotent and re-verified against the provider, and a club&#39;s wallet is checked before any disbursement. An accessibility gate runs in CI.

`Next.js` `Express` `Prisma` `PostgreSQL` `Redis` `Socket.io`

[challengeme.africa](https://challengeme.africa)

## Stack

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/stack-dark.svg?v=882abc71ae">
  <source media="(prefers-color-scheme: light)" srcset="assets/stack-light.svg?v=20f499507d">
  <img alt="Technology stack grouped by domain" src="assets/stack-dark.svg?v=882abc71ae" width="100%">
</picture>

## Learning

- Offensive practice on TryHackMe and Hack The Box, with a Kali lab and a bug-bounty kit built around the OWASP testing guides.
- Mobile security for the React Native apps I ship: MASVS and MASTG, and certificate pinning that behaves the same in a release build as in the dev client.
- A daily cybersecurity news digest I built for myself, running every morning since May 2026.

---

<sub>Generated 2026-09-17 11:13 UTC · live snapshot · no third-party trackers, badge services, or analytics on this page.</sub>
