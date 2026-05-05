# Connectors

## Solution AI Knowledge

`https://contextual-docs-mcp.contextualio.workers.dev` (remote, first use now requires OAuth sign-in)

Tools: `search`, `list_paths`, `list_headings`, `read_chunk_context`, `read_section`, `read_page`, `list_versions`

The bundled connector still uses the same URL-only `.mcp.json` entry. MCP clients that support OAuth discovery should handle the `401` challenge, then continue through the Stytch Connected Apps flow exposed by the remote MCP server.

## ctxl-flow-editor

`http://localhost:5051/` (local, requires `ctxl mcp serve` to be running)

Bridges to live SolutionAI browser sessions via the Contextual CLI. Start the server before use:

```bash
ctxl mcp serve --config-id <config-id>
```

See the `solai-cli` skill for full MCP server documentation.
