# Contributing to FedComment

Thanks for your interest in contributing. FedComment is an open-source
project and we welcome issues, patches, and documentation improvements.

Before you contribute, please read this document. **Every contribution
requires a signed-off commit** — see §4 below.

## 1. Ground rules

- Be excellent to each other. Treat every interaction as if you were
  speaking face-to-face.
- Keep scope small. One logical change per pull request is ideal; it is
  easier to review and easier to revert.
- Don't land code without tests. Coverage is enforced at ≥ 70 %.
- Don't add dependencies casually. Explain why in the PR description.
- English-only for all repository files (code comments, docs, commit
  messages, PR descriptions).

## 2. Before you start

- **Search the issue tracker** to see if the bug or feature is already
  reported or in progress. Comment on an existing thread rather than
  opening a duplicate.
- **For non-trivial features**, open an issue first to discuss the
  approach. This avoids wasted work on a direction the maintainers are
  not ready to accept.
- **Security vulnerabilities** — do **not** open a public issue. See
  [SECURITY.md](SECURITY.md) for the disclosure process.

## 3. Development setup

See the `Quick Start` section of the [README.md](README.md). In short:

```bash
git clone https://github.com/alexdoroshevich/RegScope.git
cd RegScope
make setup        # uv sync + pre-commit + .env
make check        # lint + test — must pass before PR
```

Project conventions live in [CLAUDE.md](CLAUDE.md) — follow them for code
style, tooling choices, and architectural constraints.

## 4. Developer Certificate of Origin (DCO)

FedComment uses the [Developer Certificate of Origin
1.1](https://developercertificate.org) to ensure every contribution is
submitted with appropriate rights. By signing off on a commit, you
certify that:

1. The contribution was created in whole or in part by you and you have
   the right to submit it under the open-source licence indicated in the
   file.
2. The contribution is based on previous work that, to the best of your
   knowledge, is covered under an appropriate open-source licence.
3. The contribution was provided directly to you by some other person
   who certified (1) or (2) and you have not modified it.
4. You understand and agree that this project and the contribution are
   public and that a record of the contribution (including all personal
   information you submit with it) is maintained indefinitely.

### How to sign off

Add a sign-off line to every commit message:

```
Signed-off-by: Your Name <your.email@example.com>
```

The easiest way is the `-s` flag on `git commit`:

```bash
git commit -s -m "feat: add docket autocomplete"
```

Set up the sign-off automatically via a commit template if you prefer:

```bash
git config commit.template .gitmessage
```

Pull requests with unsigned commits will be asked to rebase and re-sign.

## 5. Coding standards

### Python

- Ruff for linting **and** formatting. Run `make format` before
  committing.
- mypy strict mode. Every function has type hints.
- 100-char line length.
- `from __future__ import annotations` in every `.py` file.
- `logging.getLogger(__name__)` — never `print()` outside CLI demos.
- `pathlib.Path` — never string paths.
- `httpx` for HTTP — never `requests`.
- `polars` for data — never `pandas`.
- Pydantic v2 for API schemas.
- Raw DuckDB SQL — no SQLAlchemy.

### Frontend

- TypeScript strict. No `any`.
- Functional components only.
- Tailwind utility classes. No separate CSS files.
- No `localStorage` or `sessionStorage`.

### Tests

- pytest for Python, vitest for TypeScript.
- Mirror source layout: `tests/unit/test_<module>.py`.
- Mock every external API call. Never hit real APIs in tests.
- Mark slow tests `@pytest.mark.slow`, integration tests
  `@pytest.mark.integration`.

### Commits

Conventional Commits. First line ≤ 72 chars, imperative mood:

```
feat: add docket autocomplete
fix(ingest): handle 429 with exponential backoff
docs: add disclaimer banner to README
chore: bump ruff to 0.8.0
```

## 6. Pull request process

1. Fork the repository and create a feature branch from `main`
   (`feature/short-description`).
2. Make your changes. Keep commits small and logical.
3. Run `make check` locally — both lint and tests must pass.
4. Push your branch and open a pull request against `main`.
5. Fill in every section of the PR template. "N/A" is fine where it
   genuinely applies; empty sections will be asked for before review.
6. Be responsive to review feedback. We aim to review within a week,
   but please be patient — this is an open-source side project.

## 7. Reporting bugs

Open an issue with:

- A clear, descriptive title.
- The expected behaviour and the actual behaviour.
- Steps to reproduce (including command-line invocations if applicable).
- Version / commit SHA you are running.
- Relevant log output or stack trace.

## 8. Suggesting enhancements

Open an issue describing:

- The problem you are trying to solve (not the solution).
- Why the existing tools don't address it.
- A sketch of how you'd approach it, if you have one.

For larger changes we may ask you to write a short ADR in
[docs/DECISIONS.md](docs/DECISIONS.md) before implementation.

## 9. Licence

By contributing you agree that your contributions will be licensed under
the [Apache License 2.0](LICENSE), the project's licence.

Thank you for helping make FedComment better.
