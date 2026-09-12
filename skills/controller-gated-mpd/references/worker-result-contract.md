# Worker Result Contract

A worker result is a **handoff envelope, not evidence**.

Recommended fields:

- lane;
- branch/workspace;
- frozen base;
- worker-reported head;
- observed risk/escalations;
- changed files;
- tests/verification run;
- open issues/blockers;
- coordinator notes.

A worker **must not create READY**, self-approve integration, merge, deploy, or claim that its reported head is the authoritative PR head. The coordinator independently verifies all authority-bearing state.
