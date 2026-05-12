# Solution AI Connect

Solution AI Connect is the branded Claude bundle for SolAI skills.

- product / experience name: `Solution AI Connect`
- Claude plugin namespace: `ctxl`
- GitHub org: `ContextualIO`

Work with Contextual from Claude using four skills:

- `solai-knowledge` for docs-grounded product and platform answers
- `solai-cli` for shell-first tenant inspection and safe edits in local coding agents
- `solai-flow-editor` for live flow editing via the `ctxl-flow-editor` MCP server
- `solai-data-modeler` for designing and validating Contextual Object Type schemas

## Included files

- `AGENTS.md` - always-loaded session context: platform identity, reserved component types, live flow editing model, skill-gate enforcement, source-of-truth precedence, four-skill table, six-agent table, prerequisites, hard limits
- `CHANGELOG.md` - release notes (Keep a Changelog format)
- `CONNECTORS.md` - bundled MCP connector reference (`solai-knowledge-mcp` remote, `ctxl-flow-editor` local)
- `.claude-plugin/plugin.json` - plugin manifest
- `.claude-plugin/marketplace.json` - source install metadata
- `.mcp.json` - bundled `solai-knowledge-mcp` connector configuration
- `skills/solai-knowledge/` - docs-grounding skill (uses `solai-knowledge-mcp`; secondary to plugin-side reference content per source-of-truth precedence)
- `skills/solai-cli/` - shell-first CLI skill
- `skills/solai-cli/cli-reference.md` - compact `ctxl` command reference, flow record shape, `types add` envelope, query syntax
- `skills/solai-cli/scripts/contextual_login.py` - browser login helper
- `skills/solai-cli/scripts/json_diff.py` - diff preview helper for replace flows
- `skills/solai-flow-editor/` - live flow editor skill
- `skills/solai-flow-editor/node-reference.md` - node-specific reference and foot-gun catalogue (function-node logging, loop wiring, Native Object TypedInput patterns, `http-response` status precedence, Query Object node, etc.)
- `skills/solai-data-modeler/` - Object Type schema design skill
- `agents/` - Contextual subagents (solution-architect, plan-flow, flow-editor, data-modeler, docs-reader, seed-builder) — see `docs/agents.md` for the full workflow
- `docs/agents.md` - agent lineup, workflow, and per-project suppression guide

## Install

The flow is two steps: add this repo as a plugin marketplace, then install the plugin from it. You only need the marketplace-add step once per machine.

### Easiest path — `/plugin` interactive UI

From inside a Claude Code session (CLI or VS Code extension), run:

```text
/plugin
```

This opens a tabbed UI (Discover / Installed / Marketplaces / Errors — cycle with Tab / Shift+Tab) that handles everything: adding marketplaces, browsing and installing plugins, and managing updates. Same command in both CLI and the VS Code extension.

To add this plugin's marketplace from the UI: go to the **Marketplaces** tab → add → enter `ContextualIO/solution-ai-connect`. Then go to **Discover** or **Installed** to install `ctxl`.

### Script-friendly path — explicit shell commands

**Step 1 — Add the marketplace** (one-time per machine):

```bash
claude plugin marketplace add ContextualIO/solution-ai-connect
```

**Step 2 — Install the plugin:**

```bash
claude plugin install ctxl@contextual-io
```

### After install (either path)

You should see namespaced skills available:

- `/ctxl:solai-knowledge`
- `/ctxl:solai-cli`
- `/ctxl:solai-flow-editor`
- `/ctxl:solai-data-modeler`

Example prompts:

```text
/ctxl:solai-knowledge explain flow-http path behavior
/ctxl:solai-cli inspect the current tenant's flow types
/ctxl:solai-flow-editor add a log-tap node after the ai-generate node
/ctxl:solai-data-modeler design a schema for a customer order type
```

### Claude Cowork and Chat (Claude Desktop app)

These surfaces are **provisioned at the org level** for Contextual users — no install action is needed from you. The plugin's **core capabilities** are available in your Cowork and Chat sessions. Capabilities that depend on local resources — notably live flow editing (which requires a `ctxl mcp serve` MCP server on your machine) — only work in Claude Code (CLI, VS Code extension, or Desktop app).

### Claude Code in the Claude Desktop app

The Claude Code experience inside the Claude Desktop app shares the same install context as the Claude Code CLI and the VS Code extension. If you've installed the plugin via the steps above (CLI or VS Code), Claude Code in Desktop will pick up the same install — no separate install needed.

### Local development install (for testing unreleased changes)

If you've cloned this repo and want to load the plugin from your local checkout:

**Session-scoped (single session):**

```bash
claude --plugin-dir .
```

**User-scoped (persistent across sessions and projects):**

```bash
claude plugin add .
```

Add `--debug` to write a timestamped log file to `~/.claude/debug/` — useful for verifying that agents and skills loaded correctly:

```bash
claude --plugin-dir . --debug
```

## Keeping Up to Date

**Manual update check — run any time:**

```bash
claude plugin update ctxl@contextual-io
```

If the plugin is already at the latest version, the command says so and nothing changes. If a new version is available, it updates immediately — **restart Claude after** to load the new content.

(The `/plugin` UI also exposes an Update action under the **Installed** tab, but the shell command above is the more reliable update path in practice.)

`/ctxl:solai-cli`, `/ctxl:solai-flow-editor`, and `/ctxl:solai-knowledge` also run this check automatically on first invocation each session and prompt you to restart if a new version was pulled. The shell command above is the right choice when you want to check between sessions or on demand.

See [`CHANGELOG.md`](CHANGELOG.md) for what's new in each release.

## Publishing Updates

Claude Code caches plugin files at install time and only rebuilds the cache when `plugin.json` version changes. **Content changes to skill files (SKILL.md, cli-reference.md, scripts) will not reach users until the version is bumped**, even if the changes are pushed to GitHub and the marketplace git clone is fetched.

Bump `.claude-plugin/plugin.json` version on every meaningful content change. Prefer **frequent patch releases** over batching — `claude plugin update` treats a patch bump identically to a minor bump, so users benefit from updates sooner with no extra friction.

- Patch (`0.7.x`) — any content change: corrections, new guidance, clarifications, behavioral tweaks. Default for most changes.
- Minor (`0.x+1.0`) — new skills, new agents, or changes that alter the skill interface in a meaningful way.
- Major (`x+1.0.0`) — breaking changes to skill interface or hard rules.

**When in doubt, patch.** A small bump ships fast; batching causes users to run stale content longer than necessary.

## Contributing

For local working files (scratch notes, drafts, personal experiments) that should not be committed, add them to `.git/info/exclude` rather than `.gitignore`. This keeps personal ignore rules off the shared list:

```
echo "private-notes/" >> .git/info/exclude
```

## Notes

- `solai-knowledge` is the bundled docs-grounding skill and uses the `solai-knowledge-mcp` connector.
- `solai-cli` requires a runtime with local shell access such as Claude Code, Claude Cowork, OpenCode, or Codex.
- `solai-cli` expects `ctxl` to already be installed and available on the machine.
- `solai-flow-editor` requires the `ctxl mcp serve` server to be running. The skill connects to it — it does not start it. The server can be run manually in a persistent terminal (`ctxl mcp serve --config-id <config-id>`) or managed by the **Ctxl Tool** desktop app, which handles the lifecycle for you.
- `solai-data-modeler` pairs with `solai-cli` for deployment and `solai-knowledge` for doc-backed schema verification.
- Plugin agents (`agents/`) are installed globally and available across all projects. To suppress a specific agent at project level, add `"permissions": { "deny": ["Agent(agent-name)"] }` to `.claude/settings.json`. To replace one with a local version, drop a `.claude/agents/<name>.md` in the project. See `docs/agents.md` for details.
- Plugin agents do not support `mcpServers` in frontmatter — MCP access is provided through the plugin's bundled connectors.
- The repo name is `solution-ai-connect`, while the Claude plugin namespace stays `ctxl`.
- See [`CHANGELOG.md`](CHANGELOG.md) for release notes and what's new in each version.
- Replace operations should be previewed with a diff and explicitly confirmed before writing.
- This plugin does not expose delete/remove flows for tenant operations.
