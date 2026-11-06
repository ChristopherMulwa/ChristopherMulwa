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
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg?v=80e1735887">
  <source media="(prefers-color-scheme: light)" srcset="assets/hero-light.svg?v=585890295a">
  <img alt="Christopher Mulwa" src="assets/hero-dark.svg?v=80e1735887" width="100%">
</picture>

&nbsp;

<a href="https://devsirchhub.co.ke"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-devsirchhub-co-ke-dark.svg?v=c0556a46cf"><source media="(prefers-color-scheme: light)" srcset="assets/pill-devsirchhub-co-ke-light.svg?v=8b0575b505"><img alt="devsirchhub.co.ke" src="assets/pill-devsirchhub-co-ke-dark.svg?v=c0556a46cf" height="32"></picture></a><a href="https://www.linkedin.com/in/christophermulwa"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-linkedin-dark.svg?v=01dacb6356"><source media="(prefers-color-scheme: light)" srcset="assets/pill-linkedin-light.svg?v=f3da5a227f"><img alt="LinkedIn" src="assets/pill-linkedin-dark.svg?v=01dacb6356" height="32"></picture></a>

</div>

## whoami

I build and run software that moves money, and I do the security work on it myself: threat models, hardening, testing, incident response. Trained in information security first (BSc, 2019 to 2023), learned full-stack and mobile development by shipping. Founder of Devsirch Hub in Nairobi.


> Almost all of my work is in private client repositories, so the public repos here are not representative. The activity card includes the private ones.

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

**Threat model before code.** For anything that handles money or personal data, I write down who could attack it and how before the design is settled, and the design answers each one.

**Standards, not instinct.** OWASP ASVS and the API Security Top 10 for web and services, MASVS and MASTG for mobile, the Kenya Data Protection Act for anything personal. Reviews are run against the list, and findings stay open until the fix is merged and retested.

**Self-review is labelled as such.** I test my own work and say so. An independent penetration test is a different thing, and I tell clients to commission one.

**Operations are part of security.** Every alert has a severity, an owner and a runbook, logs carry no personal data, and backups are restored on a schedule to prove they work.

## How I work

**Design first.** The design is agreed in writing before code. Anything it did not settle is written into the PR as an assumption, so it can be argued with.

**Review before merge.** Every change is reviewed before it merges, and the findings are listed in full before anything is filtered out.

**Incidents become checks.** After an incident I write down the lesson with the date, and where a script can enforce it, it becomes a CI gate.

**Real devices.** A mobile change is tested on a physical phone before it ships, including a cheap one.

## Shipping

### ChallengeMe &nbsp;·&nbsp; `live`

**Side-competitions platform for golf clubs in Kenya.**

Built for a client. Mobile-money entry fees, event management and payouts for club admins. Live since 2025.

`Next.js` `Express` `Prisma` `PostgreSQL` `Redis` `Socket.io`

[challengeme.africa](https://challengeme.africa)

### RSA Boda &nbsp;·&nbsp; `private`

**Savings and lending platform for riders&#39; groups in Kenya.**

Built and operated for a client. Mobile apps, admin dashboard, backend and bank-connected payments. Closed source.

`NestJS` `Next.js` `React Native` `PostgreSQL`

## Stack

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/stack-dark.svg?v=7b31c1d05f">
  <source media="(prefers-color-scheme: light)" srcset="assets/stack-light.svg?v=8229a0fa96">
  <img alt="Technology stack grouped by domain" src="assets/stack-dark.svg?v=7b31c1d05f" width="100%">
</picture>

## Learning

- Offensive work on TryHackMe and Hack The Box, Burp Suite against my own apps first.
- Mobile security: MASVS and MASTG, applied to the React Native apps I ship.
- A cybersecurity news digest I built for myself, running every morning since May 2026.

---

<sub>Generated 2026-09-17 11:13 UTC · live snapshot · no third-party trackers, badge services, or analytics on this page.</sub>
