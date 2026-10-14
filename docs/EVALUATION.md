# Reproducible evaluation

Run `python3 -m unittest discover -s tests -v` for the automated suite and `python3 scripts/evaluate.py` for the recorded demonstration checks.

The evaluation script measures 19 explicit conditions: retrieval placement, empty evidence handling, reverse import reachability, citation/source equality, five static rules and two safe counterexamples, parse warnings, cycle termination, failing original tests, passing patched tests and unchanged fixture source. Reports include timestamps and the source fingerprint.

## What passing means

It means the named assertions passed on this controlled dataset. It does not estimate accuracy on unfamiliar repositories. The incident is deliberately seeded and its runbook provides a strong retrieval clue. The patch is predefined rather than discovered by the model.

The 32-test automated suite adds malformed input, traversal and file limits, mock provider interactions, citation rejection and real HTTP request checks. A mocked provider validates orchestration but does not measure a model's reasoning.

## Release validation

- Local suite: 32 tests passed on Python 3.14.4.
- Recorded evaluation: 19/19 checks passed.
- JavaScript syntax: checked with Node.
- Interface: manually exercised in the local browser, including mobile layout.
- GitHub Actions: configured for Python 3.11, 3.12 and 3.13; the workflow badge is the source of current CI status.
- Real paid LLM endpoint: not exercised; requires the user's provider credentials.
- Docker execution: not exercised in the initial development environment.

## A defensible future model benchmark

Create independent incidents with accepted root causes and expected evidence, split repositories between development and held-out evaluation, and compare retrieval-only and LLM-assisted runs. Measure correct diagnosis, evidence support, abstention on unanswerable cases, latency and token cost. Publish failed cases and denominators. Avoid reporting fixture pass rates as agent accuracy.
