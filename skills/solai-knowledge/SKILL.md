---
name: solai-knowledge
description: Ground Solution AI and Contextual product answers in the official platform documentation — for **platform/runtime behavior not already covered by plugin-side reference content** (`cli-reference.md`, `node-reference.md`, the relevant `SKILL.md`). For CLI command shapes, JSONL formats, flow record structure, native-object-config shape, or node-level authoring patterns, prefer the plugin-side references first; this skill is the second stop, for behavior the plugin-side does not cover.
---

# SolAI Knowledge

Use this skill for product and platform questions where doc-backed answers are safer than memory.

## Precedence

**Plugin-side reference content is the first stop** for CLI shapes, node-level behavior, and authoring patterns. Those references (`cli-reference.md`, `node-reference.md`, the relevant `SKILL.md`) are kept current via ongoing empirical verification against the live platform, and they often have answers this skill's docs do not. **This skill is the second stop** — use it for **platform/runtime behavior** that the plugin-side references don't cover (e.g. agent runtime semantics, deployment behavior, error patterns from the agent runtime, broader platform philosophy).

If a question lands here that should have been answered by plugin-side reference (e.g. *"what's the minimum X shape?"*, *"how do I configure node Y?"*, *"what are the foot-guns on Z?"*), redirect — invoke `ctxl:solai-flow-editor` or `ctxl:solai-cli` and read the relevant reference file before searching.

## Setup Check

On first invocation each session, check for plugin updates. Before running, tell the user:

> Checking for Solution AI Connect plugin updates — you may be prompted to allow this command.

Then run:

```bash
claude plugin update ctxl@contextual-io
```

The raw command output uses `ctxl` as the marketplace plugin identifier, but `ctxl` is also the name of the separately-versioned Contextual CLI. To avoid confusion, **always restate the result in "Solution AI Connect plugin" terms** rather than letting the raw output stand:

- If the output contains "updated from X to Y": tell the user "Solution AI Connect plugin updated from X to Y — restart Claude to load the new version, then re-invoke this skill."
- If the output says "already at the latest version (X)": tell the user "Solution AI Connect plugin is already at the latest version (X)." Then proceed.

Only run this check once per session.

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
- **If `search` errors (`-32603` or similar) twice in a row, OR returns no relevant hits after one query refinement, stop searching.** Switch to plugin-side reference content — invoke `ctxl:solai-flow-editor` or `ctxl:solai-cli` (per the Precedence section above) and read `node-reference.md` / `cli-reference.md` / the relevant `SKILL.md` directly. Don't loop on a broken or unhelpful search.
