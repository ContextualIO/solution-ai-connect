---
name: solai-flow-editor
description: Edit live Contextual flows in the Flow Editor — read state, import nodes, wire connections, update properties, edit code, and validate. Use AFTER a plan is in place. Do NOT plan architecture here — use plan-flow first.
---

# SolAI Flow Editor

Use this skill to interact with live Contextual flows through the `ctxl-flow-editor` MCP server.

## Setup Check

The MCP server must already be running in the user's own terminal — never start it yourself. Any process started via shell from this context is ephemeral and dies immediately.

**If `mcp__ctxl-flow-editor__*` tools appear in the deferred tool list, the server is already up.** Load the tool schemas and call `info` / `list_sessions` to verify the connection.

If those tools are not available, tell the user to run this in their own terminal first:

```bash
ctxl mcp serve --config-id <config-id>
```

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

This is a proprietary platform. Do not apply assumptions from public knowledge of other flow-based tools. When uncertain about node behaviour or platform conventions: if a live session is active, use `type_info` to retrieve the node definition and documentation directly from the connected editor — that is the authoritative source. Only defer to the `solai-knowledge` skill when no live session is available.

## Available tools (by category)

- **Read state**: `editor_state`, `flow_read`, `search`, `validate`, `type_info`, `info`, `logger_messages`, `result_read`
- **Navigate**: `navigate`, `select`
- **Write**: `import`, `wire`, `node_update`, `delete`, `move`, `copy`, `group`
- **Tray** (node properties panel): `tray_open`, `tray_read`, `tray_write`, `tray_commit`
- **Code** (function/template node editors): `code_read`, `code_write`, `code_edit`, `code_grep`, `code_patch`

## Important behaviors

- **Navigation side-effects:** Many tools (`import`, `node_update`, `navigate`, `code_edit`, etc.) navigate the user's viewport, switch tabs, and change selection in real-time. Be deliberate — don't jump the user around unnecessarily.
- **Concurrent editing:** The user may be editing at the same time. Warn before editing code in a node they may be actively working in.
- **Saving:** Changes are live but not saved until the user acts. Do not remind by default — mention **Save the Flow** only when needed (before run/test/verify, or when context is unclear).
- **Testing:** You cannot run flows or view test results. You can create `contextual-test` nodes and `inject` nodes for manual testing.
- **Imported nodes start detached:** Internal wires among an imported batch are preserved, but no connections to existing canvas nodes are made. Use `wire` after importing to connect to existing nodes.
- **One wire per output port:** Do not connect multiple wires from the same output port to different destinations. `log-tap` nodes must be wired inline (A → log-tap → B), never branched off a shared output.
- **Navigate before importing:** `import` always targets the active tab. Call `navigate` to switch to the correct tab before each `import`. Be aware that `tray_read`, `code_read`, `node_update`, and `navigate` with `action: "reveal"` can switch the active tab as a side-effect — re-navigate if uncertain.

## Sequencing rules

Follow these on every task:
1. Call `list_sessions` if the target flow ID is unknown
2. Call `editor_state` to confirm the active tab before any write operation
3. Call `type_info` before importing a node type you haven't used in this session
4. Call `navigate` to the target tab before calling `import`
5. Call `validate` scoped to the affected tab after every batch of changes. Separate findings into **newly introduced** vs **pre-existing**. Auto-fix newly introduced **errors**. Present newly introduced **warnings** to the user. Report pre-existing issues for awareness only.

## Editing code

Use `code_edit` (find-replace) first. If a clean replace is not possible, use `code_patch` (unified diff). Use `code_write` (full replacement) only as a last resort. For rewrites of 30+ lines, tell the user first.

```
code_read → understand content → code_edit
```

Changed lines are highlighted in the editor. Do not call `tray_commit` after code edits unless the user explicitly asks — leave the tray open for review.

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
| Full live field model with values | `tray_read` | Auto-opens tray. Resolves TypedInput state, editor values, tab associations. |
| Raw node data without side-effects | `flow_read` with `action: "node"` | Lightweight. No tray interaction. Missing live editor values. |
| Code editor content | `code_read` | Paginated. Works while expanded editor is open. |
| Node type defaults and help | `type_info` | Use before creating nodes or to understand a type's properties. |

## Wiring discipline

- **Prefer `wire` for all connection changes** — it is explicit, targeted, and reliable. `node_update` does not manage wires; wires are maintained by the editor's link layer and must be set via `wire`. Never attempt to set wires through `node_update`.
- After any wiring changes, call `flow_read` on the affected tab and audit wires on every node added or modified in this task
- Trace each changed path end-to-end from entry node to terminal. Scope to paths in focus, not the entire flow.

## Deployment discipline

- Import in batches of 3–5 nodes max — larger imports cause silent node loss
- After each import batch, call `flow_read` on the tab and confirm node count matches expectation before continuing
- Never work from memory — always read current state before acting
- Every tab needs error handling: catch → log-tap (error) → http-response 500 or contextual-error

## Direct property updates

Use the tray workflow for most property changes. Use `node_update` when the tray is not open and the change does not need user review (e.g. renaming a node). Note that renaming changes rendered width — use `move` afterward if needed.

`node_update` auto-commits immediately without opening the tray. If the target node's tray is already open with pending changes, use `tray_write` instead.

## Tray workflow

```
tray_read → tray_write (one or more calls)
```

Only call `tray_commit` when the user explicitly asks to save or commit. Otherwise leave the tray open for review.

`tray_read` auto-opens the tray — use `tray_open` only when you don't need to read values first. For editable lists, prefer semantic row selectors from `tray_read(includeListItems: true)`. Treat `warningCount`/`warnings` on `tray_write` responses as a sign to re-inspect tray state before continuing.

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
- **Event-based flows:** `contextual-start` → (nodes) → `contextual-end`
- **HTTP flows:** `http-in` → (nodes) → `http-response`
- Every `contextual-start` output must be wired and must eventually reach a `contextual-end`
- Every wire path must eventually reach a terminal node

### Custom node reference

| Node | Use |
|------|-----|
| `contextual-start` | Entry point for every event-based flow (not HTTP) |
| `contextual-end` | Terminal for every event-based flow (not HTTP) |
| `contextual-error` | Error terminal for both event and HTTP flows |
| `send-to-agent` | Send messages to a separate Contextual Agent/Flow |
| `http-in` | Entry point for HTTP flows |
| `http-response` | Terminal for HTTP flows — set status codes appropriately |
| `log-tap` | All logging — replaces debug node entirely |
| `catch` | Error handling — see catch node rules below |

---

## log-tap node

`log-tap` replaces the `debug` node entirely. The `debug` node is **deprecated and non-functional** — never suggest or create debug nodes.

Default configuration:
```json
{
  "level": "debug",
  "toConsole": false,
  "toSideBar": true,
  "outputProperty": "payload",
  "outputPropertyType": "msg"
}
```

In a `catch` error handling context:
```json
{
  "level": "error",
  "outputProperty": "",
  "outputPropertyType": "full"
}
```

When logging the full `msg` object:
```json
{
  "outputProperty": "",
  "outputPropertyType": "full"
}
```

`log-tap` nodes must always be inline on the flow (A → log-tap → B), never dangling off to the side.

## catch node rules

- Catch nodes only apply to nodes on the **same tab or subflow**
- Scope to specific nodes, all nodes in a group, or the entire tab — do NOT individually select every node
- **"Catch errors from: uncaught errors only" should almost always be checked** — prevents duplicate error handling
- Top-level catch nodes (whole tab) should almost always use uncaught only
- Catch nodes inherit the end-node requirement of the tab or group they protect:
  - HTTP route catch → must reach `http-response`
  - Event route catch → must reach `contextual-end`
  - AI tool route catch → must reach `ai-tool-response`
- When multiple route types share a tab, each needs its own scoped catch node
- Do NOT create a separate group + catch for every individual node

---

## HTTP nodes — use Contextual Connection-native nodes

For all outbound HTTP communication, use Contextual Connection-native nodes. **Never use the generic `http request` node.**

| Operation | Node |
|-----------|------|
| GET | `http-get` |
| POST | `http-post` |
| PUT | `http-put` |
| PATCH | `http-patch` |
| DELETE | `http-delete` |

Usage pattern in end-to-end flows: `function` → `http-[method]` → `function`

All Contextual HTTP nodes use:
- `"nativeObjectConfig": "default-native-object-config"`
- `"apiIdType": "conn"` with the correct Connection `apiId` from the tenant

The `http-in` and `http-response` nodes handle string-to-object and object-to-string conversion automatically — no separate parse/convert nodes needed.

Always use `type_info` to confirm the full property shape before importing any HTTP node.

---

## inject nodes — simulating trigger and action payloads

Use `inject` nodes only when explicitly requested for manual testing in the Flow Editor. Never configure `inject` to automatically start or perform rapid repeated injection.

### Post-Insert trigger shape
Headers include: `x-subkind: post-insert`, `x-kind: trigger`, `x-type-id`, `x-uri`.
Payload is the full new record including `_metaData`.

### Post-Update trigger shape
Headers include: `x-subkind: post-update`.
Payload shape: `{ "new": { ...record }, "old": { ...record } }` — both with `_metaData`.

### Post-Delete trigger shape
Headers include: `x-subkind: post-delete`.
Payload is the deleted record including `_metaData`.

### Send-to-Agent action shape
Headers include: `x-kind: action`, `x-subkind: <action-id>`, `x-type-id`.
Payload shape: `{ "instance": { ...record }, "params": {} }`.

When building inject test payloads for a specific Object Type, use `type_info` or ask the user for the actual `x-type-id` and record field shape.

---

## Native Object nodes

Use these nodes to interact with records stored in the Contextual platform. `function` nodes cannot interact directly with Native Object records.

| Node | Purpose |
|------|---------|
| `search-native-object` | Search/query records of an Object Type |
| `get-native-object` | Retrieve a single record by ID |
| `create-native-object` | Create a new record |
| `patch-native-object` | Patch a record (input must be a JSON patch operation) |
| `put-native-object` | Replace a record |
| `import-native-objects` | Bulk import an array of records |
| `delete-native-object` | Delete a record |
| `execute-native-object` | Execute an Action on a record (dispatches to an Agent/Flow) |

All use `"nativeObjectConfig": "default-native-object-config"`. Always confirm the Object Type `typeId` (lowercase with dashes, not the display name) before use.

For `patch-native-object`, include a `function` node before it to prepare the JSON patch payload.
For `import-native-objects`, include a `function` node before it to prepare the records array.

Always use `type_info` to confirm the full property shape before importing any Native Object node.

---

## function nodes

Prettify all code in `function` nodes. Follow the **Function Node Return Contract** below.

Supported NPM packages (available out of the box): `uuid`, `short-uuid`, `jsonwebtoken`

Declare packages in `libs` and reference by the `var` name directly — do NOT use `const X = require(...)`:
```json
"libs": [{ "var": "short", "module": "short-uuid" }]
```

### Function Node Return Contract

- Never use `return null` as the full return value
- Single-output nodes: `return msg`
- Multi-output nodes: return an array, routing down exactly one output per invocation (e.g. `return [msg, null]` or `return [null, msg]`)
- Every branch — success, validation, error — must continue to appropriate downstream handling (`contextual-end`, `http-response`, `ai-tool-response`, or explicit error route)
- `null` is only valid inside an output array to suppress delivery on specific outputs
- Logging is not an endpoint

## template nodes

- `format`: default `"handlebars"` (options: `"html"`, `"json"`, `"javascript"`, `"css"`, `"markdown"`)
- `syntax`: default `"mustache"` (only other option: `"plain"`)
- `output`: default `"str"` (options: `"json"`, `"yaml"`)
- Use Mustache syntax only — Handlebars advanced logic (e.g. `{{#each`) is **not supported**

---

## Web application and front-end guidelines

When building user-facing web interfaces (HTML/CSS/JS in `template` nodes):

**Design standards:**
- Follow modern, responsive best practices
- Use Bootstrap or equivalent toolkit for layout and components
- Use Font Awesome for icons
- Use `https://picsum.photos/{width}/{height}` for placeholder images (append `?blur=2` for blurred)
- Use DiceBear for avatars/profile icons: `https://api.dicebear.com/9.x/thumbs/svg?seed=Name`
- Avoid inline CSS — use `<style>` blocks with comments for atypical definitions
- Use Mustache (`{{ }}`) in templates — not Handlebars

**Before building any page, ask:**
- Should I include a navigation bar? Footer? Copyright?
- Would images improve this layout?
- Who is the end user, and what content do they need?

Outline content sections for user confirmation before building complex pages.

**Forms:**
- Mark required fields appropriately
- Implement client-side validation
- Provide clear, user-friendly error feedback

When writing HTML/CSS/JS as part of an end-to-end flow, import nodes directly by default. Use `interactiveInsert` only if the user explicitly asks for manual placement.

---

## Other supported nodes

`comment`, `inject`, `catch`, `switch`, `change`, `range`, `delay`, `trigger`, `rbe`, `loop`, `split`, `join`, `sort`, `batch`, `template`, `status`, `MSSQL`, `sse-client`, `odbc`, `gql`, `kafka-producer`, `source-from`, `sink-collect`, `map`, `batch-source`, `filter-source`, `read-stream`, parsers: `csv`, `html`, `json`, `xml`, `yaml`

---

## Output format

Return a concise summary: what changed, node IDs affected, validation result. Do not return raw JSON or full flow dumps.
