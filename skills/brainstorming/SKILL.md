---
name: brainstorming
description: Use when a task needs product/design exploration before implementation, especially new behavior, new subsystems, or unresolved choices.
---

# Brainstorming Ideas Into Designs

Brainstorming is a design-exploration policy. It does not choose risk level and it does not create a generic implementation approval gate. Follow the active Adaptive Superpowers execution profile.

## Profile behavior

### FAST
Use at most a brief intent statement when the change is already well defined. Do not stop for design approval. If a hidden product choice appears, escalate the design mode rather than pretending the choice is settled.

### STANDARD
Explore the code/project context, resolve material ambiguities, compare 2–3 viable approaches when there is a real design choice, then produce a **short-design** in chat. Proceed without a routine implementation-approval stop. Ask only when the user's preference is part of the product decision and cannot be safely inferred.

### CRITICAL
Use deeper design analysis proportional to the consequence, not to ceremony. A persistent spec is appropriate when interfaces, security/data boundaries, migration shape, or multi-lane contracts need a durable authority. CRITICAL classification alone does not mean "wait for approval before reversible work."

## What to understand

Focus on purpose, constraints, success criteria, architecture, interfaces, data flow, failure handling, testing strategy, and rollback where relevant. In existing codebases, inspect current patterns before proposing changes and avoid unrelated refactors.

## Genuine user-choice boundary

Ask the user when multiple materially different product or visual worlds are valid and the choice changes what gets built. Do not ask merely to confirm an already precise request.

## Design quality

Prefer small, well-bounded units with explicit interfaces. Apply YAGNI. If scope contains independent subsystems, decompose them before implementation. Hidden complexity can escalate the active risk/design profile.

## Persistent spec

When the active profile calls for a persistent spec, save it to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` (or the user's requested path), self-review it for placeholders, contradictions, scope, and ambiguity, then hand it to the profile-selected planning policy. A spec is an authority artifact, not a permission ritual.

## Visual companion

Use the existing visual companion only when seeing a mockup/diagram would materially improve a real design decision. For frontend/UI work, the Impeccable domain skill may provide the stronger visual workflow; Adaptive risk/authorization remains authoritative.
