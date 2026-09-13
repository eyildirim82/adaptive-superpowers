# Worker Prompt Template

Prompt-Handoff worker prompts are **zero-context execution contracts**. The deterministic renderer owns concrete values; this reference defines the minimum content.

Every worker prompt must include:

- the literal framework instruction `Adaptive Superpowers + Controller-Gated MPD kullan`;
- lane ID and exact task authority;
- repository and trunk;
- canonical spec, canonical plan, and canonical wave-profile pointer;
- assigned branch/workspace and full frozen-base SHA;
- inherited Adaptive risk floor, lane-declared risk, and effective starting floor;
- exclusive owned paths;
- shared/read-only paths;
- forbidden/hot-zone paths;
- reserved migrations/resources;
- current prerequisite state and downstream dependency contract;
- granted/denied/unknown effect authorization plus branch-scoped authorization boundaries, kept independent from risk;
- required verification with `NOT VERIFIED` semantics for skipped checks;
- explicit scope-boundary handling: shared-file/out-of-scope work becomes a coordinator blocker;
- explicit **no self-READY** and **no self-merge** rules;
- the worker-result envelope and the statement that worker results are not evidence.

Blocked preview prompts must start with a conspicuous `DO NOT START` marker and enumerate unmet prerequisites. The ordinary rendering path must withhold blocked prompts entirely.

A worker may report `READY_FOR_COORDINATOR: YES` only as a handoff hint. It never means MPD `READY@SHA`, evidence, approval, or merge authority.
