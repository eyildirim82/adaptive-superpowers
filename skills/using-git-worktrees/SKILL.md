---
name: using-git-worktrees
description: Use when the active execution profile requires or benefits from an isolated Git workspace.
---

# Using Git Worktrees

Isolation strength is profile-selected: `current-ok`, `isolated-preferred`, or `isolated-required`.

## Policy
- **current-ok (FAST):** a clean existing feature branch is acceptable for narrow reversible work.
- **isolated-preferred (STANDARD):** isolate multi-file/multi-step work when it reduces interference; a suitable existing feature worktree/branch is acceptable.
- **isolated-required (CRITICAL):** use an isolated workspace. Do not implement on main/master unless the user explicitly authorized that exact risk.

Creating a local reversible worktree does not require a separate approval prompt when the profile calls for isolation.

## Detect existing isolation first
Use `git rev-parse --git-dir`, `--git-common-dir`, `--show-superproject-working-tree`, and current branch. A linked worktree (not a submodule) already satisfies isolation; do not nest another one.

## Creation order
1. Prefer a native harness worktree mechanism such as `EnterWorktree`, `WorktreeCreate`, `/worktree`, or an explicit `--worktree` facility when available.
2. Otherwise use Git worktrees.
3. For manual Git worktrees, honor an explicit repo/user location preference, then an existing `.worktrees/` or `worktrees/` directory; otherwise **default to `.worktrees/` at the project root**.
4. Before creating a project-local manual worktree, verify the directory is ignored. If it is not ignored, make the smallest safe ignore change before use.

Do not bypass a native harness worktree facility merely because `git worktree add` is familiar; the harness may own cleanup and lifecycle state.

## Baseline evidence
Verification depth is adaptive:
- FAST: targeted sanity proof when needed;
- STANDARD: affected/relevant baseline;
- CRITICAL: strong clean-baseline evidence for the surfaces that will be used as gates.

If baseline failures already exist, record them as pre-existing evidence. Investigate only when they block attribution or the requested work; do not force a user stop solely because the repository was already imperfect.
