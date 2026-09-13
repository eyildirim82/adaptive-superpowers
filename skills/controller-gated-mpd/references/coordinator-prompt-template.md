# Coordinator Prompt Template

The coordinator owns integration, evidence review, READY materialization, dependency release, and merge-train control; it does **not** implement worker lanes.

A zero-context coordinator handoff must contain:

- `Adaptive Superpowers + Controller-Gated MPD kullan`;
- repository, trunk, wave ID, frozen-base SHA, canonical spec/plan, and canonical wave-profile path;
- every lane's branch, ownership, declared/effective floor, prerequisites, dependency state, downstream lanes, and reserved resources;
- the parent Adaptive risk floor and complete effect-authorization state;
- which prompts are currently dispatchable and which lanes are blocked;
- the deterministic integration order;
- a requirement to re-read current Git/PR/Actions metadata instead of trusting worker prose;
- exact-head evidence policy and V6-only READY binding/invalidation rules;
- the rule that only the coordinator may materialize `READY@SHA`;
- merge authorization handling (`merge == granted` for mutation) and serialized integration;
- post-merge trunk verification before downstream release.

For ChatGPT Prompt-Handoff transport, say exactly:

> Bu promptları ayrı ChatGPT pencerelerinde aç.

Never claim that workers or agents were launched or are running merely because prompts were rendered; such claims require actual native-dispatch evidence.
