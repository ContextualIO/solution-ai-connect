---
name: solai-knowledge
description: Ground Solution AI and Contextual product answers in docs before responding. Use when verifying platform behavior, flows, nodes, routing, object types, or runtime details.
---

# SolAI Knowledge

Use this skill for product and platform questions where doc-backed answers are safer than memory.

## Use These Tools

Use tools from the `solai-knowledge-mcp` server:

- `search`
- `list_paths`
- `list_headings`
- `read_chunk_context`
- `read_section`
- `read_page`
- `list_versions`

## Workflow

1. Run `search` with a focused query.
2. Expand the best hits with `read_chunk_context`.
3. If the path or heading is unclear, discover first with `list_paths` and `list_headings`.
4. Use `read_section` for exact or fuzzy heading lookup.
5. Use `read_page` only when section-level context is not enough.
6. Answer with grounded guidance and cite the relevant doc path or heading.

## Behavior

- Prefer documented behavior over memory.
- Refine the search query once if the first results are weak.
- Prefer section-level reads over full-page reads to keep context focused.
- If the docs do not answer the question, say that clearly and mark any recommendation as inference.
