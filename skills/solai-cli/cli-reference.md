# Contextual CLI Reference

Use this as the compact command map for `ctxl`. It tracks the current CLI README while limiting the skill to non-destructive operations.

## Config

- `ctxl config list --json`
- `ctxl config current --json`
- `ctxl config get [CONFIG-ID] --json`
- `ctxl config add CONFIG-ID [--tenant-id TENANT-ID]`
- `ctxl config use CONFIG-ID`
- `ctxl config login`

## Records

- `ctxl records add [URI] --type TYPE --input-file FILE`
- `ctxl records get [URI] --type TYPE --id ID`
- `ctxl records list [URI] --type TYPE [--search FIELD=VALUE] [--exact-search FIELD=VALUE] [--from FIELD=VALUE] [--to FIELD=VALUE] [--order-by FIELD:desc] [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress]`
- `ctxl records query [URI] --type TYPE --query-file FILE [--order-by FIELD:desc] [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress]`
- `ctxl records patch [URI] --type TYPE --id ID [--set FIELD=VALUE] [--replace FIELD=VALUE] [--remove FIELD] [--add FIELD=VALUE] [--increment FIELD=DELTA]`
- `ctxl records replace [URI] --type TYPE --id ID --input-file FILE`
- `ctxl records stats [URI] --type TYPE --id ID`

Aliases documented by the CLI:

- `ctxl records create` and `ctxl records import` -> same behavior as `records add`
- `ctxl records search` -> same behavior as `records list`

## Types

Important model:

- For normal callers, `ctxl types list` is the discovery path for tenant-defined custom object types.
- Do not assume `ctxl types list` will surface reserved admin component types.
- For reserved admin component types, start from known IDs and fetch them directly with `ctxl types get --type TYPE` and `ctxl records ... --type TYPE`.
- Current reserved component set used by admin-console code: `agent`, `flow`, `topics`, `api-configuration` (known to users as "Connections"), `ai-route`, `jwks-configuration`, `authorization-code-app`.
- `ctxl types get --type <type-id>` returns the full JSON schema for any type — enums, patterns, min/max constraints, defaults, and relations. Use this as the authoritative source for field shapes before any create or replace operation.

- `ctxl types add --input-file FILE`
- `ctxl types get [URI] --type TYPE`
- `ctxl types list [--search FIELD=VALUE] [--exact-search FIELD=VALUE] [--from FIELD=VALUE] [--to FIELD=VALUE] [--order-by FIELD:desc] [--include-total] [--page-size N] [--page-token TOKEN] [--export] [--progress]`
- `ctxl types replace [URI] --type TYPE --input-file FILE`

Aliases documented by the CLI:

- `ctxl types create` and `ctxl types import` -> same behavior as `types add`
- `ctxl types search` -> same behavior as `types list`

## Global Flag

- `-C, --config-id CONFIG-ID` can be added to tenant commands when needed.

## File Inputs

- `--input-file -` reads JSON from stdin.
- `--query-file -` reads query JSON from stdin.

## Disallowed In This Skill

- `ctxl config delete`
- `ctxl records delete`, `ctxl records remove`, `ctxl records rm`
- `ctxl types delete`, `ctxl types remove`, `ctxl types rm`
