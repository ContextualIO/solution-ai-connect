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

Editing flows is the primary development activity on this platform. The mechanism is a live tunnel, not file editing:

1. The user runs `ctxl mcp serve --config-id <config-id>` in a persistent terminal. This starts a local MCP server at `http://localhost:5051/`.
2. The user opens a flow in their browser's Flow Editor.
3. The MCP server detects that browser session and makes it available as a **Flow Editor Session**.
4. Claude connects to that session via `mcp__ctxl-flow-editor__*` tools and edits the live canvas directly — nodes, wires, properties, and code — with changes reflected in the browser in real time.

**"Which flows do I have open?"** means: which flows have an active browser session the MCP server can tunnel into. Call `list_sessions` to discover them. A flow that exists on the tenant but is not open in the browser is not reachable — the user must open it first.

**Connection handshake:** The first tool call targeting a flow triggers an "MCP requesting access" dialog in the Flow Editor's right sidebar. The user must click **Accept** before any tool calls succeed. Always prompt the user to watch for this.

**The MCP server cannot be started by Claude.** Any process Claude launches via shell is ephemeral and dies immediately. The server must be running in the user's own terminal before flow editing can begin.

**Check for a live server before assuming one is needed:** if `mcp__ctxl-flow-editor__*` tools appear in the available tool list, the server is already running — call `info` and `list_sessions` to orient, do not ask the user to start it again.

Use the `ctxl:solai-flow-editor` skill or `flow-editor` agent for all live canvas work.

---

## Skills

Four skills are available. Reach for them before answering platform questions from memory.

| Skill | When to use |
|---|---|
| `ctxl:solai-knowledge` | Any question about platform behavior, node types, flow patterns, routing, Object Types, or runtime details. Ground answers in docs before responding. |
| `ctxl:solai-cli` | Inspecting or editing a tenant from a shell-capable runtime (Claude Code, Cowork, OpenCode). Also the correct skill for **creating new flows** — use this, not `plan-flow`, when the user wants to actually build or create something. Requires `ctxl` CLI installed locally. |
| `ctxl:solai-flow-editor` | Making changes to a live flow open in the browser Flow Editor. Requires `ctxl mcp serve` running in a terminal. Use after a plan is in place — plan first with the `plan-flow` agent. |
| `ctxl:solai-data-modeler` | Designing or validating Object Type schemas — fields, relations, primaryKeys, generated properties. |

**Universal rule:** If a platform question can't be answered from memory with confidence, invoke `ctxl:solai-knowledge` to ground the answer in docs first.

---

## Agents

Six subagents cover the full delivery lifecycle. Use them in sequence or in parallel depending on the task.

| Agent | Role |
|---|---|
| `solution-architect` | Translate requirements into a full platform design — connections, object types, flow topology, auth, UI scope, scale |
| `plan-flow` | Design node-level flow changes — tab structure, node selection, wiring, error handling, patch sequencing |
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
- **`ctxl:solai-flow-editor` and `flow-editor`** require `ctxl mcp serve --config-id <config-id>` running in a persistent terminal before use
- **`ctxl:solai-knowledge`** uses a remote MCP connector — no local setup needed

---

## Hard limits (apply at all times)

- Never read `~/.config/ctxl/config.json` or any raw credential store
- Never call Contextual APIs directly with `curl`, `fetch`, or handwritten HTTP requests
- Never expose bearer tokens, refresh tokens, or auth headers
- Do not use destructive CLI commands: `ctxl config delete`, `ctxl records delete/remove/rm`, `ctxl types delete/remove/rm`
- Replace operations must be previewed with a diff and explicitly confirmed before writing
