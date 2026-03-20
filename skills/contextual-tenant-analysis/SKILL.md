---
name: contextual-tenant-analysis
description: Analyze the structure, data model, and flow footprint of a Contextual tenant.
---

# Contextual Tenant Analysis

Use this skill when the user wants an overview, audit, or analysis of a tenant.

## Use These Tools

- `setup_access`
- `config_list`
- `config_current`
- `config_use`
- `types_list`
- `types_get`
- `records_list`
- `records_get`
- `records_query`
- `records_stats`
- `contextual-docs` tools for platform grounding

## Workflow

1. Ensure access with `setup_access` if needed.
2. Confirm the active config with `config_current` or switch with `config_use`.
3. Start with `types_list` to understand the tenant model.
4. If a tenant read returns `authRequired: true` or says the config is not logged in, run `login_start`, wait with `login_await`, and retry the blocked read.
5. Use `types_get` on important types.
6. Use `records_list`, `records_query`, and `records_stats` to inspect activity and sample data.
7. If flows matter, inspect flow records with `records_list(type: "flow")` and `records_get(type: "flow", id: flowId)`.
8. Ground platform-specific claims with `contextual-docs`.

## Output

- Lead with the tenant's main structure.
- Call out important object types, flows, integrations, and risks.
- Separate confirmed observations from inferences.
- Suggest next inspection targets only when they are clearly useful.
