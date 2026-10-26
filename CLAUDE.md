# Rules for Claude Code in this repo

- Before you call a change done, run `pytest`, `ruff check .`, `ruff format --check .` and `mypy`. All four must pass.
- Never print, log, or write an API key. Never put one in a test, a fixture, a trace, or the README. Keys come from the environment or a gitignored `.env`.
- Traces contain prompts and tool output. Never commit a file from `traces/` or `checkpoints/`. The only committed trace is `examples/policy-block.trace.jsonl`.
- A new tool needs four things: a file in `src/agent_runtime/tools/`, a registration in `builtin_tools`, a row in `config/policy.toml`, and a test. Add an eval task in `evals/tasks/` if the model must use it.
- A tool with no policy row is denied. Do not add a row with `allow` just to make a test pass.
- `CONTEXT.md` is a glossary. Keep it free of implementation detail.
- Record a decision in `docs/adr/` only when it is hard to reverse, surprising without context, and the result of a real trade-off.
- Do not commit or push unless the owner asks.
