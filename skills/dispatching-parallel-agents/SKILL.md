---
name: dispatching-parallel-agents
description: Use when multiple independent work domains could be executed concurrently without shared-state conflicts.
---

# Dispatching Parallel Agents

Parallelism is an optimization, not a default. Dispatch only when expected speedup is greater than **coordination cost**.

## Profile behavior
- **FAST:** parallelism off by default; one agent is usually cheaper and faster.
- **STANDARD:** use `net-benefit` parallelism only for truly independent domains with distinct files/state and enough work to justify coordination.
- **CRITICAL:** parallelism may be used only with a `contract-required` ownership model.

## Net-benefit test
Parallelize only when all are true:
1. Tasks can be understood independently.
2. They do not edit shared files/state or depend on each other's intermediate result.
3. Integration is predictable.
4. Dispatch/review/merge overhead is smaller than the expected wall-clock gain.

Batch small same-shape edits into one worker instead of one agent per file/task.

## Engine boundary

This skill owns lightweight parallel execution, not distributed integration authority. One branch with two small independent edits stays here (or inline/SDD); do not activate Controller-Gated MPD merely because more than one task exists.

Route back to the Adaptive Superpowers Orchestrator when the work becomes a real multi-branch/multi-PR convergence problem: multiple branches or PRs must converge on one trunk, lanes share a frozen base, dependency ordering/DAG state matters, ownership or reserved identifiers must be machine-coordinated, exact-head evidence is required, or integration must run as a serialized merge train. The orchestrator may then select `controller-gated-mpd`.

Transport descriptions must match runtime facts. Use `native-dispatch` only when isolated worker launch is actually available. In ordinary ChatGPT without that capability, use `prompt-handoff`; say that prompts were generated for separate ChatGPT windows, not that workers/agents are running.

## CRITICAL ownership contract
Every lane must receive the relevant base/frozen SHA, branch/workspace, exclusive files, shared/read-only files, reserved migration/version identifiers, dependency/integration order, inherited risk floor, authorization limits, and required evidence.

If workers discover shared state or conflicts, reduce parallelism and escalate risk when appropriate. Do not hide coordination conflicts behind retries.

## Integration
Review returned summaries/diffs, detect overlap, then run integration-level verification. Coordinator owns shared files unless explicitly reserved to a lane.
