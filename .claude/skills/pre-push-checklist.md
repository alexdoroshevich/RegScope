---
name: pre-push-checklist
description: Run every step before proposing a git push to the user. Validates local quality, workflow YAML, secret scan, action versions, and file paths — catches everything that would show up red in GitHub Actions.
---

Run in order. Every step must pass before proposing the push to the user.

## 1. Local quality gate
Invoke skill `check`. All four (ruff lint, ruff format, mypy, pytest) must be green.

## 2. Workflow YAML validation (if `.github/workflows/*` changed)
```bash
for f in .github/workflows/*.yml; do
  python -c "import yaml; yaml.safe_load(open(r'$f', encoding='utf-8'))" && echo "OK: $f" || echo "FAIL: $f"
done
```
Any FAIL = stop, fix the YAML, re-run.

## 3. Action version sanity (if any `uses:` line changed)
- The `@<sha>` must match an actual release of that action.
- The input field names must match that tag — field names change across major versions.
- Prefer pinning to the full commit SHA over a floating tag.
- Note the version next to the SHA as a comment: `uses: owner/action@abc123… # v1.2.3`.

## 4. Secret scan on the diff
```bash
git diff --cached | grep -E '(sk-|AKIA|ghp_|AIza|xoxb-|BEGIN [A-Z ]*PRIVATE KEY)' && echo 'SECRET DETECTED — STOP' && exit 1 || echo 'OK'
```
Also confirm `.env` / `.env.local` / `secrets/` are not staged. Only `.env.example` is allowed.

## 5. File-path sanity
- Every path referenced in workflows (`working-directory`, `cache-dependency-path`, config files) resolves to a real file.
- `pyproject.toml`, `package-lock.json`, `frontend/package.json` exist where the workflow expects them.

## 6. Conflict pre-check
```bash
git fetch origin
git diff origin/main -- <your-touched-files>
```
If another branch or a recent main touched these files, resolve locally before push — don't let GitHub surface the conflict.

## 7. Public-repo hygiene
- `git status --short` shows nothing from `docs/internal/` or `.claude/private/`.
- No screenshots with internal URLs/Slack/emails in the diff.

## 8. Stop and report to the user
State: what you're about to push, to which branch, what commits it contains. Ask for explicit approval. **Do not run `git push` autonomously.**

## After push (once user approves)
Run `gh run watch` or `gh run list --branch <branch> --limit 3`. If any check fails, invoke the `ci-doctor` agent — don't guess.
