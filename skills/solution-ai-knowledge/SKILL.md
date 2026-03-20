---
name: solution-ai-knowledge
description: Ground Solution AI and Contextual answers in indexed knowledge before responding. Use when verifying platform behavior, implementation patterns, flows, nodes, routing, object types, runtime details, or solution-building guidance.
---

# Solution AI Knowledge

Use this skill for product, platform, and implementation questions where indexed knowledge is safer than memory.

The `solution-ai-knowledge` server spans more than public docs. It includes at least two important sources:

- `contextual-docs` - public product and platform documentation
- `contextual-context` - private implementation guidance, snippets, and flow-building context

## Use These Tools

Use tools from the `solution-ai-knowledge` server:

- `list_sources`
- `search`
- `list_paths`
- `list_headings`
- `read_chunk_context`
- `read_section`
- `read_page`
- `list_versions`

## Workflow

1. If source choice is unclear, run `list_sources` once to confirm what is available.
2. Start with a focused `search`.
3. For canonical product behavior, prefer `source: contextual-docs`.
4. For implementation guidance, snippets, or flow-building context, prefer `source: contextual-context`.
5. For applied questions like "how should I build this?", use both sources when helpful: public docs for behavior, context repo for working patterns.
6. Expand strong hits with `read_chunk_context`.
7. If the path or heading is unclear, discover first with `list_paths` and `list_headings`.
8. Use `read_section` for exact or fuzzy heading lookup.
9. Use `read_page` only when section-level context is not enough.
10. Answer with grounded guidance and cite the relevant source, path, and heading.

## Source Selection

- Use `contextual-docs` when the question is about official behavior, semantics, runtime expectations, configuration rules, or current platform guidance.
- Use `contextual-context` when the question is about how to implement something, how flows are commonly built, what snippets or patterns already exist, or what working examples can be adapted.
- If the same path exists in multiple sources, pass `source` explicitly to `list_headings`, `read_section`, and `read_page`.
- The context repo can be especially useful for snippets, functions, flow-building patterns, and implementation guidance that may not appear in public docs.
- The context repo is often stronger for semantic retrieval of implementation examples, especially when the user describes behavior rather than exact file names.

## Behavior

- Prefer indexed sources over memory.
- Refine the search query once if the first results are weak.
- Prefer section-level reads over full-page reads to keep context focused.
- If public docs are thin, check whether the context repo has implementation guidance before concluding there is no answer.
- If the indexed sources still do not answer the question, say that clearly and mark any recommendation as inference.
- If the answer depends on tenant, flow type, object type, runtime, or another detail that is missing, ask one targeted clarifying question.
- If search results are split across multiple plausible interpretations, briefly explain the ambiguity and ask for the missing detail that would change the answer.
