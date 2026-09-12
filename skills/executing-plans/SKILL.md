---
name: executing-plans
description: Use when a written implementation plan should be carried through in the current or separate execution session.
---

# Executing Plans

Read the authoritative spec/plan and execute coherent change units under the active Adaptive Superpowers profile.

## Start
- Confirm the relevant plan/spec paths and current Git/workspace state.
- Honor branch/base/ownership contracts exactly.
- Use the profile-selected workspace mode; never silently rewrite a frozen base or shared ownership contract.
- Create lightweight todos/ledger entries only when the active `ledger.mode` needs them.

## Execution loop
For each coherent task/lane:
1. Re-read the task's requirement and interfaces.
2. Apply profile-selected TDD/debugging/review depth.
3. Make reversible rulings when the spec/plan leaves a reasonable safe choice; record material rulings in the ledger when enabled.
4. Run the task's relevant verification before marking it complete.
5. Continue without routine "should I continue?" stops.

## Stop conditions
Stop only when:
- an unauthorized irreversible/destructive/security-sensitive external effect is reached;
- an external side effect requires permission not already granted;
- every reasonable path forward is guesswork because authority/spec/repo reality is unrecoverably ambiguous.

Ordinary blockers, plan defects, or small ambiguities should trigger investigation and a reversible ruling when a defensible path exists, not an automatic human stall.

## Completion
Use the intent-aware finishing policy after fresh verification. The plan does not imply push, merge, PR, deploy, or destructive cleanup unless those effects are already authorized by task intent.
