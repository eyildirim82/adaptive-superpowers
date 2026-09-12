---
name: controller-gated-mpd
description: Use when multiple branches, worktrees, or pull requests must converge through a controlled integration wave with frozen-base, exact-head evidence, READY binding, or serialized merge-train requirements.
---

# Controller-Gated MPD

Controller-Gated MPD is the Adaptive Superpowers execution engine for distributed multi-lane integration. It is **not** a second orchestrator.

## Authority split

Adaptive Superpowers owns:
- FAST / STANDARD / CRITICAL classification;
- inherited risk floors and escalation;
- effect authorization;
- TDD/review/verification strength;
- whether parallelism is worthwhile.

Controller-Gated MPD owns:
- frozen-base and lane ownership contracts;
- wave/dependency state;
- prompt/native transport for worker execution;
- exact-head GitHub Actions metadata evidence;
- READY@SHA materialization and invalidation;
- serialized merge-train mechanics;
- post-merge trunk proof.

## Activation

Use MPD only when work is a real distributed integration problem: multiple isolated branches/worktrees/PRs must converge to one trunk, especially when frozen-base, ownership, dependency DAGs, reserved migrations/resources, exact-head CI, or controlled merge order matter.

Do not activate MPD merely because two subtasks exist. Ordinary parallel work stays with `dispatching-parallel-agents` / `subagent-driven-development`.

An MPD wave has a minimum **STANDARD** coordination floor. Child lanes inherit the wave floor and may escalate to CRITICAL, never downgrade below the floor.

## Transport

- `native-dispatch`: use when the runtime can actually start isolated workers.
- `prompt-handoff`: use in a normal ChatGPT conversation without native worker dispatch.

For **Prompt-Handoff Parallelism**, generate complete zero-context prompts for the coordinator and currently dispatchable lanes. Tell the user to open worker prompts in separate ChatGPT windows. Never claim workers were launched when only prompts were generated.

Blocked downstream lane prompts are withheld by default. A preview may be rendered only when explicitly marked `DO NOT START` with unmet prerequisites.

## Evidence and READY

Worker prose, pasted logs, screenshots, and worker-reported SHAs are handoff hints only. They are **not evidence** and must not create READY.

The coordinator independently re-reads Git/PR/Actions state. READY is a machine integration capability bound to the exact repo, PR, head, base, profile digest, effective Adaptive risk, run ID/attempt, and evidence digest. READY is not user approval.

V5 schema/protocol authority does not upgrade into V6 authority. V6 fails closed on legacy READY/evidence.

## Merge train

Plan mode is non-mutating. A mutating merge train requires Adaptive authorization `merge == granted`. `unknown` or `denied` may preview the train and reach READY, but must stop before merge mutation.

Already-granted merge authority is reused without asking again.

## Ledger

While MPD is active, `.superpowers/mpd/<wave>/` is the canonical recovery ledger. Do not create a competing generic SDD ledger for the same wave.

## References

- `references/dispatch-modes.md`
- `references/project-profile-template.md`
- `references/wave-profile-template.json`
- `references/worker-prompt-template.md`
- `references/coordinator-prompt-template.md`
- `references/worker-result-contract.md`
- `references/controller-review-template.md`
