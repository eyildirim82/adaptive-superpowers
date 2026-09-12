---
name: writing-plans
description: Use when implementation needs an explicit multi-step plan or worker contracts before code changes.
---

# Writing Plans

Planning depth comes from the active Adaptive Superpowers execution profile.

## FAST — none
Do not create a plan file. Keep only the short execution intent needed to make the change and verify it.

## STANDARD — lightweight
Use a **lightweight** task plan when the work spans multiple coherent changes, files, or dependencies. A lightweight plan should state:
- goal and architecture/approach;
- files or ownership boundaries;
- behavior and interfaces;
- testing/verification strategy;
- completion criteria and relevant constraints.

Do not pre-write every RED/GREEN shell command or large implementation blocks merely to satisfy a template. Tasks are coherent reviewable change units, not 2–5 minute micro-steps.

## CRITICAL — persistent
Write a durable implementation plan when risk, migration history, security/data boundaries, parallel lanes, or recovery needs require an execution authority. Include exact ownership contracts, dependencies, irreversible boundaries, rehearsals, evidence expectations, and integration order. Plan detail scales to ambiguity and consequence; CRITICAL does not require bloated code-by-code transcription.

Default path: `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md` unless the user/repo specifies another location.

## Plan rules
- Map files and interfaces before splitting tasks.
- Prefer independent, testable deliverables.
- Keep assumptions explicit; use `Assumption`, `Gate`, or `Evidence` when a fact cannot yet be known.
- No `TBD`/`TODO` placeholders in executable requirements.
- Follow existing repository patterns unless the task itself changes them.
- Parallel lanes require exclusive/shared-file ownership and a defined integration order.

## Self-review
Check requirement coverage, placeholders, contradictory interfaces/types, scope, and unauthorized effects. Fix the plan before execution. Execution then uses the profile-selected engine: inline, subagent-driven, or parallel lanes only when their coordination cost is justified.
