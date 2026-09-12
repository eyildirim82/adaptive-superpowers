#!/usr/bin/env bash
# Prove a V6 lane checkout starts at the exact frozen base, expected branch, and clean tree.
set -euo pipefail

[[ $# -ge 1 && $# -le 3 ]] || { echo "usage: assert_frozen_base.sh <FROZEN_BASE_SHA> [WORKDIR] [EXPECTED_BRANCH]" >&2; exit 1; }
EXPECTED=$1
WORKDIR=${2:-.}
EXPECTED_BRANCH=${3:-}
command -v git >/dev/null || { echo "git not found" >&2; exit 1; }
ACTUAL=$(git -C "$WORKDIR" rev-parse HEAD)
if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo "FROZEN BASE MISMATCH: expected $EXPECTED, got $ACTUAL" >&2
  exit 2
fi
if [[ -n "$EXPECTED_BRANCH" ]]; then
  BRANCH=$(git -C "$WORKDIR" branch --show-current)
  if [[ "$BRANCH" != "$EXPECTED_BRANCH" ]]; then
    echo "FROZEN BRANCH MISMATCH: expected $EXPECTED_BRANCH, got ${BRANCH:-DETACHED}" >&2
    exit 2
  fi
fi
if [[ -n "$(git -C "$WORKDIR" status --porcelain -uall)" ]]; then
  echo "FROZEN CHECKOUT NOT CLEAN: commit/stash/remove working-tree changes before implementation" >&2
  exit 2
fi
echo "FROZEN BASE OK: $ACTUAL${EXPECTED_BRANCH:+ branch=$EXPECTED_BRANCH} clean=true"
