# CG-MPD V6 Task 10 Verification Evidence

**Date:** 2026-09-13
**Integration source commit:** `02a626c6e22ec228e8975bbade8a5ca1525e7874`
**GitHub Actions run:** https://github.com/eyildirim82/adaptive-superpowers/actions/runs/34751689933

## Scope

Task 10 covers cross-harness packaging assertions, OpenAI skill metadata packaging, ChatGPT Prompt-Handoff documentation, the 18-scenario behavioral-eval catalog, and deterministic verification evidence.

## Deterministic gates

The staging workflow commits Task 10 output only after all of these commands exit successfully on a real GitHub checkout:

- `python3 -m unittest discover -s tests/controller-gated-mpd -p 'test*.py' -v`
- `bash tests/adaptive-orchestrator/test-policy-contracts.sh`
- `bash tests/codex/test-marketplace-manifest.sh`
- `bash tests/codex/test-package-codex-plugin.sh`
- `bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh`
- `python3 skills/controller-gated-mpd/scripts/validate_wave_profile.py skills/controller-gated-mpd/references/wave-profile-template.json`
- Python compile checks for all MPD Python scripts
- shell syntax checks for all MPD shell scripts
- `git diff --check`

A committed Task 10 result therefore means the listed staging gates passed in the cited workflow run. Task 11 still owns the broader final cross-harness matrix.

## OpenAI packaging contract

The Codex package test explicitly requires both:

- `skills/controller-gated-mpd/SKILL.md`
- `skills/controller-gated-mpd/agents/openai.yaml`

and verifies that the source-owned Controller-Gated MPD OpenAI metadata is preserved, matching the existing Impeccable source-metadata precedence rule.

## Behavioral evals

All 18 approved scenarios are present in:

- `tests/controller-gated-mpd/pressure-scenarios.md`
- `skills/controller-gated-mpd/evals/evals.json`

**Live agent runner:** NOT RUN.
**Live behavioral verdict:** NOT VERIFIED.

No live behavior PASS is inferred from deterministic tests, packaging, build success, or documentation checks.
