---
description: Diagnose failing GitHub Actions on the current branch and apply a root-cause fix. Loops until all checks are green.
---

1. `gh run list --branch "$(git branch --show-current)" --limit 3 --json databaseId,name,conclusion,event,url`
2. For each failed run, invoke agent `ci-doctor` with the run id — get the triage block (root cause + proposed fix + suggested commit message).
3. Apply the fix in code. **Never disable the failing check to make it pass.**
4. Invoke skill `check` — local gate must go green before pushing.
5. Ask the user for commit + push approval (separate approvals).
6. After push: `gh run watch`.
7. If still red: loop back to step 1 with the new run id.
8. On all green: report the PR URL and hand off to the user for review + merge.

## Never
- Force-push to `main`.
- Merge with a red check.
- `--no-verify` the pre-commit hook.
- Guess the fix — if `ci-doctor` says "log insufficient, need X", get X before continuing.
