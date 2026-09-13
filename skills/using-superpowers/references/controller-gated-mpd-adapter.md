# Controller-Gated MPD Adapter

Use this adapter only after the **Adaptive Superpowers Orchestrator** decides that work is a genuine distributed convergence problem. Adaptive is the **single top-level authority**. Controller-Gated MPD is an execution engine for coordinated branches/PRs; it does not own a second risk model, a second authorization model, or a second completion truth.

## Authority split

Adaptive owns:

- FAST / STANDARD / CRITICAL classification and inherited risk floors;
- effect authorization (push, merge, deploy, production write, destructive action, history rewrite, secrets/config changes);
- planning/testing/review/isolation/verification strength;
- truthful completion claims.

Controller-Gated MPD owns, once selected:

- frozen-base and lane ownership mechanics;
- dependency-aware handoffs;
- exact-head evidence and READY mechanics;
- canonical wave recovery state;
- serialized integration / merge-train mechanics subject to Adaptive authorization.

MPD may never lower Adaptive risk, convert risk into permission, or convert READY into effect authorization.

## Activation routing

Use the smallest engine that matches the integration shape:

| Situation | Engine |
|---|---|
| one branch + two small independent edits | existing parallel / SDD (or inline); **no MPD** |
| independent contexts with predictable same-branch integration | existing parallel / SDD |
| three PRs from one frozen base | **Controller-Gated MPD** |
| dependency DAG across branches/PRs | **Controller-Gated MPD** |
| exact-head evidence + serialized merge proof required | **Controller-Gated MPD** |

Other strong MPD signals include exclusive cross-lane ownership, reserved migration/version identifiers, a shared frozen base, and CRITICAL multi-lane convergence that needs machine-checkable coordination.

Do not activate MPD simply because there are two subtasks.

## Transport routing and truthful claims

Transport is a runtime fact, not a preference:

- `native-dispatch`: use only when the current runtime really provides isolated worker launch/capability.
- `prompt-handoff`: use in ordinary ChatGPT when native isolated-worker dispatch is unavailable.

For `prompt-handoff`, truthful wording is: **“Worker prompts were generated for separate ChatGPT windows.”** Never say “workers started”, “3 agents running”, or equivalent unless the runtime produced evidence that it actually launched those isolated workers.

Prompt-Handoff is transport, not evidence. A pasted worker result is a navigation hint only.

## Risk inheritance

An MPD wave has a minimum STANDARD coordination floor. The effective child risk is never below the Adaptive wave floor. A CRITICAL parent/wave keeps a docs-only child CRITICAL. Children may escalate when paths or discoveries require it; they may not de-escalate.

Risk escalation strengthens process controls. **Risk escalation alone is not a user approval gate.** Authorization remains independent.

## Authorization boundary

READY is state-bound integration capability; it is not user permission.

If `adaptive.authorization.merge` is `denied` or `unknown`, the coordinator may still perform non-mutating work that is otherwise authorized, including review, exact-head verification, READY issuance, and merge-train preview. It must stop before merge mutation. If merge is already `granted`, do not ask for the same permission again.

The same independence applies to push, deploy, production writes, destructive actions, secrets/config mutation, and history rewrite.

## Canonical ledger ownership

While MPD is active, the only cross-lane recovery ledger for that wave is:

```text
.superpowers/mpd/<wave>/
├── wave.json
├── handoffs/
├── evidence/
├── approvals/
└── integration.json
```

Do not create a competing `.superpowers/sdd/<plan>/` ledger for the same active wave. SDD may be used inside a lane, but cross-lane state belongs to MPD.

`wave.json` is the canonical static wave contract. `integration.json` is canonical dynamic coordination state. Derived prompts/evidence live under their named directories.

## Dependency and head authority

Conversation memory and worker prose never release a downstream lane.

Keep at least two distinct head facts in integration state:

- `worker_report.reported_head_sha` — untrusted handoff/navigation hint;
- `verified_pr.head_sha` — independently verified current PR head used for dependency and integration decisions.

Never overwrite one with the other. If they differ, the independently verified PR head wins; the mismatch is evidence to investigate. A worker report saying “done” cannot mark a prerequisite satisfied or make a downstream prompt dispatchable.

Downstream release requires the prerequisite's **verified dependency state** in the canonical MPD ledger, refreshed from current Git/PR/Actions facts as required by the wave contract.

## Recovery after compaction/restart

A new coordinator reconstructs state without chat memory:

1. Load `.superpowers/mpd/<wave>/wave.json` and `integration.json`.
2. Re-read current Git branch/trunk and lane heads.
3. Re-read PR target/head/state from the provider.
4. Re-read exact Actions/CI metadata and READY/evidence artifacts required by the wave.
5. Reconcile external facts into the separate verified fields; retain worker-reported heads only as hints.
6. Run dependency-state checks before rendering or dispatching any downstream handoff.
7. Continue only from the reconciled ledger and current external evidence.

If any required current fact cannot be verified, keep the dependent lane blocked and report an evidence gap.
