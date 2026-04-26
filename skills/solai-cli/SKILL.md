---
name: solai-cli
description: Use the local Contextual CLI from shell-capable agents to inspect tenants, analyze flows, and apply safe edits. Use only in runtimes with local shell access.
argument-hint: "[task]"
---

# SolAI CLI

This skill has two layers:

- **Reference and guidance** — command patterns, schema rules, flow heuristics, type IDs, write discipline. Available in any runtime, useful for planning, understanding, and answering questions even without executing anything.
- **Execution** — running `ctxl` commands against a live tenant. Requires local shell access (Claude Code, Claude Cowork, OpenCode, Codex, or similar).

If shell access is unavailable, make clear that commands cannot be executed — but continue to use this skill's reference material to answer questions, explain concepts, or help the user plan what they would run.

## Setup Check

On first invocation each session, check for plugin updates. Before running, tell the user:

> Checking for Solution AI Connect plugin updates — you may be prompted to allow this command.

Then run:

```bash
claude plugin update ctxl@contextual-io
```

The raw command output uses `ctxl` as the marketplace plugin identifier, but `ctxl` is also the name of the separately-versioned Contextual CLI. To avoid confusion, **always restate the result in "Solution AI Connect plugin" terms** rather than letting the raw output stand:

- If the output contains "updated from X to Y": tell the user "Solution AI Connect plugin updated from X to Y — restart Claude to load the new version, then re-invoke this skill."
- If the output says "already at the latest version (X)": tell the user "Solution AI Connect plugin is already at the latest version (X)." Then proceed.

Only run this check once per session.

## Installation & Setup

The Contextual CLI (`ctxl`) must be installed globally before using this skill. Requires Node.js 18.0.0 or later.

Install via npm (or your preferred Node package manager — `pnpm`, `yarn`, `bun`, etc.):

```bash
npm install -g @contextual-io/cli
```

If the user has a preferred package manager or install method, defer to their choice. Visit [npm/@contextual-io/cli](https://www.npmjs.com/package/@contextual-io/cli) for the latest version and release notes.

## Runtime Checks

1. Confirm the environment can run shell commands.
2. Run `command -v ctxl && ctxl --version`.
3. If `ctxl` is missing, tell the user it must already be installed locally before this skill can run.
4. Read [cli-reference.md](cli-reference.md) now. Use it as the authoritative command reference for the rest of this session — do not construct `ctxl` commands from memory.

## Supporting Files

Two helper scripts are bundled with this skill. When invoking them, tell the user what is happening before running so the path doesn't appear alarming:

- **`contextual_login.py`** — orchestrates browser-based login for a config. When invoking, tell the user: "Starting browser login for `<config-id>` — a verification code will appear shortly for you to confirm in your browser."
  ```
  ${CLAUDE_SKILL_DIR}/scripts/contextual_login.py --state-dir "${CLAUDE_PLUGIN_DATA:-${CLAUDE_SKILL_DIR}/.local}/login-jobs"
  ```

- **`json_diff.py`** — previews the difference between the current and proposed version of a flow or record before any write is made. When invoking, tell the user: "Generating a diff so you can review what will change before anything is written."
  ```
  ${CLAUDE_SKILL_DIR}/scripts/json_diff.py <current-file> <proposed-file>
  ```

## Hard Rules

- Never read raw `ctxl` config or credential files directly — always use `ctxl` CLI commands to interact with configs and credentials.
- Never call Contextual APIs directly with `curl`, `fetch`, custom headers, or handwritten HTTP requests.
- Never expose or summarize bearer tokens, refresh tokens, or auth headers.
- Do not use `ctxl config delete`, `ctxl records delete/remove/rm`, or `ctxl types delete/remove/rm`.
- Before any `replace` or `patch` operation, show a diff or the exact planned patch flags and ask for explicit confirmation.
- Once you know the target config, prefer `--config-id <config-id>` on tenant commands even if you already ran `ctxl config use`.
- Use `solai-knowledge` before making detailed platform claims about flows, nodes, routing, runtime behavior, payload shapes, or implementation patterns.
- Before starting `ctxl mcp serve`, verify the config is logged in. The server rejects expired or missing tokens at startup.

## Config Workflow

Start with:

```bash
ctxl config list --json
ctxl config current --json
```

Config commands (`config list`, `config current`, `config get`) support `--json` for structured JSON output instead of the default table format. Records and types commands already output JSON by default.

If a config is missing and the user supplied a tenant identifier:

```bash
ctxl config add <config-id> --tenant-id <tenant-id>
```

Select the config before tenant work:

```bash
ctxl config use <config-id>
```

## Automatic Auth Recovery

If a tenant command reports that the config is not logged in, unauthorized, expired, or otherwise needs auth:

Tell the user: "Your session isn't logged in or has expired — starting browser login for `<config-id>` now."

1. Start login for that same config:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/contextual_login.py" --state-dir "${CLAUDE_PLUGIN_DATA:-${CLAUDE_SKILL_DIR}/.local}/login-jobs" start <config-id>
```

2. Relay the verification code immediately.
3. Tell the user to confirm that same code in the browser window and approve it there.
4. Wait for completion:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/contextual_login.py" --state-dir "${CLAUDE_PLUGIN_DATA:-${CLAUDE_SKILL_DIR}/.local}/login-jobs" await <job-id> --timeout-seconds 90
```

5. If waiting times out, check again with:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/contextual_login.py" --state-dir "${CLAUDE_PLUGIN_DATA:-${CLAUDE_SKILL_DIR}/.local}/login-jobs" status <job-id>
```

6. Retry the original blocked command after login succeeds.

Make sure the retried command includes `--config-id <config-id>`.

Do not ask the user to manually invoke another skill during normal CLI work.

## Everyday CLI Work

Use `cli-reference.md` for exact command forms.

Type discovery follows two tracks:

- reserved admin component types: do not rely on `ctxl types list` to discover these. For normal callers, type listing is effectively limited to tenant-defined custom object types. Treat this reserved set as known IDs:
  - `agent`
  - `flow`
  - `api-configuration` (known to users as "Connections")
  - `ai-route`
  - `jwks-configuration`
  - `authorization-code-app`
- tenant-defined data object types: use `ctxl types list` to discover these, then `ctxl types get` to inspect the chosen type.

When inspecting a tenant, choose the track explicitly:

1. If the user is asking about flows, agents, connections, AI routes, JWKS configs, or authz code apps, start from the reserved component map.
2. If the user is asking about tenant business data, schemas, records, triggers, actions, or custom objects, start with `ctxl types list`.
3. Once you know the type ID, use `ctxl types get native-object:<type-id> --config-id <config-id>` to retrieve the full JSON schema — enums, patterns, constraints, defaults, and relations. This is the authoritative source for field shapes before any create or replace operation. Then use `ctxl records ... --type <type-id> --config-id <config-id>`.

Common reads:

- configs: `ctxl config list --json`, `ctxl config current --json`, `ctxl config get <config-id> --json`
- types: `ctxl types list --config-id <config-id>`, `ctxl types get --type <type-id> --config-id <config-id>`
- records: `ctxl records list --type <type-id> --config-id <config-id>`, `ctxl records get --type <type-id> --id <id> --config-id <config-id>`, `ctxl records query native-object:<type-id> --query-file <file> --config-id <config-id>`, `ctxl records stats --type <type-id> --id <id> --config-id <config-id>`

Reserved admin component examples:

```bash
ctxl records list --type flow --config-id <config-id>
ctxl records list --type agent --config-id <config-id>
ctxl records list --type ai-route --config-id <config-id>
ctxl records list --type api-configuration --config-id <config-id>
ctxl records list --type jwks-configuration --config-id <config-id>
ctxl records list --type authorization-code-app --config-id <config-id>
```

**When answering general questions about a tenant** ("what's in this tenant?", "what does this tenant do?", "what solutions are built here?"), fetch all six reserved component types in parallel alongside `ctxl types list` for custom object types. Empty results are fine — they complete the picture. Do not skip any component type because it seems unlikely to have content.

Tenant-defined data object example:

```bash
ctxl types list --config-id <config-id>
ctxl types get --type <custom-type-id> --config-id <config-id>
ctxl records list --type <custom-type-id> --config-id <config-id>
```

For writes:

- create with `ctxl types add` or `ctxl records add`
- patch with `ctxl records patch`
- replace with `ctxl types replace` or `ctxl records replace`

## Querying Records

`ctxl records query` accepts a JSON file containing MongoDB-style query predicates. Fields are prefixed with `$.` and operators use the `$` prefix.

**Important:** `records query` requires the `native-object:<type-id>` URI positional argument, not `--type`.

### Stdin piping

Pass a query inline via stdin (the default `--query-file` is `-`):

```bash
echo '{"$.status": "active"}' | ctxl records query native-object:<type-id> --config-id <config-id>
```

### Query file

Or write the query to a file:

```bash
ctxl records query native-object:<type-id> --query-file query.json --config-id <config-id>
```

### Supported operators

The query format follows [MongoDB query predicates](https://www.mongodb.com/docs/manual/reference/mql/query-predicates/). Common operators:

- Exact match: `{"$.field": "value"}`
- `$in`: `{"$.field": {"$in": ["val1", "val2"]}}`
- `$gt`, `$gte`, `$lt`, `$lte`: `{"$.balance": {"$gt": 100}}`
- `$and`: `{"$and": [{"$.field1": "a"}, {"$.field2": {"$lt": 0}}]}`
- `$or`: `{"$or": [{"$.status": "active"}, {"$.status": "pending"}]}`
- `$exists`: `{"$.field": {"$exists": true}}`

Query commands support the same pagination flags as `records list` (`--page-size`, `--page-token`, `--include-total`, `--export`, `--progress`).

## Pagination

For large result sets, use `--page-size` and `--page-token` to paginate:

```bash
ctxl records list --type <type-id> --page-size 50 --config-id <config-id>
```

To stream all records as JSONL, use `--export` (optionally with `--progress` for status output):

```bash
ctxl records list --type <type-id> --export --progress --config-id <config-id>
```

Maximum page size is 250. The CLI handles page-token chaining automatically during export.

## Rate Limiting

The CLI has no built-in retry or rate-limit handling. If the platform returns a 429 or 5xx error, the command fails immediately. When running multiple commands in sequence, pace requests and avoid tight loops. If a command fails with a transient error, wait a few seconds before retrying manually.

Important write gotchas:

- `ctxl records add` expects JSONL (one JSON object per line), not pretty-printed JSON.
- `primaryKey` on an Object Type is immutable once deployed — get it right before the first `ctxl types add`.
- Every record gets a `_metaData` envelope from the platform automatically. Never include `createdAt`, `updatedAt`, `hash`, `version`, or `secrets` in a schema.

## Flow Work

Flows are records under `--type flow`.

Useful commands:

```bash
ctxl records list --type flow --config-id <config-id>
ctxl records get --type flow --id <flow-id> --config-id <config-id>
```

When summarizing a flow, inspect `node_red_data.flows` and report:

- tabs
- entry points
- main execution chains
- major branches
- referenced record types

For creating new flows:

**Always use the CLI-stub + flow editor handoff pattern.** Never try to write complex node content (HTML, JavaScript, multi-line logic) through the CLI — shell escaping across Python/JSON/JS layers is error-prone and unreliable.

**Step 1 — Clarify flow type before generating anything:**
Ask the user: "Is this an HTTP flow (serves requests), an event flow (triggered by object-type events or agents), or a scheduled flow (cron)?" The skeleton structure differs by type.

**Step 2 — Create a minimal but complete skeleton via CLI:**

Generate hex IDs for all nodes (see cli-reference.md). Build the skeleton with:
- The structural nodes (entry, stub function, terminal)
- Full error handling chain from the start — a flow that opens lint-clean is the goal

| Flow type | Skeleton |
|-----------|---------|
| HTTP | `http-in` → `function` (stub) → `http-response 200` + `catch` (uncaught) → `log-tap` (error/full) → `http-response 500` |
| Event | `contextual-start` → `function` (stub) → `contextual-end` + `catch` (uncaught) → `log-tap` (error/full) → `contextual-end` |
| Scheduled | `inject` (cron) → `function` (stub) → `contextual-end` + `catch` (uncaught) → `log-tap` (error/full) → `contextual-end` |

Stub function node content: `// TODO: implement\nreturn msg;`

Always write the flow JSON to a file using a Python heredoc (`<< 'PYEOF'`) — never inline complex content in a shell command. See cli-reference.md for the correct file-based approach.

**Step 3 — Hand off to the flow editor:**

After creating the flow, tell the user: "The flow skeleton is created with error handling in place — open it in your browser at `https://<flow-id>.flow.<tenant-id>.my.contextual.io/.editor` and I can build out the logic interactively through the Flow Editor, which is much cleaner for complex node content."

---

For editing existing flows:

**Preferred path: Flow Editor Session via MCP tunnel.** Before editing a flow via CLI:

1. Check whether `mcp__ctxl-flow-editor__*` tools appear in the deferred tool list — if they do, the MCP server is running (Ctxl Tool or manual `ctxl mcp serve`).
2. If the tools are present, call `list_sessions` to check for active browser sessions. **Tool availability alone does not mean a session exists** — a session only exists when the user has the flow open in their browser.
3. Only if `list_sessions` returns one or more sessions, recommend the live editor path and offer to switch to `solai-flow-editor`. Reasons to prefer it:
   - Changes are staged live and visible before the flow is saved or versioned
   - Node-level granularity — no need to touch the full flow JSON
   - Safer for large or complex flows where a full-record replace risks corrupting structure

   Tell the user: "I can see a Flow Editor session is available — I can make these changes live in the editor so you can review them before saving. Would you like to do that, or continue via CLI?"

4. If no sessions are returned, proceed with the CLI path below. Optionally note that opening the flow in a browser would enable the live editing experience.

If the tools are not available at all, proceed directly with the CLI path and optionally note that opening the Ctxl Tool would enable live editing.

**CLI path (when MCP tunnel is unavailable or user prefers it):**

1. Fetch the current flow to a temp file.
2. Create the proposed edited file using Python — never inline complex content in shell flags.
3. Preview the diff:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/json_diff.py" <current-file> <proposed-file>
```

4. Show the diff to the user and ask for explicit confirmation.
5. Replace only after confirmation:

```bash
ctxl records replace --type flow --id <flow-id> --input-file <proposed-file> --config-id <config-id>
```

6. Re-read the flow and verify the expected structure landed.

For record patches, show the exact `ctxl records patch ...` flags before confirmation.

## Important Flow Heuristics

- For `flow-http`, HTTP In paths are root-relative to the flow subdomain. Use `/list`, not `/<flow-id>/list`.
- Treat event-trigger payload data as `msg.payload` unless docs clearly say otherwise.
- `log-tap` must have `outputs: 1` and a valid `level`.
- Wire `log-tap` inline in the chain, not as a dead-end fork.
- `flows_cred: {}` must be inside `node_red_data`, not at the top level of the flow record.
- Tab objects in existing flows typically include `env: []` — preserve it when editing; omitting it may cause issues in the editor.
- After edits, re-read the flow and verify the change actually landed.

## MCP Server

`ctxl mcp serve` starts a local MCP HTTP server that bridges to live SolutionAI browser sessions. It binds to `http://localhost:5051/` by default and exposes SolutionAI tools as standard MCP tools that AI agents can call.

For real-time flow interaction via AI agents, the MCP server is the preferred path over manual `records get` / `records replace` round-trips on flow records.

### When to use

Use the MCP server when the user wants an AI agent (Claude, Cursor, etc.) to interact with SolutionAI flows in real time — editing nodes, reading flow state, or calling flow-scoped tools through the MCP protocol.

### Starting the server

The active config must be logged in before starting. If auth is needed, follow the Automatic Auth Recovery flow first.

```bash
ctxl mcp serve --config-id <config-id>
```

With a specific flow pre-selected:

```bash
ctxl mcp serve --flow <flow-id> --config-id <config-id>
```

With tool name prefixing (adds `ctxl_` prefix to all tool names):

```bash
ctxl mcp serve --tool-prefix --config-id <config-id>
```

With verbose diagnostics:

```bash
ctxl mcp serve -V --config-id <config-id>
```

Custom port:

```bash
ctxl mcp serve --port 8080 --config-id <config-id>
```

### Built-in MCP tools

The server always exposes two meta-tools:

- `list_sessions` — lists flows with available browser sessions. A browser must be open on the flow editor for a flow to appear. Returns flow IDs and names. Accepts an optional `flowId` filter.
- `info` — returns runtime state: tenant, interface type, connected flows, and any recent errors.

All other tools are dynamically loaded from SolutionAI's tool manifest for the `flow-editor` interface (the default).

### Session model

- `list_sessions` is scoped to the current user and current tenant (from the active config). Other users' browser sessions never appear, even on a shared tenant.
- The user must have the target flow open in their own browser for it to appear. If the desired flow is missing, direct the user to open it themselves — do not attempt to open it programmatically. Developers may have multiple browser profiles, windows, or tenant sessions active; only the user knows which one is the right context for this work.
- **Connection handshake**: The first tool call targeting a flow triggers an "MCP requesting access" dialog in the **SolutionAI tab of the Flow Editor's right sidebar**. The user must click **Accept** for the tunnel to be established. Always prompt the user to watch for and accept this dialog before expecting tool calls to succeed. If they deny, the call fails and they must re-trigger it.
- If the user has the same flow open in multiple browser tabs, all tabs receive the accept dialog simultaneously — the first to accept wins the tunnel.
- Each tool call requires a `flowId`. If `--flow` was passed at startup, that flow is used globally. Otherwise the agent must pass `flowId` with each call, or call `list_sessions` first to discover available flows.
- The server auto-binds to flows on first tool call and caches connections for subsequent calls to the same flow.
- The tunnel runs through the user's browser, so all actions are performed from that user's point of view.

### Hard rules for MCP

- **Never run `ctxl mcp serve` yourself.** The server must be started by the user in their own persistent terminal — any process the agent starts via shell is ephemeral and dies immediately. It cannot serve MCP tools.
- **If `mcp__ctxl-flow-editor__*` tools appear in the deferred tool list, the server is already running.** Do not start another one. Load the tool schemas and call `info`/`list_sessions` to verify the connection. If the tools are not in the deferred list, tell the user to run `ctxl mcp serve --config-id <config-id>` in their own terminal.
- Do not start the MCP server if the user has not logged in.
- The server locks to the active config's tenant and silo at startup. Switching configs with `ctxl config use` while the server is running has no effect. If the user needs to target a different tenant, the server must be stopped and restarted with the new config.
- Do not change the default port unless the user requests it or port 5051 is occupied.
- The MCP server runs as a foreground process. If the user needs CLI commands alongside it, they need a separate terminal or the server must be backgrounded.
- Do not attempt to call MCP tools via curl or HTTP directly — they are meant for MCP-compatible clients.

## Output Expectations

- State the result first.
- Summarize command results unless the user explicitly asked for raw output.
- When auth recovery happens, continue the original task after retry.
- For writes, include the diff or exact patch plan before asking for confirmation.
- After any confirmed write, verify and report what changed.
