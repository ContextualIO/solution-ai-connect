# Contextual Agents

Subagents for Contextual.io platform work. Each agent is scoped to a distinct phase or concern — use them in sequence or in parallel depending on the task.

## Agent Lineup

| Agent | Role | Scope |
|---|---|---|
| `solution-architect` | Translate requirements into a platform design | Connections, object types, flow topology, auth, UI, scale |
| `plan-flow` | Design node-level flow changes | Tab structure, node selection, wiring, error handling |
| `data-modeler` | Design and validate Object Type schemas | Fields, relations, primaryKeys, generated properties |
| `flow-editor` | Implement changes in the live Flow Editor | Canvas editing via MCP — imports, wiring, code edits |
| `docs-reader` | Look up Contextual platform documentation | Node behaviour, platform APIs, flow patterns |
| `seed-builder` | Generate seed data and test fixtures | Records, demo datasets, inject node payloads |

## Workflow

### Discovery (main context, human-driven)

Before involving any agent, work through requirements in the main conversation. The goal is a clear statement of:

- What business problem is being solved and for whom
- What outcomes or metrics define success (OKRs/KPIs)
- What external systems are involved
- What users or roles interact with the solution
- Volume and frequency expectations
- Any constraints (existing connections, object types already in use, auth requirements)

This phase is intentionally human-driven. A prompt template for structured discovery may be available in the project's `team-context/prompts/` directory.

### Design (solution-architect)

Hand the discovery output to `solution-architect`. It reads existing tenant context, inspects the live platform state, and produces a design artifact covering the full solution shape — connections, object types, flow topology, auth, UI scope, and scale considerations.

The design artifact is the input to all subsequent agents. Review and confirm it before proceeding.

### Planning (plan-flow + data-modeler, parallel)

With a confirmed design in hand:

- `plan-flow` designs the node-level flow changes — tabs, node types, wiring, error handling patterns, patch sequencing
- `data-modeler` designs the Object Type schemas — fields, relations, primaryKeys, generated properties

These can run in parallel if the object type design is sufficiently stable.

### Implementation (flow-editor + solai-cli)

- `flow-editor` implements planned flow changes in the live Flow Editor via the `ctxl-flow-editor` MCP server
- `/solai-cli` skill handles Object Type deployment and record operations via the `ctxl` CLI

### Verification (seed-builder + docs-reader)

- `seed-builder` generates test fixtures and inject node payloads to exercise the implementation
- `docs-reader` is available throughout for platform behaviour lookups

## Notes

- Plugin agents do not support `mcpServers` in frontmatter — MCP access is provided through the plugin's bundled connectors.
- `flow-editor` requires `ctxl mcp serve` to be running in a persistent terminal before it can connect to a live session.
- `solution-architect` and `plan-flow` are read/design only — neither touches the live Flow Editor.
- `docs-reader` can be called by other agents (especially `plan-flow`) when platform behaviour is uncertain.
