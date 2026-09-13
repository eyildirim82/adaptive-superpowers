# CG-MPD V6 Verification Matrix

## Deterministic / static gates

| Surface | Command | Task 10 expectation |
|---|---|---|
| V6 policy, prompts, evidence, READY, merge, routing/ledger, integration | `python3 -m unittest discover -s tests/controller-gated-mpd -p 'test*.py' -v` | PASS |
| Adaptive orchestration policy | `bash tests/adaptive-orchestrator/test-policy-contracts.sh` | PASS |
| Codex marketplace identity | `bash tests/codex/test-marketplace-manifest.sh` | PASS |
| Codex package contents / metadata precedence | `bash tests/codex/test-package-codex-plugin.sh` | PASS |
| Codex source/package sync | `bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh` | PASS |
| Shell syntax | `bash -n skills/controller-gated-mpd/scripts/*.sh` | PASS |
| Python syntax | `python3 -m py_compile skills/controller-gated-mpd/scripts/*.py` | PASS |
| Profile template | `python3 skills/controller-gated-mpd/scripts/validate_wave_profile.py skills/controller-gated-mpd/references/wave-profile-template.json` | PASS |
| Whitespace / patch hygiene | `git diff --check` | PASS |

## Behavioral evidence

The 18 scenarios in `pressure-scenarios.md` and `skills/controller-gated-mpd/evals/evals.json` are the canonical behavioral-eval catalog. Task 10 does not have a configured live agent runner, so live scenario status is **NOT RUN**. Deterministic tests establish implementation contracts only; they are not reported as live behavioral PASS.

## Release boundary

Task 11 must run the full repository cross-harness matrix on the final candidate tree before version/tag publication. Environment-gated harnesses must be reported exactly; missing tools or live runtimes are not silently promoted to success.
