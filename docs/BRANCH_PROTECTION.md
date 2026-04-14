# Branch Protection — one-time GitHub setup

After `gh repo create`, configure these rules on `main`. GitHub UI path:
**Settings → Branches → Branch protection rules → Add rule**, branch name pattern = `main`.

## Required settings

| Setting | Value | Why |
|---|---|---|
| Require a pull request before merging | ✅ | No direct pushes to main |
| Require approvals | `1` | At least one human review |
| Dismiss stale reviews on new commits | ✅ | Force re-review after changes |
| Require review from Code Owners | ✅ | Only `@alexdoroshevich` can approve |
| Require status checks to pass | ✅ | Block merge on red CI |
| Required status checks | `All gates passed`, `Validate (semantic-pull-request)`, `Validate commit messages`, `Analyze (python)`, `Analyze (javascript)`, `pip-audit (Python deps)`, `Bandit (Python SAST)` | Full quality gate |
| Require branches to be up to date before merging | ✅ | No stale-base merges |
| Require conversation resolution before merging | ✅ | No unaddressed review comments |
| Require linear history | ✅ | Clean log, squash-merge only |
| Require signed commits | optional | Set up GPG/SSH signing separately |
| Include administrators | ✅ for external PRs, ❌ for owner | Owner can override in emergencies |
| Restrict who can push to matching branches | yourself only | Prevents accidental pushes |
| Allow force pushes | ❌ | Never force-push main |
| Allow deletions | ❌ | Main must not be deletable |

## Solo self-approval flow

You (`alexdoroshevich`) are Code Owner. GitHub **allows you to approve your own PR**
when you are the code owner listed in CODEOWNERS. Workflow:

1. Push a `feature/` branch.
2. Open PR via `gh pr create` with filled template.
3. Wait for all required checks to go green (auto-triggered by `pr-gate.yml`).
4. Add your own approval: `gh pr review --approve`.
5. Merge: `gh pr merge --squash --delete-branch`.

Note: if GitHub ever enforces "Require approval from someone other than author" as
the default (this setting has shipped in some enterprise plans), flip to **not
requiring approval count** — only require passing status checks. The Code Owner
gate still forces external contributors to wait for your review, because only you
can merge on a protected branch.

## For external contributors

External contributor opens a PR from their fork:
1. All status checks run (same ones as above).
2. Claude auto-reviews the PR.
3. You (`@alexdoroshevich`) add a Code Owner approval — their approval does not count.
4. You merge.

They cannot merge without your approval — that's what `Require review from Code Owners` enforces.

## Repo-level settings (Settings → General)

- **Default branch**: `main`
- **Allow merge commits**: ❌
- **Allow squash merging**: ✅ (the only allowed merge style)
- **Allow rebase merging**: ❌
- **Automatically delete head branches**: ✅ (clean up `feature/` branches after merge)
- **Visibility**: Private initially; flip to Public once MVP is polished

## Secrets (Settings → Secrets and variables → Actions)

Required repository secrets:
- `ANTHROPIC_API_KEY` — for `claude-review.yml`. Copy value from your Interviewcraft repo's secrets.

GitHub's `GITHUB_TOKEN` is auto-provided — no setup needed.

## Rulesets (alternative to classic branch protection)

GitHub Rulesets (`Settings → Rules → Rulesets`) are the newer, more flexible
system. Either works. If you want to manage protection-as-code, export rulesets
with `gh api repos/alexdoroshevich/RegScope/rulesets` and commit the JSON here.
