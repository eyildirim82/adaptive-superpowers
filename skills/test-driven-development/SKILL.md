---
name: test-driven-development
description: Use when implementing or changing behavior where executable tests can materially reduce regression risk.
---

# Test-Driven Development

TDD is a profile-aware engineering policy, not a universal ceremony. The active execution profile selects `opportunistic`, `default`, or `strict`.

## opportunistic — FAST
Use test-first when a meaningful failing test is cheap. For trivial/local changes where test-first adds more ceremony than signal, implement the narrow change and run targeted verification. Add a regression test when it provides durable value.

## default — STANDARD
Prefer RED → GREEN → REFACTOR for behavioral changes. First prove the test fails for the intended reason, implement the smallest coherent fix, prove it passes, then refactor while green. If test-first is impractical (generated code, pure configuration, inaccessible external boundary), record the reason and use the strongest available executable verification; do not stop merely to ask permission to skip ritual.

## strict — CRITICAL
For behavioral/security/data-integrity changes, a failing executable regression test or equivalent rehearsal is required before the behavior-changing implementation. For migrations and external systems, the equivalent can be a database test, clean replay, dry-run, contract test, or production-history-shaped rehearsal that demonstrably fails before the fix and succeeds after it.

## Test quality

A good test proves one behavior, has a clear name, exercises real behavior rather than mock bookkeeping, and would fail if the production change were removed. Avoid brittle implementation assertions.

## Relationship to verification

TDD does not replace completion verification. The final claim still follows **Evidence Before Claims** in `verification-before-completion`. A user may explicitly request no tests; then do not claim that tests passed or that untested properties are verified.
