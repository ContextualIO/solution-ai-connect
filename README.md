# contextual-docs plugin

Claude plugin that bundles:

- the `contextual-docs` MCP connector
- a docs-grounding skill
- slash commands for answer, browse, and section retrieval workflows

## Included components

- `.claude-plugin/plugin.json` - plugin manifest
- `.mcp.json` - MCP server config
- `skills/contextual-docs/SKILL.md` - retrieval and grounding policy
- `commands/answer.md` - grounded Q&A flow
- `commands/browse.md` - path/heading discovery flow
- `commands/section.md` - exact/fuzzy section retrieval flow

## Install in Cowork

1. Open Claude Desktop and switch to **Cowork**.
2. Go to **Customize** -> **Browse plugins**.
3. Upload this plugin folder (or a zip containing this folder).
4. Install it.

## Install from GitHub source (sync-enabled)

If you add this repository as a **plugin source** in Claude, the source loader expects a marketplace manifest at `.claude-plugin/marketplace.json`.

- Marketplace name: `contextual-scratchpad`
- Plugin name: `contextual-docs`

CLI install example:

```bash
claude plugin install contextual-docs@contextual-scratchpad
```

After install, you should see namespaced commands like:

- `/contextual-docs:answer`
- `/contextual-docs:browse`
- `/contextual-docs:section`

## Install in Claude Code (local test)

From this directory:

```bash
claude --plugin-dir .
```

Then run:

```text
/contextual-docs:answer explain ai generate tool call behavior
```

## Notes

- The MCP endpoint is public and currently does not require OAuth.
- If tool names are namespaced differently by client, always use tools from the `contextual-docs` server.
