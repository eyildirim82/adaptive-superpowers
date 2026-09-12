# Adaptive Superpowers × Impeccable Adapter

Impeccable is the frontend/UI **domain capability**. Adaptive Superpowers remains the process/risk authority.

## Ownership

Impeccable owns:
- visual direction and craft quality;
- typography, layout, spacing, color, motion, responsive behavior;
- design-system consistency and frontend accessibility/visual QA;
- browser/live visual verification and finite visual-review passes.

Adaptive Superpowers owns:
- FAST / STANDARD / CRITICAL classification and inherited risk floor;
- authorization and irreversible-effect boundaries;
- planning/workspace depth;
- general TDD and debugging policy;
- Git integration and cleanup;
- engineering/security/data review;
- Evidence Before Claims.

Impeccable may discover a new risk signal and request escalation; it may not downgrade or independently relabel the task.

## Profile composition

### FAST UI
For a narrow existing-surface polish/fix, route to the relevant Impeccable capability, make the local change, run bounded visual/targeted verification, and continue. Do not add a generic design-approval gate.

### STANDARD UI
For a new surface or meaningful redesign within an established product direction, use Impeccable for design/craft decisions plus the active STANDARD engineering policy. A short design may be stated and implementation may proceed without routine approval. Use visual review when it adds signal; add engineering review only when code/integration risk warrants it.

### CRITICAL UI
A UI change becomes CRITICAL only through Adaptive hard triggers (for example auth/security, real-user data, production-wide design-system replacement with difficult rollback, or another high-consequence boundary). Use stronger isolation/review/verification, but continue reversible design/implementation work until an unauthorized effect boundary is reached.

## User-choice boundary

Preserve genuine creative/product choices. Ask when multiple materially different visual worlds are valid and no product direction selects among them. Do not ask merely to reconfirm precise requests such as spacing, typography, polish, component fixes, or implementation within an already chosen design direction.

An irreversible design-system replacement is governed by Adaptive risk/authorization. A broad but reversible design exploration is not automatically a permission stop.

## Review composition

- Impeccable visual reviewer: design quality, hierarchy, craft, consistency, responsive behavior, visual accessibility.
- Engineering reviewer: correctness, architecture, security, data, integration, maintainability.

Do not dispatch both when one dimension is irrelevant or already adequately covered. CRITICAL engineering risk still requires independent engineering review even if visual review is excellent.

## Vendor boundary

`skills/impeccable/**` is vendored canonical upstream content. Do not implement Adaptive policy by editing those files. Put overrides and composition rules here so upstream updates remain diffable. Preserve Impeccable `LICENSE` and `NOTICE.md` in distributions.
