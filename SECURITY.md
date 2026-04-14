# Security Policy

## Supported Versions

RegScope is in pre-1.0 MVP development. Only the latest commit on `main` receives
security fixes. There are no released versions yet.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| other   | :x:                |

## Reporting a Vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Report privately via one of:

1. **GitHub Private Vulnerability Reporting** — preferred.
   Use the "Report a vulnerability" button on the repository's
   [Security tab](../../security/advisories/new).
2. **Email** — `doroshevichag@gmail.com` with subject prefix `[regscope-security]`.

Please include:

- A description of the issue and its impact.
- Steps to reproduce (proof-of-concept code, minimal request, or commit SHA).
- The affected component (`api/`, `data/`, `nlp/`, `db/`, `frontend/`, CI, or dependency).
- Your assessment of severity and any suggested mitigation.

### What to expect

- **Acknowledgement:** within 5 business days.
- **Initial triage:** within 10 business days, with a severity assessment
  (CVSS 3.1 where applicable) and an estimated remediation timeline.
- **Fix and disclosure:** coordinated. We will credit reporters who wish to be
  named once a fix is released, unless you request anonymity.

## Scope

In scope:

- This repository's source code, CI workflows, and published container images.
- Default configurations and documented deployment patterns.

Out of scope:

- Vulnerabilities in third-party services RegScope depends on
  (Federal Register API, Regulations.gov, OpenAI, etc.) — report those upstream.
- Findings that require a compromised developer machine, stolen credentials,
  or non-default insecure configuration.
- Denial-of-service via excessive request volume against a self-hosted instance.

## Handling of Secrets

If you discover a leaked credential in the repository or its history,
treat it as in-scope and report immediately. Do not test the credential.
We will rotate and force-purge history as needed.

## Safe Harbor

Good-faith security research conducted in line with this policy is welcome.
We will not pursue legal action against researchers who:

- Report promptly and privately.
- Avoid privacy violations, data destruction, or service disruption.
- Do not exploit findings beyond what is necessary to demonstrate the issue.
