---
name: writing-skills
description: Use when creating, editing, or verifying reusable agent skills and process documentation before distribution.
---

# Writing Skills

Skills are production behavior. Author them with behavioral evidence, concise discovery metadata, and pressure scenarios that test the behavior they are meant to teach.

## Preferred skill-TDD loop
For discipline/process skills, baseline the undesired behavior first when practical, then make the smallest guidance change that closes the observed failure, rerun the scenario, and add adjacent regressions. This meta-skill keeps behavior testing as a required authoring discipline for distributed process changes; it does not impose obsolete universal application-code TDD above the active execution profile.

## Skill shape
- `SKILL.md` frontmatter: `name` and a third-person `description` beginning with "Use when..." that states triggering conditions, not the workflow summary.
- Keep frequently loaded bootstrap skills extremely concise; move heavy references/tools to supporting files.
- Use concrete trigger keywords so agents can discover the right skill.
- Prefer positive output contracts/recipes for shape problems; use strong prohibitions/red flags only for demonstrated discipline failures.
- Avoid redundant cross-skill process text. Named sub-skills are capabilities governed by the active Adaptive profile.

## Testing by skill type
- Discipline skill: pressure/rationalization scenarios.
- Technique skill: application + edge cases.
- Pattern skill: recognition + counterexamples.
- Reference skill: retrieval + application.

Success means the agent behaves correctly under representative pressure, not merely that the prose sounds clear.

## Self-review
Check frontmatter, discovery wording, token efficiency, duplicated guidance, placeholders, unresolved exceptions, and whether tests actually exercise the behavior changed. Keep mechanical constraints in scripts/tests when they can be enforced mechanically.
