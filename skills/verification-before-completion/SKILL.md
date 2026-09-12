---
name: verification-before-completion
description: Use before claiming that work is complete, fixed, passing, safe, or ready for integration.
---

# Verification Before Completion

## Evidence Before Claims

Never claim a property that **fresh** evidence does not establish. This is a global truthfulness invariant, not optional ceremony.

Before a claim:
1. Identify the command, inspection, rehearsal, or evidence that proves that specific claim.
2. Run/obtain it fresh against the tree/state being claimed.
3. Read the complete relevant result and exit/status signal.
4. State exactly what the evidence proves — no more.

Examples:
- "tests pass" requires a fresh successful test run;
- "build succeeds" requires a fresh build result;
- "bug fixed" requires the original symptom/regression evidence;
- "production parity verified" requires an actual parity check;
- "requirements met" requires checking the applicable requirements, not merely a green unit test.

## Profile-selected verification depth

- **targeted (FAST):** the narrow proof that establishes the changed behavior/property.
- **relevant (STANDARD):** targeted proof plus the affected suite/build/typecheck/lint surfaces that materially constrain the change.
- **canonical (CRITICAL):** the repository/domain verification matrix, rehearsal/parity checks, and independent evidence appropriate to the risk.

Verification depth is adaptive; truthfulness is not. If a suite cannot run because a dependency/tool is unavailable, report it as **not run** with the reason. Never convert absence of evidence into a pass.

## Delegated work

Do not trust an agent's success statement by itself. Inspect the produced diff/state and run the profile-selected fresh verification before reporting completion.
