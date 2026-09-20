#!/usr/bin/env bash
set -euo pipefail

mode="${1:-sweep}"
branch_arg="${2:-}"
repo="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"

is_transient_branch() {
  case "$1" in
    feat/*|fix/*|refactor/*|ci/*|integration/*) return 0 ;;
    *) return 1 ;;
  esac
}

is_protected_branch() {
  case "$1" in
    main|archive/*|codex/*|blender-bridge) return 0 ;;
    *) return 1 ;;
  esac
}

has_open_pr() {
  local branch="$1"
  local count
  count="$(gh pr list --repo "$repo" --state open --head "$branch" --limit 1 --json number --jq 'length')"
  [[ "$count" != "0" ]]
}

delete_branch_if_safe() {
  local branch="$1"

  if ! is_transient_branch "$branch"; then
    echo "skip $branch: branch is not in a transient namespace"
    return 0
  fi
  if is_protected_branch "$branch"; then
    echo "skip $branch: branch is protected by policy"
    return 0
  fi
  if has_open_pr "$branch"; then
    echo "skip $branch: open pull request still exists"
    return 0
  fi
  if ! git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    echo "skip $branch: remote branch no longer exists"
    return 0
  fi
  if ! git merge-base --is-ancestor "origin/$branch" origin/main; then
    echo "skip $branch: branch still contains commits outside main"
    return 0
  fi

  echo "delete $branch: no open PR and fully contained in main"
  git push origin --delete "$branch"
}

git fetch --prune origin "+refs/heads/*:refs/remotes/origin/*"

case "$mode" in
  branch)
    if [[ -z "$branch_arg" ]]; then
      echo "branch mode requires a branch name" >&2
      exit 2
    fi
    delete_branch_if_safe "$branch_arg"
    ;;
  sweep)
    while IFS= read -r remote_ref; do
      branch="${remote_ref#origin/}"
      [[ "$branch" == "HEAD" ]] && continue
      delete_branch_if_safe "$branch"
    done < <(
      git for-each-ref         --format='%(refname:short)'         refs/remotes/origin         | sort
    )
    ;;
  *)
    echo "usage: $0 [branch <name>|sweep]" >&2
    exit 2
    ;;
esac
