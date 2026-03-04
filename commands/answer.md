---
description: Answer a Contextual docs question with grounded citations using the contextual-docs MCP tools.
---

# Contextual Docs Answer

User question: `$ARGUMENTS`

## Instructions

1. If `$ARGUMENTS` is empty, ask for the specific docs question.
2. Run `search` first with:
   - `query`: user question
   - `dedupe`: `section`
   - `limit`: 6
3. For top matches, run `read_chunk_context` using returned `chunk_id` or `section_id` to pull more context.
4. If wording is still ambiguous, run `read_section` with `heading_query` on the best path.
5. Use `read_page` only if section/chunk context is insufficient.

## Output

Return:

- A direct answer in plain language.
- A short "Grounding" list with:
  - heading
  - path
  - canonical link
  - section_id or chunk_id
- A confidence note if the docs are incomplete or conflicting.
