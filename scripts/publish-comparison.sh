#!/usr/bin/env bash
# Push original history and optionally create the unmerged PR using gh.
set -euo pipefail
branch=codex/xauusd-m1-strategy-comparison
repository=wadewolfie999/py-mynyra
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$root"
mode=${1:---check}
case "$mode" in
  --check|--publish) ;;
  *) echo 'Usage: bash scripts/publish-comparison.sh [--check|--publish]' >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || exit 2
[[ $(git branch --show-current) == "$branch" ]] || {
  echo "Expected branch: $branch" >&2; exit 1;
}
[[ -z $(git status --porcelain) ]] || {
  echo 'Commit or resolve working-tree changes before publication.' >&2; exit 1;
}
case "$(git remote get-url --push origin)" in
  "https://github.com/$repository.git"|"https://github.com/$repository"|"git@github.com:$repository.git") ;;
  *) echo 'Unexpected origin push URL; inspect before publishing.' >&2; exit 1 ;;
esac
git merge-base --is-ancestor e578559e4579755c21403b82741338a2b1497001 HEAD
git diff --check
if [[ "$mode" == --check ]]; then
  echo 'Preflight passed. Use --publish to push and open the unmerged PR.'
  exit 0
fi
# Never force-push or alter authentication.
if ! git push -u origin "$branch"; then
  echo 'Push failed. Resolve Git authentication/connectivity in your terminal, then rerun.' >&2
  exit 1
fi
local_head=$(git rev-parse HEAD)
remote_head=$(git ls-remote --exit-code origin "refs/heads/$branch" | cut -f1)
[[ "$remote_head" == "$local_head" ]] || {
  echo 'Remote head differs from local HEAD; inspect before creating the PR.' >&2; exit 1;
}
if command -v gh >/dev/null 2>&1; then
  # Listing failure must not be mistaken for absence and create a duplicate PR.
  existing=$(gh pr list --repo "$repository" --head "$branch" --base main --state all --json url --jq '.[0].url // empty')
  if [[ -n "$existing" ]]; then
    echo "Existing PR (inspect its state): $existing"
  else
    gh pr create --repo "$repository" --base main --head "$branch" \
      --title 'Compare five preregistered XAUUSD M1 strategies' \
      --body-file docs/XAUUSD_PR_BODY.md
  fi
else
  echo 'Branch verified on GitHub. Finish creating the PR at:'
  echo "https://github.com/$repository/compare/main...$branch?expand=1"
  echo 'Title: Compare five preregistered XAUUSD M1 strategies'
  echo 'PR body: docs/XAUUSD_PR_BODY.md'
fi
