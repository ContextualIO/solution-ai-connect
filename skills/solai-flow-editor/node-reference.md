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

**Any time you consider using the generic `http request` node, stop — use the appropriate Connection-native node instead.** The only exception is if the user has explicitly asked for `http request` or given a specific reason to use it.

For all outbound HTTP communication, use Contextual Connection-native nodes.

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

## `http-response` status code and header precedence

The configured value on the `http-response` node is **authoritative** when set. Upstream `msg.statusCode` is silently ignored if the node's `statusCode` field has a non-empty literal.

**Precedence resolution:**

1. Configured `statusCode` non-empty → that value is used. Upstream `msg.statusCode` is ignored.
2. Configured `statusCode` blank → the runtime falls back to `msg.statusCode` from the incoming message.
3. Neither set → response defaults to `200`.

The same precedence applies to headers: configured headers on the node win; `msg.headers` is the fallback channel.

**Authoring patterns:**

- **Static status code (one route, one outcome):** configure on the terminal. Don't bother setting `msg.statusCode` upstream — it'll be silently ignored.
- **Dynamic status code (success + error branches in one route, different codes per outcome):** leave the terminal's `statusCode` blank and set `msg.statusCode` end-to-end in your function nodes. The runtime then honors what your code dictates.
- **Don't mix:** if you both configure a `statusCode` on the terminal *and* set `msg.statusCode` upstream, the configured value wins — your `msg.statusCode` is silently dropped. This is the most common authoring trap; it produces symptoms like *"my 404 turned into a 302"* on routes where success paths land at a hardcoded redirect terminal.

**Diagnostic tip:** if you're seeing wrong status codes and your function node logs show `msg.statusCode` set to the right value just before the terminal, the value the log line reports is **irrelevant** to what the client receives — the configured terminal value is overriding it. Either fork the routing to reach a terminal with the matching configured value, or unhardcode the terminal's `statusCode` to let `msg.statusCode` win.

---

## HTTP ingress payload limits — editor runtime vs. agent runtime

The runtime that serves an HTTP flow's endpoint applies a hard ingress cap on request body size. The cap differs between the Flow Editor's preview runtime and a deployed agent's runtime:

| Runtime | Endpoint shape | Default ingress cap |
|---|---|---|
| Flow Editor preview | `https://<flow-id>.flow.<tenant-id>.my.contextual.io/<path>` | **~2 MB** (`nginx client_max_body_size: 2m`) |
| Agent (`flow-http`) | `https://<agent-id>.service.<tenant-id>.my.contextual.io/<path>` | **40 MB** |

The editor preview's lower cap is intentional — the editor runtime is provisioned with significantly fewer resources than a typical agent. Don't treat it as a bug; treat it as a routing decision about which runtime to test against.

**Practical implication for HTTP flows with large payloads:** testing requests above ~2 MB against the editor preview URL will fail at the proxy layer before the request reaches the flow. To test large-payload ingress (file uploads, multi-MB JSON bodies, HTML asset hosting, etc.), bind the flow to an agent and exercise the agent's runtime endpoint instead.

**Diagnostic tip:** if you see opaque `413 Request Entity Too Large` or "request body too large" responses against the editor preview URL — especially before any logging from the flow itself fires — suspect the editor's ingress cap before assuming the flow is broken. The same flow tested via its bound agent's endpoint should accept payloads up to ~40 MB.

---

## AI model selection (AI Routes)

In the Contextual AI Gateway, **the model is selected on the AI Route — and only there.** An AI Connection carries the provider type, credentials, and endpoint (no model); AI Generate and AI Tool nodes reference an AI Route and inherit its model. There is no model field on a Connection or on a node — don't set or look for one there.

When setting the model on a Route, the identifier matters and dates quickly:

- **Never fill the Route's model field from memory.** Model identifiers in training data are very likely outdated — providers iterate and retire models far faster than a training cutoff. Always derive the value from a current source when you configure the Route.
- **Confirm current models via web retrieval.** Check the provider's own model documentation, or a current-model index such as [models.dev](https://models.dev), and prefer the most recently released GA model in the family. Fetch it however the runtime allows — don't rely on a fixed command or a cached list.
- **Default to the current generation.** Choose the provider's current flagship/mainstream GA model; avoid prior major generations, anything marked preview/experimental/deprecated, and models more than roughly a year old when a newer sibling exists.
- **Scope to the Connection's provider type:** OpenAI, Anthropic, Azure OpenAI, Google AI, Vertex AI, or Vertex AI Anthropic — match the model lookup to the provider of the Connection the Route references.
- **Verify before relying on it.** Model lineups move fast, so a name that looks valid may be out of date — after configuring the Route, exercise a flow path that uses it (e.g. an `inject` into an AI Generate / AI Tool node) and confirm a successful response in the debug output.

This decision is often made when setting up a Connection and its Route on their own, separate from any flow — the same rule is carried as a hard rule in the `solai-cli` skill so it applies there too. See the [AI Routes docs](https://docs.contextual.io/documentation-and-resources/components-and-data/ai-routes) or the `solai-knowledge` skill for how Routes bind Connections to AI Generate / Tool nodes.

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

All Native Object node types reference a single `native-object-config` config node by id (`"nativeObjectConfig": "default-native-object-config"`). The config node itself persists with the minimum shape `{id, type, name}` in the flow record's config-node entries — no `z`, no `x`/`y`, no `wires`. The `id` is load-bearing (it's the reference target); `name` is a display label only. Empty credential/host fields (`host`, `orgId`, `clientId`, `clientSecret`, etc.) are inert — set them only when overriding for a non-canonical scenario. See `cli-reference.md` → "Correct empty flow shape" for full flow-record structure context.

| Node | Purpose |
|------|---------|
| `search-native-object` | Array-of-criteria search (`search` + `filters` + `order` arrays, `filterMode: "AND"\|"OR"`). More structural; preferred when the filter is composed from many parts. |
| `query-native-object` | Single-object MongoDB-style filter (`{ "$.field": "value" }`, `$in`, `$gt`, `$or`, etc.). Simpler shape; preferred for direct filter expressions. See subsection below. |
| `get-native-object` | Retrieve a single record by ID |
| `create-native-object` | Create a new record |
| `patch-native-object` | Patch a record (input must be a JSON Patch array — `[{op,path,value}]` per RFC 6902, not a plain object) |
| `put-native-object` | Replace a record |
| `import-native-objects` | Bulk import an array of records |
| `delete-native-object` | Delete a record |
| `execute-native-object` | Execute an Action on a record (dispatches to an Agent/Flow) |

All use `"nativeObjectConfig": "default-native-object-config"`. Always confirm the Object Type `typeId` (lowercase with dashes, not the display name) before use.

For `patch-native-object`, include a `function` node before it to prepare the JSON patch payload.
For `import-native-objects`, include a `function` node before it to prepare the records array.

Always use `type_info` to confirm the full property shape before importing any Native Object node.

### TypedInput pattern across Native Object nodes

Several fields on these nodes are **TypedInputs** — a string value whose runtime interpretation depends on a `*Type` companion field that's declared as a separate property in `type_info`. The companion is what the visible icon-toggle in the editor sets (e.g. the `{}` / `J:` / `msg.` dropdown next to the Query field on `query-native-object`).

**Always set both halves of any TypedInput pair explicitly on import.** Don't rely on the default for either side — `type_info` exposes both the value field and its companion separately, and the safe pattern is to fetch `type_info` and copy both into the import payload. The companion may be reported as `required: false` with a non-empty default, but the runtime Zod schema rejects the node when the companion is absent — treat both halves as effectively required.

Common TypedInput pairs on Native Object nodes:

| Value field | Companion | Effect of companion value |
|---|---|---|
| `query` (on `query-native-object`) | `queryType` | `json` (default) → value parsed as a JSON string at evaluation; `expression` → value evaluated as a JSONata expression against `msg`; `msg` → value is a `msg` property path |
| `outputProperty` | `outputPropertyType` | `msg` (typical) → write result to that msg property; `flow`/`global` for context state |
| `typeId` | `typeIdType` | `notype` (default, typical) → literal type id; `msg`/`str`/etc. for indirected lookup |
| `pageSize` | `pageSizeType` | `num` (typical) → numeric literal; `msg`/`str`/etc. for indirected lookup |

### Reserved `msg` keys override Native Object node configuration

If any of the following keys are set on `msg` upstream in a flow, every downstream Native Object node with a property of the same name will use the upstream value **instead of its own configured value**. The node does not log that an override occurred and the editor shows no visual indicator. The only diagnostic is to place a `log-tap` upstream of the node and check whether a reserved key is unexpectedly present on `msg`.

To avoid these silent obverrides on Native Object nodes, **do not store application data on these top-level `msg` keys.** Use `msg.payload.*` or any other nested path instead. All reserved keys are top-level properties on `msg`. Nested paths like `msg.payload.typeId` are not affected.

| Key | Paired type key | Native Object nodes with this property |
|---|---|---|
| `typeId` | `typeIdType` | all Native Object nodes |
| `objectId` | `objectIdType` | `get-native-object`, `patch-native-object`, `put-native-object`, `delete-native-object`, `execute-native-object` |
| `property` | `propertyType` | `create-native-object`, `patch-native-object`, `put-native-object`, `execute-native-object`, `import-native-objects` |
| `outputProperty` | — | `create-native-object`, `get-native-object`, `patch-native-object`, `put-native-object`, `execute-native-object`, `query-native-object`, `search-native-object`, `import-native-objects` |
| `responseProperty` | — | `create-native-object`, `get-native-object`, `patch-native-object`, `put-native-object`, `delete-native-object`, `execute-native-object`, `query-native-object`, `search-native-object`, `import-native-objects` |
| `actionId` | `actionIdType` | `execute-native-object` |
| `query` | `queryType` | `query-native-object` |
| `search` | — | `search-native-object` |
| `filters` | — | `search-native-object` |
| `filterMode` | — | `search-native-object` |
| `pageSize` | `pageSizeType` | `query-native-object`, `search-native-object` |
| `pageToken` | — | `query-native-object`, `search-native-object` |
| `order` | — | `query-native-object`, `search-native-object` |
| `fields` | — | `query-native-object`, `search-native-object` |
| `includeTotal` | — | `query-native-object`, `search-native-object` |

### `query-native-object` (Query Object node)

Distinct from `search-native-object` (above). Both query records of an Object Type, but with different filter models — see the row notes above. Pick `query-native-object` for direct MongoDB-style filter expressions; pick `search-native-object` when the filter is composed from many parts or relevance scoring matters.

**`query: ""` is a foot-gun.** The default value of the `query` field per `type_info` is the empty string. With `queryType: "json"` (the typical mode), runtime calls `JSON.parse("")` and throws `SyntaxError: Unexpected end of JSON input` at every invocation — there is no platform round-trip and no opportunity for the platform to interpret `""` as "no filter". The canvas widget shows a red triangle on initial paint but the warning **clears on user interaction with the node** and is not surfaced by `validate` or `flow_read` — a node can pass all validation surfaces and still be guaranteed to throw at runtime.

**The canonical "match all records" form (when `queryType: "json"`) is the literal two-character string `"{}"`.** Set this explicitly on import; do not ship the default.

**Page size controls the output shape.** For the normal, non-source output mode:

| Page size | Matches     | Output                                 |
| --------- | ----------- | -------------------------------------- |
| `>= 2`    | One or more | `{ "items": [...records] }`            |
| `>= 2`    | Zero        | `{ "items": [] }`                      |
| `1`       | One         | The matching record directly           |
| `1`       | Two or more | The first record returned by the query |
| `1`       | Zero        | `undefined`                            |

The flat-record output applies only when the evaluated numeric page size === 1. For indirect `pageSize` values (for example, `pageSizeType: "msg"`), `0` is treated as unset, and a value that cannot be converted to a number is likewise omitted from the request. In either case, the API's default page size applies, and the output remains an envelope.

For page sizes of `2` or greater, `includeTotal: true` adds a top-level `totalCount` to the envelope. When more pages exist, the envelope also includes `nextPageToken`. With `pageSize: 1`, the node emits only the first record returned by the query and discards the response envelope, including `totalCount` and `nextPageToken`. The output therefore does not indicate whether additional matches exist. Configure `order` when it matters which matching record is returned.

**Passing the standard output of a Query Object node configured with a page size of `2` or greater directly to a downstream `loop` node configured to enumerate the whole message payload (`enumeration: "payload"`, `enumerationType: "msg"`) is a silent foot-gun.** The Loop iterates once per top-level property in the output envelope, not once per record in `msg.payload.items`. `validate` reports nothing, the flow can still return 200, and the only tell may be the wrong per-pass count. To iterate records:
- Target the inner array on the loop: `enumeration: "payload.items"` (with `enumerationType: "msg"`)
- Or insert an unwrap function between query and loop: `msg.payload = msg.payload.items; return msg;`

When **Unfold all pages to source** is enabled, the normal output table does not apply: each emitted message carries one record at the configured output path regardless of page size.

See the Loop node section's silent-failure list for the generic diagnostic recipe.

**Filter syntax** (MongoDB-style query predicates, same as `ctxl records query`):

| Predicate | Form |
|---|---|
| Exact match | `{"$.field": "value"}` |
| `$in` | `{"$.field": {"$in": ["a","b"]}}` |
| Comparison | `{"$.balance": {"$gt": 100}}` |
| `$and` / `$or` | `{"$and": [{"$.f1": "a"}, {"$.f2": {"$lt": 0}}]}` |
| `$exists` | `{"$.field": {"$exists": true}}` |

See `cli-reference.md` "Querying Records" for the full predicate list — the syntax is shared between the CLI and the node.

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

### Logging from inside function nodes — use `await logger.*`, not `node.*`

| Surface | When |
|---|---|
| `await logger.debug/info/warn/error(...)` | All in-function logging. printf templating, object args, four levels, async-safe (you can log intermediate state during long-running work before the function returns). Reaches both the editor sidebar and the persistent contextual log. |
| `log-tap` node | Inline observability **between** nodes — assertions like "this msg passed this point at level X". No code change needed; level visibility on tap entries is omitted (structural tell vs. function logger output). |
| `node.log(...)` | Never. Silently dropped — invisible in the editor sidebar and the persistent contextual log. |
| `node.warn(...)` / `node.error(...)` | Avoid. Vestigial Node-RED contract: single-string only, no printf templating, no object args, no `debug` level. Strict subset of `logger.*` with worse ergonomics. |

Function nodes do real in-process work using the platform's supported NPM library surface — file-format parsing (PDF, Excel, ZIP, XML, .msg email), JWT signing and JWKS verification, query expressions (JSONata, JSONPath), data transformations (lodash, date utilities), templating, crypto, JSON Patch construction, ID generation. Multi-step bodies have multiple distinct failure modes — parse errors, validation gaps, schema mismatches, missing fields — between any two seams a `log-tap` could sit at. `await logger.*` is the right surface for visibility into those failure modes from inside the body.

**Connection-based interactions are strongly and almost always preferred over library-driven I/O inside function bodies.** Outbound work — HTTP, DB, LLM, agent dispatch — should go through the Connection-native nodes (`http-get`/`http-post`/..., `MSSQL`/`ODBC`/native-object nodes, AI Routes, `send-to-agent`). They handle auth via the configured Connection, give you uniform observability and error routing, and keep config centralized. Reach for an HTTP-capable library inside a function body only when the user has explicitly asked for it or there's a specific reason no Connection-native path covers (e.g. a library that composes a multi-step protocol in a way discrete nodes can't cleanly express). The function node's primary job is the in-process work *around* those calls.

Example — emitting multiple structured entries from one function body, e.g. parsing an uploaded XLSX and validating rows before staging records for `import-native-objects`:

```js
const wb = xlsx.read(msg.payload.fileBytes, { type: "buffer" });
const sheet = wb.Sheets[wb.SheetNames[0]];
const rows = xlsx.utils.sheet_to_json(sheet);
await logger.info("xlsx parsed sheets=%d rows=%d", wb.SheetNames.length, rows.length);

const errors = [];
for (const [i, row] of rows.entries()) {
  if (!row.email?.includes("@")) {
    errors.push({ rowNum: i + 2, reason: "invalid-email", value: row.email });
  }
}
if (errors.length) {
  await logger.warn("xlsx validation failures rows=%d", errors.length);
  await logger.debug({ stage: "xlsx-validate", errors });
}

msg.payload = {
  valid: rows.filter((_, i) => !errors.find(e => e.rowNum === i + 2)),
  errors,
};
return msg;
```

A `log-tap` after this node sees only the final shape of `msg.payload`. The `await logger.*` calls inside surface the *intermediate* state — sheet/row counts, per-row validation failures, the validation stage marker — that you'd otherwise have to reconstruct by re-running with different log-tap placements.

`logger.debug(...)` is the only way to emit a `debug`-level entry from inside a function node that's visible in the editor sidebar — `node.log` cannot reach either surface.

### "logs" vs. "logger" — two retrieval surfaces

"logs" and "logger" are overloaded. When working in the Flow Editor, they almost always mean the **debug drawer** for the current editor session — read it with the `logger_messages` MCP tool. That surface is **ephemeral and editor-only**: it exists while the flow is open in the editor and reflects this session's runtime. It is distinct from **Tenant Logs** — the persistent emissions of running/deployed agents, retrieved with the `ctxl logs` CLI family in the `solai-cli` skill (and CLQL-queryable). CLQL applies to Tenant Logs only; it has no meaning for the debug drawer.

| | Flow Editor logger (debug drawer) | Tenant Logs |
|---|---|---|
| Retrieve with | `logger_messages` (this MCP) | `ctxl logs` family (CLI, `solai-cli` skill) |
| Lifetime / scope | Ephemeral; this editor session only | Persistent; tenant-wide, across runs |
| CLQL | No | Yes (`--clql-file`) |

**Routing:** in the editor, bare "check the logs/logger" → `logger_messages`. Switch to Tenant Logs only on explicit cues — "agent / deployed / prod / over the last hour / session id / query / CLQL." When context and cues conflict (e.g. a flow that's both open here *and* deployed), ask: "the editor's debug drawer for this session, or the tenant logs from the deployed agent?"

Note: the same `await logger.*` / `log-tap` output can appear in **both** — the editor drawer during editor runs and Tenant Logs from deployed agent runs (see the logging table above) — so the question is which *retrieval surface* is wanted. And both are served by the same `ctxl` binary — `ctxl logs` is a direct command; the editor logger rides the `ctxl mcp serve` bridge — same binary, **distinct channels**; the shared origin is not a reason to treat them as one.

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

## Loop node (`loop` — based on `node-red-contrib-loop`)

The loop node iterates by re-receiving the per-pass message on its own input. **Port 1 (pass-of-loop) must close back into the loop's input port** — wiring port 1 to a terminal like `contextual-end` is wrong and produces a silent zero-iteration fall-through to port 0. Port 0 (end-of-loop) is the iteration's terminal.

**Wiring pattern:**

```
upstream → loop.in
           loop.out[0] (end-of-loop) → terminal node (contextual-end / http-response / etc.)
           loop.out[1] (pass-of-loop) → per-pass chain → back to loop.in
```

**Three import-time gates that all silently fail to a port-0-only firing** (the loop "completes" with no error, no catch firing, no warning — just zero iterations):

1. **Missing feedback wire from the per-pass chain back to `loop.in`** (see above).
2. **`enumeration` field defaults to `msg.enum`.** If the iterable lives elsewhere (typically `msg.payload`), set `enumeration: "payload"` with `enumerationType: "msg"` on import.
3. **`kind` must be a short code: `"fcnt"`, `"cond"`, or `"enum"`.** Never accept long-form labels (`"enumeration"`, `"fixed count"`, etc.) into the import payload — they're persisted but unrecognized by the form widget, and the loop falls back to fixed-count behavior with empty `count`.

**Per-pass `msg` shape (enumeration kind, correctly configured):**

| Property | Value |
|---|---|
| `msg.loop.value` | The current item |
| `msg.loop` | Full loop-state object (`index`, `value`, `key`, etc.) |
| `msg.payload` | Determined by `loopPayload` mode — see table below |
| `msg["loop-val"]` | Always undefined. `loop-val` is a *mode name*, not a msg property. |

**`loopPayload` mode selector** (what gets written to `msg.payload` each pass):

| Mode | Effect |
|---|---|
| `loop-keep` | Unchanged from upstream |
| `loop-orig` | The original full iterable |
| `loop-index` | Numeric 0-based pass index |
| `loop-val` | Current item value |
| `loop-key` | Current key (objects/maps) |

**Silent failure modes to verify against:** missing iterable, empty array, wrong `kind`, missing feedback wire — all produce a clean port-0-only firing with no error, no catch, no warning. After importing or modifying a loop, **explicitly verify port 1 fires the expected number of times** before considering the loop functional.

**Iterating an envelope's keys instead of an array.** A loop downstream of any record source can silently iterate the wrong thing if upstream returns its records inside an envelope object. When configured with `enumeration: "payload"` and `enumerationType: "msg"`, the loop enumerates an object's keys when given an object — not the array inside. Common case: `query-native-object` with a page size of `2` or greater returns an envelope containing `items` and, conditionally, `totalCount` and `nextPageToken`. A downstream loop therefore runs one to three times — once per envelope property present — not once per record. It can even run once for an empty `items` array when the query matches no records. `validate` reports nothing.

**Diagnostic recipe** (generic — applies any time a loop iterates a suspicious number of times after a record source): have the per-pass function log `msg.loop.key` and `Array.isArray(msg.payload)`. If `key` is a string like `items` / `totalCount` / `nextPageToken` / `records`, the loop is enumerating an envelope's keys, not an array. Either target the inner array via `enumeration: "payload.items"` (or whatever the wrapper field is), or insert an unwrap function (`msg.payload = msg.payload.items; return msg;`) between the upstream node and the loop.

**Minimal valid enumeration-loop import payload** (iterating `msg.payload`, item on `msg.payload` per pass):

```json
{
  "id": "<loop-id>",
  "type": "loop",
  "z": "<tab-id>",
  "name": "Iterate items",
  "kind": "enum",
  "enumeration": "payload",
  "enumerationType": "msg",
  "loopPayload": "loop-val",
  "x": 400,
  "y": 200,
  "wires": [
    ["<end-of-loop-handler-id>"],
    ["<per-pass-handler-id>"]
  ]
}
```

Wire the per-pass handler chain so its terminal output wires back to this loop's id.

---

## Other supported nodes

`comment`, `inject`, `catch`, `switch`, `change`, `range`, `delay`, `trigger`, `rbe`, `split`, `join`, `sort`, `batch`, `template`, `status`, `MSSQL`, `sse-client`, `odbc`, `gql`, `kafka-producer`, `source-from`, `sink-collect`, `map`, `batch-source`, `filter-source`, `read-stream`, parsers: `csv`, `html`, `json`, `xml`, `yaml`
