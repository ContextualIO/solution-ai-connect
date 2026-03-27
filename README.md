# contextual-docs plugin

Work with Contextual from Claude in two ways:

- `solai-knowledge` for docs-grounded product and platform answers
- `solai-cli` for shell-first tenant inspection and safe edits in local coding agents

## Included files

- `.claude-plugin/plugin.json` - plugin manifest
- `.claude-plugin/marketplace.json` - source install metadata
- `.mcp.json` - bundled `solai-knowledge-mcp` connector
- `skills/solai-knowledge/` - docs-grounding skill submodule
- `skills/solai-cli/` - shell-only CLI skill submodule
- `skills/solai-cli/cli-reference.md` - compact `ctxl` command reference
- `skills/solai-cli/scripts/contextual_login.py` - browser login helper
- `skills/solai-cli/scripts/json_diff.py` - diff preview helper for replace flows

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

- `/contextual-docs:solai-knowledge`
- `/contextual-docs:solai-cli`

## Install in Claude Code

From this directory:

```bash
claude --plugin-dir .
```

Example prompts:

```text
/contextual-docs:solai-knowledge explain flow-http path behavior
/contextual-docs:solai-cli inspect the current tenant's flow types
```

## Notes

- `solai-knowledge` is the bundled docs-grounding skill and uses the `solai-knowledge-mcp` connector.
- `solai-cli` requires a runtime with local shell access such as Claude Code, Claude Cowork, OpenCode, or Codex.
- `solai-cli` expects `ctxl` to already be installed and available on the machine.
- `skills/solai-knowledge/` and `skills/solai-cli/` are linked into this plugin as Git submodules from `ContextualScratchpad`.
- Replace operations should be previewed with a diff and explicitly confirmed before writing.
- This plugin does not expose delete/remove flows for tenant operations.
