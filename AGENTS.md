# Solution AI Connect

This plugin bundles skills, agents, and docs-grounding for working with the **Contextual.io** platform (also called **Solution AI** or **SolAI**).

Contextual.io is a proprietary AI platform for building intelligent, flow-based solutions. Core concepts:

**Platform components** (reserved, built-in — not discoverable via `ctxl types list`):
- **Flows** — canvas-based logic built from typed nodes, organized into tabs and subflows; stored as records under type `flow`
- **Agents** — scalable compute runtimes on the platform (Kubernetes-backed, node/memory/parallel instance configurable); may run AI workloads but are general-purpose execution units, not AI agents in the Claude sense; stored under type `agent`
- **AI Routes** — routing logic that directs AI requests; stored under type `ai-route`
- **Connections** — configured integrations to external systems; stored under type `api-configuration`
- **JWKS Configurations** — JWT/key-set auth configs; stored under type `jwks-configuration`
- **Authorization Code Apps** — OAuth app configurations; stored under type `authorization-code-app`

**Data layer**:
- **Object Types** — tenant-defined JSON Schema-backed data models; discoverable via `ctxl types list`
- **Records** — instances of an Object Type or platform component
- **Tenants** — isolated platform environments, accessed via a named config in the `ctxl` CLI

Do not apply assumptions from other flow-based or low-code platforms. When uncertain about platform behavior, ground answers in the docs (see `solai-knowledge` below).

---

## Live Flow Editing — the core development motion

Editing flows is the primary development activity on this platform. It happens through a live MCP tunnel into the user's browser-open Flow Editor (mechanics below).

### Skill gate — invoke `ctxl:solai-flow-editor` before touching a flow

**Trigger:** any user request that implies inspecting or modifying a live flow — *add, edit, change, update, move, wire, connect, delete, rename, configure, set, fix, group, copy, validate, look at, check, read* a node / wire / property / code / tab. The trigger is the **intent to work on a flow**, regardless of whether the user names the skill or the word "edit" appears.

**Exempt — orientation only, no skill needed:**
- `info` — server metadata
- `list_sessions` — which flows are open in the browser

These exist so Claude can answer "is the server up / which flows are open?" without loading the skill. Nothing else is exempt.

**Not exempt — skill must be invoked first:**
- Reads into flow contents: `editor_state`, `flow_read`, `tray_open`, `tray_read`, `result_read`, `logger_messages`, `search`, `type_info`, `validate`, `navigate`
- All writes: `import`, `wire`, `node_update`, `code_read`, `code_write`, `code_edit`, `code_grep`, `code_patch`, `tray_write`, `tray_commit`, `move`, `copy`, `delete`, `group`, `select`

Tool availability ≠ guidance loaded. Skipping the skill produces silent failures the MCP server does not catch: missing pre-generated node IDs, wrong node types, dropped cross-batch wires, broken `tray_open`→`tray_read` sequences, malformed `editable-list` defaults. Errors surface obscurely or partial changes apply.

**Sequence when a flow-editing intent is detected:**
1. (Optional) `list_sessions` to confirm a session exists for the target flow.
2. **Invoke `ctxl:solai-flow-editor`.** Do this before the next tool call, even if you already know the flow is open.
3. Proceed with reads/writes per the skill's guidance.

### How the tunnel works

1. The user runs `ctxl mcp serve --config-id <config-id>` in a persistent terminal. This starts a local MCP server at `http://localhost:5051/`.
2. The user opens a flow in their browser's Flow Editor.
3. The MCP server detects that browser session and makes it available as a **Flow Editor Session**.
4. Claude connects to that session via `mcp__ctxl-flow-editor__*` tools and edits the live canvas directly — nodes, wires, properties, and code — with changes reflected in the browser in real time.

**"Which flows do I have open?"** means: which flows have an active browser session the MCP server can tunnel into. Call `list_sessions` to discover them. A flow that exists on the tenant but is not open in the browser is not reachable — the user must open it first.

**Connection handshake:** The first tool call targeting a flow triggers an "MCP requesting access" dialog in the Flow Editor's right sidebar. The user must click **Accept** before any tool calls succeed. Always prompt the user to watch for this.

**The MCP server cannot be started by Claude.** Any process Claude launches via shell is ephemeral and dies immediately. The server must be running in the user's own terminal (via `ctxl mcp serve`) or via the Ctxl Tool desktop app, which manages the server for the user.

---

## Skills

Four skills are available. Reach for them before answering platform questions from memory.

| Skill | When to use |
|---|---|
| `ctxl:solai-knowledge` | Any question about platform behavior, node types, flow patterns, routing, Object Types, or runtime details. Ground answers in docs before responding. |
| `ctxl:solai-cli` | Inspecting or editing a tenant from a shell-capable runtime (Claude Code, Cowork, OpenCode). Also the correct skill for **creating new flows** — use this, not `plan-flow`, when the user wants to actually build or create something. Requires `ctxl` CLI installed locally. |
| `ctxl:solai-flow-editor` | **Required before any `mcp__ctxl-flow-editor__*` call that inspects or modifies flow contents.** Only `info` and `list_sessions` are exempt (orientation). Triggers: any imperative against a flow — add/edit/move/wire/delete/configure/validate a node, wire, property, or code. Requires the MCP server running (`ctxl mcp serve` or the Ctxl Tool desktop app). For complex multi-step work, planning with `plan-flow` first is helpful but not required. |
| `ctxl:solai-data-modeler` | Designing or validating Object Type schemas — fields, relations, primaryKeys, generated properties. |

**Universal rule:** Don't answer platform questions from memory. Source-of-truth precedence: (1) plugin-side reference content (`cli-reference.md`, `node-reference.md`, the relevant `SKILL.md`) — empirically-verified build-time reality, kept current via ongoing verification against the live platform; (2) `ctxl:solai-knowledge` — for platform/runtime behavior not covered in (1). For genuinely cross-cutting queries (spanning both build-time mechanics and broader platform context), run both in parallel — the answers are complementary. Plugin-first precedence is current state and may shift as `solai-knowledge` matures.

**How to access plugin-side reference:** Invoke the relevant skill (`/ctxl:solai-flow-editor`, `/ctxl:solai-cli`, `/ctxl:solai-data-modeler`) — it loads the reference content (`node-reference.md`, `cli-reference.md`, the relevant `SKILL.md`) properly into context, along with sequencing rules and validation discipline. **Do not `grep`, `find`, or otherwise enumerate the plugin install directory** (`~/.claude/plugins/...`) to locate plugin reference content directly. That path is implementation detail, bypasses skill-level guidance (sequencing rules, validation patterns, hex-id pre-generation, etc.), and exposes plugin internals as if they're a normal interaction surface. Always go through the skill.

---

## Agents

Six subagents cover the full delivery lifecycle. Use them in sequence or in parallel depending on the task.

| Agent | Role |
|---|---|
| `solution-architect` | Translate requirements into a full platform design — connections, object types, flow topology, auth, UI scope, scale |
| `plan-flow` | Design-phase planning only — produces a plan for tab structure, node selection, wiring, error handling, patch sequencing. Does not create flows or touch the editor. To actually create a flow, use `ctxl:solai-cli` instead. |
| `data-modeler` | Design and validate Object Type schemas |
| `flow-editor` | Implement planned flow changes in the live Flow Editor via the `ctxl-flow-editor` MCP server |
| `docs-reader` | Look up Contextual platform documentation — callable by other agents when behavior is uncertain |
| `seed-builder` | Generate seed data, test fixtures, and inject node payloads |

### Typical workflow

1. **Discovery** (main conversation) — clarify the business problem, outcomes, external systems, users, volume, and constraints before involving any agent.
2. **Design** (`solution-architect`) — produces a design artifact covering the full solution shape. Review and confirm before proceeding.
3. **Planning** (`plan-flow` + `data-modeler`, can run in parallel) — node-level flow plan and Object Type schemas.
4. **Implementation** (`flow-editor` + `ctxl:solai-cli`) — flow changes in the live editor; Object Type deployment and record operations via CLI.
5. **Verification** (`seed-builder` + `docs-reader`) — test fixtures and doc-backed behavior checks.

`solution-architect` and `plan-flow` are read/design only — neither touches the live Flow Editor.

### Suppressing or overriding agents per-project

Add to `.claude/settings.json` in the project to suppress without replacing:
```json
{ "permissions": { "deny": ["Agent(solution-architect)", "Agent(seed-builder)"] } }
```

Drop a `.claude/agents/<name>.md` in the project to replace a plugin agent with a local version.

---

## Prerequisites

- **`ctxl:solai-cli` and `flow-editor`** require the `ctxl` CLI: `npm install -g @contextual-io/cli`
- **`ctxl:solai-flow-editor` and `flow-editor`** require the MCP server running before use — either `ctxl mcp serve --config-id <config-id>` in a persistent terminal, or via the Ctxl Tool desktop app
- **`ctxl:solai-knowledge`** uses a remote MCP connector — no local setup needed

---

## Hard limits (apply at all times)

- Never read `~/.config/ctxl/config.json` or any raw credential store
- Never call Contextual APIs directly with `curl`, `fetch`, or handwritten HTTP requests
- Never expose bearer tokens, refresh tokens, or auth headers
- Do not use destructive CLI commands: `ctxl config delete`, `ctxl records delete/remove/rm`, `ctxl types delete/remove/rm`
- Replace operations must be previewed with a diff and explicitly confirmed before writing
