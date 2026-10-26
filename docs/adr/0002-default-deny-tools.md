# 0002: A tool with no policy row is denied

## Status

Accepted.

## Context

Tools are the part of an agent that can change the world. A new tool can be registered and forgotten, and the model can call any registered tool.

## Decision

A tool with no policy row is denied. Each tool must be listed as allow, ask or deny before it can run.

## Consequences

- A new tool does nothing until someone adds its row. This is intentional: the first run after adding a tool fails loudly with "blocked by policy".
- Adding a tool means editing `config/policy.toml` as well as the code.
- MCP tools follow the same rule. Each `<server>__<tool>` needs its own row.
