# Security and data handling

LegacyLens is a local portfolio application. Keep it on loopback. The built-in server is not a production multi-user service.

Imported source is stored in process memory and is not executed. Optional provider mode transmits the question and selected source evidence to the configured provider only after explicit UI opt-in. Do not import secrets or confidential employer repositories; filename exclusions are not comprehensive secret detection.

The repair runner executes only the bundled, trusted fixture in a temporary directory. This is not a sandbox suitable for untrusted uploaded code. Do not extend it to arbitrary repositories without an isolated execution design.

Never commit API keys. For a potential vulnerability, contact the repository owner privately through their GitHub profile where possible. Do not include credentials or sensitive source in a public issue.
