# Worker Prompt Template

A worker prompt must contain enough context to execute without access to the coordinator conversation:

- repository;
- canonical spec and plan;
- lane/task identity;
- assigned branch/workspace;
- frozen base SHA;
- inherited Adaptive risk floor;
- exclusive/shared/read-only files;
- reserved migrations/resources;
- dependency state;
- granted/denied/unknown effect authorization;
- required verification;
- explicit no-self-READY/no-self-merge rule;
- worker result contract.
