---
name: systematic-debugging
description: Use when a bug, failing test, build error, integration issue, or unexpected behavior needs diagnosis before a fix.
---

# Systematic Debugging

**Core principle: find root cause before fixing symptoms.** The active profile selects one of three depths.

## short-root-cause — FAST
For a local, reproducible issue: reproduce → identify the direct cause → make the smallest fix → targeted verify. Do not add a separate pattern-analysis ceremony when the evidence is already decisive.

## evidence-driven — STANDARD
1. Reproduce and read the actual error/stack/output.
2. Inspect recent changes and compare with a working pattern.
3. State one falsifiable hypothesis.
4. Test the smallest change that distinguishes that hypothesis.
5. Fix the root cause and add regression evidence where valuable.
6. Verify the original symptom and relevant surrounding behavior.

## full-tracing — CRITICAL
Use complete boundary/data-flow tracing across components, configuration, environment, persistence, and external interfaces. Capture evidence at each boundary before changing production behavior. Prefer source-level fixes over downstream symptom patches.

## Failed hypotheses and escalation

Do not stack guesses. If a hypothesis fails, return to evidence and form a new one. After **three failed evidence-based hypotheses**, escalate to CRITICAL/architecture review before a fourth fix attempt. Repeatedly moving the failure to a different shared-state boundary is an architecture signal.

## TDD relationship

When a fix needs a regression test, use the active TDD mode. This skill does not independently force a stricter TDD profile than the orchestrator selected.
