---
description: Browse indexed Contextual docs paths and headings for a topic.
---

# Contextual Docs Browse

Topic or prefix: `$ARGUMENTS`

## Instructions

1. If `$ARGUMENTS` looks like a path prefix (contains `/`), call `list_paths` with `prefix`.
2. Otherwise, call `search` with:
   - `query`: `$ARGUMENTS`
   - `dedupe`: `path`
   - `limit`: 8
3. For the best 3 paths, call `list_headings(path, query?)` using the same topic as `query`.
4. If available, include each heading's `section_id` and `chunk_id` for follow-up reads.

## Output

Return a compact shortlist grouped by path:

- path
- heading_path
- canonical link
- section_id
- chunk_id
