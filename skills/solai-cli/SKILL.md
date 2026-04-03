---
name: solai-cli
description: Use the local Contextual CLI from shell-capable agents to inspect tenants, analyze flows, and apply safe edits. Use only in runtimes with local shell access.
disable-model-invocation: true
argument-hint: "[task]"
---

# SolAI CLI

Use this skill only in environments with local shell access such as Claude Code, Claude Cowork, OpenCode, Codex, or another local coding agent.

If shell access is unavailable, stop and tell the user this skill requires a shell-capable runtime. If docs would still help, switch to `solai-knowledge`.

## Runtime Checks

1. Confirm the environment can run shell commands.
2. Run `command -v ctxl && ctxl --version`.
3. If `ctxl` is missing, tell the user it must already be installed locally before this skill can run.

## Supporting Files

- Use [cli-reference.md](cli-reference.md) for the near-1:1 command map.
- Use `${CLAUDE_SKILL_DIR}/scripts/contextual_login.py --state-dir "${CLAUDE_PLUGIN_DATA:-${CLAUDE_SKILL_DIR}/.local}/login-jobs"` for browser login orchestration.
- Use `${CLAUDE_SKILL_DIR}/scripts/json_diff.py` to preview replace operations before writing.

## Hard Rules

- Never read `~/.config/ctxl/config.json` or any raw credential store.
- Never call Contextual APIs directly with `curl`, `fetch`, custom headers, or handwritten HTTP requests.
- Never expose or summarize bearer tokens, refresh tokens, or auth headers.
- Do not use `ctxl config delete`, `ctxl records delete/remove/rm`, or `ctxl types delete/remove/rm`.
- Before any `replace` or `patch` operation, show a diff or the exact planned patch flags and ask for explicit confirmation.
- Once you know the target config, prefer `--config-id <config-id>` on tenant commands even if you already ran `ctxl config use`.
- Use `solai-knowledge` before making detailed platform claims about flows, nodes, routing, runtime behavior, payload shapes, or implementation patterns.

## Config Workflow

Start with:

```bash
ctxl config list --json
ctxl config current --json
```

If a config is missing and the user supplied a tenant identifier:

```bash
ctxl config add <config-id> --tenant-id <tenant-id>
```

Select the config before tenant work:

```bash
ctxl config use <config-id>
```

## Automatic Auth Recovery

If a tenant command reports that the config is not logged in, unauthorized, expired, or otherwise needs auth:

1. Start login for that same config:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/contextual_login.py" --state-dir "${CLAUDE_PLUGIN_DATA:-${CLAUDE_SKILL_DIR}/.local}/login-jobs" start <config-id>
```

2. Relay the verification code immediately.
3. Tell the user to confirm that same code in the browser window and approve it there.
4. Wait for completion:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/contextual_login.py" --state-dir "${CLAUDE_PLUGIN_DATA:-${CLAUDE_SKILL_DIR}/.local}/login-jobs" await <job-id> --timeout-seconds 90
```

5. If waiting times out, check again with:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/contextual_login.py" --state-dir "${CLAUDE_PLUGIN_DATA:-${CLAUDE_SKILL_DIR}/.local}/login-jobs" status <job-id>
```

6. Retry the original blocked command after login succeeds.

Make sure the retried command includes `--config-id <config-id>`.

Do not ask the user to manually invoke another skill during normal CLI work.

## Everyday CLI Work

Use `cli-reference.md` for exact command forms.

Type discovery follows two tracks:

- reserved admin component types: do not rely on `ctxl types list` to discover these. For normal callers, type listing is effectively limited to tenant-defined custom object types. Treat this reserved set as known IDs:
  - `agent`
  - `flow`
  - `topics`
  - `api-configuration`
  - `ai-route`
  - `jwks-configuration`
  - `authorization-code-app`
- tenant-defined data object types: use `ctxl types list` to discover these, then `ctxl types get` to inspect the chosen type.

When inspecting a tenant, choose the track explicitly:

1. If the user is asking about flows, agents, connections, AI routes, JWKS configs, authz code apps, or topics, start from the reserved component map.
2. If the user is asking about tenant business data, schemas, records, triggers, actions, or custom objects, start with `ctxl types list`.
3. Once you know the type ID, use `ctxl types get --type <type-id> --config-id <config-id>` and then `ctxl records ... --type <type-id> --config-id <config-id>`.

Common reads:

- configs: `ctxl config list --json`, `ctxl config current --json`, `ctxl config get <config-id> --json`
- types: `ctxl types list --config-id <config-id>`, `ctxl types get --type <type-id> --config-id <config-id>`
- records: `ctxl records list --type <type-id> --config-id <config-id>`, `ctxl records get --type <type-id> --id <id> --config-id <config-id>`, `ctxl records query --type <type-id> --query-file <file> --config-id <config-id>`, `ctxl records stats --type <type-id> --id <id> --config-id <config-id>`

Reserved admin component examples:

```bash
ctxl types get --type flow --config-id <config-id>
ctxl records list --type flow --config-id <config-id>
ctxl types get --type agent --config-id <config-id>
ctxl records list --type agent --config-id <config-id>
ctxl types get --type ai-route --config-id <config-id>
ctxl records list --type ai-route --config-id <config-id>
```

Tenant-defined data object example:

```bash
ctxl types list --config-id <config-id>
ctxl types get --type <custom-type-id> --config-id <config-id>
ctxl records list --type <custom-type-id> --config-id <config-id>
```

For writes:

- create with `ctxl types add` or `ctxl records add`
- patch with `ctxl records patch`
- replace with `ctxl types replace` or `ctxl records replace`

## Flow Work

Flows are records under `--type flow`.

Useful commands:

```bash
ctxl records list --type flow --config-id <config-id>
ctxl records get --type flow --id <flow-id> --config-id <config-id>
```

When summarizing a flow, inspect `node_red_data.flows` and report:

- tabs
- entry points
- main execution chains
- major branches
- referenced record types

For flow edits:

1. Fetch the current flow to a temp file.
2. Create the proposed edited file.
3. Preview the diff:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/json_diff.py" <current-file> <proposed-file>
```

4. Show the diff to the user and ask for explicit confirmation.
5. Replace only after confirmation:

```bash
ctxl records replace --type flow --id <flow-id> --input-file <proposed-file> --config-id <config-id>
```

6. Re-read the flow and verify the expected structure landed.

For record patches, show the exact `ctxl records patch ...` flags before confirmation.

## Important Flow Heuristics

- For `flow-http`, HTTP In paths are root-relative to the flow subdomain. Use `/list`, not `/<flow-id>/list`.
- Treat event-trigger payload data as `msg.payload` unless docs clearly say otherwise.
- `log-tap` must have `outputs: 1` and a valid `level`.
- Wire `log-tap` inline in the chain, not as a dead-end fork.
- For new flows, preserve top-level `flows_cred: {}` and tab `env: []`.
- After edits, re-read the flow and verify the change actually landed.

## Output Expectations

- State the result first.
- Summarize command results unless the user explicitly asked for raw output.
- When auth recovery happens, continue the original task after retry.
- For writes, include the diff or exact patch plan before asking for confirmation.
- After any confirmed write, verify and report what changed.
