---
name: contextual-docs
description: Ground Contextual product answers with the contextual-docs MCP search and section retrieval workflow.
---

# Contextual Docs Skill

Use this skill when a user asks for Contextual product behavior, API details, flow/node behavior, or setup guidance that must be doc-grounded.

## Tooling

Use tools from the `contextual-docs` MCP server:

- `search`
- `list_paths`
- `list_headings`
- `read_chunk_context`
- `read_section`
- `read_page`
- `list_versions`

Note: tool names can appear namespaced in some clients. Always choose the tools exposed by the `contextual-docs` server.

## Default Retrieval Workflow

1. Run `search` with a focused query first.
2. If path/heading is unclear, discover before guessing:
   - `list_paths(prefix?, version?)`
   - `list_headings(path, query?, version?)`
3. Expand best hits using `read_chunk_context` with `chunk_id` or `section_id`.
4. Resolve exact section text with `read_section`:
   - exact: `heading_path`
   - fuzzy: `heading_query`
5. Use `read_page` only when section/chunk context is insufficient.

## Search Defaults

Unless the user asks otherwise:

- `dedupe`: `section`
- `limit`: 5 to 8
- Prefer `path_prefix` only when you have a strong scope hint
- Use `path_regex` and `heading_contains` for precision

## Answer Format Expectations

When answering from docs:

- State the answer directly.
- Include grounding references (path + heading + canonical link).
- If docs are ambiguous or missing, say so explicitly and mark any inference as inference.

## Safety and Quality

- Prefer current indexed content over memory.
- Do not invent section names or file paths.
- If no reliable match is found, propose a narrower follow-up query.
