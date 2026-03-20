---
name: flow-context
description: Summarize a flow before drilling into details.
disable-model-invocation: true
argument-hint: <config-id> :: <flow-id>
---

# Contextual Flow Context

Input: `$ARGUMENTS`

Format: `<config-id> :: <flow-id>`

## Instructions

1. Parse `$ARGUMENTS` using `::`.
2. If config id is missing, call `config_current` first.
3. If config id is provided and is not current, call `config_use`.
4. Call `records_get` with `type: "flow"` and `id: flowId`.
5. Summarize the returned flow by reading `node_red_data.flows`.
6. Include tabs, entry points, main chains, major branches, and referenced record types.
7. If auth fails, run login and retry.
8. Summarize instead of dumping the whole record unless the user explicitly asks for raw JSON.

## Output

Return:

- flow name and id
- tabs and execution chains
- major record type references
- any obvious wiring or structure issues
