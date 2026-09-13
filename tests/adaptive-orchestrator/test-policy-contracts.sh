#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
failures=0
pass() { printf '  [PASS] %s\n' "$1"; }
fail() { printf '  [FAIL] %s\n' "$1" >&2; failures=$((failures+1)); }
assert_contains() { local f="$1" p="$2"; grep -Fq "$p" "$f" && pass "$f contains '$p'" || fail "$f missing '$p'"; }
assert_not_contains() { local f="$1" p="$2"; if grep -Fq "$p" "$f"; then fail "$f still contains '$p'"; else pass "$f omits '$p'"; fi; }
assert_exists() { [[ -f "$1" ]] && pass "$1 exists" || fail "$1 missing"; }

echo "Adaptive Superpowers policy contract tests"
assert_contains skills/using-superpowers/SKILL.md "FAST"
assert_contains skills/using-superpowers/SKILL.md "STANDARD"
assert_contains skills/using-superpowers/SKILL.md "CRITICAL"
assert_contains skills/using-superpowers/SKILL.md "Risk Router"
assert_contains skills/using-superpowers/SKILL.md "risk floor"
assert_contains skills/using-superpowers/SKILL.md "Evidence Before Claims"
assert_contains skills/using-superpowers/SKILL.md "Authorized Effects Only"
assert_contains skills/using-superpowers/SKILL.md "Risk is not permission"
assert_contains skills/using-superpowers/SKILL.md "process skills are policies"
assert_not_contains skills/using-superpowers/SKILL.md "even a 1% chance"
assert_not_contains skills/brainstorming/SKILL.md "EVERY task"
assert_not_contains skills/test-driven-development/SKILL.md "NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST"
assert_exists skills/using-superpowers/references/risk-policy.md
assert_exists skills/using-superpowers/references/impeccable-adapter.md
assert_contains skills/using-superpowers/references/impeccable-adapter.md "frontend/UI **domain capability**"
assert_contains skills/using-superpowers/references/impeccable-adapter.md "Do not add a generic design-approval gate"
assert_contains skills/using-superpowers/references/impeccable-adapter.md "genuine creative/product choices"
assert_contains skills/using-superpowers/references/impeccable-adapter.md "engineering review"
assert_exists skills/impeccable/LICENSE
assert_exists skills/impeccable/NOTICE.md
assert_contains skills/verification-before-completion/SKILL.md "fresh"
assert_contains skills/verification-before-completion/SKILL.md "Evidence Before Claims"

# Profile-aware policy markers
for marker in opportunistic default strict; do assert_contains skills/test-driven-development/SKILL.md "$marker"; done
for marker in short-root-cause evidence-driven full-tracing; do assert_contains skills/systematic-debugging/SKILL.md "$marker"; done
assert_contains skills/writing-plans/SKILL.md "lightweight"
assert_contains skills/using-git-worktrees/SKILL.md "isolated-required"
assert_contains skills/dispatching-parallel-agents/SKILL.md "coordination cost"
assert_contains skills/requesting-code-review/SKILL.md "risk-based"
assert_contains skills/subagent-driven-development/SKILL.md "risk floor"
assert_contains skills/finishing-a-development-branch/SKILL.md "unknown external effect"
assert_contains skills/finishing-a-development-branch/SKILL.md "known denied effect"
assert_contains skills/finishing-a-development-branch/SKILL.md "without asking the same permission again"
assert_not_contains skills/finishing-a-development-branch/SKILL.md "present exactly these 3 options"

# Controller-Gated MPD adapter / Task 8 routing contracts
assert_exists skills/using-superpowers/references/controller-gated-mpd-adapter.md
assert_contains skills/using-superpowers/SKILL.md "single top-level authority"
assert_contains skills/using-superpowers/SKILL.md "controller-gated-mpd"
assert_contains skills/using-superpowers/SKILL.md "prompt-handoff"
assert_contains skills/using-superpowers/SKILL.md "native-dispatch"
assert_contains skills/using-superpowers/SKILL.md ".superpowers/mpd/<wave>/"
assert_contains skills/using-superpowers/references/controller-gated-mpd-adapter.md "one branch + two small independent edits"
assert_contains skills/using-superpowers/references/controller-gated-mpd-adapter.md "three PRs from one frozen base"
assert_contains skills/using-superpowers/references/controller-gated-mpd-adapter.md "Worker prompts were generated for separate ChatGPT windows."
assert_contains skills/using-superpowers/references/controller-gated-mpd-adapter.md "workers started"
assert_contains skills/using-superpowers/references/controller-gated-mpd-adapter.md "3 agents running"
assert_contains skills/using-superpowers/references/controller-gated-mpd-adapter.md "CRITICAL parent/wave keeps a docs-only child CRITICAL"
assert_contains skills/using-superpowers/references/controller-gated-mpd-adapter.md "stop before merge mutation"
assert_contains skills/using-superpowers/references/controller-gated-mpd-adapter.md "worker_report.reported_head_sha"
assert_contains skills/using-superpowers/references/controller-gated-mpd-adapter.md "verified_pr.head_sha"
assert_contains skills/using-superpowers/references/risk-policy.md "minimum STANDARD coordination floor"
assert_contains skills/using-superpowers/references/risk-policy.md "does **not** by itself create a user approval gate"
assert_contains skills/dispatching-parallel-agents/SKILL.md "real multi-branch/multi-PR convergence problem"
assert_contains skills/subagent-driven-development/SKILL.md 'do not create `.superpowers/sdd/<plan>/`'
assert_contains skills/using-git-worktrees/SKILL.md "exact frozen-base contract"

if (( failures > 0 )); then
  printf 'STATUS: FAILED (%d contract violations)\n' "$failures" >&2
  exit 1
fi
printf 'STATUS: PASSED\n'
