# Adaptive Superpowers + Impeccable Verification Evidence

**Date:** 2026-09-13  
**Base:** `69363e3eab5c48820173a98bbf7f3354c406e9aa`  
**Verified implementation head before this evidence-only commit:** `f6820402f61b7f3eeb320aca306a65a2f160a595`

## Scope

This evidence covers the Adaptive Superpowers implementation described by:

- `docs/superpowers/specs/2026-09-12-adaptive-superpowers-design.md`
- `docs/superpowers/plans/2026-09-12-adaptive-superpowers-implementation.md`

It includes the Adaptive Orchestrator, risk-aware process policies, intent-aware finishing, canonical Impeccable skill 4.3.1 (engine 0.1.5) vendoring, Codex metadata precedence, cross-harness bootstrap compatibility, documentation, and deterministic policy contracts.

## Deterministic verification

| Check | Result | Evidence / note |
| --- | --- | --- |
| Adaptive policy contracts | PASS | `bash tests/adaptive-orchestrator/test-policy-contracts.sh` |
| SessionStart bootstrap | PASS | `bash tests/hooks/test-session-start.sh` |
| Shell lint regression suite | PASS | `bash tests/shell-lint/test-lint-shell.sh` |
| Codex package archive | PASS | `bash tests/codex/test-package-codex-plugin.sh` |
| Codex marketplace manifest | PASS | `bash tests/codex/test-marketplace-manifest.sh` |
| Codex sync | PASS | `bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh` |
| Kimi plugin manifest | PASS | `bash tests/kimi/run-tests.sh` |
| OpenCode unit suite | PASS | `bash tests/opencode/run-tests.sh` (2 passed, 0 failed; integration portion not requested by this script) |
| Pi extension | PASS | `node --experimental-strip-types tests/pi/test-pi-extension.mjs` (6/6). Plain `node` cannot import the bundled `.ts` extension in this environment. |
| Hermes | PASS | `pytest -q tests/hermes` (19 passed) |
| Antigravity | PASS | `bash tests/antigravity/run-tests.sh` |
| Devin | PASS | `bash tests/devin/test-devin-plugin.sh` |
| Writing-skills graph renderer | PASS | `bash tests/writing-skills/test-render-graphs.sh` (8 passed) |
| Worktree path policy | PASS | `bash tests/claude-code/test-worktree-path-policy.sh` |
| SDD workspace | PASS | `bash tests/claude-code/test-sdd-workspace.sh` |
| Git whitespace/error check | PASS | `git diff --check` |
| Impeccable vendor integrity | PASS | `diff -ru --exclude LICENSE --exclude NOTICE.md <upstream .agents/skills/impeccable> skills/impeccable` returned no semantic diff |

## Dependency-gated verification

The following suites were **not run** and are not represented as passing:

| Suite | Status | Reason |
| --- | --- | --- |
| Version-bump regression | NOT RUN | `yq` is not on `PATH` |
| Explicit named-skill behavior suite | NOT RUN | `claude` CLI is unavailable |
| Claude Code skill suite | NOT RUN | `claude` CLI is unavailable |
| Claude Code integration suite | NOT RUN | `claude` CLI is unavailable |
| Native worktree preference behavior test | NOT RUN | test dispatch requires `claude` CLI |
| Adaptive behavior eval scenarios | NOT RUN | runner exited successfully with an explicit `claude binary unavailable` report; no scenario was executed |

## Before / after contract evidence

The final Adaptive policy contract was also executed against the imported Superpowers baseline by checking out base commit `69363e3` in a temporary detached worktree and copying only the final contract test into it.

| Tree | Contract violations |
| --- | ---: |
| Imported Superpowers baseline | 36 |
| Adaptive implementation | 0 |

This proves the deterministic policy surface changed from the old unconditional contracts to the approved Adaptive contracts. It does **not** substitute for agent-behavior evals.

## Whole-branch review findings

- No process skill outside vendored Impeccable retains the old universal `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST`, `EVERY task`, `present exactly these 3 options`, or equivalent blanket ceremony markers.
- `requesting-code-review` still makes independent review mandatory for CRITICAL security/authorization/migration/history/data-loss/payment/destructive boundaries; that is intentional policy, not a universal rule.
- Risk-floor language is present in the orchestrator and delegated-execution policies; children may escalate but not de-escalate below inherited risk.
- FAST/STANDARD brainstorming explicitly avoids generic approval stops while preserving genuine unresolved product/visual choices.
- Finishing distinguishes granted, denied, and unknown external effects and reuses already-granted authorization rather than asking twice.
- Impeccable is vendor-pure relative to the supplied v0.1.5 canonical `.agents/skills/impeccable` tree. Adaptive behavior lives in `skills/using-superpowers/references/impeccable-adapter.md`.
- Impeccable Apache-2.0 `LICENSE` and `NOTICE.md` are preserved in the vendored skill directory.
- Codex packaging includes Impeccable source-owned `agents/openai.yaml`, license, and notice without replacing its metadata from the legacy overlay source.

## Acceptance status

Design acceptance criteria supported by deterministic/static evidence are satisfied except for the criteria that specifically require live agent-behavior measurements. In particular, criteria requiring measured reductions in user stops/reviewer dispatches/plan artifacts and observed zero unauthorized effects/unsupported completion claims across executed behavior scenarios remain **unverified in this environment** because the Claude CLI is unavailable.

The repository may be published as an initial adaptive fork / release candidate with that limitation stated. Do not describe the live behavior-eval acceptance criteria as empirically passed until those scenarios are run in a Claude-capable environment.
