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

Aliases: `records create` / `records import` -> `records add`; `records search` -> `records list`

Record input gotchas:
- `ctxl records add` expects **JSONL** (one JSON object per line). Pretty-printed JSON throws a parse error. Use `echo '{"id":"x","name":"y"}' > file.jsonl`.
- Flow records require a top-level `"id"` field — omitting it returns a 400 validation error. Choose a slug-style id (e.g. `"id": "my-flow"`).

### Correct empty flow shape

Flow records have a required internal structure. Getting this wrong produces a flow record that silently fails to open in the editor with no error message.

**Critical structural rules:**
- Tab `id` values, when present, must be **16-character lowercase hex strings** (e.g. `"aadb6bbe8c6cd017"`). A slug like `"tab1"` looks valid but breaks the editor.
- Every flow must include a `native-object-config` config node with `"id": "default-native-object-config"` — that id is the load-bearing reference target for consuming nodes (`query-native-object`, `get-native-object`, etc.).
- `flows_cred: {}` must be **inside `node_red_data`**, not at the top level.
- Do **not** include `_metaData` — the platform generates it automatically.

**What's load-bearing vs. convention on `native-object-config`:**
- `id` and `type` are load-bearing — `id` matches the consumer-side `nativeObjectConfig` reference; `type` makes it a config node.
- `name` is a **display label**, not a tenant resolver. By convention the dashboard sets it to the active tenant id (e.g. `"speedrun"`); you can do the same. The runtime ignores this field — orgId and tenant are resolved from the request context, not from this field.
- Empty credential / host fields (`host`, `orgId`, `clientId`, etc.) are **not required**. They're inert — present-as-empty-string and absent are equivalent. Set them only when overriding a default for a non-canonical scenario.

**Tab presence:** the dashboard's "new flow" UI does **not** emit a tab in the persisted record. The editor injects a default `Flow 1` tab on load and only persists it once a tab-touching change is saved. So a tab-less persisted record is valid; the example below includes one for clarity in cases where you're writing programmatically and want a known tab id present from the start.

**Single-tab empty flow** (reference shape, pretty-printed for readability — minify to one line before passing to `ctxl records add`):

```json
{
  "id": "my-flow",
  "name": "My Flow",
  "description": "Optional description",
  "node_red_data": {
    "flows": [
      {
        "id": "aadb6bbe8c6cd017",
        "type": "tab",
        "label": "Flow 1",
        "disabled": false,
        "info": "",
        "env": []
      },
      {
        "id": "default-native-object-config",
        "type": "native-object-config",
        "name": "<tenant-id>"
      }
    ],
    "flows_cred": {}
  }
}
```

**Two-tab flow with nodes** — nodes belong to a tab via the `z` field (must match the tab's hex `id`):

```json
{
  "id": "my-flow",
  "name": "My Flow",
  "node_red_data": {
    "flows": [
      {"id": "aadb6bbe8c6cd017", "type": "tab", "label": "Tab 1", "disabled": false, "info": "", "env": []},
      {"id": "8016b31394f01fbf", "type": "tab", "label": "Tab 2", "disabled": false, "info": "", "env": []},
      {"id": "default-native-object-config", "type": "native-object-config", "name": "<tenant-id>"},
      {"id": "e0a5c06a89566f9c", "type": "comment", "z": "aadb6bbe8c6cd017", "name": "Tab 1 comment", "info": "", "x": 180, "y": 100, "wires": []},
      {"id": "7916c3f31b6a7a1d", "type": "comment", "z": "8016b31394f01fbf", "name": "Tab 2 comment", "info": "", "x": 180, "y": 100, "wires": []}
    ],
    "flows_cred": {}
  }
}
```

To generate a valid 16-char hex tab ID, tell the user: "Generating a random node ID using Python's built-in `secrets` module — this is a standard random number generator, no credentials or sensitive data involved." Then run:
```bash
python3 -c "import secrets; print(secrets.token_hex(8))"
```

### Flow skeleton patterns

When creating a new flow, always include error handling from the start so the flow opens lint-clean. Use these skeletons based on flow type. Generate all node IDs upfront, write the JSON via Python heredoc (never inline in a shell flag), minify to JSONL before passing to `ctxl records add`.

**HTTP flow** — `http-in` → `function` (stub) → `http-response 200` + `catch` → `log-tap` → `http-response 500`:
```python
# python3 << 'PYEOF'
import json, secrets

tab     = secrets.token_hex(8)
h_in    = secrets.token_hex(8)
fn      = secrets.token_hex(8)
h_ok    = secrets.token_hex(8)
catch   = secrets.token_hex(8)
logtap  = secrets.token_hex(8)
h_err   = secrets.token_hex(8)

flow = {
  "id": "my-http-flow", "name": "My HTTP Flow",
  "node_red_data": {
    "flows": [
      {"id": tab,   "type": "tab",                    "label": "Main", "disabled": False, "info": "", "env": []},
      {"id": "default-native-object-config", "type": "native-object-config", "name": "<tenant-id>"},
      {"id": h_in,  "type": "http in",                "z": tab, "name": "GET /",       "url": "/",    "method": "get",   "x": 120, "y": 120, "wires": [[fn]]},
      {"id": fn,    "type": "function",               "z": tab, "name": "Handler",     "func": "// TODO: implement\nreturn msg;", "outputs": 1, "x": 360, "y": 120, "wires": [[h_ok]]},
      {"id": h_ok,  "type": "http response",          "z": tab, "name": "",            "statusCode": "200",  "x": 560, "y": 120, "wires": []},
      {"id": catch, "type": "catch",                  "z": tab, "name": "Catch",       "scope": None, "uncaught": True,  "x": 120, "y": 240, "wires": [[logtap]]},
      {"id": logtap,"type": "log-tap",                "z": tab, "name": "Log Error",   "level": "error", "outputProperty": "", "outputPropertyType": "full", "toConsole": False, "toSideBar": True, "outputs": 1, "x": 340, "y": 240, "wires": [[h_err]]},
      {"id": h_err, "type": "http response",          "z": tab, "name": "",            "statusCode": "500",  "x": 540, "y": 240, "wires": []}
    ],
    "flows_cred": {}
  }
}
with open('/tmp/my-http-flow.jsonl', 'w') as f:
    f.write(json.dumps(flow) + '\n')
print('Written')
# PYEOF
```

**Event flow** — `contextual-start` → `function` (stub) → `contextual-end` + `catch` → `log-tap` → `contextual-end`:
Replace `http-in`/`http-response` with `contextual-start`/`contextual-end`. The catch chain terminal is also `contextual-end` (not `http-response`).

**Scheduled flow** — same as event but entry node is `inject` with a cron schedule instead of `contextual-start`.

After creating, resolve the tenant ID via `ctxl config current --json` and tell the user to open the flow at the fully-resolved URL `https://<flow-id>.flow.<resolved-tenant-id>.my.contextual.io/.editor` so refinements can be made interactively through the Flow Editor rather than via CLI string manipulation. Never leave `<tenant-id>` as a literal placeholder for the user to fill in.

### Writing complex flow content

Never inline HTML, JavaScript, or multi-line strings in shell flags — shell expansion will corrupt the content. Always write to a file using a Python heredoc:

```bash
python3 << 'PYEOF'
import json

content = """your complex content here"""
# build and write JSON
PYEOF
```

The single-quoted `'PYEOF'` delimiter prevents all shell expansion inside the block.

## Types

- `ctxl types add --input-file FILE`
- `ctxl types get [URI] --type TYPE`
- `ctxl types list [--search FIELD=VALUE] [--exact-search FIELD=VALUE] [--from FIELD=VALUE] [--to FIELD=VALUE] [--order-by FIELD:desc] [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress]`
- `ctxl types replace [URI] --type TYPE --input-file FILE`

Aliases: `types create` / `types import` -> `types add`; `types search` -> `types list`

Type input gotchas:
- `ctxl types add` expects **JSONL** (one JSON object per line) — same as `ctxl records add`. Pretty-printed JSON throws `SyntaxError: Expected property name or '}'` from the local JSONL parser before any HTTP request is issued. Minify with `python3 -c "import json,sys; json.dump(json.load(sys.stdin), sys.stdout)"` or equivalent before passing via `--input-file`.

> `ctxl types list` returns custom object types only. To get the full schema of any type, custom or platform, use `ctxl types get native-object:<type-id>`. This is the authoritative source for enums, patterns, constraints, defaults, and relations.

## Platform Type IDs

These built-in types are managed via `ctxl records` commands:

| Type ID | Description |
|---------|-------------|
| `flow` | Flow definitions |
| `agent` | Agent definitions |
| `api-configuration` | Connections |
| `ai-route` | AI routing configuration |
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

## Object Type Schemas

### Envelope for `ctxl types add`

`ctxl types add` requires a record envelope that wraps the JSON schema. The schema documents what the data looks like; the envelope tells the platform how to register and display the type. Sending only the inner schema produces a 400 with missing-field errors for `display`, `defaultListStyle`, `objectType`, `features`.

Minimum envelope shape:

```json
{
  "id": "<type-id>",
  "type": "custom",
  "name": "<display name>",
  "pluralName": "<plural display name>",
  "description": "<description>",
  "display": "default",
  "defaultListStyle": "table",
  "objectType": "internal",
  "features": {
    "auditTrail": { "enabled": false },
    "version": { "enabled": false }
  },
  "schema": { "...the JSON Schema body — see rules below..." }
}
```

Allowed values for the four envelope keys most commonly missed:

| Field | Allowed values | Notes |
|---|---|---|
| `display` | `"default"` \| `"pinned"` \| `"setting"` \| `"component"` \| `"security"` | How the type appears in the platform UI list/picker. `"default"` for typical custom types. |
| `defaultListStyle` | `"table"` \| `"card"` | Default list rendering when browsing records. |
| `objectType` | `"internal"` (native-object — typical) \| `"external"` (platform-managed external source) | Who owns the data lifecycle. Use `"internal"` unless you specifically need an external-managed type. |
| `features.auditTrail.enabled` / `features.version.enabled` | boolean (typically `false`) | Feature toggles for audit trail and versioning. |

The `schema` field then carries the JSON Schema described below.

### Inner schema rules

When creating types with `ctxl types add`, follow these conventions for the `schema` field:

- Object type IDs must use only lowercase letters, numbers, and dashes
- All schemas need a top-level `primaryKey` property naming the primary key field
- **`primaryKey` is immutable once deployed** — only the default (unsaved) schema may have its primaryKey changed
- Default primary key: auto-generated UUID — do not mark as `required`
  ```json
  "id": { "type": "string", "generate": { "type": "uuid", "format": "v4" } }
  ```
- Do not mark any auto-generated fields (UUIDs, timestamps) as `required` — they don't exist at validation time
- Every record automatically gets a `_metaData` envelope (`createdAt`, `updatedAt`, `hash`, `id`, `schema`, `type`, `version`, `secrets`) from the platform. **Never define these fields in a schema.**
- Relations are always a top-level schema property, defined on the child pointing to the parent:
  ```json
  "relations": {
    "customer": {
      "typeRef": "native-object:customer/id",
      "localField": "customerId",
      "displayField": "name"
    }
  }
  ```
- Use `description` or `$comment` for documentation — not JS-style `//` comments
- Designate sensitive strings with `"secret": true` to encrypt in the key store

## URL Patterns

| Context | Pattern |
|---------|---------|
| Flow Editor | `https://{flowId}.flow.{tenantId}.my.contextual.io/{path}` |
| Agent-bound service | `https://{agentId}.service.{tenantId}.my.contextual.io/{path}` |

For non-prod silos, insert the silo name: `{tenantId}.my.{silo}.contextual.io`.

## Global Flag

- `-C, --config-id CONFIG-ID` can be added to tenant commands when needed.

## File Inputs

- `--input-file -` reads JSON from stdin.
- `--query-file -` reads query JSON from stdin.

## Disallowed In This Skill

- `ctxl config delete`
- `ctxl records delete`, `ctxl records remove`, `ctxl records rm`
- `ctxl types delete`, `ctxl types remove`, `ctxl types rm`
