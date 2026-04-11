# Connectors

## Solution AI Knowledge

`https://contextual-docs-mcp.contextualio.workers.dev` (remote, always available)

Tools: `search`, `list_paths`, `list_headings`, `read_chunk_context`, `read_section`, `read_page`, `list_versions`

## ctxl-flow-editor

`http://localhost:5051/` (local, requires `ctxl mcp serve` to be running)

Bridges to live SolutionAI browser sessions via the Contextual CLI. Start the server before use:

```bash
ctxl mcp serve --config-id <config-id>
```

See the `solai-cli` skill for full MCP server documentation.
