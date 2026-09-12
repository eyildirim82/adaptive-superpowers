# Adaptive Superpowers + Controller-Gated MPD V6 Implementation Plan

**Date:** 2026-09-13  
**Status:** Proposed implementation plan — awaiting execution approval  
**Repository:** `eyildirim82/adaptive-superpowers`  
**Baseline main:** `2582bf030a623b5e37f84dd7f3f4b2d12b52bf34`  
**Canonical design:** `docs/superpowers/specs/2026-09-13-adaptive-superpowers-cg-mpd-v6-design.md`  
**Canonical plan destination:** `docs/superpowers/plans/2026-09-13-adaptive-superpowers-cg-mpd-v6-implementation.md`  
**Target release:** `adaptive-v0.2.0-rc1`

## Goal

Integrate Controller-Gated MPD as an Adaptive-native multi-lane execution engine without introducing a second risk or authorization authority. Preserve V5's frozen-base, exact-head evidence, READY@SHA, run-attempt binding, serialized merge train, and post-merge trunk proof; add Adaptive FAST/STANDARD/CRITICAL semantics and ChatGPT Prompt-Handoff Parallelism.

## Architecture

- `skills/using-superpowers` remains the only top-level risk/authorization orchestrator.
- `skills/controller-gated-mpd` owns distributed-lane coordination and integration mechanics.
- MPD activates only for real multi-branch/multi-PR convergence problems.
- MPD waves have a minimum STANDARD coordination floor.
- Prompt-Handoff is a transport, not evidence: generated ChatGPT worker reports never directly create READY.
- MPD wave state under `.superpowers/mpd/<wave>/` is the canonical ledger while the engine is active.
- `merge_train.sh --apply` requires Adaptive merge authorization to be explicitly `granted` in the V6 profile.

## Baseline finding that must not be hidden

The supplied V5 package is not fully green in this environment. The focused test:

```bash
cd controller-gated-mpd/tests
python3 -m unittest -v \
  test_v5.FrozenAndMergeTests.test_merge_train_merges_and_proves_risk_bound_trunk
```

currently times out after the test harness's 15-second subprocess deadline. Therefore V6 implementation must not treat the V5 merge train as a clean inherited baseline. Task 0 establishes deterministic behavior before semantic migration.

## Global constraints

- Preserve **Evidence Before Claims** and **Authorized Effects Only** exactly.
- One severity vocabulary only: `FAST < STANDARD < CRITICAL`.
- Risk and authorization remain independent.
- V5 schema/protocol (`3/5`) cannot authorize V6 READY or merge.
- Worker prose, screenshots, logs, and pasted test output are navigation hints only; Git/PR/Actions metadata remain evidence authority.
- No production writes, deploys, merges, force-pushes, or destructive external effects are part of implementation unless separately authorized.
- Existing `adaptive-v0.1.0-rc1` and `adaptive-v0.1.0-rc2` tags remain immutable.
- Keep Impeccable vendor contents untouched.

---

## Task 0 — Freeze the RC2 Baseline and Stabilize the Imported V5 Merge-Train Test Harness

**Purpose:** establish trustworthy inherited behavior before changing semantics.

**Create/publish first:**
- `docs/superpowers/specs/2026-09-13-adaptive-superpowers-cg-mpd-v6-design.md` from the approved design artifact
- `docs/superpowers/plans/2026-09-13-adaptive-superpowers-cg-mpd-v6-implementation.md` from this approved plan
- `docs/superpowers/evidence/2026-09-13-cg-mpd-v5-baseline.md`

**Temporary/reference source:**
- supplied `controller-gated-mpd-v5-risk-adaptive` archive

**Inspect/adapt later:**
- V5 `scripts/merge_train.sh`
- V5 `scripts/check_trunk_evidence.py`
- V5 `tests/test_v5.py`

**Steps:**
1. Freshly verify GitHub `main` still equals the recorded baseline or record the new base before implementation.
2. Commit the approved design and implementation plan to their canonical repo paths before worker dispatch.
3. Run the V5 class-scoped suites independently so one timeout cannot hide unrelated results.
4. Reproduce the focused merge-train timeout with diagnostic command/call logging.
5. Determine whether the timeout is:
   - a V5 implementation bug,
   - a fake-`gh` harness bug,
   - a test timing assumption,
   - or environment-specific behavior.
6. Record exact passing/failing V5 behaviors in the evidence file.
7. Carry only proven invariants into the V6 port; add a regression for the timeout root cause before porting merge behavior.

**Verification:**
```bash
python3 -m unittest -v test_v5.ProfilePolicyTests
python3 -m unittest -v test_v5.RiskAdaptiveEvidenceTests
python3 -m unittest -v test_v5.ReadyV5Tests
python3 -m unittest -v test_v5.FrozenAndMergeTests
```

**Done when:** inherited V5 behavior is classified with no silent timeout/error and the merge-train root cause is covered by a deterministic test.

---

## Task 1 — Land RED V6 Contract Tests Before the Skill Exists

**Purpose:** prove the current RC2 repository lacks the approved V6 behavior.

**Create:**
- `tests/controller-gated-mpd/test_v6_policy.py`
- `tests/controller-gated-mpd/test_prompt_handoff.py`
- `tests/controller-gated-mpd/test_evidence_ready.py`
- `tests/controller-gated-mpd/test_merge_train.py`
- `tests/controller-gated-mpd/fixtures/`

**Modify:**
- `tests/adaptive-orchestrator/test-policy-contracts.sh`

**RED scenarios:**
1. V6 schema rejects `low/normal/high`.
2. V6 schema accepts only FAST/STANDARD/CRITICAL and enforces monotonic gate sets.
3. MPD wave floor cannot be below STANDARD.
4. Child risk cannot downgrade inherited floor.
5. auth/migration/security path floors escalate to CRITICAL.
6. ChatGPT/no-native-dispatch renders Prompt-Handoff instead of claiming workers were launched.
7. blocked downstream lanes are not rendered runnable by default.
8. worker report cannot create READY.
9. V5 evidence/READY is rejected by V6.
10. `merge --apply` is rejected when `adaptive.authorization.merge != granted`.
11. READY invalidates on head/base/profile/evidence/run-attempt/effective-risk change.
12. worker-reported head loses to live PR head.

**Verification:**
```bash
python3 -m unittest discover -s tests/controller-gated-mpd -p 'test*.py' -v
bash tests/adaptive-orchestrator/test-policy-contracts.sh
```

Expected: new V6 tests fail for missing behavior while existing Adaptive contracts remain green.

---

## Task 2 — Add the Adaptive-Native Controller-Gated MPD Skill Skeleton

**Create:**
- `skills/controller-gated-mpd/SKILL.md`
- `skills/controller-gated-mpd/README.md`
- `skills/controller-gated-mpd/agents/openai.yaml`
- `skills/controller-gated-mpd/references/controller-review-template.md`
- `skills/controller-gated-mpd/references/dispatch-modes.md`
- `skills/controller-gated-mpd/references/project-profile-template.md`
- `skills/controller-gated-mpd/references/wave-profile-template.json`
- `skills/controller-gated-mpd/references/worker-prompt-template.md`
- `skills/controller-gated-mpd/references/coordinator-prompt-template.md`
- `skills/controller-gated-mpd/references/worker-result-contract.md`

**Source material:** V5 skill package, rewritten to the approved V6 authority split.

**Required skill contract:**
- Adaptive owns severity and effect authorization.
- MPD owns multi-lane convergence mechanics.
- MPD activation requires distributed integration, not merely two subtasks.
- `prompt-handoff` and `native-dispatch` are explicit transports.
- READY is state-bound integration capability, not user approval.
- worker results are untrusted handoff hints.

**Do not:**
- copy V5 `low/normal/high` wording into the V6 public contract;
- hard-code universal RED→GREEN wording in worker prompts;
- imply ChatGPT launched workers when it emitted prompts.

**Verification:** structural skill checks plus Task 1 discovery/routing assertions.

---

## Task 3 — Port the Wave Schema and Risk Policy to Protocol 6 / Schema 4

**Create/port:**
- `skills/controller-gated-mpd/scripts/policy.py`
- `skills/controller-gated-mpd/scripts/validate_wave_profile.py`
- `skills/controller-gated-mpd/scripts/assert_frozen_base.sh`

**Schema changes:**
```json
{
  "schema_version": 4,
  "protocol_version": 6,
  "adaptive": {
    "risk_floor": "STANDARD",
    "authorization": {
      "push": "unknown|granted|denied",
      "merge": "unknown|granted|denied",
      "deploy": "unknown|granted|denied",
      "production_write": "unknown|granted|denied",
      "destructive_action": "unknown|granted|denied"
    },
    "transport": "native-dispatch|prompt-handoff"
  }
}
```

**Policy requirements:**
- risk order: FAST < STANDARD < CRITICAL;
- effective risk = max(parent floor, lane declaration, changed-path floor, runtime escalation supplied by current state);
- MPD profile floor must be STANDARD or CRITICAL;
- path ownership remains deterministic: exact file or terminal `/**` subtree only;
- semantic ownership overlap remains rejected;
- gate sets are non-empty and monotonic;
- authorization values are validated but never converted into risk levels.

**GREEN verification:** Task 1 policy tests.

---

## Task 4 — Implement Deterministic Prompt-Handoff Rendering

**Create:**
- `skills/controller-gated-mpd/scripts/render_handoff_prompts.py`

**Inputs:**
- V6 `wave.json`
- canonical spec/plan pointers from the wave/project profile
- current dependency state

**Outputs:**
```text
.superpowers/mpd/<wave>/handoffs/
├── coordinator.md
├── <dispatchable-lane>.md
└── ...
```

**Behavior:**
- default renders only dispatchable lanes;
- optional `--preview-blocked` renders blocked prompts with prominent `DO NOT START` and unmet prerequisites;
- prompts contain zero-context repo/branch/frozen-base/risk/ownership/authorization/verification contracts;
- prompts include `Adaptive Superpowers + Controller-Gated MPD` explicitly;
- prompts tell workers not to self-READY/self-merge;
- worker-result schema is embedded or referenced;
- ChatGPT transport language says “open these prompts in separate windows,” never “workers started.”

**Determinism:** same normalized profile + dependency state => byte-identical handoff files.

**GREEN verification:** `test_prompt_handoff.py` including snapshot/golden assertions for runnable/blocked/coordinator prompts.

---

## Task 5 — Port Exact-Head Actions Metadata Evidence to V6

**Create/port:**
- `skills/controller-gated-mpd/scripts/actions_metadata.py`
- `skills/controller-gated-mpd/scripts/check_exact_head.py`
- `skills/controller-gated-mpd/scripts/check_trunk_evidence.py`

**Preserve from V5:**
- canonical workflow name/path/event identity;
- exact source-head binding;
- explicit run-attempt jobs endpoint;
- one successful workflow attempt must satisfy the entire gate set;
- no aggregating required gates across runs;
- metadata jobs/steps, not log text, are proof;
- fail closed on missing/paginated/incomplete metadata.

**Adapt:**
- evidence schema/protocol -> `4/6`;
- risk payload -> Adaptive names;
- profile digest binds V6 wave profile;
- evidence records effective risk and escalation reasons;
- worker-result envelopes are never accepted as evidence inputs.

**GREEN verification:** `test_evidence_ready.py` exact-head/evidence cases.

---

## Task 6 — Port READY@SHA and Make V5 Authority Explicitly Non-Upgradable

**Create/port:**
- `skills/controller-gated-mpd/scripts/approve_ready.py`
- `skills/controller-gated-mpd/scripts/verify_ready.py`

**Requirements:**
- accept only V6 schema/protocol and V6 actions-metadata evidence;
- bind repo, PR, head, base, profile digest, effective Adaptive risk, selected run ID/attempt, evidence digest;
- re-resolve risk against current changed files at verify time;
- invalidate on head/base/profile/evidence/run-attempt/risk change;
- refuse zero-gate authority;
- refuse V5 receipt/evidence even if fields are otherwise similar;
- controller is the only role documented as allowed to materialize READY.

**GREEN verification:** Task 1 READY tests plus adapted V5 stale-authority regressions.

---

## Task 7 — Port the Merge Train with Adaptive Authorization Enforcement

**Create/port:**
- `skills/controller-gated-mpd/scripts/merge_train.sh`

**Behavior:**
- plan mode remains non-mutating by default;
- `--apply` performs mutation only if profile has `adaptive.authorization.merge == "granted"`;
- `unknown` or `denied` may still preview the train but cannot merge;
- READY-bound profile digest must equal train profile;
- initial trunk SHA is pinned;
- every PR must target the configured trunk;
- use `--match-head-commit` or equivalent exact-head protection;
- verify GitHub reports the PR merged and trunk equals the resulting merge commit;
- prove exact post-merge trunk with the risk gates bound into READY;
- stop if trunk moves unexpectedly or metadata is not GREEN;
- do not prompt again when merge is already granted.

**Critical regression:** resolve and cover Task 0's V5 merge-train timeout before claiming this task green.

**GREEN verification:**
```bash
python3 -m unittest -v tests.controller-gated-mpd.test_merge_train
```
(or the repo's chosen import-safe equivalent), including granted/denied/unknown cases.

---

## Task 8 — Integrate MPD Routing into Adaptive Superpowers Without a Second Orchestrator

**Modify:**
- `skills/using-superpowers/SKILL.md`
- `skills/using-superpowers/references/risk-policy.md`
- `skills/dispatching-parallel-agents/SKILL.md`
- `skills/subagent-driven-development/SKILL.md`
- `skills/using-git-worktrees/SKILL.md`
- `skills/finishing-a-development-branch/SKILL.md` only if needed to preserve integration authorization semantics

**Create:**
- `skills/using-superpowers/references/controller-gated-mpd-adapter.md`

**Routing contract:**
- ordinary parallelism -> existing parallel/SDD skills;
- real distributed branch/PR convergence -> MPD;
- ChatGPT without isolated dispatch -> `prompt-handoff`;
- native isolated worker runtime -> `native-dispatch`;
- MPD active -> generic SDD ledger disabled; MPD wave directory is canonical;
- child lanes inherit wave risk floor and can only escalate;
- risk escalation does not itself become a user approval gate.

**Behavioral RED/GREEN scenarios:**
- one branch with two tiny edits does not activate MPD;
- three PR frozen-base wave does;
- ChatGPT emits prompts, not fictitious launch claims;
- CRITICAL child remains CRITICAL even for docs-only changes;
- merge denied reaches READY/preview but stops before mutation.

**Verification:**
```bash
bash tests/adaptive-orchestrator/test-policy-contracts.sh
python3 -m unittest discover -s tests/controller-gated-mpd -p 'test*.py' -v
```

---

## Task 9 — Add Canonical Ledger / Recovery and Dependency-State Commands

**Create or extend:**
- `skills/controller-gated-mpd/scripts/check_deps.sh`
- optional `skills/controller-gated-mpd/scripts/wave_state.py` if a single state helper reduces duplication

**Canonical project layout:**
```text
.superpowers/mpd/<wave>/
├── wave.json
├── handoffs/
├── evidence/
├── approvals/
└── integration.json
```

**Requirements:**
- dependency readiness is derived from canonical lane/integration state, not chat memory;
- record worker-reported head separately from independently verified PR head;
- downstream prompt release uses verified prerequisite state;
- new coordinator after compaction/restart can reconstruct wave status from Git/PR/CI + ledger;
- never create a competing `.superpowers/sdd/<plan>/` ledger for the same active MPD wave.

**Verification:** recovery tests with stale worker report, missing conversation context, and dependency-blocked lane.

---

## Task 10 — Cross-Harness Packaging, OpenAI Metadata, Docs, and Behavioral Evals

**Modify:**
- `tests/codex/test-package-codex-plugin.sh`
- `tests/codex-plugin-sync/test-sync-to-codex-plugin.sh` if required
- `README.md`
- `RELEASE-NOTES.md`
- `.codex-plugin/plugin.json` version only at release step

**Create:**
- `tests/controller-gated-mpd/pressure-scenarios.md`
- `tests/controller-gated-mpd/verification-matrix.md`
- `skills/controller-gated-mpd/evals/evals.json` or repo-standard behavioral eval location
- `docs/superpowers/evidence/2026-09-13-cg-mpd-v6-verification.md`

**Codex/OpenAI packaging:**
- package must include `controller-gated-mpd/SKILL.md` and its `agents/openai.yaml`;
- new skill must not change Impeccable source-owned metadata precedence;
- ChatGPT documentation explicitly explains Prompt-Handoff Parallelism.

**Behavioral evals must cover the 18 scenarios in the approved design.** If the required live agent runner is unavailable, record `NOT RUN`; deterministic/static tests do not substitute for live behavior evidence.

---

## Task 11 — Final Integration Review and Release Candidate

**Proposed version:** `0.2.0-rc1` / tag `adaptive-v0.2.0-rc1`.

**Fresh final verification matrix:**
```bash
python3 -m unittest discover -s tests/controller-gated-mpd -p 'test*.py' -v
bash tests/adaptive-orchestrator/test-policy-contracts.sh
bash tests/hooks/test-session-start.sh
bash tests/shell-lint/test-lint-shell.sh
bash tests/codex/test-marketplace-manifest.sh
bash tests/codex/test-package-codex-plugin.sh
bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh
bash tests/kimi/run-tests.sh
bash tests/opencode/run-tests.sh
node --experimental-strip-types tests/pi/test-pi-extension.mjs
pytest -q tests/hermes
bash tests/antigravity/run-tests.sh
bash tests/devin/test-devin-plugin.sh
bash tests/claude-code/test-worktree-path-policy.sh
bash tests/claude-code/test-sdd-workspace.sh
git diff --check
```

Also run:
- V6 profile validator against the shipped template;
- Python compile checks for MPD scripts;
- `bash -n` on MPD shell scripts;
- package archive inspection confirming MPD files and OpenAI metadata;
- exact scan proving canonical V6 source no longer uses `low|normal|high` as active risk values (historical docs may be excluded explicitly);
- scan proving V5 `schema_version: 3 / protocol_version: 5` cannot enter V6 READY/merge authority.

**Independent review focus:**
- authorization bypasses;
- stale READY acceptance;
- evidence aggregation across workflow attempts;
- dependency prompt release;
- fake native-dispatch claims in ChatGPT;
- ledger duplication;
- path-floor downgrade or ownership overlap bypass;
- V5/V6 protocol confusion.

**Release rule:** publish/tag only after the final tree passes the applicable deterministic matrix. Live behavior evals may remain explicitly pending in an RC, but must never be reported as passed when not run.

---

## Parallel implementation strategy

Do **not** parallelize the schema foundation. Tasks 0–3 are serial because all later lanes consume the V6 contract.

After Task 3 is green, these implementation lanes can run concurrently from one frozen integration base:

### Lane A — Prompt-Handoff
- Task 4
- exclusive: renderer + handoff templates + prompt-handoff tests

### Lane B — Evidence / READY
- Tasks 5–6
- exclusive: actions metadata, exact-head, trunk evidence, READY scripts + evidence tests

### Lane C — Merge / Authorization
- Task 7
- exclusive: merge train + merge tests
- depends on shared V6 policy contract from Task 3; use test fixtures rather than editing Lane B files

### Lane D — Adaptive Routing / Ledger
- Tasks 8–9
- exclusive: orchestrator adapters, parallel/SDD/worktree integration, dependency/ledger helpers + routing tests

**Shared/read-only during parallel phase:**
- `skills/controller-gated-mpd/scripts/policy.py`
- `skills/controller-gated-mpd/scripts/validate_wave_profile.py`
- canonical design + implementation plan

If any lane discovers a required change to shared foundation, it reports a coordinator blocker instead of editing shared files.

Coordinator integrates A/B/C/D serially, resolves shared-foundation changes centrally, then executes Tasks 10–11.

## ChatGPT execution behavior while implementing this plan

Until V6 is itself available, ChatGPT can still use manual multi-window execution for the parallel phase. The coordinator should generate one zero-context prompt per Lane A/B/C/D containing:

- exact repository and frozen integration SHA;
- assigned branch;
- exclusive/shared/read-only files;
- inherited STANDARD risk floor (or CRITICAL when warranted);
- no merge/deploy/production-write authority;
- required tests and result envelope;
- explicit prohibition on editing shared foundation.

Worker reports return to the coordinator, which independently re-checks GitHub state before integration. Worker prose is never accepted as final evidence.

## Acceptance checklist

- [ ] Controller-Gated MPD exists as an Adaptive domain/process engine, not a second orchestrator.
- [ ] Only FAST/STANDARD/CRITICAL are active V6 risk values.
- [ ] MPD coordination floor is at least STANDARD.
- [ ] ChatGPT uses Prompt-Handoff when native dispatch is absent.
- [ ] Runnable prompts are zero-context and deterministic.
- [ ] Blocked downstream prompts are withheld by default.
- [ ] Worker result envelopes cannot create READY.
- [ ] Exact-head/run-attempt evidence remains machine-checked.
- [ ] READY invalidation semantics remain intact.
- [ ] V5 authority fails closed under V6.
- [ ] Merge `--apply` requires explicit Adaptive merge authorization.
- [ ] Already-granted merge authority is not asked twice.
- [ ] MPD wave state is the only ledger for active MPD waves.
- [ ] STANDARD/CRITICAL TDD and review behavior comes from Adaptive profile.
- [ ] V5 merge-train timeout/root-cause regression is resolved.
- [ ] Codex/OpenAI package contains the new skill metadata.
- [ ] Existing harness suites remain green or dependency-gated limitations are reported exactly.
- [ ] RC publish occurs only from a freshly verified final tree.
