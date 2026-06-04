# Changelog

All notable changes to the Solution AI Connect plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.4] — 2026-06-04

Adds documentation and release-management tooling for the `services` and `servicereleases` topics introduced in recent `@contextual-io/cli` builds, and ships a new `solai-release-manager` skill that wraps two workflows on top of the new CLI surface: a pre-update hotfix-drift audit for services installed from another tenant, and a pre-publish cherry-pick advisor for services owned on the current tenant. Also documents the new `logs` topic (`ctxl logs`, `ctxl logs backlog`, `ctxl logs backlog flush`) and the `--fields` positive field-projection flag landed on every list command, with a safe-consumption discipline framing the logs surface as a passthrough for tenant-flow-emitted content (`log-tap` and similar nodes serialize what they receive without platform-side redaction — flows that log request/response objects naturally surface `Authorization` headers, bodies, and cookies, so agents project to the envelope with text tools before ingestion — `ctxl logs` emits line-formatted text, not JSON). Refreshes the MCP section for `@contextual-io/cli` 0.11 — the `--trace` verbosity flag on `ctxl mcp serve` and a new `ctxl mcp debug` connectivity diagnostic, hard-gated as a last resort so a missed approval dialog is recovered by re-triggering rather than chasing a diagnostic. Also documents the HTTP ingress payload-cap delta between the Flow Editor preview runtime (~2 MB) and a deployed `flow-http` agent runtime (40 MB). Primary tickets (CTX-3451, CTX-3522, CTX-3492); related to (CTX-3504), (CTX-3464), (CTX-3517).

### Added

#### `skills/solai-release-manager/` (new skill)

- `SKILL.md` orchestrates two workflows on top of the new services CLI surface, branching on whether the active service is **installed** (`sourceTenantId` present) or **owned** (absent). Two modes per workflow:
  - **Preview** — fast advisory report, no acknowledgement collection. Use for "what am I about to walk into?" inspection before the workspace UI.
  - **Assessment** — interactive walkthrough that writes a markdown artifact with checkbox slots per detected hotfix (`Back-port to source` / `Apply (or confirm) env-appropriate override at update time` / `Accept loss`) plus notes. Intended as the formal record paired with the actual update applied in the workspace UI.
- `scripts/service_manifest_summarize.py` — compact manifest table for a service (working manifest or a specific release), optionally diffed against another release with per-dep tenant-max version lookup. Strips inline `data` from `services get --with-data` / `servicereleases get` output so routine inventory stays well under the megabyte an unfiltered manifest dump can produce on a multi-dep service.
- `scripts/hotfix_drift_report.py` — pre-update audit on an installed service: sources the incoming release inline from `servicereleases list --updates` (the only read path that routes via the source tenant's `sourceTenantId` — `servicereleases get` would 404 on the target tenant), walks each direct dep, compares against the tenant's current state via `recordversions list ... --page-size 1 --order-by version:desc`, summarises `recordversions diff --format jsonpatch` ops for any pruning candidates (handling the `recordversions diff` exit-code-1-when-versions-differ semantic correctly), classifies each op as one of three buckets — **functional change**, **env-override-pattern divergence** (endpoint / secret / size / envVars keywords), or **platform-metadata noise** (`_metaData/*` paths that always change on save) — and surfaces a metadata-only-drift summary when a record was re-saved without a content change. Emits markdown via `--mode preview` (stdout) or `--mode assessment --output <path>` (checkbox-bearing artifact). Defaults `--incoming-version` to the highest available upstream update.
- Both scripts are read-only: they never invoke `services patch` or any other write. The skill is explicit that it never enacts a service install / update / release-snap — those remain workspace UI actions today; the skill produces the report and patch plan the user takes into the UI.
- **Permission-setup UX** in `SKILL.md`: first-invocation-per-session step presents a **three-way choice**: (1) default prompt-each-time, (2) helper scripts only, (3) helper scripts + narrow read-only `ctxl` patterns the skill uses directly (`services list/get`, `servicereleases list/get/diff/updatediff`, `config current/list`). The third option provides a friction-free read workflow while keeping all writes (`services patch`, `records patch`, `records replace`, `recordversions rollback`, etc.) prompting because they are deliberately not in the allow-list. JSON snippets for `.claude/settings.json` are provided for each option, plus neutral guidance for other shell-sandboxed environments. Explicitly warns against broad write-covering patterns (`Bash(ctxl services *)`, `Bash(ctxl records *)`, `Bash(ctxl types *)`, `Bash(ctxl recordversions *)`, `Bash(ctxl * patch *)`, etc.) and includes an audit step that inspects the existing `permissions.allow` array, surfaces any already-present broad write-covering patterns as a tightening opportunity, and never modifies existing rules without explicit confirmation.
- **Reference-read discipline** in `SKILL.md`: runtime checks instruct the agent to read the entire `solai-cli/cli-reference.md` in one pass on entry, explicitly *not* grepping for specific sections. Section-specific grepping was observed to miss cross-cutting content (Output Formatting, large-payload warnings, source-tenant routing table) that the agent then needed mid-workflow.
- **Assessment-artifact default path**: `hotfix_drift_report.py --mode assessment` now defaults `--output` to `./release-assessment-<service>-<UTC-timestamp>.md` in the current working directory when omitted. Previously the skill template wrote artifacts into the plugin install directory (`${CLAUDE_SKILL_DIR}/.local/assessments/...`), which is version-pinned and gets wiped on plugin reinstall. `SKILL.md` now instructs the agent to ask the user where to save (default CWD, accept any override) and explicitly warns against writing to the plugin install directory.
- **Permission walk: piped-segment behaviour + `jq` preference**. The permission walk in `SKILL.md` now documents that Claude Code's Bash allow-list **splits piped commands on shell operators** (`|`, `&&`, `||`, `;`) and matches each subcommand independently — so an idiom like `ctxl ... | python3 -c "..."` needs **both** segments allow-listed, not just the first. Option 3 of the three-way choice now includes `Bash(jq *)` so the agent's inline-parse idiom (`ctxl ... | jq '...'`) is prompt-free; `jq` is read-only and safe to broadly allow-list, unlike `python3 -c '...'` which can execute arbitrary code. New hard rule directs the agent to **prefer `jq` over `python3 -c` for inline JSON parsing**, reserving `python3 -c` for genuinely complex transformations. Also documents that Claude Code **hot-reloads `permissions` rules live** — no session restart needed for newly added allow patterns to take effect.

#### `skills/solai-flow-editor/node-reference.md`

- New **"HTTP ingress payload limits — editor runtime vs. agent runtime"** section. Documents the runtime-side ingress cap delta: the Flow Editor's preview runtime caps HTTP request bodies at ~2 MB (`nginx client_max_body_size: 2m`), while a deployed `flow-http` agent's runtime accepts up to 40 MB. Includes the practical routing implication — testing large-payload ingress requires binding the flow to an agent and exercising the agent's runtime endpoint rather than the editor preview — and a diagnostic tip for spotting the cap as the cause of opaque `413 Request Entity Too Large` responses.

### Changed

#### `skills/solai-cli/cli-reference.md`

- New `## Output Formatting` section near the top: JSON output is compact (single-line) by default; pass `--pretty` for indented output. Covers all topics that emit JSON. Includes the empirical caveat that large responses (e.g. `servicereleases list` with inline `data`) can exceed 800KB even compact — for routine work, prefer flags that omit inline record bodies.
- New `## Services` section: ownership model (owned versus installed, detected by `sourceTenantId` on the response), dependency entry shape (`typeId / instanceId? / version / data?`) with the type-definition vs typed-instance distinction (`instanceId` absent means the type definition itself, versioned), direct versus peer semantics, the `services patch` URI form (`native-object:<type-id>#N` or `native-object:<type-id>/<instance-id>#N`), the `--with-data` size note, and write discipline for `services patch`.
- **Working-version mechanic clarified** in the Services section: snapping a release atomically bumps the working `version` by +1 as part of the snap transaction (verified empirically by timestamp delta on a snap). Immediately post-snap, `service.version` equals `(latest_released_version) + 1` and the working manifest's direct-dep pins are byte-identical to the just-snapped release — the **normal baseline, not a pending change**. Working `version` advances further only on subsequent `services patch` calls. `servicereleases get -v <service.version>` 404s on the post-snap baseline — expected, not an error.
- **Services have no audit trail**: `ctxl recordaudittrail --type service` returns `404 Type 'service' not found`. Documented as a note under the working-version subsection; suggests comparing `_metaData.updatedAt` on the service against `_metaData.createdAt` on the latest release to investigate timing.
- New `## Service Releases` section: the four `releaseTrack` values (`development`, `release-candidate`, `general-availability`, `removed-from-distribution`), the release object shape (`id`, `name`, `version`, `releaseTrack`, `description`, `dependencies`, `_metaData`), diff scope (computed over `dependencies` only — `jsonpatch` paths begin at `/direct/...` or `/peer/...`, not `/dependencies/direct/...`), and the **update-time pruning of direct deps** semantics — at update, any direct-dep record version in the target tenant that exceeds the incoming pinned version is pruned (peer deps are not). Cross-refers to `solai-release-manager` for the structured pre-update audit.
- New **"Which read paths route via `sourceTenantId`"** subsection under Service Releases: table mapping each `servicereleases` read command (`list --updates`, `updatediff`, `get`, `list`, `diff`) to whether it routes via the installed service's `sourceTenantId`. Documents the gotcha that `servicereleases get -v N` 404s on installed services for releases the target tenant has never pulled, because only `--updates` and `updatediff` route via the source. Recommends using the inline release object from `--updates` rather than chaining a separate `get`.
- New **"Field projection on `list` commands"** subsection under `## Output Formatting` documenting `--fields <comma-separated-paths>` on every list topic (`records list`, `types list`, `recordversions list`, `recordaudittrail list`, `services list`, `servicereleases list`). Positive projection — server returns only the named paths per item. Motivated by the CTX-3517 measurement that a single service's `servicereleases list` can exceed 30 MB driven by inline `dependencies.direct[].data`. Cross-referenced from `## Service Releases` → `### Release object shape`.
- New **`## Logs`** section (placed between Service Releases and Platform Type IDs) covering:
  - `ctxl logs [SUB-KIND]` with the flag table (`-f, --follow`, `-l, --level` repeatable, `--since` relative duration, `--since-time` ISO8601 zulu, `-s, --sub-kind`, `-t, --tail` defaulting to `-1` / max page-size 250, `-q, --clql-file` server-side CLQL query from a file or stdin, `--pretty`). Documents `--since` / `--since-time` as mutually exclusive and notes that follow mode ignores page-based filters.
  - **subKind auto-expansion** — `ctxl logs <x>` matches both `<x>` and `<x>-agent-<silo>` on the active silo; pass the fully-qualified form to disable expansion.
  - Output line format (`<createdAt> [<typeId>/<instanceId>] [<sessionId>] <level>: <message>`) and the `--pretty` switch (Node `util.inspect` `%o` vs. `JSON.stringify`). Notes that `ctxl logs` output is line-formatted text, not JSON — not `jq`-parseable; project with `sed`/`awk` or filter server-side with `--clql-file`.
  - `LogMessage` shape table (`id`, `createdAt`, `level`, `kind` ∈ `trigger|action|execution`, `subKind`, `typeId`, `instanceId`, `sessionId`, optional `correlationId`, `source`, `type` ∈ `string|json`, `message`).
  - `ctxl logs backlog` (GET) and `ctxl logs backlog flush` (DELETE — flagged ⚠️ write, irreversible).
  - Common-patterns block with concrete invocations (error tail with `--since 5m`, follow with auto-expansion, fully-qualified subKind with absolute time cutoff).
- New **`### Safe consumption patterns`** subsection under `## Logs` framing the logs surface as a passthrough for content emitted by tenant flows — `log-tap` and similar nodes serialize whatever object they receive without platform-side redaction, so HTTP-handling flows that log request/response objects naturally surface `Authorization` headers, bodies, and cookies. Frames the discipline for both ends of the pipe: flow authors should be intentional about what `log-tap` receives (log keys and shapes, not whole objects); log consumers — especially AI agents — should project to the envelope by default. Section documents three consumption patterns: (1) **envelope-only projection** as the default (text-based `sed` against the line format — drops `message` entirely; usable for "what's happening?" queries without exposing payload content; `ctxl logs` is text, not `jq`-parseable), (2) **targeted message inspection with JWT redaction** via `sed` (when the user explicitly asks to expand a specific log's payload), (3) **`--follow` discipline** that always projects before any stdout-consumer in the agent's context sees a line, bounded by `head -N` or `timeout`. Also covers `backlog` projection (which *is* JSON, so `jq` applies there).
- **MCP section updated for CLI 0.11**: documents the new `--trace` flag on `ctxl mcp serve` (socket-level diagnostics, verbosity level 2 vs. `-V` level 1) and adds a `### ctxl mcp debug` subsection — a one-shot connectivity diagnostic (connect → ping → manifest → bind JSON report) with a scope note framing it as a last-resort tool for genuine connection failures, not a fix for a missed approval dialog.
- Agent Records "Key gotchas" extended with a bullet on the 40 MB `flow-http` agent ingress ceiling vs. the ~2 MB editor preview ceiling, cross-referring to the new `solai-flow-editor/node-reference.md` section for the routing detail.

#### `skills/solai-cli/SKILL.md`

- Write-discipline hard rule extended to name `services patch` explicitly: project the patch against current `services get` output, surface the dependency-list diff, ask for explicit confirmation. For full release-management workflows, defer to `solai-release-manager`.
- New hard rule for `ctxl logs backlog flush`: irreversible DELETE on the user's per-user log backlog. Must be its own confirmed step — show the user the current backlog content via `ctxl logs backlog` first, then ask explicitly before flushing. Not bundled into broader sequences.
- New hard rule framing **`ctxl logs` as a passthrough for tenant-flow-emitted content**. Because `message` is serialized by the emitting node (`log-tap` and similar) with no platform-side redaction, HTTP-handling flows that log request/response objects naturally surface `Authorization` headers, bodies, and cookies. Rule directs the agent to default to envelope-only projection (text-based `sed` for `ctxl logs`, which emits line-formatted text rather than JSON; `jq` for `logs backlog`, which returns JSON) before any logs output reaches the agent's context, and to expand `message` only when the user explicitly asks — paired with JWT redaction even then. Applies on tenants the user owns, not just third-party.
- `## Output Expectations` adds a bullet on the compact-by-default JSON + `--pretty` convention for human-facing output.
- MCP guidance updated for CLI 0.11: notes the `--trace` verbosity level on `ctxl mcp serve`, and adds a hard rule gating `ctxl mcp debug` as a last-resort connectivity diagnostic — the missed-dialog recovery (re-trigger + watch the sidebar) stays primary; escalate to `mcp debug` only when the connection itself is suspect.

## [0.7.3] — 2026-05-15

Replaces the flow-editor hex-ID pre-generation rule with a placeholder/uniqueness rule that matches the import tool's actual contract, documents `node_update`'s silent no-op on the `wires` field, and refreshes the silent-failure catalogue against the empirically-confirmed list. Also adds an MIT LICENSE at repo root.

### Added

- `LICENSE` — standard OSI MIT license at repo root, copyright Contextual, Inc. The repo went public without an explicit license file; this formalizes it.

### Changed

#### `skills/solai-flow-editor/SKILL.md`

- **Sequencing rule 3 replaced.** Previous rule mandated pre-generated hex IDs via `secrets.token_hex(8)` before every `import`. Empirical testing against the live MCP confirmed the editor regenerates provided IDs under `preserveIds:false` (so hex IDs are no different from any short placeholder), and the actual invariant the rule was defending is *intra-batch uniqueness*: duplicate placeholder IDs silently drop the duplicate node, and numeric or empty-string `id`s silently drop the node entirely. New rule frames `id` in an import payload as a *placeholder used to resolve intra-batch wires*, requires uniqueness within the batch, and keeps the hex-ID recipe only as an optional uniqueness guarantee for payloads built in pieces.
- **Wiring discipline tightened.** `node_update` is now documented as a silent no-op on the `wires` field — both `changes:{wires:...}` and JSON Patch `/wires` paths return `status:"ok", updated:["wires"], valid:true` while leaving wires unchanged. Applies to adding a wire, redirecting an existing wire, and clearing wires. Verified directly against `node_update changes:{name:...}` which does mutate, confirming the no-op is scoped to the `wires` field specifically. The `wire` tool is the only path that modifies wires.
- **Silent-failure catalogue refreshed** in the skill-gate paragraph and the `nodeCount` verification rule. Replaces stale "missing pre-generated node IDs" framing with the empirically-confirmed list: cross-batch wire drops, intra-batch placeholder-ID collisions, invalid-`id`-type drops (numeric, empty string), and `node_update` wire no-ops.

#### `AGENTS.md`

- Silent-failure catalogue at the skill-gate updated to match the SKILL.md catalogue.
- "Hex-id pre-generation" example replaced with "wiring discipline" in the skill-bypass warning paragraph.

## [0.7.2] — 2026-05-12

Tracks `@contextual-io/cli@0.10.0`. CLI reference picks up the new `recordversions` topic, the new `recordaudittrail list` command, and the extended `records get --version` / `#N` URI fragment. Flow editor reference also picks up a new **Reserved `msg` keys** subsection for Native Object nodes, addressing a class of silent-override foot-guns observed when AI agents author flows.

### Added

#### `skills/solai-cli/cli-reference.md`

- New **`## Record Versions`** section covering `recordversions list`, `recordversions diff`, `recordversions rollback` (and their `rv …` aliases). Documents the `diff` version-range mini-grammar (`5..7`, `7^`, `7^^^`, `7~3`), the three `--format` options (`console` / `json` / `jsonpatch`), and the *non-obvious* `diff` exit-code semantics (1 when versions differ, 0 when identical).
- New **`## Record Audit Trail`** section covering `recordaudittrail list` (and the `ra …` aliases), framed against the version history so the two are not confused.
- New cross-cutting note on **default ordering asymmetry**: `recordversions list` and `recordaudittrail list` default to `_metaData.createdAt:desc`; `records list` and `types list` have no default ordering.
- `records get` synopsis updated to document the new `--version N` flag and the `native-object:TYPE/ID#N` URI fragment, including the rule that `--version` is incompatible with multiple `--id`.
- New **"Handling large diffs"** subsection under Record Versions: `--format jsonpatch` + summarization recipe, `--no-moves` for layout-noise suppression, and the redirect-to-file-then-Read pattern for full human review without inflating the shell-output preview path.
- New **"Counting without pulling bodies"** cross-cutting callout: `--include-total --page-size 1` on any `list` command returns `totalCount` in one round-trip. Documents the **`--page-size 0` server-ignore foot-gun** (CLI accepts it; server falls back to default page ~25), and the residual cost on `recordversions list` (single returned body is the full per-version record content). Empirically verified against a flow with 38 versions.

#### `skills/solai-flow-editor/`

- New **"Reserved `msg` keys"** subsection under Native Object nodes in `node-reference.md` documenting **15 reserved `msg` properties** (`objectId`, `typeId`, `query`, `search`, `filters`, `filterMode`, etc.) that **silently override** a node's configured value when set upstream — no runtime warning, no validation error. Addresses a class of foot-guns where SAI-authored function nodes write to `msg.objectId` / `msg.typeId` / `msg.query` and downstream Native Object node configuration is silently bypassed.
- `SKILL.md` updated with an explicit authoring-time callout for reserved `msg` keys on Native Objects, reinforcing the `node-reference.md` content at the skill-orchestration layer. Spot-check eval across six prompts (main vs. reference-only vs. reference + skill) showed a 3/6 → 4/6 → 5/6 pass rate, confirming the skill-level reinforcement carries weight beyond the reference doc alone.

### Changed

- **Disallowed In This Skill** list extended with `ctxl recordversions rollback --do-not-bump` (and the `rv rollback --do-not-bump` alias). Plain `rollback` without the flag remains allowed because version history is preserved and the operation is recoverable; only the history-truncating variant is destructive.

### Fixed

- `recordversions diff` synopsis corrected to **URI form only**. Earlier draft suggested `[--type TYPE] [--id ID]` was interchangeable with the URI argument as it is for `list` and `rollback`; in fact `diff` takes `VERSIONS` as a second positional, and oclif cannot skip the first positional, so flag-only invocation always misroutes the version range into the URI slot and fails URI-regex validation. Confirmed via clean-context test session.

## [0.7.1] — 2026-04-27

The first comprehensive release of the plugin since adopting verify-first empirical testing as the operating model for documentation evolution. This release lands a substantial body of empirically-verified reference content alongside foundational restructuring of the plugin's skills and agents.

### Added

#### Plugin baseline

- New root-level **`AGENTS.md`** providing always-loaded session context: platform identity (Contextual.io / Solution AI / SolAI naming), reserved component type map, live flow editing model with skill-gate enforcement, four-skill table with trigger conditions, six-agent table with role mapping, prerequisites, and hard limits.
- New **plugin update flow** via `claude plugin update ctxl@contextual-io`, replacing the previous no-op `autoUpdate` mechanism. User-facing output is restated in "Solution AI Connect plugin" terms rather than letting the raw `ctxl` marketplace output stand.
- New **"Contributing"** section in README with `.git/info/exclude` guidance for personal working files.

#### `skills/solai-flow-editor/`

- **Split** into `SKILL.md` (orchestration, behavioral rules, sequencing) + `node-reference.md` (node-specific reference, foot-gun catalogue).
- **Skill gate hardening**: required before any non-orientation `mcp__ctxl-flow-editor__*` call. Explicit trigger verb list (add, change, move, wire, delete, rename, configure, group, copy, validate, look at, check, read), exempt vs non-exempt tool list, three-step sequence when flow-editing intent is detected.
- **Skill scope expanded** beyond edit-only: now also the source-of-truth for node-level behavior, configuration, and authoring patterns (function-node logging, loop wiring, Native Object node TypedInput patterns, `http-response` status precedence, etc.) — so node-behavior Q&A routes here rather than to `solai-knowledge`.
- **Reading `node-reference.md` is now mandatory**, not advisory: explicit "not optional" framing with concrete foot-gun examples and the type_info-vs-node-reference asymmetry (*type_info reports defaults; node-reference warns when those defaults will throw at runtime*).
- **Sequencing Rule 4 restructured** to mandate node-reference consultation before any `import` or `node_update`: first confirm `node-reference.md` has been read this session and consult its entry for the node type, then call `type_info`.
- Platform-framing precedence ladder: `type_info` (live session) → `node-reference.md` + `SKILL.md` → `solai-knowledge`.
- "Reading node configuration" table: new "Wire / connection audit on a single node" row pointing at `flow_read action:"tab" includeNodeDetails:true` (the only path that returns wires per node today).

#### `skills/solai-flow-editor/node-reference.md` (new file)

- **Function-node logging surfaces** — `await logger.debug/info/warn/error(...)` is the right surface; `node.log(...)` is silently dropped; `node.warn`/`node.error` are vestigial Node-RED contract; `log-tap` for between-node observability. Includes Connection-first boundary for outbound I/O.
- **Loop node section** — wiring pattern (port 1 must close back to loop input), three import-time silent gates (feedback wire, `enumeration` source default, `kind` short codes — `fcnt`/`cond`/`enum`), per-pass `msg` shape, `loopPayload` mode selector table, minimal valid enumeration-loop import payload.
- **Loop downstream `includeTotal: true` envelope foot-gun** — when upstream wraps results in `{items, totalCount}`, default loop enumeration iterates the envelope's keys (twice, regardless of record count). Includes a generic diagnostic recipe for any wrong-iteration-count case.
- **Query Object node** (previously undocumented in any layer) — distinct from `search-native-object` (different filter models — MongoDB-style object vs array-of-criteria); `query: ""` foot-gun (guaranteed `JSON.parse("")` runtime throw); canonical match-all is `"{}"`; full MongoDB-style filter syntax table.
- **TypedInput pattern subsection** covering all Native Object nodes — `query`/`queryType`, `outputProperty`/`outputPropertyType`, `typeId`/`typeIdType`, `pageSize`/`pageSizeType`. Both halves of any TypedInput pair must be set explicitly on import; runtime Zod-rejects missing `*Type` companions even when `type_info` marks them `required: false`.
- **`http-response` status code and header precedence** — configured value on the terminal is authoritative; upstream `msg.statusCode` is silently ignored when configured value is non-empty; falls back to `msg.statusCode` only when the terminal's value is blank. Authoring patterns for static / dynamic / mixed cases. Diagnostic tip for the *"msg.statusCode log shows the right value but client receives the wrong one"* trap.
- **Native Object nodes intro** — `native-object-config` minimum record shape `{id, type, name}`; `id` load-bearing, `name` display label only, empty credential fields inert.
- **`patch-native-object`** input must be RFC 6902 JSON Patch array `[{op,path,value}]`, not a plain object.
- **Cross-batch wire rule** — any wire targeting a node outside the imported batch is silently dropped; always wire after import using the `wire` tool.
- **Tray sequencing** — `tray_open` before `tray_read`; `delete` requires `useSelectionAction` as a boolean, not a string.
- **Save vs Deploy terminology** — the editor button is "Save"; "Deploy" means binding a flow to an Agent for production execution.
- **HTTP nodes** — strong preference for Connection-native nodes (`http-get`, `http-post`, etc.) over the generic `http request` node.
- **`inject` HTTP route limitation** — `res` object cannot be JSON-serializable; use `contextual-test` nodes for HTTP route testing in-editor.
- **`log-tap` configuration** — confirmed level enum (`debug`, `info`, `warn`, `error`) from live tray; default config; in-catch-context config.
- **Function node return contract** — never `return null` as full return; multi-output array form; logging is not an endpoint.
- **Web application / front-end guidelines** — Bootstrap, Font Awesome, Mustache (not Handlebars), placeholder image services, form validation patterns.

#### `skills/solai-cli/`

- **Two-layer SKILL.md structure** — reference/guidance (always available) and execution (shell required) — so reference value isn't lost when shell is unavailable.
- **Plugin update check** on first invocation each session.
- **Tenant overview discipline** — parallel fetch of all six reserved component types (`flow`, `agent`, `ai-route`, `api-configuration`, `jwks-configuration`, `authorization-code-app`) plus custom types for "what's in my tenant?" queries.
- **Flow creation pattern** — CLI-stub + flow editor handoff: CLI creates a minimal lint-clean skeleton with full `catch → log-tap → error-response` chain, then hands off to the live editor for complex node content.
- **Live editor preference** — when `mcp__ctxl-flow-editor__*` tools are available and `list_sessions` returns sessions, recommend switching to `solai-flow-editor`.
- **Helper script narration** — `contextual_login.py` and `json_diff.py` both have user-facing narration before invocation.
- **Auth recovery** narration before login flow.

#### `skills/solai-cli/cli-reference.md`

- Flow skeleton patterns for **HTTP, event, and scheduled flows** — full error handling chain from the start.
- **Python heredoc requirement** for any complex content (HTML, JS, multi-line strings) — never inline in shell flags.
- **Hex node ID generation** with explicit narration ("using Python's built-in `secrets` module — standard random number generator").
- **`flows_cred` placement** corrected (inside `node_red_data`, not top-level).
- **Tab `env: []` preservation** for editing existing flows.
- **`/.editor` URL suffix** for browser handoff (without it, HTTP flows serve their root endpoint).
- **`ctxl types add` envelope** — full required shape (`id`, `type: "custom"`, `name`, `pluralName`, `description`, `display`, `defaultListStyle`, `objectType`, `features.auditTrail.enabled`, `features.version.enabled`, `schema`) with allowed values for the four envelope keys most commonly missed.
- **`ctxl types add` JSONL constraint** documented (parallel to the existing `records add` JSONL note).

#### `skills/solai-knowledge/`

- **Plugin update check** matching `solai-cli`.
- **Secondary-by-design framing** — frontmatter description scopes coverage to platform/runtime behavior NOT already covered by plugin-side reference content; redirects "what's the X shape?", "how do I configure node Y?", "what are the foot-guns on Z?" type questions to `solai-flow-editor` or `solai-cli`.
- **Precedence section** at the top of the body reinforcing plugin-first source-of-truth.
- **MCP-failure fallback rule** — if `search` errors twice in a row or returns no relevant hits after one query refinement, stop searching and switch to plugin-side reference content.

#### `agents/`

- `flow-editor.md` updated to load both `SKILL.md` and `node-reference.md` after the split.
- `plan-flow.md` description tightened to design-only; explicitly directs flow creation to `ctxl:solai-cli`.
- `seed-builder.md` typo fixed (`ctxl types:get` → `ctxl types get`).

### Changed

- **"Universal rule" in AGENTS.md**: source-of-truth precedence is now plugin-side reference content first (kept current via ongoing empirical verification against the live platform), `ctxl:solai-knowledge` second (for platform/runtime behavior not covered in plugin-side reference). Cross-cutting queries can run both in parallel.
- **"How to access plugin-side reference"** added to AGENTS.md and mirrored to `solai-cli` Hard Rules: invoke the relevant skill — do not `grep`, `find`, or otherwise enumerate the plugin install directory (`~/.claude/plugins/...`) directly.
- **"Correct empty flow shape"** in `cli-reference.md` corrected: `native-object-config` `name` is a display label, not a tenant resolver; empty credential fields are inert; tab is optional in the persisted record (the dashboard does not emit one).
- **README "Keeping Up to Date"** rewritten to reflect actual behavior — `autoUpdate` was found to be a no-op via empirical testing, replaced with the real `claude plugin update` command.
- **README "Publishing Updates"** updated to favor frequent patch releases (*"when in doubt, patch"*).
- **`solai-cli` package manager flexibility** — no longer prescriptive about npm; defers to user preference (`pnpm`, `yarn`, `bun`, etc.).
- **`solai-cli` hard rule for credential files** generalized from the specific `~/.config/ctxl/config.json` path.
- **Validate guidance** — distinguishes runtime-risk warnings (e.g. `require-catch-nodes`) from cosmetic warnings; never report "zero errors" if warnings exist.

### Fixed

- Removed deprecated `topics` reserved type from `cli-reference.md` (verified empirically against the registry — confirmed gone, not just unused).
- Tray-corruption foot-gun on native-object nodes documented (open in tray auto-commits and may corrupt `typeId`).
- Cross-batch wire drops correctly framed as silent and unconditional (not a sometimes-failure).
- `flow-editor` agent updated to load both `SKILL.md` and `node-reference.md` after the skill split.

### Notes

- This release establishes a **verify-first** operating model for plugin doc evolution: every reported behavior is empirically reproduced against the live platform before it ships in the reference content. The principle caught multiple cases where shipping a reported behavior verbatim would have actively misled users — including framing-inverted claims about `msg.statusCode` precedence, `native-object-config` `name` semantics, and empty-credential-field requirements.

[0.7.1]: https://github.com/ContextualIO/solution-ai-connect/releases/tag/v0.7.1
