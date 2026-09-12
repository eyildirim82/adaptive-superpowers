# Adaptive Risk Policy

## CRITICAL hard triggers

Any of these makes the task CRITICAL regardless of diff size:

- production write;
- destructive data or schema change;
- authentication, authorization, or security boundary change;
- secrets, credentials, or production configuration mutation;
- irreversible external action;
- mutation of real user/customer data;
- payment or financial side effect;
- protected-branch history mutation, force-push, or history rewrite;
- high-risk schema change where rollback/parity is uncertain.

A development-only additive migration can remain STANDARD when it is reversible, does not affect production history, and does not cross a security/data boundary.

## FAST characteristics

FAST is appropriate only when the work is local, reversible, narrow, understood, does not change a shared contract/security/data boundary, and has a cheap reliable verification surface. If meaningful discovery is required, prefer STANDARD.

## STANDARD is the default engineering level

Use STANDARD for ordinary features, multi-file bug fixes, reversible integrations, refactors with behavioral impact, additive migrations, and changes whose blast radius is larger than FAST but lack a CRITICAL trigger.

## Escalation signals

Escalate when any of these appears:

- diff scope expands materially;
- a shared dependency or public contract is discovered;
- security/data boundary appears;
- rollback becomes uncertain;
- production parity becomes unclear;
- verification is weaker than expected;
- three evidence-based debugging hypotheses fail;
- parallel workers conflict or discover shared state;
- plan/spec and repository reality materially contradict each other.

## Risk floor

A child task inherits the parent risk floor. It can escalate above that floor but cannot downgrade below it. When the child finishes, the coordinator returns to the parent task's profile; it does not rewrite history to claim the child was lower risk.

## Examples

- Rename button copy: FAST.
- Add endpoint to an existing service: STANDARD.
- Replace an RLS policy: CRITICAL.
- Add a reversible local-only table for tests: STANDARD.
- One-line credential handling fix: CRITICAL.
- Twenty-file documentation reorganization: usually STANDARD.
