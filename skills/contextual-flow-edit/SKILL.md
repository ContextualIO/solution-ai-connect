---
name: contextual-flow-edit
description: Edit existing Contextual flows safely with the contextual MCP and docs grounding.
---

# Contextual Flow Edit

Use this skill when the user wants to inspect or modify an existing flow.

## Use These Tools

- `setup_access`
- `config_list`
- `config_current`
- `config_use`
- `records_get`
- `records_replace`
- `records_patch`
- `contextual-docs` tools for node and flow behavior

## Workflow

1. Ensure access with `setup_access` if needed.
2. Confirm the active config with `config_current` or switch with `config_use`.
3. Fetch the flow with `records_get(type: "flow", id: flowId)`.
4. Inspect `node_red_data.flows`.
5. Ground platform behavior questions with `contextual-docs` before editing.
6. Prefer full replacement with `records_replace(type: "flow", id: flowId, input: document)`.
7. Re-read the flow after each change and verify the exact structure landed.

## Flow Heuristics

- For `flow-http`, HTTP In paths are root-relative to the flow subdomain.
- Treat event-trigger payload data as `msg.payload` unless docs clearly say otherwise.
- `log-tap` must have `outputs: 1` and a valid `level`.
- Wire `log-tap` inline in the chain, not as a dead-end fork.
- Preserve top-level `flows_cred: {}` and tab `env: []` when creating new flow documents.

## Output

- State the change first.
- Mention what was verified after the edit.
- Summarize the affected nodes and chains instead of dumping the whole flow unless asked.
