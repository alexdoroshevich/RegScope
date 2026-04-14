---
name: pr
description: Open a GitHub pull request with a fully-filled template body. Never opens an empty PR. Use after pre-push-checklist passes and the user has approved the push.
---

## Preconditions (verify before invoking)
1. Skill `pre-push-checklist` passed.
2. User explicitly approved `git push` for this branch.
3. Branch is `feature/<something>`, not `main`.
4. Branch is already pushed to origin.

## Draft the body from the diff
```bash
git log origin/main..HEAD --oneline     # commits in this PR
git diff origin/main...HEAD --stat      # files changed
```

Fill every section of `.github/pull_request_template.md`. No placeholder strings left behind — `auto-pr-description.yml` and `pr-metadata` will both block the merge if they detect one.

## Open the PR
```bash
gh pr create \
  --base main \
  --head "$(git branch --show-current)" \
  --title "<type>: <lowercase subject, ≤72 chars>" \
  --body "$(cat <<'EOF'
## What does this PR do?

<one specific paragraph — what changed and WHY, not a title repeat>

## Type of change

- [x] <pick one: Bug fix | New feature | Refactor / cleanup | Docs / config only | CI / build | Test-only>

## Checklist (author)

- [x] `uv run ruff check .` is clean
- [x] `uv run ruff format --check .` is clean
- [x] `uv run mypy data/ nlp/ api/ db/` is clean
- [x] `uv run pytest -m "not slow and not integration" -q` passes locally
- [x] New Python files have type hints and at least one smoke test
- [x] No `print()` — using `logging`
- [x] No PII / API keys / `.env` content in code or logs
- [x] No new deps added without prior discussion
- [x] Conventional commit prefix on every commit
- [x] MVP scope: astroturf-detector or cluster-analyzer flow (or justified)

## How to test

1. <concrete reproduction step>
2. <concrete reproduction step>
3. <what to observe — what proves this works>

## Screenshots (UI change only)

<before / after — or "N/A">

## Related issues / spec sections

<link to issue, or "N/A">
EOF
)"
```

## After opening
```bash
gh run watch                            # stream CI progress
gh pr view --web                        # open in browser to review your own PR
```

If any check goes red, invoke the `ci-doctor` agent — get the root cause, apply the fix, ask the user for commit+push approval, loop until green.

## Never
- Use `gh pr create --fill` alone — it only uses commit messages; the template stays unfilled; `pr-metadata` blocks the merge.
- Leave `<concrete step>` or `<one specific paragraph…>` placeholders — those exact strings are what `pr-metadata` scans for.
- Auto-merge. The user merges after reviewing green CI.
