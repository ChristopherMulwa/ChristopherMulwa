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

<a href="https://devsirchhub.co.ke"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-devsirchhub-co-ke-dark.svg?v=c0556a46cf"><source media="(prefers-color-scheme: light)" srcset="assets/pill-devsirchhub-co-ke-light.svg?v=8b0575b505"><img alt="devsirchhub.co.ke" src="assets/pill-devsirchhub-co-ke-dark.svg?v=c0556a46cf" height="32"></picture></a><a href="https://www.linkedin.com/in/christophermulwa"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-linkedin-dark.svg?v=01dacb6356"><source media="(prefers-color-scheme: light)" srcset="assets/pill-linkedin-light.svg?v=f3da5a227f"><img alt="LinkedIn" src="assets/pill-linkedin-dark.svg?v=01dacb6356" height="32"></picture></a><a href="https://challengeme.africa"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-challengeme-africa-dark.svg?v=70a2efc4dd"><source media="(prefers-color-scheme: light)" srcset="assets/pill-challengeme-africa-light.svg?v=f4f5d8f833"><img alt="challengeme.africa" src="assets/pill-challengeme-africa-dark.svg?v=70a2efc4dd" height="32"></picture></a>

</div>

## whoami

I build and run software that moves money, and I do the security work on it myself: threat models, hardening, testing, incident response. Trained in information security first (BSc, 2019 to 2023), learned full-stack and mobile development by shipping. Founder of Devsirch Hub in Nairobi, where the same person who writes the code is accountable for keeping it safe in production.


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

**Money paths.** Integer amounts only. Every balance change runs in a database transaction with the row locked. Transaction state machines are enforced by Postgres triggers, so an application bug cannot move a payment backwards. Every payment mutation carries an idempotency key that is claimed before the provider call, not after.

**Bank and provider integrations.** The service that talks to a bank is the only service that talks to a bank. Webhooks are logged raw before they are parsed, deduplicated under a lock, and never trusted on their own: the provider&#39;s status API confirms them. Callback URLs are set by the server, never accepted from a caller.

**Data at rest.** National IDs, bank account numbers and provider credentials are AES-256-GCM encrypted per row, with the row&#39;s identity bound into the authenticated data so a ciphertext cannot be moved between rows. Audit logs are append-only and hash-chained. Personal data is redacted at the logger, not by whoever remembers to.

**Access.** Ownership is checked in the handler and again by row-level security. Services authenticate to each other with short-lived Ed25519 tokens. Admin actions need a second factor; the sensitive ones need it again. Secrets are read from a secret manager and the service refuses to boot if one is missing.

**Mobile.** Tokens in the platform keystore, never in app storage. Public-key pinning. Device attestation checked on the server before any payout. Screens that show a PIN or confirm a payment block screenshots.

**Operations.** Metrics, traces and logs through one collector. Every alert has a severity, a destination and a runbook. A webhook that fails signature verification is treated as an attack, and a ledger that disagrees with the bank is an incident.

**Testing my own work.** OWASP API Security Top 10 and MASVS reviews before launch, with findings tracked until the fix is merged and retested. I say plainly that this is self-review, and that an independent test is a different thing.

## How I work

**Design first.** The design is agreed in writing before code. Anything it did not settle is written into the PR as an assumption, so it can be argued with.

**Review before merge.** Every change is reviewed before it merges, and the findings are listed in full before anything is filtered out.

**Incidents become checks.** After an incident I write down the lesson with the date, and where a script can enforce it, it becomes a CI gate.

**Real devices.** A mobile change is tested on a physical phone before it ships, including a cheap one.

## Shipping

### ChallengeMe &nbsp;·&nbsp; `live`

**Side-competitions platform for golf clubs in Kenya.**

Players pay entry fees by M-Pesa, club admins run events and payouts from a live dashboard. Payment webhooks are idempotent and confirmed against the provider before anything is credited, and a club&#39;s wallet is checked before any payout.

`Next.js` `Express` `Prisma` `PostgreSQL` `Redis` `Socket.io`

[challengeme.africa](https://challengeme.africa)

### RSA Boda &nbsp;·&nbsp; `in build`

**Savings group platform for boda-boda riders in Kenya, built for BladeDoc Network.**

Three mobile apps, an admin dashboard, a backend and a separate payments service with direct bank integration for collections, payouts and reconciliation. Members save, borrow and fund group projects; officials approve payouts under dual control. Entering Google Play review, November 2026.

`NestJS` `Next.js` `React Native` `Expo` `PostgreSQL` `Redis`

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
