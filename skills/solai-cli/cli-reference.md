# Contextual CLI Reference

Use this as the compact command map for `ctxl`. It tracks the current CLI README while limiting the skill to non-destructive operations.

## Config

- `ctxl config list --json`
- `ctxl config current --json`
- `ctxl config get [CONFIG-ID] --json`
- `ctxl config add CONFIG-ID [--tenant-id TENANT-ID]`
- `ctxl config use CONFIG-ID`
- `ctxl config login`

## Records

- `ctxl records add [URI] --type TYPE --input-file FILE`
- `ctxl records get [URI] --type TYPE --id ID`
- `ctxl records list [URI] --type TYPE [--search FIELD=VALUE] [--exact-search FIELD=VALUE] [--from FIELD=VALUE] [--to FIELD=VALUE] [--order-by FIELD:desc] [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress]`
- `ctxl records query [URI] --type TYPE --query-file FILE [--order-by FIELD:desc] [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress]`
- `ctxl records patch [URI] --type TYPE --id ID [--set FIELD=VALUE] [--replace FIELD=VALUE] [--remove FIELD] [--add FIELD=VALUE] [--increment FIELD=DELTA]`
- `ctxl records replace [URI] --type TYPE --id ID --input-file FILE`
- `ctxl records stats [URI] --type TYPE --id ID`

Aliases documented by the CLI:

- `ctxl records create` and `ctxl records import` -> same behavior as `records add`
- `ctxl records search` -> same behavior as `records list`

## Types

- `ctxl types add --input-file FILE`
- `ctxl types get [URI] --type TYPE`
- `ctxl types list [--search FIELD=VALUE] [--exact-search FIELD=VALUE] [--from FIELD=VALUE] [--to FIELD=VALUE] [--order-by FIELD:desc] [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress]`
- `ctxl types replace [URI] --type TYPE --input-file FILE`

Aliases: `types create` / `types import` -> `types add`; `types search` -> `types list`

> `ctxl types list` returns custom object types only. To get the full schema of any type, custom or platform, use `ctxl types get native-object:<type-id>`. This is the authoritative source for enums, patterns, constraints, defaults, and relations.

## Platform Type IDs

These built-in types are managed via `ctxl records` commands:

| Type ID | Description |
|---------|-------------|
| `flow` | Flow definitions |
| `agent` | Agent definitions |
| `api-configuration` | Connections |
| `ai-route` | AI routing configuration |
| `topics` | Topic definitions |
| `authorization-code-app` | OAuth app config |
| `jwks-configuration` | JWKS / key config |

Get the full schema for any platform type before creating or replacing records:

```bash
ctxl types get native-object:agent --config-id <config-id>
ctxl types get native-object:ai-route --config-id <config-id>
```

Apply the same diff, confirm, and replace discipline as flow work before any write.

## Agent Records

Agents are records under `--type agent`. Three agent types exist: `flow-http`, `flow-topic`, `flow-cron`.

Key gotchas:
- `image` is a runtime version string, not a Docker image.
- `size` is a UUID, not a human label.
- `flow` must be pinned to a specific version using the `#N` suffix.
- `configName` is auto-generated on creation and should not be supplied.

Common size UUIDs:
- Small: `8836d51b-51f0-4417-b799-b8fb692e6a1b`
- Medium: `97c7d433-7729-4800-ac80-086ade746541`
- Large: `5ec9113a-0f82-479b-b465-4a7459ce53fc`
- X-Large: `37a7f0f5-9afd-48df-8d4b-4b6fa61f8874`
- XX-Large: `def7d31e-cc01-4605-95d0-19765d176455`

### `flow-http`

```json
{
  "name": "my-agent",
  "type": "flow-http",
  "displayName": "My Agent",
  "description": "...",
  "flow": "my-flow#6",
  "image": "5.10.6",
  "size": "8836d51b-51f0-4417-b799-b8fb692e6a1b",
  "livenessTimeoutSeconds": 50,
  "scaleType": "cpu",
  "minReplicas": 1,
  "maxReplicas": 1,
  "targetCpu": 80
}
```

### `flow-topic`

```json
{
  "name": "my-agent",
  "type": "flow-topic",
  "displayName": "My Agent",
  "description": "...",
  "flow": "my-flow#6",
  "entryPoint": "<entry-node-id>",
  "image": "5.10.6",
  "size": "8836d51b-51f0-4417-b799-b8fb692e6a1b",
  "livenessTimeoutSeconds": 50,
  "scaleType": "lag",
  "minReplicas": 1,
  "maxReplicas": 1,
  "pollingInterval": 60,
  "cooldownPeriod": 60,
  "lagThreshold": 25
}
```

### `flow-cron`

```json
{
  "name": "my-agent",
  "type": "flow-cron",
  "displayName": "My Agent",
  "description": "...",
  "flow": "my-flow#6",
  "entryPoint": "<entry-node-id>",
  "schedule": "* * * * *",
  "image": "5.10.6",
  "size": "8836d51b-51f0-4417-b799-b8fb692e6a1b",
  "livenessTimeoutSeconds": 50
}
```

## Flow Work

Flows are records under `--type flow`:

```bash
ctxl records list --type flow --config-id <config-id>
ctxl records get --type flow --id <flow-id> --config-id <config-id>
```

After edits, re-read the flow and verify the change actually landed.

## MCP

- `ctxl mcp serve [INTERFACE] [-f FLOW-ID] [-p PORT] [-t] [-V] [-C CONFIG-ID]`

Default interface is `flow-editor`. Default port is `5051`.

Flags:

- `-f, --flow FLOW-ID` — pre-filter sessions to a specific flow
- `-p, --port PORT` — local HTTP port (default: 5051)
- `-t, --tool-prefix` — prefix all MCP tool names with `ctxl_`
- `-V, --verbose` — emit verbose MCP runtime diagnostics

Built-in MCP tools exposed by the server:

- `list_sessions` — discover flows with active browser sessions
- `info` — return runtime state (tenant, interface, connections, errors)

## Global Flag

- `-C, --config-id CONFIG-ID` can be added to tenant commands when needed.

## File Inputs

- `--input-file -` reads JSON from stdin.
- `--query-file -` reads query JSON from stdin.

## Disallowed In This Skill

- `ctxl config delete`
- `ctxl records delete`, `ctxl records remove`, `ctxl records rm`
- `ctxl types delete`, `ctxl types remove`, `ctxl types rm`
