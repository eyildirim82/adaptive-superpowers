---
name: subagent-driven-development
description: Use when an implementation plan contains independent coherent tasks or lanes that benefit from isolated subagent contexts.
---

# Subagent-Driven Development

Use isolated implementer contexts when they reduce context pollution and coordination cost. The child inherits the parent **risk floor** and relevant authorization.

## Profile behavior
- **FAST:** normally execute inline; avoid subagent overhead for tiny work.
- **STANDARD:** subagents are useful for coherent independent tasks/lanes. Batch small same-shape edits. Default review boundary is lane/feature completion, not every microtask.
- **CRITICAL:** delegation requires explicit ownership contracts and independent review. Parallel lanes must integrate through a coordinator.

## Child contract
Each brief contains: exact requirement/task authority, relevant interfaces, branch/workspace/base SHA, exclusive/shared files, inherited risk floor, granted/denied effect authorization, expected verification, report path/contract, and integration dependencies. A child may escalate risk but may not de-escalate below the inherited floor.

## Ledger / recovery
- `off`: no persistent SDD ledger.
- `conditional`: keep a small recovery ledger when the session is long, multi-agent, or compaction-prone.
- `required`: CRITICAL work records plan identity, base/branch/workspace, lane state, rulings, evidence, review findings, migrations/resources, and integration state under `.superpowers/sdd/<plan>/` or the repo-defined equivalent.

Trust Git state + ledger after context loss; do not redispatch completed lanes merely because conversation memory was compacted.

## Execution loop
1. Check isolation and plan authority.
2. Batch small same-shape work; otherwise dispatch one implementer per coherent task/lane.
3. Implementer tests and self-reviews.
4. Apply the active review mode: self, risk-based lane review, or independent-required.
5. Fix/adjudicate blocking findings with evidence.
6. Record completion/evidence and continue without asking "continue?".
7. After parallel CRITICAL lanes, coordinator performs integration review and canonical verification.

## Stop conditions
Same as the Adaptive Orchestrator: unauthorized irreversible/security-sensitive effect, permission-required external side effect not already granted, or a plan so broken that every path is guesswork.
