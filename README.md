# contextual-docs plugin

Work with Contextual from Claude in two ways:

- `solution-ai-knowledge` for docs-grounded product and platform answers
- `contextual-cli` for shell-first tenant inspection and safe edits in local coding agents

## Included files

- `.claude-plugin/plugin.json` - plugin manifest
- `.claude-plugin/marketplace.json` - source install metadata
- `.mcp.json` - bundled `solution-ai-knowledge` connector
- `skills/solution-ai-knowledge/SKILL.md` - docs-grounding skill
- `skills/contextual-cli/SKILL.md` - shell-only CLI skill
- `skills/contextual-cli/cli-reference.md` - compact `ctxl` command reference
- `skills/contextual-cli/scripts/contextual_login.py` - browser login helper
- `skills/contextual-cli/scripts/json_diff.py` - diff preview helper for replace flows

## Install in Cowork

1. Open Claude Desktop and switch to **Cowork**.
2. Go to **Customize** -> **Browse plugins**.
3. Upload this plugin folder, or a zip containing this folder.
4. Install it.

## Install from GitHub source

If this repository is added as a plugin source, install with:

```bash
claude plugin install contextual-docs@contextual-scratchpad
```

After install, you should see namespaced skills like:

- `/contextual-docs:solution-ai-knowledge`
- `/contextual-docs:contextual-cli`

## Install in Claude Code

From this directory:

```bash
claude --plugin-dir .
```

Example prompts:

```text
/contextual-docs:solution-ai-knowledge explain flow-http path behavior
/contextual-docs:contextual-cli inspect the current tenant's flow types
```

## Notes

- `solution-ai-knowledge` is the bundled docs connector name.
- `contextual-cli` requires a runtime with local shell access such as Claude Code, Claude Cowork, OpenCode, or Codex.
- `contextual-cli` expects `ctxl` to already be installed and available on the machine.
- Replace operations should be previewed with a diff and explicitly confirmed before writing.
- This plugin does not expose delete/remove flows for tenant operations.
