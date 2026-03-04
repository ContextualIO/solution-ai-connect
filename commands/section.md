---
description: Retrieve an exact or fuzzy section from Contextual docs.
---

# Contextual Docs Section

Input: `$ARGUMENTS`

Expected format: `<path> :: <heading_path_or_heading_query>`

## Instructions

1. Parse `$ARGUMENTS` using `::` separator.
2. If path is missing, use `list_paths` or `search` to discover likely paths, then continue.
3. If heading looks exact, call `read_section(path, heading_path)`.
4. Otherwise call `read_section(path, heading_query)` and use fuzzy match resolution.
5. If user asks for surrounding context, call `read_chunk_context(section_id, before, after)`.

## Output

Return:

- matched heading
- path
- canonical link
- section_id and chunk_id
- section content (or concise summary if very long)
