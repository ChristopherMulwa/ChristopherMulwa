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
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg?v=e936a91749">
  <source media="(prefers-color-scheme: light)" srcset="assets/hero-light.svg?v=b1b180e81a">
  <img alt="Christopher Mulwa — I build products, then try to break them." src="assets/hero-dark.svg?v=e936a91749" width="100%">
</picture>

&nbsp;

<a href="https://devsirchhub.co.ke"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-devsirchhub-co-ke-dark.svg?v=c0556a46cf"><source media="(prefers-color-scheme: light)" srcset="assets/pill-devsirchhub-co-ke-light.svg?v=8b0575b505"><img alt="devsirchhub.co.ke" src="assets/pill-devsirchhub-co-ke-dark.svg?v=c0556a46cf" height="32"></picture></a><a href="https://www.linkedin.com/in/christopher-mulwa/"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-linkedin-dark.svg?v=01dacb6356"><source media="(prefers-color-scheme: light)" srcset="assets/pill-linkedin-light.svg?v=f3da5a227f"><img alt="LinkedIn" src="assets/pill-linkedin-dark.svg?v=01dacb6356" height="32"></picture></a><a href="https://challengeme.africa"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-challengeme-africa-dark.svg?v=70a2efc4dd"><source media="(prefers-color-scheme: light)" srcset="assets/pill-challengeme-africa-light.svg?v=f4f5d8f833"><img alt="challengeme.africa" src="assets/pill-challengeme-africa-dark.svg?v=70a2efc4dd" height="32"></picture></a>

</div>

## whoami

Software engineer in Nairobi working across the full stack, with a second discipline in application security. Most of what I ship lately is golf technology — a live challenge platform, a tee-time booking system, and a coaching tool — built as one product family on a shared stack. The security half is not a label: it is the reason my architecture decisions look the way they do, and it is the training I put deliberate hours into rather than the thing I claim on a CV.

- Full-stack product work — Next.js and NestJS front to back, PostgreSQL underneath, React Native for mobile.
- Application security — threat modelling, authorisation design, and the boring input-handling work that stops most real bugs.
- Offensive security in training — structured practice on TryHackMe and HackerOne, applied back into how I build.
- Systems that survive contact with users — caching, background work, and failure modes considered before launch, not after.

## Telemetry

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/telemetry-dark.svg?v=8386da2e70">
  <source media="(prefers-color-scheme: light)" srcset="assets/telemetry-light.svg?v=37c7eb596c">
  <img alt="GitHub telemetry: repositories, stars, commit activity and language mix" src="assets/telemetry-dark.svg?v=8386da2e70" width="100%">
</picture>

<details>
<summary>Same numbers as text (for screen readers, and for when images are blocked)</summary>

| Metric | Value |
| --- | --- |
| Public repositories (non-fork) | 5 |
| Stars earned | 0 |
| Commits, trailing 52 weeks | 18 |
| Followers | 0 |
| Years on GitHub | 2\.5 |
| Last public push | 2026-07-26 |
| Snapshot | 2026-07-26 15:10 UTC (live) |

| Language | Share |
| --- | --- |
| TypeScript | 76% |
| Python | 14% |
| C | 10% |

</details>

## Build surface

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/stack-dark.svg?v=4bd7e426fb">
  <source media="(prefers-color-scheme: light)" srcset="assets/stack-light.svg?v=35e0af83ff">
  <img alt="Technology stack grouped by domain" src="assets/stack-dark.svg?v=4bd7e426fb" width="100%">
</picture>

## Shipping

### ChallengeMe &nbsp;·&nbsp; `live`

**Golf challenge platform, live in production.**

Players create and settle head-to-head challenges: matchmaking, scoring, and a results history that has to stay correct when two people disagree about what happened on the course. Deployed and running for real users.

`Next.js` `NestJS` `PostgreSQL` `Redis` `Docker`

[challengeme.africa](https://challengeme.africa)

### TeeupTime &nbsp;·&nbsp; `in build`

**Tee-time booking for golf clubs.**

Inventory, availability and reservations for clubs that currently run their bookings through a phone and a paper diary. The interesting problem is concurrency — two members booking the same slot at the same moment must resolve deterministically, and the club has to be able to override it.

`Next.js` `NestJS` `PostgreSQL` `Redis`

### Swing &nbsp;·&nbsp; `in build`

**Coaching management for golf coaches and their students.**

Lesson scheduling, student progress, and session notes in one place, with a mobile client for coaches who spend their working day on a range rather than at a desk. Multi-tenant from the first commit, because retrofitting tenant isolation is where authorisation bugs come from.

`React Native` `Expo` `NestJS` `PostgreSQL`

### WHS Handicap Calculator &nbsp;·&nbsp; `live`

**World Handicap System calculator and simulator.**

An implementation of the WHS handicap index rules — score differentials, the best-eight-of-twenty window, and the soft and hard caps — with a simulator for seeing how a round moves an index before it counts.

`TypeScript`

[github.com/ChristopherMulwa/WHS-Handicap-Calculator-simulator](https://github.com/ChristopherMulwa/WHS-Handicap-Calculator-simulator)

## Security practice

**Threat model before schema** — Every product above is multi-tenant. I decide who can see what, and how that is enforced at the query layer rather than the UI layer, before the first migration runs.

**Authorisation is not authentication** — Most of the serious bugs I find in training are broken object-level authorisation, not broken login. I test for it on my own work the same way — by asking what happens when a valid session requests someone else&#39;s identifier.

**Untrusted input has a boundary** — Input is validated and encoded where it enters and where it leaves, for the sink it is going to. This repository is a worked example: see generator/sanitize.py.

**Secrets and permissions are scoped down** — Least privilege applied to CI tokens, database roles, and third-party keys. If a credential can only do one thing, a leak is an incident rather than a catastrophe.

**Training that feeds back into building** — Structured offensive practice on TryHackMe and HackerOne. The point is not the badge count — it is that every class of bug I learn to exploit becomes a class of bug I stop shipping.

---

<sub>Generated 2026-07-26 15:10 UTC · live snapshot · no third-party trackers, badge services, or analytics on this page.</sub>
