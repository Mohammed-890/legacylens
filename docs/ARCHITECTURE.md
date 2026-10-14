# Architecture and engineering decisions

## Data path

The browser sends selected text files to `/api/analyze`. The server validates paths, file types, sizes and counts, then builds a project snapshot in memory. Python files are parsed with `ast`; other supported text supplies retrieval evidence. Each snapshot has a content fingerprint, source chunks, file metadata, import edges and heuristic findings.

Chunks are 24-line windows. BM25 ranks them by question terms. Source citations carry exact lines rather than generated source summaries. Reverse import traversal reports potentially affected importers while avoiding cycles. It does not prove a runtime failure path.

`/api/investigate` defaults to deterministic evidence. When a provider is configured and the caller opts in, a bounded agent loop invokes three read-only tools. Returned citation IDs are checked against the evidence the model actually retrieved. Malformed or uncited model answers fall back to evidence mode. Provider errors are surfaced without leaking credentials.

## Why these choices

**Standard-library backend:** keeps the project easy to run and makes retrieval and orchestration inspectable. It trades production server features and framework tooling for a small educational surface.

**Lexical retrieval first:** identifiers, error keys and file names are important software evidence. BM25 is deterministic and cheap. It will miss semantic matches without shared terms; embeddings and hybrid search would need comparative evaluation before claiming improvement.

**Single agent with explicit tools:** avoids unnecessary agent coordination. Inspectable tool calls are useful evidence of what the agent did; they are not hidden chain-of-thought.

**Separate investigation and repair:** LLM answers do not execute code. The only executable workflow is a shipped fixture with a predefined patch and explicit fingerprint approval. This makes the demonstration reproducible without presenting temporary directories as hostile-code isolation.

**Source-derived visualization:** buildings represent files, height represents source length, and edges represent imports. It has no invented health percentage or confidence score.

## HTTP surface

| Endpoint | Purpose |
|---|---|
| GET `/api/status` | Mode, provider availability, per-process request token |
| GET `/api/demo` | Bundled analysed project |
| GET `/api/proposal` | Predefined patch and approval fingerprint |
| POST `/api/analyze` | Validate and index selected text files |
| POST `/api/investigate` | Retrieve evidence; optionally invoke the model |
| POST `/api/impact` | Reverse import impact for one file |
| POST `/api/repair` | Verify explicit proposal approval and test the fixture |

Mutations require `X-LegacyLens-Token`. The server checks host/origin, caps request size, limits active jobs and retains at most eight imported snapshots. These controls support local use; they do not replace authentication, multi-tenant isolation or a production gateway.

## Known limitations

- Static import resolution is approximate; dynamic imports and runtime dispatch are not resolved.
- Five AST rules are narrow heuristics, not a comprehensive vulnerability scanner.
- Bounded source windows may omit context. Citation validation checks provenance, not entailment.
- Source filenames can hide sensitive data. No secret scanner is included.
- Live provider behavior, availability and model-specific protocol differences require separate testing.
- There is no persistent project store, user account system or autonomous patch generator.
