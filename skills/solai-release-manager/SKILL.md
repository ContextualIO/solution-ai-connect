---
name: solai-release-manager
description: Audit and plan changes to Contextual services on a tenant. Two workflows — pre-update hotfix-drift audit on installed services (warn before a service update prunes target-tenant component versions), and pre-publish cherry-pick advisor on owned services (decide which component bumps to include in the next release). The skill produces reports and decision support; the actual install/update/release-snap is performed in the workspace UI. Requires local shell access and an authenticated `ctxl` config.
argument-hint: "[service-id] [--mode preview|assessment]"
---

# SolAI Release Manager

This skill wraps the `services` and `servicereleases` CLI surface (documented in `solai-cli/cli-reference.md`) with two release-management workflows that the platform UI does not yet provide warnings for. Use it whenever you are about to apply a service update on a target tenant, or planning the next release of a service you own.

It produces structured reports; it does not enact installs, updates, or release snaps. Those steps remain in the workspace web app today.

## When to use

- Before applying a **service update** in the workspace UI on a target tenant — to discover which direct-dependency versions in the target tenant exceed the incoming release's pinned versions and will therefore be pruned (typically hotfixes applied since the last update). Pair the report with env-override planning so the same loss does not recur every update.
- Before **cutting a new release** of an owned service — to inspect which direct dependencies have bumps available since the last release, preview the per-component change set, and shape the `services patch` cherry-pick before snapping the release in the UI.
- For lightweight "what's installed?" / "what changed?" inventory work, this skill can also answer those questions without the full assessment flow — see [Preview mode](#preview-mode).

For raw CLI command shapes, defer to `solai-cli/cli-reference.md` (read it via the `solai-cli` skill rather than from the plugin path). This skill assumes the reference is available.

## Setup Check

On first invocation each session, check for plugin updates. Before running, tell the user:

> Checking for Solution AI Connect plugin updates — you may be prompted to allow this command.

Then run:

```bash
claude plugin update ctxl@contextual-io
```

If the output mentions "updated from X to Y", tell the user: "Solution AI Connect plugin updated from X to Y — restart Claude to load the new version, then re-invoke this skill." If "already at the latest version", proceed.

Only run this check once per session.

## Runtime Checks

1. Confirm the environment can run shell commands.
2. Run `command -v ctxl && ctxl --version`. If missing, tell the user the CLI must be installed before this skill can run.
3. Confirm `ctxl services` and `ctxl servicereleases` are available — run `ctxl services --help`. If the topics are not listed, tell the user their CLI build does not expose the services surface yet and stop.
4. Confirm an active config: `ctxl config current --json`. If none is set or the config is not logged in, follow `solai-cli`'s Automatic Auth Recovery flow first.
5. Read the **entire** `solai-cli/cli-reference.md` file in one pass — do not grep for specific sections like "Services" or "Service Releases", and do not skim. The file is the authoritative command reference for the rest of the session; reading it whole guarantees you see cross-cutting content like Output Formatting, large-payload warnings, write-discipline rules, and the source-tenant routing table that you'll need but might not think to grep for. Do not construct `ctxl` commands from memory.
6. On the **first invocation per session**, offer the helper-script permission setup below — both audit/inventory workflows run the bundled Python helpers, which otherwise fire a permission prompt on every call in shell-sandboxed environments like Claude Code.

## Permission Setup (first-invocation setup)

This skill's workflows fire many shell commands: two read-only helper scripts (`scripts/service_manifest_summarize.py`, `scripts/hotfix_drift_report.py`) plus a handful of direct `ctxl` reads (services list/get, servicereleases list/get/diff/updatediff, config current). In shell-sandboxed environments like Claude Code, each one prompts for permission by default. Across an iteration cycle this is a lot of clicks.

On the first call within a session, present the user with a **three-way choice**:

> Permission setup for this skill. Three options:
>
> **1. Default — prompt every time** (no setup). Maximum visibility, maximum friction.
>
> **2. Helper scripts only**. Allow-list the two `python3 …/scripts/*.py` patterns. The scripts handle most of the heavy lifting, but you'll still get prompted for the agent's direct `ctxl` reads (services list, services get, servicereleases list/get/diff/updatediff, etc.).
>
> **3. Helper scripts + narrow read-only `ctxl` patterns + `jq`**. Allow-list both the scripts, the specific `ctxl` read verbs this skill uses, and `jq` (used for inline JSON parsing alongside the `ctxl` reads). Friction-free for read workflows. **Writes** (`services patch`, `records patch`, etc.) **still prompt** because they are deliberately not in the list.

The choice belongs to the user. Default to recommending option 3 if the user wants a smooth iteration cycle and has confirmed they understand writes still prompt; recommend option 2 if they want more visibility into direct `ctxl` calls; option 1 if they want full visibility into every call.

If the user picks option 1: proceed normally. No setup needed.

If the user picks option 2 or 3: apply the setup below.

### Claude Code (most common)

Allow rules live in `.claude/settings.json` under `permissions.allow`. Before writing, **audit existing rules** (see "Audit existing rules before adding" below).

For **option 2** (helper scripts only):

```json
{
  "permissions": {
    "allow": [
      "Bash(python3 *solai-release-manager/scripts/service_manifest_summarize.py*)",
      "Bash(python3 *solai-release-manager/scripts/hotfix_drift_report.py*)"
    ]
  }
}
```

For **option 3** (helper scripts + narrow `ctxl` reads + `jq`):

```json
{
  "permissions": {
    "allow": [
      "Bash(python3 *solai-release-manager/scripts/service_manifest_summarize.py*)",
      "Bash(python3 *solai-release-manager/scripts/hotfix_drift_report.py*)",
      "Bash(ctxl config current*)",
      "Bash(ctxl config list*)",
      "Bash(ctxl services list*)",
      "Bash(ctxl services get*)",
      "Bash(ctxl servicereleases list*)",
      "Bash(ctxl servicereleases get*)",
      "Bash(ctxl servicereleases diff*)",
      "Bash(ctxl servicereleases updatediff*)",
      "Bash(jq *)"
    ]
  }
}
```

Notes on the patterns:
- The wildcard prefix `python3 *` covers the absolute path that `${CLAUDE_SKILL_DIR}` resolves to (which varies by plugin version installed under `~/.claude/plugins/cache/...`); the trailing `*` accepts any args.
- **Piped commands split on shell operators** (`|`, `&&`, `||`, `;`). Each segment is matched against the allow-list independently. So `ctxl servicereleases list ... | jq '...'` needs **both** `Bash(ctxl servicereleases list*)` **and** `Bash(jq *)` in the list — one rule per segment. Including `jq` here makes the agent's inline-parse idiom prompt-free.
- **`jq` is preferred over `python3 -c` for inline parsing.** `jq` is a read-only JSON filter — it cannot execute code or write files, so broadly allow-listing it (`Bash(jq *)`) is safe. `python3 -c '...'` can execute arbitrary code, so a broad `Bash(python3 -c *)` rule is a much larger surface area. **Do not add `Bash(python3 -c *)` to the allow-list by default.** If the user explicitly asks for it, surface the trade-off and let them decide.
- Writes are deliberately absent. `services patch`, `records patch`, `records replace`, `recordversions rollback`, `types replace`, `types add`, etc. will continue to prompt — preserving the diff-and-confirm discipline that protects the tenant.

If the user has the `update-config` skill available, invoke it to apply the change; otherwise show the JSON snippet and ask whether to write it to `.claude/settings.json` directly. Confirm before writing.

**Hot-reload behaviour.** Claude Code watches `settings.json` and reloads `permissions` rules live — newly added allow patterns take effect immediately for subsequent tool calls in the same session (no restart needed). Only `model` and `outputStyle` require a restart.

### Patterns to NEVER recommend

Regardless of which option the user picks, **never recommend broad `ctxl` topic patterns** — they would silently cover write subcommands and bypass the diff/confirm discipline:

| Pattern | Why not |
|---|---|
| `Bash(ctxl services *)` | Covers `ctxl services patch` (write — mutates a service's dependency manifest). |
| `Bash(ctxl records *)` | Covers `records patch`, `records replace`, `records add` (writes). |
| `Bash(ctxl types *)` | Covers `types replace`, `types add` (writes). |
| `Bash(ctxl recordversions *)` | Covers `recordversions rollback` (write — can truncate history). |
| `Bash(ctxl * patch *)` / `Bash(ctxl * replace *)` / `Bash(ctxl * rollback *)` | Covers any patch / replace / rollback subcommand on any topic. |

### Audit existing rules before adding

Before writing new rules, read the current `.claude/settings.json` (and any project-level / local overrides in the merge chain) and inspect `permissions.allow`. If any of the broad write-covering patterns from the table above are already present, surface them to the user as a tightening opportunity — **do not modify them silently**:

> Heads up — your current allow-list includes `Bash(ctxl services *)`, which covers `ctxl services patch` (a write that mutates a service's dependency manifest). Want to tighten this to the specific read verbs (`services list`, `services get`) and let `services patch` keep its prompt? Otherwise I'll leave it as-is.

Apply the same discipline to any other broad-pattern entries. Do not modify or remove existing rules without explicit user confirmation.

### Other environments (Codex, OpenCode, terminal-only)

Permission models differ. Present the script paths and command shapes from option 2 or option 3 above and ask the user to apply the equivalent allow-rules in their tool's mechanism. Apply the same discipline: narrow patterns over broad ones, no patterns that cover write subcommands. If their environment has no such mechanism, the default prompt-each-time path is the only option.

### Reverting the allow-list later

If the user wants to remove the allow-list after testing, the entries to remove are whichever subset they added (the two `Bash(python3 ...)` patterns for option 2, plus the eight `Bash(ctxl ...)` patterns for option 3). Removing the lines reverts to per-invocation prompting.

## Hard Rules

- This skill **never** runs `services patch` or any other write without explicit user confirmation that follows a diff/preview step.
- This skill **never** claims to install, update, or publish a service. Those actions happen in the workspace UI; the skill produces the report or patch plan the user takes into that UI.
- Always pass `--config-id <config-id>` on every `ctxl` command — never rely on `ctxl config use` alone.
- Treat direct and peer dependencies differently: pre-update pruning applies to **direct** deps only. Peer deps are not pruned and should not appear in the hotfix-drift report.
- Helper scripts in `scripts/` are the canonical implementation of the audit and cherry-pick projection logic. Use them rather than hand-rolling per-command shell loops, especially when a service has many direct deps or any dep has many record versions — the scripts pre-summarize output to bound context size.
- **Prefer `jq` over `python3 -c` for inline JSON parsing.** When you need to extract or transform a field from a `ctxl ...` response inline (e.g. `ctxl services list | jq '.items[].id'`), reach for `jq`. `jq` is read-only and typically allow-listed safely as `Bash(jq *)`; `python3 -c '...'` can execute arbitrary code and is a much broader allow-list surface. Reserve `python3 -c` for genuinely complex transformations that `jq` cannot express — and when you do use it, expect a per-invocation prompt unless the user has explicitly opted in to allow-listing it.
- Apply `solai-cli`'s [Disallowed In This Skill](../solai-cli/cli-reference.md#disallowed-in-this-skill) list — this skill inherits those restrictions.

## Workflow tracks

The two workflows branch on whether the service is **owned** or **installed** on the active tenant. Detect via `sourceTenantId` on the service get response:

```bash
ctxl services get <service-id> --config-id <config-id>
```

- `sourceTenantId` present → **installed** → use the [Hotfix-drift audit](#hotfix-drift-audit-installed-services) workflow.
- `sourceTenantId` absent → **owned** → use the [Cherry-pick advisor](#cherry-pick-advisor-owned-services) workflow.

If the user asks for a service-wide inventory across the tenant without specifying an ID, start with `ctxl services list --include-total --pretty --config-id <config-id>`, classify each by `sourceTenantId`, and ask which service to dig into.

## Hotfix-drift audit (installed services)

The pre-update audit walks the direct dependencies of the incoming release, fetches the target tenant's current state of each dependency, and flags any record where the target version exceeds the incoming pinned version. Those excess versions will be pruned when the update is applied in the workspace UI.

### Invoke

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/hotfix_drift_report.py" \
  --service <service-id> \
  --incoming-version <N> \
  --config-id <config-id> \
  --mode preview
```

The script:

1. Fetches the incoming release manifest (`servicereleases get <service-id> -v <N>`) for the source-tenant-pinned direct-dep versions.
2. Fetches the installed manifest (`services get <service-id>`) for the currently-applied version pin per dep.
3. For each direct dep, fetches the actual current version in the target tenant via `recordversions list ... --page-size 1 --include-total`.
4. Flags drift: any dep where target-tenant `version > incoming pinned version`.
5. For each flagged dep, runs `recordversions diff <uri> <incoming>..<current> --format jsonpatch` and counts ops by type (add/remove/replace/move) with a few representative paths — matches the large-diff summarization pattern in `solai-cli/cli-reference.md`.
6. Emits a markdown report grouped into three sections: hotfixes that will be pruned, env-override candidates (field-level divergences on connections / agents / etc. where prod values typically diverge from source), and clean components (no drift).

If `--incoming-version` is omitted, the script defaults to the highest available upstream version via `servicereleases list --updates`.

### Preview mode

Fast advisory report. Use when the user just wants to know "what am I dealing with?" before walking into the workspace UI.

- Emit the report to stdout.
- Summarize the three sections (counts + the most consequential items) inline to the user.
- Stop there — no acknowledgement collection.

### Assessment mode

Intentional, blocking flow. Produces a saved markdown artifact that becomes the formal record paired with the UI action.

**Before invoking, ask the user where they want the artifact written.** The script defaults to the current working directory (`./release-assessment-<service-id>-<UTC-timestamp>.md`) when `--output` is omitted — that's the right default for almost everyone since it lands the artifact alongside their other working files. Offer the default and let the user override with any path they prefer (e.g. a project-specific notes folder, a shared drive mount, etc.). **Do not** write to the plugin install directory (`${CLAUDE_SKILL_DIR}/.local/...`) — that path is version-pinned and gets wiped on plugin reinstall.

Invocation with the CWD default:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/hotfix_drift_report.py" \
  --service <service-id> \
  --incoming-version <N> \
  --config-id <config-id> \
  --mode assessment
```

Or with an explicit path:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/hotfix_drift_report.py" \
  --service <service-id> \
  --incoming-version <N> \
  --config-id <config-id> \
  --mode assessment \
  --output /path/the/user/picked/release-assessment.md
```

The script writes a markdown file with checkbox slots for each hotfix:

```
- [ ] Back-port to source service before update
- [ ] Apply (or confirm) env-appropriate override at update time
- [ ] Accept loss
```

Then the skill walks the user through each item:

1. Read the artifact aloud (or summarise each item, depending on length).
2. For each hotfix, ask the user to pick one option and add a short note explaining the choice.
3. For each env-override candidate, ask the user to confirm whether an existing override is correct, a new override should be applied at update time, or the divergence should be accepted as-is.
4. Update the markdown file in place with the user's selections and notes.
5. When all items are acknowledged, tell the user: "Assessment complete — the artifact at `<path>` is the record of your review. Apply the service update in the workspace UI now; remember to set or confirm the env-overrides you marked above at update time."

Do **not** proceed past an unacknowledged item. The friction is the point — the platform behaviour today is silent, and this skill exists to make it loud.

## Cherry-pick advisor (owned services)

For an owned service, the next release is composed by:

1. **Cherry-picking component versions** into the working manifest via `ctxl services patch --set-direct <uri>#N` (or `--add-direct` / `--remove-direct`). This is the cherry-pick — the CLI is the authoring surface.
2. **Snapping the release** in the workspace UI to produce an immutable release record.

This skill helps with step 1.

### Inspect candidate bumps

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/service_manifest_summarize.py" \
  --service <service-id> \
  --config-id <config-id> \
  --compare-against-release <latest-released-version>
```

The script:

1. Fetches the current working manifest (`services get <service-id>` without `--with-data`).
2. Fetches the last released manifest (`servicereleases get <service-id> -v <latest>`).
3. Diffs the two — surfaces direct deps where the working version differs from the released version, and per-dep, the actual current max version of that record in the tenant.
4. Emits a compact table: `typeId | instanceId | released_version | working_version | tenant_max_version | suggested_action`.

For each row where `working_version != released_version` or `tenant_max > working_version`, decide with the user whether to bump the working manifest's pin (cherry-pick that bump in) or hold off (defer to a later release).

### Project the patch

Before invoking `ctxl services patch`, project the patch and surface the resulting manifest. For each `--set-direct` / `--add-direct` flag the user agrees to, compute the resulting `dependencies.direct` list and show the diff against current.

Two ways to project — pick whichever is simpler for the change set:

- **Per-flag preview**: spell out each flag plus the URI it would set, and the version delta vs current.
- **Full projected manifest**: build the projected dependency list as JSON, run it through `scripts/json_diff.py` from the `solai-cli` skill against the current manifest, show the diff.

Show the projection. Ask for explicit confirmation. Only then invoke:

```bash
ctxl services patch <service-id> \
  --set-direct native-object:<type-id>/<instance-id>#<version> \
  --config-id <config-id>
```

Re-read the manifest:

```bash
ctxl services get <service-id> --config-id <config-id>
```

Confirm the resulting `version` incremented and the dependency entries match expectations.

### Snap the release

Tell the user: "The working manifest is updated. Snap the release in the workspace UI at `https://<tenant-id>.my.contextual.io/services/my-services/<service-id>` — pick the appropriate release track (`development`, `release-candidate`, `general-availability`, or `removed-from-distribution`) and add release notes. The CLI does not yet expose a release-snap command."

Resolve `<tenant-id>` via `ctxl config current --json` — never leave it as a literal placeholder.

## Helper Scripts

Two scripts live under `scripts/` and bound output size + guarantee consistent logic for the workflows above:

- **`service_manifest_summarize.py`** — Compact manifest table for a service (current working manifest or a specific release), optionally diffed against another release. Strips inline `data` to keep output bounded. Used by the cherry-pick advisor for the candidate-bumps view and by routine inventory work.
- **`hotfix_drift_report.py`** — Full pre-update audit: walks direct deps of an incoming release, compares each against the target tenant's current state, summarises diffs of pruned versions, and emits a markdown report. Supports `--mode preview` (stdout only) and `--mode assessment` (write checkbox-bearing artifact for interactive ack).

Both scripts take `--config-id` and delegate auth to whatever the active `ctxl` config has set up; neither performs writes.

## Output Expectations

- State the bottom line first — for a hotfix-drift audit, "N hotfix(es) will be pruned across M direct dep(s)" before any detail; for a cherry-pick advisor, "K direct dep(s) have bumps available since the last release."
- Always link the artifact path when assessment mode produces a file.
- For any `services patch` operation, show the projected manifest diff before asking for confirmation.
- After any confirmed write, re-read with `services get` and report the resulting `version` and dependency list.
- Surface owned/installed mismatches clearly — if the user asks for `--updates` on an owned service, explain why the operation is not available rather than retrying.
