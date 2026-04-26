# Flow Editor Node Reference

Node-specific configuration, rules, and patterns for the Contextual Flow Editor.

---

## log-tap node

`log-tap` replaces the `debug` node entirely. The `debug` node is **deprecated and non-functional** — never suggest or create debug nodes.

Available levels (confirmed from live tray — `type_info` does not enumerate these): `debug`, `info`, `warn`, `error`

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

---

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

**`nativeObjectConfig` is not set automatically on import** — always follow up with `node_update` to set it if it wasn't included in the import payload. Check with `flow_read` after import to confirm.

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

### HTTP route limitation

`inject` nodes cannot meaningfully drive `http-response` terminals. The `http-response` node requires a real Express `res` object (a live TCP connection from `http-in`) — there is no JSON-serializable substitute. Injecting a stub `res: {}` causes `TypeError: Cannot read properties of undefined (reading 'status')` at the terminal, which cascades into the catch handler and produces a "Message exceeded maximum number of catches" loop.

For HTTP route testing in-editor, use `contextual-test` nodes instead (see below), with `output` pointed at the last meaningful node before the `http-response` terminal (e.g. the shape-response `function` node). The `contextual-test` node suppresses `msg.res` cleanly, avoiding the crash entirely.

---

## flow-test contextual-test node

Use for structured in-editor testing of business logic.

Each test case defines:

- `label` — display name for the case
- `message` — JSON input `msg` object (typed input, JSON mode)
- `expected` — JSON object to assert against the output (partial match)
- `output` — node ID to monitor; the test runner watches what arrives at that node
- `timeout` — ms before the case fails (default: `5000`)

The node must be wired into the flow as an entry point — it is not self-contained.

**Key pattern for HTTP routes:** point `output` at the last `function` node before `http-response` terminals. This lets you assert on `statusCode` and payload without hitting the `res.status()` crash that occurs with `inject` nodes.

Cases can be added programmatically via `tray_write` with `action: "add_list_items"` on `fieldId: "cases"` once the tray is open.

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

---

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
