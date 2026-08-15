---
name: solai-flow-editor
description: Edit live Contextual flows in the Flow Editor — add, change, move, wire, delete, rename, configure, group, copy, or validate nodes / wires / properties / code in a flow open in the user's browser. Also the source-of-truth for node-level behavior, configuration, and authoring patterns — function-node logging (`await logger.*`), loop wiring, Native Object node TypedInput patterns, `http-response` status precedence, etc. (see `node-reference.md`). Required before any `mcp__ctxl-flow-editor__*` call other than `info`/`list_sessions` orientation. Use AFTER planning; do NOT plan architecture here — use plan-flow first.
---

# SolAI Flow Editor

Use this skill to interact with live Contextual flows through the `ctxl-flow-editor` MCP server.

## When to invoke

Invoke this skill **before** any `mcp__ctxl-flow-editor__*` tool call that inspects or modifies a flow. The only exempt orientation tools are `info` and `list_sessions` (used to answer "is the server up / which flows are open?"). Everything else is gated, including reads.

**Trigger phrases** — load the skill as soon as user intent matches any of these against a live flow:
- **Edit:** add, change, update, move, wire, connect, delete, rename, configure, set, fix, group, copy a node / wire / property / code / tab
- **Inspect:** look at, check, read, validate, search flow contents
- **Test:** create `inject` or `contextual-test` nodes, set up test data

The trigger is **intent to work on a flow**, not the literal word "edit". A request like *"add some comment nodes to my hello world flow"* qualifies — load the skill before the first `editor_state` / `flow_read` / `type_info` / `import` call.

**Why this matters:** loading this skill brings node-reference.md, sequencing rules (especially intra-batch placeholder IDs and cross-batch wiring — see Sequencing rules step 3), and the silent-failure catalogue into context. Skipping it produces failures the MCP server does not surface clearly: dropped cross-batch wires, intra-batch placeholder-ID collisions that silently drop a node, invalid `id` types (numeric, empty string) that silently drop a node, `node_update` wire-mutations that report success but do nothing, wrong node types, broken `tray_open`→`tray_read` sequences, malformed `editable-list` defaults.

## Setup Check

The Flow Editor MCP connection is typically provided by the **Ctxl Tool desktop app** (macOS and Windows): a local MCP proxy on `localhost:5051` fronting tenant-specific MCP servers the user starts and stops in the app UI. The app is also where users see and manage their CLI configs. Users without the app run the server from their own terminal instead (`ctxl mcp serve --config-id <config-id>`). Either way, the server must already be running — **never start it yourself.** Any process started via shell from this context is ephemeral and dies immediately.

**Tenant-prefixed tools.** Behind the app's proxy, each running tenant server contributes tools named `mcp__ctxl-flow-editor__<tenant>__<tool>`. Match the prefix to the tenant you intend to work in. The tool list refreshes automatically as tenant servers start and stop — tools appearing or disappearing mid-session is server lifecycle, not an error. A call against a stopped tenant's prefix fails with `unknown tool`; re-orient via `list_sessions` on a live prefix instead of retrying.

**If `mcp__ctxl-flow-editor__*` tools appear in the deferred tool list, the MCP server is running** — but this does not mean any flow sessions are active. Load the tool schemas and call `list_sessions` to check for live browser connections. Only proceed with flow editing if `list_sessions` returns sessions. If it returns none, the user needs to open the target flow in their browser first.

**If the expected tenant's tools are not in the tool list**, walk the recovery ladder in order:

1. Ask the user to check the Ctxl Tool app: is that tenant's MCP server running? Starting it there broadcasts the tools into the session.
2. If the server is running but its tools are missing or stale, ask the user to run `/mcp`, select the Flow Editor MCP (`localhost:5051`), and **reconnect** — this reliably refreshes the toolset.
3. Environments without the app: the user runs `ctxl mcp serve --config-id <config-id>` in their own terminal.

Ctxl Tool installs from [build-artifacts.contextual.io](https://build-artifacts.contextual.io) (macOS alternative: `brew install --cask contextualio/tap/ctxl-tool`).

**Read [node-reference.md](node-reference.md) now — this is not optional.** It contains node-specific foot-gun warnings that `type_info` does not surface: e.g. `query-native-object`'s `query: ""` is a guaranteed runtime `JSON.parse("")` throw despite being the registry default (canonical match-all form is `"{}"`); the loop node has three silent setup-gates that fail to a port-0-only firing; `http-response`'s configured `statusCode` silently overrides `msg.statusCode`; Native Object nodes have TypedInput companion-field pairs that runtime Zod-rejects when absent even though `type_info` marks them `required: false`. **`type_info` reports registry defaults; `node-reference.md` warns you when those defaults will throw at runtime.** Skipping it ships silent foot-guns the runtime catches but `type_info` does not.

## What this MCP server is

The `ctxl-flow-editor` MCP server bridges this AI session to an active browser-based Contextual Flow Editor session. Changes made through these tools are reflected live in the browser editor — you are not editing a file.

A flow session only exists when the flow is open in a browser tab. `list_sessions` reflects live browser connections. If a flow is not listed, the user needs to open it in their browser before you can work on it. The correct URL to open the Flow Editor is `https://<flow-id>.flow.<tenant-id>.my.contextual.io/.editor` — without `/.editor`, HTTP-based flows will serve their root endpoint instead of opening the editor. **Always resolve the tenant ID** by running `ctxl config current --json` (via Bash) before giving the URL to the user — never hand them a URL with `<tenant-id>` as a literal placeholder.

## Terminology

Use these terms consistently. Never use internal engine terminology.

| Term | Meaning |
|------|---------|
| **Flow** | The entire logical unit being edited — all tabs, subflows, config nodes, and global state together. When a user says "my flow" they mean the whole thing. |
| **Tab** | A single canvas page inside the Flow Editor. The editor has a row of tabs along the top. Each tab contains its own nodes, wires, and groups. In tool parameters, `tabId` refers to a tab or subflow ID. |
| **Subflow** | A reusable component with internal nodes. Appears in the palette and can be instanced onto any tab. Opens as its own tab when editing. |
| **Subflow instance** | A single node placed on a tab that references a subflow. Its type is `subflow:<definition-id>`. |
| **Config node** | A shared configuration node not tied to any specific tab (no `z` property). Referenced by other nodes. |
| **Active tab** | The tab currently visible in the editor. |

## Platform framing

This is a proprietary platform. Do not apply assumptions from public knowledge of other flow-based tools. Source-of-truth precedence when uncertain about node behaviour or platform conventions:

1. **`type_info`** (if a live session is active) — the connected editor's authoritative definition for the specific node type
2. **`node-reference.md` and this `SKILL.md`** — kept current with empirically-verified build-time reality via ongoing verification against the live platform; canonical for node-level behavior, authoring patterns, and sequencing rules
3. **`solai-knowledge`** — for platform/runtime behavior not in (1) or (2)

For genuinely cross-cutting queries, run multiple sources in parallel — the answers are complementary.

## Available tools (by category)

- **Read state**: `editor_state`, `flow_read`, `search`, `validate`, `type_info`, `info`, `logger_messages`, `result_read`
- **Navigate**: `navigate`, `select`
- **Write**: `import`, `wire`, `node_update`, `delete`, `move`, `copy`, `group` — note: `delete` requires `useSelectionAction` as a **boolean**, not a string
- **Tray** (node properties panel): `tray_open`, `tray_read`, `tray_write`, `tray_commit`
- **Code** (function/template node editors): `code_read`, `code_write`, `code_edit`, `code_grep`, `code_patch`

## Tool argument discipline

**Inspect the tool's parameter schema before its first use in a session — never construct a call from memory or from another session's shape.** The schemas carry the type unions, required lists, and enum values that make calls land on the first try; guessing produces silent misbehavior as often as hard errors.

Many tools in this MCP surface declare parameters as required-but-nullable (`["object","null"]`, `["array","null"]`, `["integer","null"]` type unions). **When a parameter's value would be null, omit the parameter — do not pass a literal `null`.** Tool-call harnesses that encode arguments as text deliver a bare `null` as the string `"null"`: object-, array-, and number-typed parameters reject it with `Invalid input: expected <type>, received string`, while string-typed parameters silently accept `"null"` as a real string value. Omission validates where a null placeholder errors. On any `Invalid tool arguments` error, re-read the failing parameter's type union and fix by omission — do not resubmit the same shape with cosmetic variations.

## Important behaviors

- **`import` is placement only — never include cross-batch wires:** Any wire targeting a node outside the imported batch is silently dropped with no error, always, regardless of whether the target exists. Do not include cross-batch wires in import payloads and "fix them if they drop" — they will always drop. Always wire after import using the `wire` tool. Intra-batch wires (both ends in the same import call) are the only wires that survive import.
- **Navigation side-effects:** Many tools (`import`, `node_update`, `navigate`, `code_edit`, etc.) navigate the user's viewport, switch tabs, and change selection in real-time. Be deliberate — don't jump the user around unnecessarily.
- **Concurrent editing:** The user may be editing at the same time. Warn before editing code in a node they may be actively working in.
- **Secret- and msg-bearing surfaces — project, don't dump.** Connections (`api-configuration`) carry credential values and Agents carry env-var values; when inspecting them (via `tray_read` / `flow_read` or the CLI) request only the non-secret fields you need, and never read a secret back to "verify" a Connection or Route — test the behavior instead. The same discipline applies to msg-bearing surfaces — `log-tap` / Tenant Logs output and `ctxl agents runnerstatus` — which can carry `Authorization` headers, bodies, and PII: project to the fields you need before surfacing them into context. See `solai-cli/cli-reference.md` (secret-bearing records; Agent runtime status) and `node-reference.md` (`log-tap`).
- **Saving:** Changes are live but not saved until the user acts. Do not remind by default — mention **Save the Flow** only when needed (before run/test/verify, or when context is unclear). The button in the Flow Editor UI is labelled **Save** — never use the word "Deploy" to refer to this action. Deploying means binding a flow to an Agent for production execution, which is a separate step. See "Saving and deploying" below.
- **Testing:** You cannot run flows or view test results. You can create `contextual-test` nodes and `inject` nodes for manual testing.
- **"logs"/"logger" means the debug drawer here.** In the Flow Editor, "check the logs/logger" almost always means the current session's **debug drawer** → `logger_messages` (ephemeral, editor-only). This is distinct from **Tenant Logs** (`ctxl logs` in the `solai-cli` skill — persistent, from deployed agents, CLQL-queryable). Switch to Tenant Logs only on explicit cues (agent / deployed / prod / over time / session id / query / CLQL); when context and cues conflict, ask. See `node-reference.md` → "logs" vs. "logger".
- **One wire per output port:** Do not connect multiple wires from the same output port to different destinations. `log-tap` nodes must be wired inline (A → log-tap → B), never branched off a shared output. This is a runtime rule, not a style rule: in a deployed event agent the first message to reach `contextual-end` resolves the execution and a racing branch is not guaranteed to run; on an HTTP lane, execution past the first `http-response` reaches the second terminal and produces runaway catch loops. The editor lints a warning when one output feeds multiple wires. For async side effects: respond fast, then hand off — a record-write trigger or `send-to-agent`. See `node-reference.md` → "One output, one path".
- **Navigate before importing:** `import` always targets the active tab. Call `navigate` to switch to the correct tab before each `import`. Be aware that `tray_read`, `code_read`, `node_update`, and `navigate` with `action: "reveal"` can switch the active tab as a side-effect — re-navigate if uncertain.

## Saving and deploying

**Save** and **Deploy** are different actions with different blast radii.

**Save** persists all *committed* editor changes as a new version of the flow record, immediately. Uncommitted tray edits are not included — commit trays first, or the save reports `no_changes`. Saving never changes what a deployed Agent runs.

The `flow_save` tool performs the Save. Every save that lands writes a new flow version, so treat it as significant and durable — never call it as a reflex after routine edits. Call it only when the user asks, or under a standing grant the user gave this session (e.g. unattended iteration where saves checkpoint progress). It requires `confirm: true`, no-ops cleanly when nothing is unsaved, and returns status flags only — not the new version number; the persist completes asynchronously after the tool returns.

**Deploy** pins an Agent to a flow version — the agent record's `flow` field holds `<flow-id>#<version>`. Repinning to a new version restarts the agent with a rolling restart: the new instance starts and must pass readiness before the old one stops. A restart typically takes 30–90+ seconds; npm-package-heavy flows and cold pod initialization extend it. Cron agents are not restarted on repin. Instance status and details are on the agent's **Operations** tab in the workspace UI, or via `ctxl agents instances` / `ctxl agents runnerstatus` (see `solai-cli/cli-reference.md` → "Agent runtime status" — including how to read a stuck event/cron agent).

**npm packages are part of instance readiness.** A new instance is not marked ready until its function-node packages are retrieved, installed, and loaded — the main driver of restarts approaching or exceeding 90 seconds. The previous instance keeps serving until the new one is fully ready, so a live agent never runs with unloaded packages. (The Flow Editor runtime signals the same readiness with a green **flow is ready** banner — see `node-reference.md` → function nodes.)

## Sequencing rules

Follow these on every task:
1. Call `list_sessions` if the target flow ID is unknown
2. Call `editor_state` to confirm the active tab before any write operation
3. **Use unique placeholder IDs for intra-batch wiring — do not pre-generate hex IDs.** When wiring imported nodes to each other in a single batch, each node you intend to wire to needs an `id` field in the payload. The editor replaces it with a generated ID on placement; the placeholder is used only to resolve the batch's `wires` arrays during the call. Any short string works — a counter (`n1`, `n2`, …) or descriptive labels (`in`, `parse`, `log`). **IDs must be unique within the batch:** if two nodes share an `id`, only one is placed and the duplicate is silently dropped (the import response's `nodeCount` will be lower than your input, with no error). Numeric IDs and empty-string IDs are silently rejected the same way. If you can't trust yourself to maintain a counter across a payload built in pieces, `python3 -c "import secrets; print(secrets.token_hex(8))"` is a cheap way to guarantee uniqueness — but that's the only reason to use it; the platform does not require hex IDs at import. **Cross-batch wires are a separate matter** — see the "**`import` is placement only**" rule above.
4. Before any `import` or `node_update` of a node type you haven't used in this session: **first** confirm `node-reference.md` has been read this session and consult its entry for this node type (the foot-gun warnings live there, not in `type_info`); **then** call `type_info` to confirm the property shape. Both are needed — `type_info` reports defaults, `node-reference.md` warns when those defaults will throw at runtime. Any field showing `defaultValue: "[Circular]"` in the `propertyMap` is an editable-list array — always set it to `[]` explicitly in the import payload. This is reliable across all node types; `[Circular]` is a JSON serialisation artifact, not a missing value. **For Native Object nodes:** before building the import payload, also verify that any upstream `function` or `change` nodes do not store data on reserved `msg` keys (`typeId`, `objectId`, `query`, `search`, `filters`, `property`, `order`, `fields`, etc. — see the full list in `node-reference.md`). Use nested paths like `msg.payload.*` or `msg.data.*` instead. Setting a reserved key on `msg` silently overrides the downstream node's configured value.
5. Call `navigate` to the target tab before calling `import`
6. Call `validate` scoped to the affected tab after every batch of changes. Treat the results as follows:
   - **Newly introduced errors** — block completion, fix immediately before continuing
   - **Newly introduced warnings** — assess severity before acting:
     - Warnings that indicate missing error handling or broken flow patterns (e.g. `require-catch-nodes`) are runtime risks — fix these before reporting the task as done
     - Cosmetic, structural, or naming warnings — surface to the user and leave the decision to them
   - **Pre-existing issues** — report for awareness only, do not auto-fix
   - Never summarise as "zero errors" if warnings exist — always report errors and warnings separately

## Editing code

```
code_read → understand content → code_edit
```

**Always `code_read` the target field in this session before `code_edit`.** Never build an `oldString` from memory, from an earlier read, or from content you imported — the user may have edited since, and an `oldString` that doesn't match exactly fails the edit. Reading first is the single highest-leverage habit for code edits landing on the first try.

Use `code_edit` (find-replace) first. If a clean replace is not possible, use `code_patch` (unified diff). Use `code_write` (full replacement) only as a last resort. For rewrites of 30+ lines, tell the user first.

**`code_edit` batches are atomic — all-or-nothing.** When you pass multiple `edits`, they apply sequentially, but if any one `oldString` does not match, the **entire batch is rolled back** — none of the edits take effect, including the ones that matched. The error names the failing edit's index but does **not** state that a rollback occurred, so it can read like a partial apply. After any failed batch: `code_read` to confirm the field is unchanged, fix the offending `oldString`, and resubmit the full batch. Never assume earlier edits in a failed batch landed.

Changed lines are highlighted in the editor. Do not call `tray_commit` after code edits unless the user explicitly asks — leave the tray open for review.

## Searching code across nodes

`code_grep` searches node code fields by regex, treating each node's field as a virtual file. **Set `searchScope` to match the question — do not default to a single node and page through the rest:**

| `searchScope` | Covers | Use for |
|---|---|---|
| `"all"` | every eligible node across the whole flow, one call | "where is X used anywhere?" |
| `"tab"` (`targetId` = tab id) | every node on one tab / subflow | tab-wide audits |
| `"subflow"` (`targetId` = subflow id) | internal nodes of a subflow definition | subflow-scoped search |
| `"node"` (`targetId` = node id) | a single node | one known node |

**Find references / find callers:** grep the symbol name at `"all"` (or `"tab"`) scope — the matches include the definition *and* every call site across nodes in one pass. This is the cross-node search and usage-lookup path; firing repeated single-node `code_grep`/`code_read` passes to answer a cross-node question is the slower wrong turn. An empty `fieldSelectors` array searches the default surface (`function.func` and `template.template`); widen it to search other fields.

## Canvas positioning

- Lay out nodes with generous spacing: **275px horizontal**, **70px vertical** for stacked nodes
- Never stack nodes at the same coordinates
- Flows should not exceed **1000px wide** — wrap to a second line if needed
- Nodes are positioned by their center point
- When inserting among existing nodes, use `move` to make space before importing

## Node labels and the `l` parameter

- `l: false` hides the label, showing only the node's icon
- Do not set `l: false` by default — only collapse labels when the node's purpose is clear from its icon alone, or the user requests it
- Match the label patterns already used in the flow

## Reading node configuration

| Goal | Tool | Notes |
|------|------|-------|
| Full live field model with values | `tray_read` | Auto-opens the tray when needed. Resolves TypedInput state, editor values, tab associations. |
| Raw node data without side-effects | `flow_read` with `action: "node"` | Lightweight. No tray interaction. Missing live editor values **and missing `wires` (downstream targets — both `action:"node"` and `action:"object"` omit them).** |
| **Wire / connection audit on a single node** | **`flow_read` with `action: "tab"`, `includeNodeDetails: true`** | **Returns the full tab — pick the target node from the `nodes` array. Only path that includes `wires` per node.** |
| Code editor content | `code_read` | Paginated. Works while expanded editor is open. |
| Node type defaults and help | `type_info` | Use before creating nodes or to understand a type's properties. |

## Wiring discipline

- **Use `wire` for every wire change — `node_update` silently no-ops on the `wires` field.** This applies whether you're adding a wire to a node that has none, redirecting an existing wire to a different target, or clearing wires entirely. Both `node_update changes:{wires:...}` and `node_update patch:[{op:"replace", path:"/wires", ...}]` return `status:"ok", updated:["wires"], valid:true` while leaving wires unchanged. The only signal that nothing happened is reading the node's `wires` back. Use the `wire` tool's `add` / `remove` operations exclusively for any wire modification. `node_update` is correct for non-wire properties (`name`, `func`, configuration fields) only.
- After any wiring changes, call `flow_read` on the affected tab and audit wires on every node added or modified in this task
- Trace each changed path end-to-end from entry node to terminal. Scope to paths in focus, not the entire flow.
- **Never diagnose wiring from screenshots alone.** Long wires running across the canvas can visually appear to originate from nearby nodes. Before accepting a suspected fan-out or race condition, call `flow_read` and check the node's `wires` array and `outputs` count. A wire that looks like a second output from a node may be a long wire from an upstream node passing through that region of the canvas.
- **Route bypass wires off-axis.** When a branch skips a section of the chain (e.g. an early-exit path bypassing several nodes to reach a terminal), run that wire at a y-level clearly offset from the main chain — not along the same horizontal plane as the nodes it bypasses. Wires that share the y-level of nearby nodes are easily mistaken for connections to those nodes.

## Deployment discipline

Batch size is governed by **payload size**, not node count. In testing with hefty function nodes (20+ lines of real code each), single imports of 10, 15, and 20 nodes all landed cleanly. The failure mode observed at the extreme was an MCP connection **timeout** — not silent node loss. The practical limit appears to be the MCP round-trip timeout (~30s), not a node count ceiling.

Guidelines:

- Comment/stub nodes: no meaningful limit observed up to 20
- Function nodes with substantial code: up to 20 landed reliably in a single import
- If a timeout occurs: split the batch and retry — no partial writes were observed; it's all-or-nothing
- After each import, always verify `nodeCount` in the response matches the number of nodes you sent. A mismatch indicates one or more nodes were silently dropped — common causes are duplicate placeholder IDs within the batch, invalid `id` types (numeric, empty string), and malformed payload shapes. Investigate before continuing.
- Never work from memory — always read current state before acting
- Every tab needs error handling: catch → log-tap (error) → http-response 500 or contextual-error. `contextual-error` is an event-family terminal — it must trace back to an event route, and on an inject-driven test/scratch tab (no `contextual-start`) it draws the hard lint error `no-unconnected-event-nodes`; terminate the catch chain at the error `log-tap` there instead.

## Direct property updates

Use the tray workflow for most property changes. Use `node_update` when the tray is not open and the change does not need user review (e.g. renaming a node). Note that renaming changes rendered width — use `move` afterward if needed.

`node_update` auto-commits immediately without opening the tray. If the target node's tray is already open with pending changes, use `tray_write` instead.

## Tray workflow

```
tray_read → tray_write (one or more calls)
```

Only call `tray_commit` when the user explicitly asks to save or commit. Otherwise leave the tray open for review.

`tray_read` auto-opens the target tray when needed, so a separate `tray_open` first is not required. Note that switching to a different node's tray auto-commits any pending (uncommitted) edits in the currently open tray — a session-level commit, not a flow Save (nothing is lost, but the edits are committed). For editable lists, prefer semantic row selectors from `tray_read(includeListItems: true)`. Treat `warningCount`/`warnings` on `tray_write` responses as a sign to re-inspect tray state before continuing.

When reading across multiple nodes, moving from tray to tray is fine. Before switching to non-tray tools on a different node, close with `tray_commit action: "cancel"` — unless you made edits, in which case leave the tray open for review.

## Creating nodes

| Method | When to use |
|--------|-------------|
| `import` | Default. You control coordinates and wiring. Navigate to the target tab first. Follow with `wire` to connect to existing nodes. |
| `interactiveInsert` | Only when the user explicitly asks for interactive/manual placement. |

Always call `type_info` before building node objects for import.

## Key response fields

Check these after mutation tool calls:
- `previousTrayTarget` — ID/type of a tray displaced by the operation
- `autoCommittedPreviousTray` — whether displaced tray changes were auto-saved
- `closedExpandedEditor` — whether a fullscreen editor was closed
- `uiFeedback.revealedNode` — node the editor navigated to after the operation
- `uiFeedback.selectedNodeIds` — nodes selected after the operation

## End-to-end flow guidelines

### Wiring responsibility
- When suggesting more than one node for an end-to-end flow, always connect them with correct wires end-to-end
- Wiring is your responsibility — nodes should be connected when placed on the canvas
- Before finalizing any node creation, verify: did I connect all nodes? If not, go back.
- Double-check that `log-tap` nodes are included at key steps
- Double-check that `function` nodes are included at key steps around `http-get`, `http-post`, `http-put`, `http-patch`, `http-delete`

### Flow patterns
- **HTTP is the front door; the event fabric is the hallway.** `http-in` flows serve external callers and respond fast. Work the system dispatches to itself — background jobs, long-running side effects — belongs on an event agent, reached via a record-write trigger or `send-to-agent`, never via an internal HTTP call between the solution's own agents.
- **One web app = one HTTP flow + one agent.** A deployed HTTP agent serves one flow at one base URL; every `http-in` node is a route under that origin. Add routes to the app's flow — do not create a new HTTP flow per endpoint. See `node-reference.md` → "HTTP agents, base URLs, and routes".
- **Event-based flows:** `contextual-start` → (nodes) → `contextual-end`
- **HTTP flows:** `http-in` → (nodes) → `http-response`
- Every `contextual-start` output must be wired and must eventually reach a terminal node
- **Exactly one message may reach the terminal — converge any fan-out before it.** The first message to reach a `contextual-end` ends the *whole* flow execution, so a fan-out (a `split`, or one output wired to several terminals) whose branches each reach `contextual-end` terminates on the first message and silently drops the rest. Re-collapse a fan-out to a single message (e.g. `join` in auto mode) before the terminal. See `node-reference.md` → "`split` / `join`".

### Custom node reference

| Node | Use |
|------|-----|
| `contextual-start` | Entry point for every event-based flow (not HTTP) |
| `contextual-end` | Terminal for every event-based flow (not HTTP) |
| `contextual-error` | Error terminal for both event and HTTP flows |
| `send-to-agent` | Fire-and-forget message onto an **event** agent's topic. Event agents only — an HTTP or Cron target silently receives nothing. See `node-reference.md`. |
| `http-in` | Entry point for HTTP flows |
| `http-response` | Terminal for HTTP flows — set status codes appropriately |
| `log-tap` | All logging — replaces debug node entirely |
| `catch` | Error handling — see catch node rules below |

## Output format

Return a concise summary: what changed, node IDs affected, validation result. Do not return raw JSON or full flow dumps.
