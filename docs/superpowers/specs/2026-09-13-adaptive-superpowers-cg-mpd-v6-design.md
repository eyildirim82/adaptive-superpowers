# Adaptive Superpowers + Controller-Gated MPD V6 Design

**Date:** 2026-09-13  
**Status:** Proposed canonical design — awaiting written-spec review  
**Scope:** Adaptive Superpowers orchestration, multi-lane development, ChatGPT prompt-handoff parallelism, exact-head evidence, READY authority, and merge-train integration

## 1. Purpose

Adaptive Superpowers already decides how much engineering process a task needs through **FAST / STANDARD / CRITICAL** execution profiles. Controller-Gated MPD V5 adds stronger mechanics for multi-branch, multi-PR work: frozen bases, lane ownership, exact-head CI evidence, READY receipts, and a serialized merge train.

The combined system should not create two orchestrators or two competing risk models. Adaptive Superpowers remains the policy authority. Controller-Gated MPD becomes a specialized execution engine that is activated only when work is genuinely a distributed integration problem.

The primary addition in V6 is **Prompt-Handoff Parallelism** for ordinary ChatGPT conversations. When native worker dispatch is unavailable, the framework generates complete zero-context worker prompts and a coordinator contract for the user to open in separate ChatGPT windows. It must never pretend workers were launched when they were not.

## 2. Goals

The integration MUST:

1. Keep **Adaptive Superpowers** as the single authority for risk, authorization, planning depth, TDD strength, review strength, workspace isolation, and completion truthfulness.
2. Use **Controller-Gated MPD** only for multi-lane work that will converge through shared integration authority.
3. Replace MPD's `low / normal / high` vocabulary with Adaptive's `FAST / STANDARD / CRITICAL` vocabulary.
4. Preserve MPD's frozen-base, scope, exact-head evidence, READY@SHA, and serialized merge-train guarantees.
5. Support two transports:
   - `native-dispatch` — the runtime can launch isolated workers itself.
   - `prompt-handoff` — ChatGPT generates worker/coordinator prompts for the user to open manually.
6. Treat worker reports as untrusted navigation data, never as merge authority or CI evidence.
7. Reuse already-granted push/merge/deploy authorization and stop only at an unauthorized effect boundary.
8. Keep V5 evidence/READY receipts from being silently upgraded to V6 authority.
9. Avoid turning every parallel task into MPD; lightweight parallelism and ordinary SDD remain available.

## 3. Non-goals

V6 will not:

- make MPD the default for every task with two subtasks;
- let MPD override Adaptive risk or authorization;
- treat a pasted ChatGPT worker result as proof that code, CI, or PR state is valid;
- automatically merge because a lane says it is complete;
- require user approval merely because a task is CRITICAL;
- create separate Adaptive and MPD ledgers for the same wave;
- preserve the V5 `low / normal / high` model as a second severity system.

## 4. Authority hierarchy

When MPD is active, authority is ordered as follows:

```text
Platform / harness safety constraints
        ↓
Explicit user scope and effect authorization
        ↓
Repository / frozen-base / ownership contracts
        ↓
Adaptive global invariants
        ↓
Adaptive execution profile
        ↓
Controller-Gated MPD V6 wave contract
        ↓
Worker prompt / worker report
```

The two global invariants remain unchanged:

- **Evidence Before Claims**
- **Authorized Effects Only**

MPD READY is not user approval. It is a machine integration capability bound to exact repository state. Conversely, READY does not authorize an external effect that Adaptive authorization denies or leaves unknown.

## 5. Activation policy

Adaptive Superpowers decides whether MPD is needed.

### Do not activate MPD

Use normal Adaptive execution for:

- one small change;
- one feature branch;
- one CRITICAL migration with no parallel lanes;
- a few same-session subtasks that can be handled inline;
- lightweight parallel work with no branch/PR integration contract.

Use `dispatching-parallel-agents` or `subagent-driven-development` when parallel contexts help but there is no distributed integration problem.

### Activate MPD

MPD becomes appropriate when one or more of these are true:

- two or more branches/worktrees/PRs must converge on one trunk;
- a frozen base is required across concurrent lanes;
- dependency-ordered waves or a DAG exist;
- exclusive file ownership or hot zones matter;
- reserved migration/version identifiers must not collide;
- exact-head CI evidence is required before integration;
- sequential merge with post-merge trunk proof is required;
- CRITICAL multi-lane work needs machine-checkable coordination.

Entering MPD implies a minimum **STANDARD** coordination floor. Individual lanes may escalate to CRITICAL; a trivial docs lane inside a STANDARD wave does not downgrade the parent wave below STANDARD.

## 6. Unified risk model

V6 removes `low / normal / high` from the canonical wave model.

The effective lane risk is:

```text
effective_risk = max(
  parent_risk_floor,
  lane_declared_risk,
  changed_path_floor,
  discovered_runtime_risk
)
```

Where the ordering is:

```text
FAST < STANDARD < CRITICAL
```

Examples:

- `docs/**` may have a FAST path floor, but a lane inside a STANDARD MPD wave remains STANDARD because of the inherited wave floor.
- `src/auth/**`, RLS, production config, payment code, or destructive migrations have a CRITICAL path floor.
- A worker that discovers an authorization/security boundary escalates to CRITICAL and reports the escalation.
- No worker, CLI flag, or wave-profile field may lower inherited risk.

## 7. Execution profile extension

The Adaptive execution profile gains a transport dimension for parallel work:

```yaml
parallelism:
  mode: off | net-benefit | contract-required
  transport: none | native-dispatch | prompt-handoff
  engine: none | sdd | controller-gated-mpd
```

Typical ChatGPT multi-lane state:

```yaml
risk:
  level: STANDARD
  floor: STANDARD

parallelism:
  mode: contract-required
  transport: prompt-handoff
  engine: controller-gated-mpd
```

A CRITICAL multi-lane task uses the same transport field but stronger review, ledger, isolation, and verification modes.

## 8. Prompt-Handoff Parallelism

### 8.1 Runtime rule

When the active runtime is a normal ChatGPT conversation and no native isolated-worker dispatch capability is available, MPD MUST use `prompt-handoff`.

The assistant MUST NOT say:

> "I started three agents."

It SHOULD say:

> "Three lanes can run in parallel. Open the following worker prompts in separate ChatGPT windows."

This is required by **Evidence Before Claims**.

### 8.2 Generated artifacts

For a dispatchable wave, V6 renders:

```text
.superpowers/mpd/<wave>/
├── wave.json
├── handoffs/
│   ├── coordinator.md
│   ├── p3-a.md
│   ├── p3-b.md
│   └── p3-c.md
├── evidence/
├── approvals/
└── integration.json
```

`handoffs/` is derived output. `wave.json` is canonical state.

A deterministic renderer SHOULD generate prompts from the wave profile rather than relying on ad-hoc prose. Proposed script:

```text
scripts/render_handoff_prompts.py
```

Default behavior renders only currently dispatchable lanes. An optional preview mode may include blocked downstream lanes, but every blocked prompt MUST carry a prominent `DO NOT START` marker and list unmet prerequisites.

### 8.3 Worker prompt contract

Every ChatGPT worker prompt is zero-context and contains at least:

- framework instruction: `Adaptive Superpowers + Controller-Gated MPD`;
- role and lane ID;
- repository;
- canonical spec and plan pointers;
- exact task authority;
- assigned branch/worktree;
- frozen base SHA;
- inherited risk floor;
- lane declared risk;
- exclusive owned paths;
- shared/read-only paths;
- forbidden/hot-zone paths;
- reserved migration/version IDs;
- prerequisites and downstream dependencies;
- granted/denied/unknown effect authorization relevant to the lane;
- required verification;
- prohibition on self-READY and self-merge;
- required completion-result schema.

A worker must never expand its own scope. Required shared-file work becomes a Controller blocker or assigned integration lane.

### 8.4 Coordinator prompt contract

The coordinator handoff contains:

- repository and trunk;
- wave ID and frozen base SHA;
- canonical wave-profile path;
- all lanes, branches, ownership, dependencies, and reserved resources;
- parent risk floor and authorization state;
- requirement to re-read current repository/PR/CI state rather than trust worker prose;
- exact-head evidence policy;
- READY issuance rules;
- integration order;
- merge authorization rule;
- post-merge trunk verification rule.

The coordinator is the only role that may materialize READY receipts or execute the merge train.

### 8.5 Worker result envelope

Workers return a compact machine-readable/human-readable envelope:

```text
WORKER RESULT

Lane: P3-A
Branch: agent/p3-dashboard
Frozen base: <sha>
Head: <sha>
Risk: STANDARD
Risk escalated: no
Changed files:
- ...
Verification:
- command: ...
  result: PASS
Runtime status: NOT VERIFIED | VERIFIED
Open blockers:
- none
Coordinator next action:
- review current PR head and regenerate exact-head evidence
```

This report is **not evidence**. It is a handoff hint. The coordinator must independently verify branch head, diff scope, CI metadata, and READY prerequisites.

## 9. Dependency-aware prompt release

Prompt generation follows the wave DAG.

For:

```text
A ──┐
    ├── C
B ──┘
```

initial output contains runnable prompts for A and B. C is withheld by default until A and B satisfy their prerequisites.

After prerequisites merge and trunk becomes metadata-GREEN, the coordinator regenerates C's prompt against the correct current base/contract.

This avoids stale prompts and stale frozen-base assumptions.

## 10. READY semantics

V6 preserves the strongest V5 property: **READY@SHA is state-bound authority, not prose.**

A READY receipt binds at minimum:

- repository;
- PR;
- source head SHA;
- base ref;
- V6 wave-profile digest;
- effective Adaptive risk;
- selected workflow run ID and attempt;
- exact-head evidence digest;
- Controller identity/time.

A READY receipt becomes invalid when any bound material changes, including:

- source head;
- base retarget;
- relevant workflow rerun/attempt;
- wave-profile edit;
- evidence edit;
- effective risk change.

V5 evidence or READY receipts MUST NOT be upgraded into V6 authority.

## 11. Verification gates

Risk changes verification strength, not authority.

Example V6 gate sets:

```yaml
FAST:
  - targeted-tests

STANDARD:
  - tests
  - typecheck
  - build

CRITICAL:
  - tests
  - typecheck
  - build
  - security-or-domain-gate
  - required-rehearsal-if-applicable
```

Actual gate IDs remain repository-specific and live in `wave.json`.

Even a FAST-derived lane inside MPD still requires:

- valid identity metadata;
- scope compliance;
- Controller review;
- exact-head evidence for its resolved gates;
- READY before merge;
- serialized integration.

Because MPD carries a STANDARD coordination floor, the ordinary case will resolve to STANDARD or CRITICAL.

## 12. TDD integration

MPD does not own a separate TDD doctrine.

- FAST: opportunistic test-first when cheap and meaningful.
- STANDARD: TDD default; exceptions require a concrete applicability rationale, not user approval ritual.
- CRITICAL: strict behavioral RED → GREEN or the closest executable migration/security/data-integrity rehearsal.

Worker prompt wording must consume the active Adaptive testing mode rather than always hard-coding `RED → GREEN → REFACTOR` regardless of task type.

## 13. Review integration

To prevent duplicate ceremony:

### STANDARD MPD

```text
Worker self-review
      ↓
Controller integration/code review
      ↓
Exact-head evidence
      ↓
READY
```

An additional independent reviewer is used only when risk/diff policy calls for it.

### CRITICAL MPD

```text
Worker self-review
      ↓
Independent engineering/security/domain review
      ↓
Controller integration review
      ↓
Exact-head evidence
      ↓
READY
```

Only Critical/Important findings block. Minor findings are recorded without creating endless LGTM loops.

## 14. Authorization and merge train

MPD owns integration mechanics; Adaptive owns effect authorization.

`merge_train.sh --apply` may execute only when:

```text
Adaptive.authorization.merge == granted
```

If merge is denied or unknown, the coordinator may still:

- verify lanes;
- generate exact-head evidence;
- issue READY receipts;
- construct a non-mutating merge-train preview;

but MUST stop before the mutating merge operation.

The same applies independently to push, deploy, production write, destructive action, secrets/config mutation, or any other tracked effect.

READY never upgrades unknown authorization to granted.

## 15. Canonical ledger and recovery

When MPD is active, its wave directory becomes the canonical Adaptive ledger for that wave. The generic SDD layer MUST NOT create a competing ledger.

The wave ledger records:

- parent/current risk and floor;
- authorization state;
- frozen base/trunk;
- lanes and dependencies;
- ownership/hot zones/reserved resources;
- prompt-handoff status;
- worker-reported heads as hints;
- independently verified PR heads;
- evidence receipts;
- review findings/disposition;
- READY receipts;
- integration state;
- post-merge trunk evidence.

After context compaction or a new coordinator window, recovery trusts **Git/PR/CI state + canonical wave ledger**, not conversation memory.

## 16. Proposed V6 wave schema

V6 increments protocol/schema so V5 authority cannot be mistaken for V6 authority.

Proposed header:

```json
{
  "schema_version": 4,
  "protocol_version": 6,
  "wave": "phase-3",
  "repository": {
    "repo": "OWNER/REPO",
    "trunk": "main",
    "frozen_base_sha": "..."
  },
  "adaptive": {
    "risk_floor": "STANDARD",
    "authorization": {
      "push": "granted",
      "merge": "denied",
      "deploy": "denied",
      "production_write": "denied"
    },
    "transport": "prompt-handoff"
  }
}
```

Lane risk values become `FAST | STANDARD | CRITICAL`.

Path floors use the same vocabulary.

## 17. Skill architecture

The resulting skill tree is:

```text
skills/
├── using-superpowers/             # Adaptive Orchestrator
├── brainstorming/
├── writing-plans/
├── test-driven-development/
├── systematic-debugging/
├── using-git-worktrees/
├── dispatching-parallel-agents/   # lightweight parallelism
├── subagent-driven-development/   # coherent delegated tasks
├── controller-gated-mpd/          # multi-branch/PR integration engine
├── requesting-code-review/
├── verification-before-completion/
├── finishing-a-development-branch/
└── impeccable/                    # UI-domain engine
```

`controller-gated-mpd` does not classify overall task risk. Its adapter contract states that the Adaptive Orchestrator owns severity and authorization.

## 18. V5 → V6 migration

V5 assets are reused selectively:

### Preserve conceptually

- frozen-base assertion;
- deterministic ownership/hot-zone rules;
- exact-head Actions metadata proof;
- single-run gate completeness;
- run-attempt binding;
- evidence digests;
- READY invalidation semantics;
- serialized merge train;
- post-merge trunk verification;
- fail-closed metadata behavior.

### Adapt

- `low / normal / high` → `FAST / STANDARD / CRITICAL`;
- unconditional TDD wording → profile-aware testing mode;
- standalone MPD risk authority → Adaptive risk floor/path-floor enforcement;
- standalone merge authority → Adaptive authorization-gated `--apply`;
- dispatch docs → native-dispatch + prompt-handoff transports;
- worker prompt template → full zero-context ChatGPT handoff contract;
- ledger layout → canonical `.superpowers/mpd/<wave>/` state.

### Add

- `render_handoff_prompts.py`;
- coordinator prompt template;
- worker-result contract/reference;
- prompt-handoff tests;
- runtime/transport routing tests;
- authorization-to-merge tests;
- V5-receipt rejection tests under protocol V6.

## 19. Behavioral scenarios

The implementation must cover at least these scenarios:

1. **Two tiny independent edits, one branch** → no MPD.
2. **Two independent branches, no shared integration risk** → MPD optional only if contract benefits exceed overhead.
3. **Three PRs from frozen base** → MPD activates.
4. **ChatGPT runtime without native dispatch** → generates worker prompts, does not claim workers started.
5. **Native agent runtime** → uses native dispatch without unnecessary prompt handoff.
6. **Downstream lane with unmet prereqs** → runnable prompt withheld by default.
7. **Worker says "tests pass" but CI metadata absent** → EVIDENCE GAP, no READY.
8. **Worker head differs from current PR head** → worker report ignored, current PR state wins.
9. **STANDARD lane touches auth path** → escalates CRITICAL.
10. **Parent CRITICAL, docs-only child** → child remains CRITICAL floor.
11. **READY head changes** → READY invalid.
12. **Workflow rerun attempt changes** → READY invalid.
13. **Merge authorization denied** → READY may be issued, mutating merge stops.
14. **Merge authorization granted** → no duplicate approval prompt before `--apply`.
15. **CRITICAL lane** → independent review + controller review.
16. **Context compaction/new coordinator window** → recovery from wave ledger + Git/PR/CI state.
17. **V5 READY supplied to V6** → fail closed.
18. **Real runtime unavailable** → explicit `NOT VERIFIED`, never inferred from build success.

## 20. Acceptance criteria

The design is successfully implemented when:

- one risk vocabulary exists everywhere: FAST/STANDARD/CRITICAL;
- Adaptive remains the sole risk and effect-authorization authority;
- MPD activates only for genuine distributed integration work;
- ChatGPT without native dispatch emits complete zero-context handoff prompts;
- no prompt-handoff path claims workers were actually launched;
- worker reports cannot directly create READY;
- exact-head evidence and READY invalidation remain machine-checked;
- merge mutation obeys Adaptive merge authorization;
- MPD wave state is the canonical ledger while MPD is active;
- dependency-blocked prompts are not accidentally runnable;
- STANDARD and CRITICAL review/TDD policies are profile-aware;
- V5 receipts cannot be mistaken for V6 receipts;
- deterministic tests cover prompt rendering, risk escalation, evidence, READY, authorization, and merge behavior;
- cross-harness Adaptive Superpowers tests remain green.

## 21. Final principle

> **Adaptive Superpowers decides how work should be governed. Controller-Gated MPD decides how distributed lanes safely converge. ChatGPT prompt handoff changes the transport, never the evidence standard.**
