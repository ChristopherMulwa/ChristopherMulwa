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
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg?v=368472cfa1">
  <source media="(prefers-color-scheme: light)" srcset="assets/hero-light.svg?v=82230dd277">
  <img alt="Christopher Mulwa: I build systems that move money, then try to break them." src="assets/hero-dark.svg?v=368472cfa1" width="100%">
</picture>

&nbsp;

<a href="https://devsirchhub.co.ke"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-devsirchhub-co-ke-dark.svg?v=c0556a46cf"><source media="(prefers-color-scheme: light)" srcset="assets/pill-devsirchhub-co-ke-light.svg?v=8b0575b505"><img alt="devsirchhub.co.ke" src="assets/pill-devsirchhub-co-ke-dark.svg?v=c0556a46cf" height="32"></picture></a><a href="https://www.linkedin.com/in/christophermulwa"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-linkedin-dark.svg?v=01dacb6356"><source media="(prefers-color-scheme: light)" srcset="assets/pill-linkedin-light.svg?v=f3da5a227f"><img alt="LinkedIn" src="assets/pill-linkedin-dark.svg?v=01dacb6356" height="32"></picture></a><a href="https://challengeme.africa"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/pill-challengeme-africa-dark.svg?v=70a2efc4dd"><source media="(prefers-color-scheme: light)" srcset="assets/pill-challengeme-africa-light.svg?v=f4f5d8f833"><img alt="challengeme.africa" src="assets/pill-challengeme-africa-dark.svg?v=70a2efc4dd" height="32"></picture></a>

</div>

## whoami

I came into software through security, not the other way round: a BSc in Information Security and Forensics from 2019 to 2023, then a self-taught stack on top. I founded Devsirch Hub in Nairobi, a security-first firm that also builds, and I am growing it into the cybersecurity company Kenya trusts first and the rest of the world comes to know. Right now most of my time goes into one client&#39;s financial platform, where I am the only engineer. Alongside it I shipped ChallengeMe, which golf clubs here use to run side-competitions: players pay by mobile money and winners get paid out. For the last two years I have built with AI coding agents inside rules I keep tightening, and practised security on my own code before anyone else gets to it. The part I like is the failure case: the retry that would pay twice, the audit row someone wants to quietly fix.


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

Two rules I hold because I have seen the alternative. A hand-kept allowlist of protected tables goes stale within weeks, so the CI check that proves row-level security enumerates the catalogue and fails closed on any table it has not seen. And an empty-set SELECT FOR UPDATE locks nothing, so the first write of any hash chain takes an advisory lock through one helper, and a test forces the race on purpose.

**Money moves through one door.** Only the payment gateway talks to a payment provider, and a database row chooses the adapter. Every financial mutation carries an idempotency key that the gateway claims in the database before it calls the provider, so a retried, double-tapped or replayed request maps to one transaction. The gateway never accepts a callback URL from a caller. A daily job compares the provider balance with the internal ledger, and any drift is an incident.

**The audit log is tamper-evident, not tamper-proof.** Triggers reject UPDATE and DELETE, each row hashes the one before it, and a Merkle root over each period goes into a second protected table. Anyone with DDL rights, which today means me, could still rewrite the lot. That is the residual risk, and anchoring the roots outside the database is the next step.

**Encrypted fields are bound to their place.** AES-256-GCM with a fresh IV per row and length-prefixed additional data naming the table, column and row, so a ciphertext cannot be moved into another column. Keys are versioned per field: rotation re-encrypts rows and the schema does not change. Services authenticate to each other with EdDSA-signed tokens that live for a minute, with verifier keys published on a JWKS endpoint and rotated with an overlap window.

**Config fails closed.** A strict schema parses the environment at boot, with no defaults. Anything that has touched a commit or a chat transcript I treat as compromised and rotate. When an agent or a colleague needs to show that a secret is in place, I ask for its digest, never the value. The logger and the error reporter mask phone numbers, identity numbers and account numbers before anything leaves the process.

**Self-review with tools, labelled as such.** Before a launch I run the OWASP API Security Top 10 and MASVS checklists against my own apps. Findings go into one register, and a finding closes only when the fix is merged and re-tested. That is not an independent test, and the register says so. I refuse to file a finding as both a blocker and deferred; one of those words is wrong.

**This page practises it.** Every string from the GitHub API or profile.json passes one sanitiser before it reaches Markdown or SVG. The workflow uses no third-party Actions, the cards are drawn locally so no badge service sees your visit, and a pre-commit scan checks the output for secrets and active content. [Threat model](https://github.com/ChristopherMulwa/ChristopherMulwa/blob/main/docs/THREAT-MODEL.md)

## How I work

**I decide, the agent types.** I agree a spec with the agent before any code. Then it builds without checking back and writes anything the spec did not cover into the PR as an ASSUMPTION line. Merging, pushing and anything destructive wait for me, and a mobile change waits until I have run it on a physical handset.

**Two review agents, two different questions.** One agent checks a diff against house conventions and the lessons file. Another checks it against the spec it came from. I read both verbatim and act first on the finding they disagree about. Before merge, that pass has caught a secret in cleartext and a validation error that echoed input back to the caller.

**Every post-mortem ends as a check where it can.** Each incident gets a dated entry with the rule, the reason and how to apply it, citing the PR. I delete any lesson without a concrete reason. Where a grep can enforce one, it becomes a CI check. A few hundred lessons and about thirty checks so far.

## Shipping

### A client&#39;s financial platform &nbsp;·&nbsp; `private`

**Under NDA.**

Backend services, an operations dashboard and mobile apps, built alone. The rest is the client&#39;s to describe.

`NestJS` `Next.js` `React Native` `PostgreSQL` `Redis`

### ChallengeMe &nbsp;·&nbsp; `live`

**Side-competitions platform for golf clubs, live in Kenya.**

Players pay entry fees by mobile money, club admins run events and payouts from a real-time dashboard, and every entry carries a snapshot of the fee rate that applied to it. Webhooks are idempotent and the backend re-verifies each one against the provider. The gateway checks a club&#39;s wallet before any disbursement. Tenant isolation lives at the application layer today, with a phased move to Postgres RLS written down. About 440 tests and an accessibility gate in CI.

`Next.js` `Express` `Prisma` `PostgreSQL` `Redis` `Socket.io` `Vercel`

[challengeme.africa](https://challengeme.africa)

## Stack

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/stack-dark.svg?v=22649102ac">
  <source media="(prefers-color-scheme: light)" srcset="assets/stack-light.svg?v=adb03730ee">
  <img alt="Technology stack grouped by domain" src="assets/stack-dark.svg?v=22649102ac" width="100%">
</picture>

## Learning

- Offensive practice on TryHackMe and Hack The Box, with a Kali lab and a bug-bounty kit built around the OWASP testing guides. What I want from it is better instincts for my own code.
- Mobile security for the React Native apps I ship: MASVS and MASTG, certificate pinning that behaves the same in a release build as in the dev client, and how a managed runtime changes it.
- A daily cybersecurity news digest I built for myself. The model researches, a small Python engine dedups on URL, title and CVE id and files each story as a dated card. It has run every morning since May 2026.

---

<sub>Generated 2026-09-17 11:13 UTC · live snapshot · no third-party trackers, badge services, or analytics on this page.</sub>
