# CG-MPD V5 Baseline Evidence

**Date:** 2026-09-13  
**Purpose:** classify inherited Controller-Gated MPD V5 behavior before the Adaptive-native V6 port.

## Source

Supplied archive: `controller-gated-mpd-v5-risk-adaptive (1).zip`.

## Initial symptom

The focused V5 test `FrozenAndMergeTests.test_merge_train_merges_and_proves_risk_bound_trunk` failed under the original harness with `subprocess.TimeoutExpired` after the harness-wide 15-second deadline.

The merge train did not show evidence of a semantic deadlock. Diagnostic tracing showed the environment spends roughly 1.3-1.4 seconds starting each `python3` process. The V5 fake `gh` executable is itself a Python program, and one successful merge-train scenario invokes multiple fake-`gh` processes plus Python verification helpers. The aggregate process-start cost exceeded the fixed 15-second test deadline.

## Root-cause classification

**Test timing assumption / harness portability bug.**

The production merge-train script was not changed for this diagnosis. A diagnostic copy of `tests/test_v5.py` increased only `V5Case.run_cmd`'s subprocess deadline from 15 seconds to 60 seconds.

## Diagnostic timing evidence

- `python3 -c 'pass'`: about 1.35-1.43 seconds per process in this environment.
- one fake `gh api ...` call: about 1.33 seconds.
- one fake `gh pr view ...` call: about 1.33 seconds.
- isolated `verify_ready.py`: about 3.96 seconds for two fake-`gh` invocations plus Python work.

These costs make the original 15-second merge-train test deadline environment-sensitive.

## V5 class-scoped results with diagnostic-only 60-second harness timeout

- `ProfilePolicyTests`: **3/3 PASS** in 4.435s.
- `RiskAdaptiveEvidenceTests`: **5/5 PASS** in 32.780s.
- `ReadyV5Tests`: **5/5 PASS** in 14.323s.
- `FrozenAndMergeTests`: **6/6 PASS** in 62.508s.

Total semantic scenarios classified: **19/19 PASS** once the environment-sensitive harness deadline is removed.

## Invariants safe to carry into V6

The following V5 behaviors are treated as inherited semantic requirements, subject to V6 schema/risk renaming and authority changes:

- exact-head and exact workflow identity evidence;
- one workflow attempt must satisfy the complete required gate set;
- no cross-run gate aggregation;
- run-attempt binding;
- stale/tampered evidence invalidates READY;
- base retarget invalidates READY;
- profile digest binding;
- frozen-base and clean-tree checks;
- plan-mode merge train is non-mutating;
- merge train pins initial trunk and fails on unexpected trunk movement;
- post-merge trunk proof remains required.

## V6 regression requirement

V6 tests must not rely on the V5 Python fake-`gh` + fixed 15-second portability assumption. The V6 merge harness should use a lightweight deterministic fake CLI or a timeout sized to the number of expected child invocations. A regression must prove the successful merge-train scenario completes without an environment-sensitive false timeout.

## Status

**V5 inherited semantics classified.** The original timeout is not evidence of a merge-train product deadlock; it is a harness timing assumption that V6 must not reproduce.
