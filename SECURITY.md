# Security

## Reporting a vulnerability or a leaked key

Do not open a public issue. Use GitHub's private vulnerability reporting on this repository (Security → Report a vulnerability).

## If an API key leaks

1. Revoke the key in the Claude Console first. A leaked key stays usable until it is revoked.
2. Remove the key from history: `git filter-repo --replace-text expressions.txt`, where `expressions.txt` maps the key to `***REMOVED***`. Deleting the file in a new commit is not enough, because the key stays in history.
3. Force-push the rewritten history and ask anyone with a clone to re-clone.

## What this project protects

- Secrets: keys are read from the environment or `.env`, which is gitignored. `gitleaks` runs in pre-commit and in CI.
- Tools: a tool with no policy row is denied. `read_file` and `write_file` cannot leave the directory the runtime started in, and they refuse any file whose name starts with `.env`.
- Output: tool results are capped and marked as data. They are not sanitized, so prompt injection through a tool result is still possible. See the README "What breaks" section.

## Not covered

- A tool that is allowed can still do harm inside the workspace. Keep `write_file` on `ask` unless you need it.
- The eval job uses the real key only when someone starts it by hand (`workflow_dispatch`). It never runs on pull requests, so fork pull requests never get the secret.
