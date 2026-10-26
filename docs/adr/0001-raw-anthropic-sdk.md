# 0001: Call the Anthropic API directly, not through the Claude Agent SDK

## Status

Accepted.

## Context

The project's purpose is to learn how an agent loop works: model call, tool use, repeat, with limits and a trace. The Claude Agent SDK provides that loop ready-made.

## Decision

Use the raw Anthropic Python SDK. Write the tool-use loop in `loop.py`.

## Consequences

- The loop, step cap, policy check and trace are written by hand, so each one can be explained in the README.
- The project has more code to maintain than an Agent SDK version would.
- The README's "why not the SDK's agent helpers" section compares real code against the SDK, not guesses.
