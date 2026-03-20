# contextual-docs plugin

Work with Contextual tenants from Claude:

- set up access
- refresh login
- inspect tenants and flows
- ground platform answers in docs

This plugin includes:

- a local `contextual` connector for tenant access
- the remote `contextual-docs` connector for docs grounding

## Included files

- `.claude-plugin/plugin.json` - plugin manifest
- `.claude-plugin/marketplace.json` - source install metadata
- `.mcp.json` - local `contextual` and remote `contextual-docs` connectors
- `skills/setup/SKILL.md` - setup skill
- `skills/login/SKILL.md` - login skill
- `skills/flow-context/SKILL.md` - flow summary skill
- `skills/contextual/SKILL.md` - main operating instructions
- `skills/contextual-flow-edit/SKILL.md` - focused flow editing guidance
- `skills/contextual-tenant-analysis/SKILL.md` - focused tenant analysis guidance
- `scripts/contextual_mcp.py` - local Contextual connector
- `scripts/setup_access.sh` - access setup script
- `scripts/contextual_login.py` - login job script

## Install in Cowork

1. Open Claude Desktop and switch to **Cowork**.
2. Go to **Customize** -> **Browse plugins**.
3. Upload this plugin folder (or a zip containing this folder).
4. Install it.

## Install from GitHub source

If this repository is added as a plugin source, install with:

```bash
claude plugin install contextual-docs@contextual-scratchpad
```

After install, you should see namespaced skills like:

- `/contextual-docs:setup`
- `/contextual-docs:login`
- `/contextual-docs:flow-context`
- `/contextual-docs:contextual`

## First use

Run:

```text
/contextual-docs:setup
```

That prepares local access and shows saved tenant configs.

## Install in Claude Code

From this directory:

```bash
claude --plugin-dir .
```

Example prompts:

```text
/contextual-docs:setup
/contextual-docs:flow-context client-services-dev :: some-flow-id
/contextual-docs:contextual inspect the current tenant's flow types
```

## Notes

- Tenant inspection and changes run through the local `contextual` connector.
- The local `contextual` connector stays close to `ctxl` command structure.
- Product and platform claims should be grounded with `contextual-docs`.
- Login usually starts automatically on the first protected tenant action and may open a browser window for approval.
- `/contextual-docs:login` remains available as a manual fallback.
- Replace operations should be previewed with a diff and confirmed before writing.
- Full tenant features require a Claude runtime that supports local MCP connectors.
- Login jobs store temporary state in `.local/login-jobs/`, which is gitignored.
