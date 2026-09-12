---
name: finishing-a-development-branch
description: Use when implementation is ready for final verification and any authorized Git integration or cleanup effect.
---

# Finishing a Development Branch

Finishing is intent-aware. Reuse authorization already granted by the user/task; do not force a generic merge/push/keep menu.

## 1. Fresh verification first
Apply the active verification mode to the exact tree/state that may be integrated:
- FAST: targeted proof;
- STANDARD: relevant affected suite/build/typecheck surfaces;
- CRITICAL: canonical verification/rehearsal matrix.

If evidence fails, report the actual status and investigate. Do not perform an integration effect whose safety depends on a verification claim that is not established.

## 2. Detect Git/workspace state
Identify current branch or detached HEAD, base/fork point when known, worktree ownership, uncommitted/untracked files, and current authorization/task intent for push, PR, merge, deploy, destructive cleanup, or history mutation.

## 3. Intent-aware effect matrix

```text
known authorized + requested effect -> execute after verification
known denied effect                 -> do not execute or offer it as default
unknown external effect             -> leave work ready; do not invent authority
irreversible/destructive cleanup    -> explicit authorization required
```

Examples:
- User already said "push and open a PR when done" → after fresh verification, push/open the PR without asking the same permission again.
- User said "do not push/merge/deploy" → leave branch/commit ready and report it.
- No integration intent was given → do not silently push or merge; report branch/commit state.
- CRITICAL classification alone does not revoke authorization that was explicitly granted.

## 4. Merge / push / PR safety
Never force-push, rewrite protected/shared history, merge to an unknown base, or deploy unless that specific effect is authorized. A rejected push or moved remote is evidence to investigate, not permission to force.

When local merge is authorized, verify the merged result before cleanup. When PR creation is authorized, preserve the worktree for feedback unless cleanup was separately requested/authorized.

## 5. Cleanup ownership
Automatic cleanup is allowed only for agent-owned temporary workspaces and only when it cannot destroy unique work. Project-local worktrees under **`.worktrees/` or `worktrees/`** are eligible for owned cleanup; host-managed/external workspaces are not assumed owned.

If worktree removal is refused because modified/untracked files exist, inspect and report them. Do not use destructive `--force` cleanup without explicit authorization.

Discarding a branch/commits/worktree is destructive. Require explicit discard authorization and show what would be lost before deletion.

## Completion report
Report fresh evidence, resulting branch/commit/PR state, effects actually performed, effects explicitly not performed, and any not-run verification surfaces. Do not imply push/merge/deploy occurred when it did not.
