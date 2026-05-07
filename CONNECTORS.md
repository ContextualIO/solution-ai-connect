# Connectors

## Solution AI Knowledge

`https://contextual-docs-mcp.contextualio.workers.dev` (remote, OAuth-protected)

Tools: `search`, `list_paths`, `list_headings`, `read_chunk_context`, `read_section`, `read_page`, `list_versions`

The bundled `.mcp.json` entry is URL-only. The server returns `401` on unauthenticated requests; MCP clients with OAuth discovery handle the challenge and complete sign-in via the server's OAuth flow (provided by Stytch). Clients without OAuth discovery cannot connect.

## ctxl-flow-editor

`http://localhost:5051/` (local, requires `ctxl mcp serve` to be running)

Bridges to live SolutionAI browser sessions via the Contextual CLI. Start the server before use:

```bash
ctxl mcp serve --config-id <config-id>
```

See the `solai-cli` skill for full MCP server documentation.
