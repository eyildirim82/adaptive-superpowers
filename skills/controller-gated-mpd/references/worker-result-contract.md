# Worker Result Contract

A worker result is a **handoff envelope, not evidence**. It is navigation input for the coordinator and **must not create READY**.

Return a compact envelope with at least:

```text
WORKER RESULT

LANE: <lane id>
RISK: <effective risk observed>
BRANCH: <assigned branch>
FROZEN_BASE: <frozen base sha>
FINAL_HEAD: <worker-reported head sha; coordinator re-verifies>
CHANGED_FILES: <paths or none>
TESTS: <commands/results>
VERIFICATION: <commands/results>
OPEN_ISSUES: <issues/blockers or none>
RISK_ESCALATIONS: <reasons or none>
READY_FOR_COORDINATOR: YES|NO
```

`READY_FOR_COORDINATOR: YES` is not MPD `READY@SHA`. It does not prove the reported head, CI state, scope compliance, evidence completeness, authorization, or merge readiness.

The worker must not self-approve integration, create READY/evidence receipts, merge, deploy, or claim that its reported head is the authoritative PR head. The coordinator independently re-reads Git/PR/Actions state and verifies every authority-bearing fact.
