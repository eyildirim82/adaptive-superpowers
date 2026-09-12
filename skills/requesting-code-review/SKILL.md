---
name: requesting-code-review
description: Use when a change needs an independent engineering review based on diff consequence, risk, or integration boundary.
---

# Requesting Code Review

Review depth is selected by `review.mode = self | risk-based | independent-required`.

## self — FAST
Use implementer self-review and targeted verification. Do not dispatch an external reviewer for a trivial reversible diff merely because a task ended. A hard-risk domain (security/auth, destructive migration/data loss, irreversible effect) escalates the profile and review requirement.

## risk-based — STANDARD
Request one independent review when the diff has meaningful behavioral/integration risk, crosses module boundaries, changes public contracts, or is large enough that a fresh perspective is worth the coordination cost. Prefer lane/feature completion as the review boundary instead of reviewing every mechanical microtask.

## independent-required — CRITICAL
Independent review is mandatory. Security, authorization, migration/history, data-loss, payment, and destructive-effect boundaries require review regardless of diff size. Parallel CRITICAL lanes receive lane-completion review plus coordinator integration review.

## Review package
Provide the reviewer a precise package: requirement/spec authority, base/head or diff scope, changed files/interfaces, active risk floor/reasons, authorization constraints, and verification evidence. Do not dump unrelated session history.

## Findings
- **Critical / Important:** block the affected completion/integration claim until fixed or technically adjudicated with evidence.
- **Minor:** non-blocking by default; record or fix when cheap and in scope.

Verify reviewer claims against code/tests. Reviewer authority does not override repository/user constraints or the execution profile.
