# Contextual CLI Reference

Use this as the compact command map for `ctxl`. It tracks the current CLI README while limiting the skill to non-destructive operations.

## Output Formatting

JSON output is **compact (single-line) by default**. Pass `--pretty` to indent and line-break for human reading; omit it when piping into `jq`, `python3 -c`, or another consumer:

```bash
ctxl config current --json               # compact
ctxl config current --json --pretty      # pretty-printed
```

`--pretty` is supported on the `services`, `servicereleases`, `records`, `recordversions`, `recordaudittrail`, `types`, and `config` topics. Empirically: large responses (e.g. `servicereleases list` with inline `data`) can exceed 800KB even compact — for routine inventory work, prefer commands and flags that omit inline record bodies (see the `--with-data` note in [Services](#services)).

## Config

- `ctxl config list --json`
- `ctxl config current --json`
- `ctxl config get [CONFIG-ID] --json`
- `ctxl config add CONFIG-ID [--tenant-id TENANT-ID]`
- `ctxl config use CONFIG-ID`
- `ctxl config login`

## Records

- `ctxl records add [URI] --type TYPE --input-file FILE`
- `ctxl records get [URI] --type TYPE --id ID [--version N]` — `--id` may be repeated for multiple records; URI fragment `native-object:TYPE/ID#N` selects a specific version. `--version` is incompatible with multiple `--id`.
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
- `name` is a **display label**, not a tenant resolver. By convention the dashboard sets it to the active tenant id (e.g. `"my-tenant"`); you can do the same. The runtime ignores this field — orgId and tenant are resolved from the request context, not from this field.
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

## Record Versions

When a type has versioning enabled, every write produces a numbered version. These commands operate on that history.

- `ctxl recordversions list [URI] --type TYPE [--id ID] [--order-by FIELD:desc] [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress]`
- `ctxl recordversions diff URI VERSIONS [--format console|json|jsonpatch] [--no-moves] [--object-keys KEYS]` — **URI form only** (see note)
- `ctxl recordversions rollback [URI] --type TYPE --id ID --version N [--do-not-bump]` ⚠️ write — see foot-guns below

Aliases: `rv list`, `recordversions search`, `rv search`; `rv diff`; `rv rollback`.

URI fragment `native-object:TYPE/ID#N` selects a specific version (same syntax as `records get`).

> **`diff` requires the URI form.** Unlike `list` and `rollback`, `diff` takes `VERSIONS` as a second positional argument — and oclif cannot skip the first positional. Passing `--type FOO --id BAR 4..7` makes oclif assign `4..7` to the URI slot, which fails URI-regex validation. Always invoke as `ctxl recordversions diff native-object:TYPE/ID 4..7`.

**Version-range syntax for `diff`:**

| Form | Meaning |
|---|---|
| `5..7` | explicit range, version 5 vs 7 |
| `7^` | version 7 vs 6 (one parent) |
| `7^^^` | version 7 vs 4 (count `^`s) |
| `7~3` | version 7 vs version 7−3 = 4 |

**`diff` output formats** (`--format`):
- `console` (default) — colorized human-readable diff
- `json` — raw `jsondiffpatch` delta
- `jsonpatch` — RFC 6902 JSON Patch

`diff` exits with code **1 when versions differ**, **0 when identical**. Useful for scripting, but means a non-zero exit is not necessarily an error — check the output.

**Handling large diffs.** Flow records routinely produce 30KB+ console diffs once you cross more than a handful of node moves. The default `console` format is meant for human eyes; piping it back into the model is wasteful. Three patterns, in order of preference:

1. **Summarize via `--format jsonpatch`.** Pipe through `jq` or Python to count operations by type and surface representative paths — far more useful than a wall of text:
   ```bash
   ctxl recordversions diff native-object:flow/my-flow 4..7 --format jsonpatch \
     | python3 -c "import json,sys; p=json.load(sys.stdin); ops={}
   [ops.setdefault(o['op'],[]).append(o['path']) for o in p]
   for k,v in ops.items(): print(f'{k}: {len(v)}'); [print(f'  {x}') for x in v[:5]]"
   ```
2. **Suppress array-move noise** with `--no-moves` when reordered nodes (common in flows after a layout shuffle) are dominating the diff and you want only structural changes.
3. **Redirect raw diff to a file, then slice with `grep`/`awk`/`jq`** when full review or targeted inspection is needed:
   ```bash
   ctxl recordversions diff native-object:flow/my-flow 4..7 > /tmp/flow-diff.txt
   grep -n "<node-id-of-interest>" /tmp/flow-diff.txt
   ```
   Don't reach for the `Read` tool here — its default cap (~25K tokens) matches MCP output (not larger), and it tokenizes the **whole file** before applying offset/limit, so very large diffs are refused outright regardless of the slice you ask for. Shell tools are the way through.

**`rollback` behavior:**
- Default — appends a new version at the top with the content of version `N`. Full history preserved; recoverable.
- `--do-not-bump` — **truncates** every version past `N`. Irreversible. Disallowed in this skill (see bottom).

## Record Audit Trail

The audit trail is the log of user-attributable mutations to records. Distinct from the version history (which stores record content per version) — the audit trail records *who/when/what action*.

- `ctxl recordaudittrail list [URI] --type TYPE [--id ID] [--order-by FIELD:desc] [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress]`

Aliases: `ra list`, `recordaudittrail search`, `ra search`.

> **Default ordering differs from `records list` / `types list`.** Both `recordversions list` and `recordaudittrail list` default `--order-by` to `_metaData.createdAt:desc` (newest first). `records list` and `types list` have no default ordering — the server returns its natural order. Pass `--order-by` explicitly when you need a specific order on the latter two.

> **Counting without pulling bodies.** Pair `--include-total --page-size 1` on any `list` command (`records list`, `types list`, `recordversions list`, `recordaudittrail list`) to get a `totalCount` in one round-trip. The CLI accepts `--page-size 0` but **the server silently ignores it** and falls back to its default page (~25 items) — always use `1`, not `0`. Caveat for `recordversions list`: the single returned body is still the full record content per version (for flows that's the entire `node_red_data`, typically 50–100KB). Significant saving over pulling all versions; not zero-cost. Empirically verified against a flow with 38 versions: 1.8MB at `--page-size 0` (server-ignored) → 90KB at `--page-size 1` → both report `totalCount: 38` correctly.

## Services

Services are the canonical, portable deployment primitive on Contextual: a versioned, release-managed package of native-object dependencies pulled by a target tenant from a source tenant. Scope is flexible — a service may represent a microservice, an app, a use case, or any other deployable unit; the publisher decides what to bundle.

- `ctxl services list [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress] [-s FIELD=VALUE] [--exact-search FIELD=VALUE] [--from FIELD=VALUE] [--to FIELD=VALUE] [--order-by FIELD:desc]`
- `ctxl services get [ID] [--id ID]... [--with-data]` — `--id` may be repeated to fetch multiple services in one call
- `ctxl services patch ID [--add-direct URI]... [--add-peer URI]... [--remove-direct URI]... [--remove-peer URI]... [--set-direct URI]... [--set-peer URI]...` ⚠️ write — see write discipline below

Aliases: `services search` -> `services list`.

### Owned vs. installed services

Two service shapes exist on a tenant. Detect the distinction by checking for `sourceTenantId` on the response.

| | Owned | Installed |
|---|---|---|
| `sourceTenantId` | absent | present (source tenant id) |
| Extra fields on `list` / `get` | none | `releaseTrack`, `description`, `endpoint`, `sourceTenantId` |
| Pull updates from upstream | n/a | yes — `servicereleases list --updates` and `updatediff` apply |
| `services patch` | mutates working manifest in advance of cutting a new release | technically possible but pointless — installed manifests are reset to upstream content on the next update |

### Dependency entries

Each dependency is `{ typeId, instanceId?, version, data? }`:

| Form | Meaning |
|---|---|
| `{ typeId: "<type-id>", version: N }` (no `instanceId`) | The **object type definition** itself, at that version. |
| `{ typeId, instanceId, version }` | A typed **instance** record at the pinned version. |

Common `typeId` values mirror the platform native-object types: `flow`, `agent`, `api-configuration`, `ai-route`, `authorization-code-app`, `jwks-configuration`, plus any custom object type IDs.

Two dependency classes carry different semantics:

- `direct` — dependencies the service owns; the service release is the source of truth for these versions in any target tenant. Subject to pruning at update time (see [Update-time pruning of direct deps](#update-time-pruning-of-direct-deps)).
- `peer` — dependencies the host context is expected to provide; **not** subject to pruning at update time.

### Patch URI format

`services patch` flags take a URI in the same form used elsewhere in the CLI; the CLI parses it into `{ typeId, instanceId, version }` and sends a structured patch to the services API:

| URI form | Meaning |
|---|---|
| `native-object:<type-id>#N` | The type definition at version N. |
| `native-object:<type-id>/<instance-id>#N` | A typed instance at version N. |

```bash
ctxl services patch my-service \
  --set-direct native-object:my-type#42 \
  --add-direct native-object:api-configuration/my-connection#3 \
  --config-id <config-id>
```

### `--with-data` size note

Without `--with-data`, `services get` returns the manifest list only (~hundreds of bytes per dep). With `--with-data`, each entry is hydrated with the full underlying native-object record — flows carry the entire `node_red_data`, typically 30–100KB per flow. A six-dep service can exceed 800KB. Use `--with-data` only when you specifically need inline record bodies; for routine inventory, skip the flag and fetch individual deps on demand with `ctxl records get`.

### Working version vs. released version

`services get` returns the current working manifest with a `version` integer that increments on **both** `services patch` calls and release snaps. Snapping a release (in the workspace UI) atomically bumps the working `version` by +1 as part of the snap transaction. So immediately after a release is cut:

- `service.version` equals `(latest_released_version) + 1`
- The working manifest's direct-dep pins are byte-identical to the just-snapped release

That post-snap state is the **normal baseline, not a pending change**. Working `version` advances further only on subsequent `services patch` calls. Because of this, `servicereleases get -v <service.version>` will 404 on the post-snap baseline (no release record exists at that version yet) — expected, not an error.

> **Services have no audit trail.** `ctxl recordaudittrail --type service` returns `404 Type 'service' not found`. Services are not records, so the record audit trail surface does not apply. To investigate when a service was last patched or snapped, compare `_metaData.updatedAt` on the service against `_metaData.createdAt` on the latest release.

### Write discipline for `services patch`

Apply the same discipline as `records patch` / `records replace`:

1. Read the current manifest (`services get <id>` without `--with-data`).
2. Project the patch — for each flag, compute the resulting dependency list and surface the field-level diff against the current manifest.
3. Show the planned flags and the diff to the user; ask for explicit confirmation.
4. Invoke `services patch ID ...` only after confirmation.
5. Re-read with `services get <id>` and verify the resulting `version` and dependency state.

The `solai-release-manager` skill provides a structured pre-patch advisor (cherry-pick mode); for ad-hoc patches via this skill, hand-roll the diff against `services get` output.

## Service Releases

Service releases are the immutable, versioned snapshots that target tenants pull. Each release pins every direct and peer dependency to a specific version, carries a `releaseTrack`, and may include human-authored release notes (`description`).

- `ctxl servicereleases list [ID] [--updates] [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress] [-s FIELD=VALUE] [--exact-search FIELD=VALUE] [--from FIELD=VALUE] [--to FIELD=VALUE] [--order-by FIELD:desc]`
- `ctxl servicereleases get [ID] -v N [-v M]...` — `--version` may be repeated to fetch multiple releases
- `ctxl servicereleases diff ID VERSIONS [--format console|json|jsonpatch] [--no-moves] [--object-keys KEYS]`
- `ctxl servicereleases updatediff ID -v N [--format console|json|jsonpatch] [--no-moves] [--object-keys KEYS]`

Aliases: `sr list`, `servicereleases search`, `sr search`; `sr get`; `sr diff`; `sr updatediff`.

### Release track values

Each release is on one of four tracks (workspace UI exposes the same set):

| Track | Meaning |
|---|---|
| `development` | In-progress or experimental; not promoted for staging. |
| `release-candidate` | Stable for staging; not yet promoted to general availability. |
| `general-availability` | Promoted to general availability. |
| `removed-from-distribution` | Deprecated; should not be installed or updated to. |

### Release object shape

```json
{
  "id": "<service-id>",
  "name": "<display name>",
  "version": N,
  "releaseTrack": "general-availability",
  "description": "release notes...",
  "dependencies": {
    "direct": [
      { "typeId": "<type-id>", "instanceId": "<instance-id>", "version": M, "data": { "...full native-object record..." } }
    ],
    "peer": []
  },
  "_metaData": { }
}
```

`dependencies.direct[].data` carries the full native-object record at the time the release was cut. Same large-output caveats apply as `services get --with-data`.

### Diff scope and version-range syntax

`servicereleases diff` and `servicereleases updatediff` reuse the same version-range mini-grammar and `--format` options as `recordversions diff` — see [Record Versions](#record-versions). One scope detail to keep in mind: the diff is computed over the `dependencies` sub-tree only, so `jsonpatch` paths start at `/direct/...` or `/peer/...`, not `/dependencies/direct/...`.

### Which read paths route via `sourceTenantId`

For installed services, release records live on the **source tenant**, not the target tenant. Among the `servicereleases` read commands, only `--updates` and `updatediff` route the request through `sourceTenantId`; `servicereleases get` and `servicereleases list` (without `--updates`) hit the target tenant directly and **404** for releases the target has never pulled.

| Command | Routes via `sourceTenantId` on installed services? | Behaviour on a release that lives only on source |
|---|---|---|
| `servicereleases list <id> --updates` | yes | returns the release inline in the items list |
| `servicereleases updatediff <id> -v N` | yes | returns the diff against the installed manifest |
| `servicereleases get <id> -v N` | no | **404** "Service release not found" |
| `servicereleases list <id>` (no `--updates`) | no | returns only releases the target tenant has locally |
| `servicereleases diff <id> N..M` | no | requires both versions visible to the target tenant |

Practically: to inspect an incoming upstream release from a target tenant, use `--updates` and read the release object inline from the items list — do not chain a separate `servicereleases get`.

### `--updates` and `updatediff` semantics

Both commands return `Cannot fetch updates for an owned service` on owned services (no `sourceTenantId`). On installed services:

- `servicereleases list <id> --updates` — lists upstream releases with version greater than the currently installed version. Each item is the full release object (`id`, `version`, `releaseTrack`, `description`, `dependencies.direct[]` with inline `data`, `_metaData`). `totalCount: 0` means no upgrade candidates available.
- `servicereleases updatediff <id> -v <target-version>` — diffs the installed manifest against the candidate upstream release. Can return non-empty output even when comparing against the currently installed version, because the installed copy may lack metadata fields (e.g. `hash`) that the upstream record carries. **`--updates totalCount == 0` is the authoritative "no upgrade available" signal**, not an empty `updatediff`.

### Update-time pruning of direct deps

When a target tenant applies a service update, direct dependencies are reset to the versions pinned in the incoming release. Any version of a direct-dep record that exists in the target tenant **above** the incoming pinned version is **pruned** — those incremental versions (typically applied as hotfixes between updates) are lost. Versions **below** the incoming pinned version are preserved in the record's version history.

Peer dependencies are not subject to this pruning behaviour.

The platform behaviour today does not warn at update time. The `solai-release-manager` skill provides a structured pre-update audit that walks each direct dep, identifies hotfix drift in the target tenant, and produces a markdown assessment artifact — see that skill for the workflow. Use it before applying any service update in the workspace UI.

### Routine workflow

For release management end-to-end (pre-update hotfix-drift audit on target tenants, pre-publish cherry-pick advisor on source tenants), use the `solai-release-manager` skill rather than orchestrating from raw CLI calls.

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
- `ctxl recordversions rollback --do-not-bump` (and the `rv rollback --do-not-bump` alias) — irreversibly truncates version history past the target. Plain `rollback` without this flag is allowed (history is preserved and the operation is recoverable).
