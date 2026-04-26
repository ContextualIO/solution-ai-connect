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

- `.claude-plugin/plugin.json` - plugin manifest
- `.claude-plugin/marketplace.json` - source install metadata
- `.mcp.json` - bundled `solai-knowledge-mcp` connector
- `skills/solai-knowledge/` - docs-grounding skill submodule
- `skills/solai-cli/` - shell-only CLI skill submodule
- `skills/solai-cli/cli-reference.md` - compact `ctxl` command reference
- `skills/solai-cli/scripts/contextual_login.py` - browser login helper
- `skills/solai-cli/scripts/json_diff.py` - diff preview helper for replace flows
- `skills/solai-flow-editor/` - live flow editor skill
- `skills/solai-data-modeler/` - Object Type schema design skill
- `agents/` - Contextual subagents (solution-architect, plan-flow, flow-editor, data-modeler, docs-reader, seed-builder) — see `docs/agents.md` for the full workflow
- `docs/agents.md` - agent lineup, workflow, and per-project suppression guide

## Install in Cowork

1. Open Claude Desktop and switch to **Cowork**.
2. Go to **Customize** -> **Browse plugins**.
3. Upload this plugin folder, or a zip containing this folder.
4. Install it.

## Install from GitHub source

If this repository is added as a plugin marketplace from `ContextualIO/solution-ai-connect`, install with:

```bash
claude plugin install ctxl@contextual-io
```

After install, you should see namespaced skills like:

- `/ctxl:solai-knowledge`
- `/ctxl:solai-cli`
- `/ctxl:solai-flow-editor`
- `/ctxl:solai-data-modeler`

## Install in Claude Code

**CLI (session-scoped):** load the plugin for a single session from this directory:

```bash
claude --plugin-dir .
```

Add `--debug` to write a timestamped log file to `~/.claude/debug/` — useful for verifying that agents and skills loaded correctly:

```bash
claude --plugin-dir . --debug
```

**IDE extension (VSCode / Cursor):** the extension has no `--plugin-dir` equivalent. Install to user scope instead, then the plugin is available in all IDE sessions automatically:

```bash
claude plugin add .
```

Example prompts:

```text
/ctxl:solai-knowledge explain flow-http path behavior
/ctxl:solai-cli inspect the current tenant's flow types
/ctxl:solai-flow-editor add a log-tap node after the ai-generate node
/ctxl:solai-data-modeler design a schema for a customer order type
```

## Keeping Up to Date

This plugin updates frequently. Run the following command to pull the latest version and restart Claude to apply it:

```bash
claude plugin update ctxl@contextual-io
```

If the plugin is already at the latest version, the command will say so and nothing changes. If a new version is available it will update immediately — restart Claude after to load the new content.

Both `/solai-cli` and `/solai-knowledge` will check for updates automatically on first invocation each session and prompt you to restart if a new version was pulled.

## Publishing Updates

Claude Code caches plugin files at install time and only rebuilds the cache when `plugin.json` version changes. **Content changes to skill files (SKILL.md, cli-reference.md, scripts) will not reach users until the version is bumped**, even if the changes are pushed to GitHub and the marketplace git clone is fetched.

Bump `.claude-plugin/plugin.json` version on every meaningful content change:
- Patch (`0.x.1`) — doc fixes, clarifications, typos
- Minor (`0.x+1.0`) — new sections, new capabilities, behavioral changes
- Major (`x+1.0.0`) — breaking changes to skill interface or hard rules

## Notes

- `solai-knowledge` is the bundled docs-grounding skill and uses the `solai-knowledge-mcp` connector.
- `solai-cli` requires a runtime with local shell access such as Claude Code, Claude Cowork, OpenCode, or Codex.
- `solai-cli` expects `ctxl` to already be installed and available on the machine.
- `solai-flow-editor` requires the `ctxl mcp serve` server to be running in a persistent terminal. The skill connects to it — it does not start it.
- `solai-data-modeler` pairs with `solai-cli` for deployment and `solai-knowledge` for doc-backed schema verification.
- Plugin agents (`agents/`) are installed globally and available across all projects. To suppress a specific agent at project level, add `"permissions": { "deny": ["Agent(agent-name)"] }` to `.claude/settings.json`. To replace one with a local version, drop a `.claude/agents/<name>.md` in the project. See `docs/agents.md` for details.
- Plugin agents do not support `mcpServers` in frontmatter — MCP access is provided through the plugin's bundled connectors.
- The repo name is `solution-ai-connect`, while the Claude plugin namespace stays `ctxl`.
- `skills/solai-knowledge/` and `skills/solai-cli/` are linked into this plugin as Git submodules from `ContextualIO`.
- Replace operations should be previewed with a diff and explicitly confirmed before writing.
- This plugin does not expose delete/remove flows for tenant operations.
