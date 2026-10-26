# Glossary

**Run**: one task from a user prompt to a final answer, a policy stop, or a step-cap stop.

**Step**: one model call and the tool calls it returns. The step cap limits steps per run.

**Tool**: a function the model may call.

**Policy**: the decision for a tool: allow, ask the user first, or deny.

**Trace**: the record of one run: every step, tool call, policy decision and stop reason.
