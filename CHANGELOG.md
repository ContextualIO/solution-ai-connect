# Changelog

All notable changes to the Solution AI Connect plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.2] — 2026-05-04

Tracks `@contextual-io/cli@0.10.0`. CLI reference picks up the new `recordversions` topic, the new `recordaudittrail list` command, and the extended `records get --version` / `#N` URI fragment.

### Added

#### `skills/solai-cli/cli-reference.md`

- New **`## Record Versions`** section covering `recordversions list`, `recordversions diff`, `recordversions rollback` (and their `rv …` aliases). Documents the `diff` version-range mini-grammar (`5..7`, `7^`, `7^^^`, `7~3`), the three `--format` options (`console` / `json` / `jsonpatch`), and the *non-obvious* `diff` exit-code semantics (1 when versions differ, 0 when identical).
- New **`## Record Audit Trail`** section covering `recordaudittrail list` (and the `ra …` aliases), framed against the version history so the two are not confused.
- New cross-cutting note on **default ordering asymmetry**: `recordversions list` and `recordaudittrail list` default to `_metaData.createdAt:desc`; `records list` and `types list` have no default ordering.
- `records get` synopsis updated to document the new `--version N` flag and the `native-object:TYPE/ID#N` URI fragment, including the rule that `--version` is incompatible with multiple `--id`.
- New **"Handling large diffs"** subsection under Record Versions: `--format jsonpatch` + summarization recipe, `--no-moves` for layout-noise suppression, and the redirect-to-file-then-Read pattern for full human review without inflating the shell-output preview path.
- New **"Counting without pulling bodies"** cross-cutting callout: `--include-total --page-size 1` on any `list` command returns `totalCount` in one round-trip. Documents the **`--page-size 0` server-ignore foot-gun** (CLI accepts it; server falls back to default page ~25), and the residual cost on `recordversions list` (single returned body is the full per-version record content). Empirically verified against a flow with 38 versions.

### Changed

- **Disallowed In This Skill** list extended with `ctxl recordversions rollback --do-not-bump` (and the `rv rollback --do-not-bump` alias). Plain `rollback` without the flag remains allowed because version history is preserved and the operation is recoverable; only the history-truncating variant is destructive.

### Fixed

- `recordversions diff` synopsis corrected to **URI form only**. Earlier draft suggested `[--type TYPE] [--id ID]` was interchangeable with the URI argument as it is for `list` and `rollback`; in fact `diff` takes `VERSIONS` as a second positional, and oclif cannot skip the first positional, so flag-only invocation always misroutes the version range into the URI slot and fails URI-regex validation. Confirmed via clean-context test session.

## [0.7.1] — 2026-04-27

The first comprehensive release of the plugin since establishing the BYOS pioneer feedback cycle. This release lands a substantial body of pioneer-fed reference content alongside foundational restructuring of the plugin's skills and agents. Reporters whose findings shipped in this release: **Marcelo Lopes**, **Angela Woods**, **James Stolp**, **Kevin OBryan**.

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

- **"Universal rule" in AGENTS.md**: source-of-truth precedence is now plugin-side reference content first (kept current via the BYOS pioneer feedback cycle), `ctxl:solai-knowledge` second (for platform/runtime behavior not covered in plugin-side reference). Cross-cutting queries can run both in parallel.
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

- This release establishes the **BYOS pioneer feedback cycle** (Report → Bucket → Verify → Draft → Implement → Validate → Release → Forward) as the operating model for plugin doc evolution. The cycle's verify-first principle caught multiple cases where shipping a session retro verbatim would have actively misled users — including framing-inverted claims about `msg.statusCode` precedence, `native-object-config` `name` semantics, and empty-credential-field requirements. See `working-private/byos-pioneer-process-and-governance.md` for the full taxonomy.
- Pioneer reporter credits for findings shipped in this release:
  - **Marcelo Lopes** — function-node logging (`logger.*` vs `node.*` vs `log-tap`), loop node setup-gates, `ctxl types add` envelope fields, cross-batch wire silent-drop behavior, `flow_read` wire audit gap, `node.log()` silent behavior
  - **Angela Woods** — `query-native-object` `query: ""` empty-string foot-gun, `outputPropertyType` requirement, MCP server flow-lock behavior
  - **James Stolp** — `ctxl types add` JSONL constraint, `http-response` `statusCode` precedence (D&D session diagnosis)
  - **Kevin OBryan** — `native-object-config` record-shape investigation; T-D4 verification empirically resolved the cluster
- **Versioning history**: personal-fork iterations 0.7.2 through 0.7.16 were used for live testing during the development of this release; only 0.7.1 is the official version.

[0.7.1]: https://github.com/ContextualIO/solution-ai-connect/releases/tag/v0.7.1
