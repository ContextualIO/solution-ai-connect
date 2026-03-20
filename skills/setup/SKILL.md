---
name: setup
description: Ensure Contextual access is installed and ready.
disable-model-invocation: true
---

# Contextual Setup

Request: `$ARGUMENTS`

## Instructions

1. Call `setup_access` from the `contextual` server.
2. Call `config_list` after setup.
3. Tell the user that login usually happens automatically on the first protected tenant action.
4. If the local `contextual` tools are unavailable, explain that this runtime needs local MCP support for full tenant access.
5. If setup succeeds but no configs are saved yet, tell the user the next step is to add or choose a tenant config.

## Output

Return:

- whether access was already present or installed now
- version
- whether config discovery succeeded
- the next step, usually login or tenant inspection
