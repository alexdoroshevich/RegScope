---
description: Full pre-merge ritual — run quality gate, open review, push (with approval), open PR, watch CI, loop on failures. Stops for user approval at commit and push.
---

Run the full ritual end-to-end. Stop and report clearly at each gate.

## 1. Local quality gate
Invoke skill `check`. If red → diagnose, fix, restart.

## 2. Code review
Invoke agent `code-review` against the staged diff (or the full feature branch if nothing is staged yet). The report must end in ✅ APPROVED or 💬 COMMENT ONLY. If ⚠️ REQUEST CHANGES → fix the P0 findings, restart at step 1.

## 3. Pre-push checklist
Invoke skill `pre-push-checklist`. All 8 steps must pass.

## 4. Draft commit message, request user approval
Draft a Conventional-Commits message from the staged diff — read `git diff --cached` and `git log --oneline -5` for style. Format:
```
<type>(<optional-scope>): <lowercase imperative subject, ≤72 chars>

<optional body: wrap at 72, explain WHY not WHAT>
```
Present the drafted message + staged file list to the user. **Ask for explicit approval** before `git commit`. On approval, commit.

## 5. Push (with user approval)
Confirm branch is `feature/<something>`. Ask the user for explicit `git push` approval. Push.

## 6. Open PR
Invoke skill `pr`. Fill the template completely. Use the same title as the commit message for clean squash-merge history.

## 7. Watch CI
```bash
gh run watch
```

## 8. On failure → loop
If any check fails, invoke agent `ci-doctor`. Apply the proposed fix, return to step 1. **Never disable a failing check to make it green.**

## 9. On all green → hand off
Report to the user: PR URL, all checks green, ready for their review + squash-merge.

## Never in this ritual
- Auto-merge the PR.
- Force-push to `main`.
- Skip the user-approval gate at commit (step 4) or push (step 5).
- `--no-verify` to bypass pre-commit.
