# Security policy

## Scope

This repository builds my GitHub profile page. It contains no service, no user
data, and no credentials. The interesting surface is the build pipeline
itself — a scheduled workflow that holds a write-capable token — rather than
anything it produces.

The design and its residual risks are written up in
[docs/THREAT-MODEL.md](docs/THREAT-MODEL.md).

## Reporting

If you find a way to make this pipeline do something it should not, I want to
know, and I will thank you publicly if you would like me to.

- **Preferred:** open a [private security advisory](https://github.com/ChristopherMulwa/ChristopherMulwa/security/advisories/new).
- **Alternative:** message me on [LinkedIn](https://www.linkedin.com/in/christopher-mulwa/) and I will open a private channel.

Please do not open a public issue for something exploitable.

I will acknowledge within 72 hours and tell you what I intend to do about it,
including if the answer is "nothing, and here is why".

## In scope

- Command or expression injection into any workflow
- Anything that lets a third party influence what gets committed here
- Escaping the sanitiser in `generator/sanitize.py` — a payload that reaches
  the rendered SVG or Markdown as active content
- Credential exposure in generated output, logs, or history
- A path that reaches the network outside `api.github.com` during a build

## Out of scope

- Findings that require my GitHub account to already be compromised
- Denial of service against GitHub's own infrastructure
- Missing hardening that carries no exploit path (tell me anyway — just not as
  a vulnerability report)
- The residual risks already documented in the threat model, unless you can
  show my reasoning about them is wrong. That case is very much in scope.

## Testing this repository

Everything runs locally with no dependencies and no network:

```sh
make test          # unit tests, including the injection suite
make build         # render from the committed snapshot
make audit         # secret and active-content scan of the output
```

If you are looking for somewhere to start, `tests/test_sanitize.py` lists the
payloads I already thought of. The interesting bug is the one that is not in
that list.
