---
name: using-superpowers
description: Use when starting a coding or software-development task that may need Superpowers process or domain skills.
---

# Adaptive Superpowers Orchestrator

Superpowers is risk-adaptive. The orchestrator chooses the smallest process that can produce trustworthy evidence without crossing an unauthorized effect boundary.

## Global invariants

### Evidence Before Claims
Never claim a property that fresh evidence does not establish. A skipped test means the result is unverified, not passing.

### Authorized Effects Only
Never perform an external, destructive, security-sensitive, or irreversible effect outside authority already granted by the user/task.

These are invariants. Brainstorming, planning, TDD, review, worktrees, parallelism, and finishing are policies.

## Risk Router

Classify each task before process routing:

- **FAST** — local, reversible, narrow, understood, with a clear verification surface.
- **STANDARD** — normal engineering work: features, multi-file changes, ordinary integrations, or uncertain-but-reversible work.
- **CRITICAL** — any hard trigger or discovered high-consequence boundary. CRITICAL means stronger controls, not "ask before doing anything."

Use the hard triggers and examples in `references/risk-policy.md` when classification is not obvious.

**Risk is not permission.** A CRITICAL action may already be authorized; an unauthorized external effect is still unauthorized even if the task looks FAST.

## Risk floor and escalation

A parent/coordinator may pass a **risk floor** to child work. A child may classify at or above that floor, never below it. Risk may escalate when new evidence appears; do not silently de-escalate during the same task.

When risk escalates, state the reason briefly and strengthen the active profile. Escalation alone is not an approval stop.

## Execution profile

Use compact policy modes rather than dozens of booleans:

| Dimension | FAST | STANDARD | CRITICAL |
|---|---|---|---|
| design | none / intent | short-design | persistent-spec when useful |
| planning | none | lightweight | persistent |
| workspace | current-ok | isolated-preferred | isolated-required |
| TDD | opportunistic | default | strict for behavior |
| debugging | short-root-cause | evidence-driven | full-tracing |
| parallelism | off | net-benefit | contract-required |
| review | self | risk-based | independent-required |
| ledger | off | conditional | required |
| verification | targeted | relevant | canonical |
| integration | obey authorization | obey authorization | obey authorization |

Risk level controls required safeguards, not document length. A one-line security boundary change can be CRITICAL; a large documentation refactor can remain STANDARD.

## Skill routing

**process skills are policies.** Invoke only the process/domain skills needed by the active profile. A legacy `REQUIRED`, `MUST`, or named-skill instruction means "apply this capability at the active profile-selected strength"; it does not create a stronger workflow by itself.

Domain skills can be added independently of process severity. For frontend/UI intent, use the `impeccable` domain skill when available and apply `references/impeccable-adapter.md`; Adaptive risk and authorization remain authoritative.

If a process skill discovers a new hard trigger, route that discovery back through the Risk Router and escalate.

## User interaction

- FAST and STANDARD: state a compact intent/profile when useful, then proceed. Do not insert routine implementation-approval gates.
- CRITICAL: state the risk reason and the effect boundary that may require authorization, then continue with reversible preparation, tests, rehearsal, and review.
- Ask only when a genuinely unresolved product/design choice is required, every safe path is a guess, or an unauthorized effect boundary is reached.
- Reuse authorization already granted; do not ask twice for the same effect.

## Legacy compatibility

Existing skill names stay valid. Existing plans can still name `brainstorming`, `test-driven-development`, `requesting-code-review`, `executing-plans`, and the rest. Those skills consume this execution profile rather than overriding it with unconditional ceremony.

## Platform Adaptation

Load only the mapping for the runtime actually in use; do not force-load every reference into context.

- Codex: `references/codex-tools.md`
- Pi: `references/pi-tools.md`
- Antigravity: `references/antigravity-tools.md`
- Hermes: `references/hermes-tools.md`
- Gemini: `references/gemini-tools.md`

These mappings adapt tool names and harness behavior. They do not change the active risk, authorization, or execution profile.
