---
name: contextual
description: Inspect, update, and explain Contextual tenants with guided workflows and docs grounding.
---

# Contextual

Use this skill for Contextual tenant work: setup, login, inspection, edits, and docs-grounded platform guidance.

When a task is specifically about editing an existing flow, prefer the `contextual-flow-edit` skill.

When a task is specifically about understanding the shape of a tenant, prefer the `contextual-tenant-analysis` skill.

## Use This Skill When

- The user wants to inspect a tenant, object type, record, agent, or flow.
- The user wants to change tenant data or a flow.
- The user needs Contextual access set up or refreshed.
- The user asks how Contextual platform behavior works and the answer should be grounded in docs.

## Available Tools

Use tools from the local `contextual` server for tenant work:

- `setup_access`
- `config_list`
- `config_current`
- `config_get`
- `config_add`
- `config_use`
- `config_delete`
- `login_start`
- `login_status`
- `login_await`
- `types_add`
- `types_list`
- `types_get`
- `types_replace`
- `types_remove`
- `records_add`
- `records_list`
- `records_get`
- `records_query`
- `records_patch`
- `records_replace`
- `records_remove`
- `records_stats`

Use these `contextual-docs` tools for docs grounding:

- `search`
- `list_paths`
- `list_headings`
- `read_chunk_context`
- `read_section`
- `read_page`
- `list_versions`

## Hard Rules

- Never read `~/.config/ctxl/config.json`, `~/.flowcraft/tenants.json`, or any raw credential store.
- Never call Contextual APIs directly with `curl`, `fetch`, custom headers, or handwritten HTTP requests.
- Never expose or summarize bearer tokens, refresh tokens, or auth headers.
- Use the `contextual` server for tenant access instead of direct shell commands.
- Only involve the user when browser approval is required for login.
- Use docs tools before making detailed platform claims.
- Prefer targeted inspection and summaries over full JSON dumps.

## First Run

1. Call `setup_access`.
2. Call `config_list`.
3. If needed, call `config_current`.
4. If the local `contextual` tools are unavailable, explain that this runtime needs local MCP support for full tenant access.

## Docs Workflow

When the request depends on product or platform behavior:

1. Run `search` with a focused query.
2. Expand the best hits with `read_chunk_context`.
3. Use `read_section` for exact or fuzzy heading reads.
4. Use `read_page` only when section reads are not enough.
5. Answer with grounded path and heading references.

Use docs grounding for topics like:

- flow and node behavior
- event payload shape
- routing rules
- agent configuration
- object type behavior

## Config and Login Workflow

Start with:

`config_list` and `config_current`

If a config is missing and the user supplied a tenant identifier:

`config_add(configId, tenantId?)`

If auth is stale or missing, start login yourself.

Preferred login workflow:

`config_use(configId)` then `login_start(configId)` then `login_await(jobId, timeoutSeconds?)`

During login:

- Relay the verification code immediately.
- Tell the user to confirm the same code in the browser window and approve it there.
- Retry the blocked command after login completes.
- If waiting times out, keep the job id and check again with `login_status(jobId)`.

## Common Commands

Use these tools for tenant inspection:

- `types_list`
- `types_get`
- `records_list`
- `records_get`
- `records_query`
- `records_stats`

## Flow Work

Flows are records under `type: "flow"`.

Useful commands:

- `records_list(type: "flow")`
- `records_get(type: "flow", id: flowId)`

For flow edits:

1. Fetch the flow record.
2. Edit `node_red_data.flows` carefully.
3. Replace the flow with `records_replace(type: "flow", id: flowId, input: document)`.
4. Re-read the flow and verify the expected structure landed.

For record patches, use `records_patch` only when the change is naturally expressible as field operations.

For full replacements, prefer `records_replace`.

## Important Flow Heuristics

- For `flow-http`, HTTP In paths are root-relative to the flow subdomain. Use `/list`, not `/<flow-id>/list`.
- Treat event-trigger payload data as `msg.payload` unless docs clearly say otherwise.
- `log-tap` must have `outputs: 1` and a valid `level`.
- Wire `log-tap` inline in the chain, not as a dead-end fork.
- For new flows, preserve top-level `flows_cred: {}` and tab `env: []`.
- After edits, re-read the flow and verify the change actually landed.

## Output Expectations

- State the result first.
- Cite docs when claims depend on platform behavior.
- Summarize command results unless the user asked for raw output.
- If auth is stale, say that clearly and start login.
