---
name: solai-release-advisor
description: Advise on the next release of a Contextual service you own — inspect which component bumps are available since the last release, preview the per-component change set, and compose the Build (pinning selected component versions via `services patch`) before snapping the release in the workspace UI. Also answers read-only "what's owned / what changed?" inventory questions. Produces decision support only; the actual release snap / install / update is performed in the workspace UI. Requires local shell access and an authenticated `ctxl` config.
argument-hint: "[service-id]"
---

# SolAI Release Advisor

This skill wraps the `services` and `servicereleases` CLI surface (documented in `solai-cli/cli-reference.md`) to help plan the next release of a service **you own** from the CLI / an agent context — composing the **Build** (the working manifest for the next Release Version) by pinning selected component versions, and assessing what each bump changes (behavioral vs cosmetic) before you snap. The workspace Build tab offers the same composition plus a side-by-side version diff in the browser; this skill is the scriptable, headless counterpart for terminal- and agent-driven workflows.

It produces structured decision support; it does not enact installs, updates, or release snaps. Those steps remain in the workspace web app.

## When to use

- Before **cutting a new release** of an owned service — to inspect which direct dependencies have bumps available since the last release, preview the per-component change set, and compose the Build (pinning selected component versions via `services patch`) before snapping the release in the UI.
- For lightweight inventory work ("what services exist / what changed?"), classify `ctxl services list` output without the full advisor flow.

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
3. Confirm `ctxl services` and `ctxl servicereleases` are available — run `ctxl services --help`. If the topics are not listed, tell the user their CLI build does not expose the services surface and stop.
4. Confirm an active config: `ctxl config current --json`. If none is set or the config is not logged in, follow `solai-cli`'s Automatic Auth Recovery flow first.
5. Read the **entire** `solai-cli/cli-reference.md` file in one pass — do not grep for specific sections like "Services" or "Service Releases", and do not skim. The file is the authoritative command reference for the rest of the session; reading it whole guarantees you see cross-cutting content like Output Formatting, large-payload warnings, write-discipline rules, and the source-tenant routing table that you'll need but might not think to grep for. Do not construct `ctxl` commands from memory.
6. On the **first invocation per session**, offer the helper-script permission setup below — the advisor and inventory workflows run the bundled Python helper, which otherwise fires a permission prompt on every call in shell-sandboxed environments like Claude Code.

## Permission Setup (first-invocation setup)

This skill's workflow fires several shell commands: a read-only helper script (`scripts/service_manifest_summarize.py`) plus a handful of direct `ctxl` reads (services list/get, servicereleases list/get/diff, config current). In shell-sandboxed environments like Claude Code, each one prompts for permission by default. Across an iteration cycle this is a lot of clicks.

On the first call within a session, present the user with a **three-way choice**:

> Permission setup for this skill. Three options:
>
> **1. Default — prompt every time** (no setup). Maximum visibility, maximum friction.
>
> **2. Helper script only**. Allow-list the `python3 …/scripts/service_manifest_summarize.py` pattern. The script handles most of the heavy lifting, but you'll still get prompted for the agent's direct `ctxl` reads (services list, services get, servicereleases list/get/diff, etc.).
>
> **3. Helper script + narrow read-only `ctxl` patterns + `jq`**. Allow-list the script, the specific `ctxl` read verbs this skill uses, and `jq` (used for inline JSON parsing alongside the `ctxl` reads). Friction-free for read workflows. **Writes** (`services patch`, `records patch`, etc.) **still prompt** because they are deliberately not in the list.

The choice belongs to the user. Default to recommending option 3 if the user wants a smooth iteration cycle and has confirmed they understand writes still prompt; recommend option 2 if they want more visibility into direct `ctxl` calls; option 1 if they want full visibility into every call.

If the user picks option 1: proceed normally. No setup needed.

If the user picks option 2 or 3: apply the setup below.

### Claude Code (most common)

Allow rules live in `.claude/settings.json` under `permissions.allow`. Before writing, **audit existing rules** (see "Audit existing rules before adding" below).

For **option 2** (helper script only):

```json
{
  "permissions": {
    "allow": [
      "Bash(python3 *solai-release-advisor/scripts/service_manifest_summarize.py*)"
    ]
  }
}
```

For **option 3** (helper script + narrow `ctxl` reads + `jq`):

```json
{
  "permissions": {
    "allow": [
      "Bash(python3 *solai-release-advisor/scripts/service_manifest_summarize.py*)",
      "Bash(ctxl config current*)",
      "Bash(ctxl config list*)",
      "Bash(ctxl services list*)",
      "Bash(ctxl services get*)",
      "Bash(ctxl servicereleases list*)",
      "Bash(ctxl servicereleases get*)",
      "Bash(ctxl servicereleases diff*)",
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

Permission models differ. Present the script path and command shapes from option 2 or option 3 above and ask the user to apply the equivalent allow-rules in their tool's mechanism. Apply the same discipline: narrow patterns over broad ones, no patterns that cover write subcommands. If their environment has no such mechanism, the default prompt-each-time path is the only option.

### Reverting the allow-list later

If the user wants to remove the allow-list after testing, the entries to remove are whichever subset they added (the `Bash(python3 ...)` pattern for option 2, plus the seven `Bash(ctxl ...)` patterns for option 3). Removing the lines reverts to per-invocation prompting.

## Hard Rules

- This skill **never** runs `services patch` or any other write without explicit user confirmation that follows a diff/preview step.
- This skill **never** claims to install, update, or publish a service. Those actions happen in the workspace UI; the skill produces the patch plan the user takes into that UI.
- Always pass `--config-id <config-id>` on every `ctxl` command — never rely on `ctxl config use` alone.
- Helper script in `scripts/` is the canonical implementation of the Build-composition projection logic. Use it rather than hand-rolling per-command shell loops, especially when a service has many direct deps or any dep has many record versions — the script pre-summarizes output to bound context size.
- **Prefer `jq` over `python3 -c` for inline JSON parsing.** When you need to extract or transform a field from a `ctxl ...` response inline (e.g. `ctxl services list | jq '.items[].id'`), reach for `jq`. `jq` is read-only and typically allow-listed safely as `Bash(jq *)`; `python3 -c '...'` can execute arbitrary code and is a much broader allow-list surface. Reserve `python3 -c` for genuinely complex transformations that `jq` cannot express — and when you do use it, expect a per-invocation prompt unless the user has explicitly opted in to allow-listing it.
- Apply `solai-cli`'s [Disallowed In This Skill](../solai-cli/cli-reference.md#disallowed-in-this-skill) list — this skill inherits those restrictions.

## Workflow

This skill covers the **owned-service** release path. Detect ownership via `sourceTenantId`. Note that `services get` without `--with-data` returns only `id`/`name`/`version`/`_metaData` (no ownership or dependency detail), so pass `--with-data` — or classify from `services list`, which carries `sourceTenantId` per service:

```bash
ctxl services get <service-id> --with-data --config-id <config-id>
```

- `sourceTenantId` **absent** → **owned** → use the [Compose the Build](#compose-the-build-owned-services) advisor below.
- `sourceTenantId` **present** → **installed** (the service was installed from another tenant — operating on it means acting against a *target* tenant, often production). **This skill has no target-tenant workflow, and you must not improvise one.** Do **not** hand-roll update or pruning analysis: no interpreting `servicereleases --updates` / `updatediff`, no `recordversions` version-history checks, and no "what would be pruned" / hotfix-drift assessment. That analysis requires a dedicated installed-service workflow; done ad-hoc here it is unreliable and dangerous — a correct pruning check must compare the incoming pinned version against each record's **actual version history in the target tenant** (not the manifest's pin), and getting it wrong yields a false "nothing will be pruned." The workspace does warn about pruning and dropped-dep removal at apply time, but a wrong pre-assessment still misleads the go/no-go decision before the user ever reaches that prompt. State that target-tenant assessment is out of scope for this skill, that the install/update and its review happen in the workspace UI (least-privilege credentials, per your organization's policy for production or otherwise sensitive tenants), and **stop** — do not offer update inspection as a consolation. (Listing services and owned-service reads remain fine.)

If the user asks for a service-wide inventory across the tenant without specifying an ID, start with `ctxl services list --include-total --config-id <config-id>`, classify each by `sourceTenantId`, and dig into an **owned** service.

## Compose the Build (owned services)

For an owned service, the next release is composed in two steps:

1. **Compose the Build** — pin component versions into the working manifest via `ctxl services patch --set-direct <uri>#N` (or `--add-direct` / `--add-peer` / `--remove-direct`). The CLI is the authoring surface; the core motion is selecting a version (not always the latest) for each component, occasionally adding or dropping a dep.
2. **Snap the release** in the workspace UI to freeze the Build into an immutable release record.

This skill helps with step 1.

### Inspect candidate bumps

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/service_manifest_summarize.py" \
  --service <service-id> \
  --config-id <config-id> \
  --compare-against-release <latest-released-version>
```

The script:

1. Fetches the current working manifest (`services get <service-id> --with-data` — required to return the dependency manifest — projecting away inline `.data`).
2. Fetches the last released manifest (`servicereleases get <service-id> -v <latest>`).
3. Diffs the two — surfaces direct deps where the working version differs from the released version, and per-dep, the actual current max version of that record in the tenant.
4. Emits a compact table: `typeId | instanceId | released_version | working_version | tenant_max_version | suggested_action`.

For each row where `working_version != released_version` or `tenant_max > working_version`, decide with the user whether to bump the working manifest's pin (pin that version into the Build) or hold off (defer to a later release).

### Assess what a bump changes (net diff)

Show the **net** pinned→target diff before deciding a bump — not the intermediary churn (versions introduced-then-reverted net out). Drop `_metaData` noise (`hash`, `updatedAt`, `version`, `recordCount` — the last is live row count, not schema) and report whether the change is **behavioral or cosmetic**.

- **Records with an instance id** — flows, agents, connections, typed instances — diff directly: `ctxl recordversions diff native-object:<type-id>/<instance-id> <pinned>..<target> --format jsonpatch`.
- **Type definitions** (`native-object:<type-id>`, no instance id) are a **CLI blind spot**: the CLI exposes no type-def version retrieval (the registry API supports it — and the workspace Build tab diffs type-def versions side-by-side in the browser — but no `ctxl` command routes there). For the pinned→current case, reconstruct the diff from the CLI — the **pinned** content is the dep's hydrated `.data` in the working manifest (`services get <svc> --with-data` hydrates each dep at its pinned version), and the **current** content is `ctxl types get native-object:<type-id>`; diff the two with `solai-cli`'s `scripts/json_diff.py`. **Never** use `types get native-object:<type-id>#<version>` for the pinned side — the `#version` is silently ignored and returns current (a false "no changes"). For any comparison the CLI workaround can't express — arbitrary version-to-version where neither side is current (e.g. two historical releases) — point the user to the **Build tab's side-by-side version diff** in the browser.

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

Re-read the manifest (`--with-data` — the dependency entries appear only with it):

```bash
ctxl services get <service-id> --with-data --config-id <config-id>
```

Confirm the resulting `version` incremented and the dependency entries match expectations.

**One change per call.** Apply a single `--set-direct` / `--add-direct` / `--add-peer` per `services patch`, and re-verify with `services get` before the next — don't batch multiple add/set flags in one call, since they may not all take effect. When composing a multi-dependency Build, walk the user through the bumps one at a time, patching and confirming each before moving on.

### Snap the release

Tell the user: "The working manifest is updated. Snap the release in the workspace UI at `https://<tenant-id>.my.contextual.io/services/my-services/<service-id>` — pick the appropriate release track (`development`, `release-candidate`, `general-availability`, or `removed-from-distribution`) and add release notes. The CLI does not expose a release-snap command."

Resolve `<tenant-id>` via `ctxl config current --json` — never leave it as a literal placeholder.

## Helper Script

One script lives under `scripts/` and bounds output size + guarantees consistent logic for the workflow above:

- **`service_manifest_summarize.py`** — Compact manifest table for a service (current working manifest or a specific release), optionally diffed against another release. Strips inline `data` to keep output bounded. Used by the Build-composition advisor for the candidate-bumps view and by routine inventory work.

It takes `--config-id` and delegates auth to whatever the active `ctxl` config has set up; it performs no writes.

## Output Expectations

- State the bottom line first — "K direct dep(s) have bumps available since the last release."
- For any `services patch` operation, show the projected manifest diff before asking for confirmation.
- After any confirmed write, re-read with `services get --with-data` and report the resulting `version` and dependency list (`dependencies` appears only with `--with-data`).
- If the user asks for an installed-service / target-tenant operation, surface that this skill covers owned services only (see [Workflow](#workflow)) rather than improvising.
