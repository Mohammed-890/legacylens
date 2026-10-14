# A 90-second walkthrough

1. **Show the system (20 seconds).** Open the local app. Switch between City and Graph. Select `customers.py` and show its importers. Explain that edges come from Python imports and building height comes from source length.
2. **Investigate the incident (25 seconds).** Open Investigate and ask: “Why are invoices failing after the customer schema migration?” Open a source citation and point to the exact field mismatch. In evidence mode, explain that this is lexical retrieval. Only call it an LLM investigation if the configured provider is enabled.
3. **Review and verify (25 seconds).** Open Repair lab. Read the `full_name` to `display_name` diff, approve it, and run verification. Show the actual before-and-after test outputs. Explain that the patch is predefined and runs on a temporary copy of a shipped fixture.
4. **Show engineering discipline (20 seconds).** Open Evaluations, export the report, then show the repository's tests and architecture notes. Explain one limitation and the next experiment you would run.

For a deeper interview, import a small Python repository you are authorised to inspect and discuss where the import graph or retrieval falls short. Do not upload employer code or claim measured production savings.

## Project ownership

Describe it as “my portfolio project, built with AI assistance.” Be ready to explain the AST analysis, BM25 ranking, bounded tool loop, citation validation, HTTP request protections and controlled repair runner. Do not claim to have written every line without assistance or to have deployed it at a former employer.
