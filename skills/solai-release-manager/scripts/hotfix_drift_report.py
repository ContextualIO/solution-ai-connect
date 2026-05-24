#!/usr/bin/env python3
"""Pre-update hotfix-drift audit for a Contextual service on a target tenant.

When a service update is applied in the workspace UI, direct dependencies are
reset to the versions pinned in the incoming release. Any version of a direct
dep that exists in the target tenant above the incoming pinned version is
pruned. Those incremental versions are usually hotfixes applied between
updates, and today the platform does not warn before they are lost.

This script audits an upcoming update before the user enacts it in the UI:

  1. Determines the incoming release (defaults to the highest available
     upstream release via `servicereleases list --updates`).
  2. Reads the direct-dep pin list from that release.
  3. For each direct dep, fetches the target tenant's current max version of
     the record (`recordversions list` page-size 1, ordered desc).
  4. Flags drift where tenant max > incoming pin and runs
     `recordversions diff <uri> <incoming>..<current> --format jsonpatch` to
     summarise what would be pruned. Diffs are reduced to op counts and a
     handful of representative paths so a large drift does not blow up
     context.
  5. Heuristically classifies each diff op as an env-override candidate
     (e.g. endpoints, secrets, agent sizing) or a true hotfix.
  6. Emits a markdown report. In preview mode it goes to stdout; in
     assessment mode it is written to a file with checkbox slots intended
     for interactive acknowledgement by the release manager before they
     run the update in the UI.

The script never enacts a service update or any other write.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ENV_SENSITIVE_KEYWORDS = (
    # connection / api-configuration
    "endpoint", "host", "url", "baseUrl",
    "bearerToken", "apiKey", "secret", "token", "credentials",
    "clientId", "clientSecret", "orgId", "tenant",
    "headers",
    # agent
    "envVars",
    "size", "image",
    "minReplicas", "maxReplicas", "targetCpu",
    "livenessTimeoutSeconds", "scaleType",
    "pollingInterval", "cooldownPeriod", "lagThreshold",
)

MAX_REPRESENTATIVE_PATHS_PER_OP = 5


def ensure_ctxl() -> None:
    if shutil.which("ctxl") is None:
        raise SystemExit("ctxl is not installed or not on PATH.")


def run_ctxl(args: list[str], allow_failure: bool = False) -> Any:
    result = subprocess.run(["ctxl", *args], capture_output=True, text=True)
    if result.returncode != 0:
        if allow_failure:
            return None
        sys.stderr.write(result.stderr)
        raise SystemExit(f"ctxl {' '.join(args)} failed with exit {result.returncode}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        if allow_failure:
            return None
        raise SystemExit(f"could not parse ctxl JSON output: {exc}")


def fetch_service(service_id: str, config_id: str) -> dict[str, Any]:
    return run_ctxl(["services", "get", service_id, "--config-id", config_id])


def fetch_available_updates(service_id: str, config_id: str) -> list[dict[str, Any]]:
    """Return the available upstream releases for an installed service.

    The CLI's `servicereleases list --updates` is the only `servicereleases` read
    path that routes via the installed service's `sourceTenantId` and returns
    release records that live on the source tenant. Plain `servicereleases get`
    against the target tenant 404s for installed services, since the release
    record only exists on the source. Each item in this response is the full
    release object (`id`, `version`, `releaseTrack`, `description`,
    `dependencies.direct[]` with inline `data`, `_metaData`) — so we never need
    a separate `servicereleases get` call for incoming-release inspection.
    """
    result = run_ctxl([
        "servicereleases", "list", service_id,
        "--updates",
        "--include-total",
        "--page-size", "250",
        "--order-by", "version:desc",
        "--config-id", config_id,
    ])
    if isinstance(result, dict):
        return list(result.get("items") or [])
    return []


def fetch_tenant_max_version(type_id: str, instance_id: str | None, config_id: str) -> int | None:
    if instance_id is None:
        type_record = run_ctxl(
            ["types", "get", f"native-object:{type_id}", "--config-id", config_id],
            allow_failure=True,
        )
        if isinstance(type_record, dict):
            v = (type_record.get("_metaData") or {}).get("version")
            return int(v) if isinstance(v, int) else None
        return None

    result = run_ctxl([
        "recordversions", "list",
        "--type", type_id,
        "--id", instance_id,
        "--page-size", "1",
        "--include-total",
        "--order-by", "version:desc",
        "--config-id", config_id,
    ], allow_failure=True)
    if not isinstance(result, dict):
        return None
    items = result.get("items") or []
    if not items:
        return None
    # recordversions list items carry the underlying record's version as a top-level
    # `version` field; their own `_metaData` is audit metadata about the version record.
    v = items[0].get("version")
    return int(v) if isinstance(v, int) else None


def fetch_jsonpatch_diff(type_id: str, instance_id: str | None, low: int, high: int, config_id: str) -> list[dict[str, Any]] | None:
    """Return the jsonpatch diff between low and high versions of a record, or None on error.

    Note: `ctxl recordversions diff` exits **1 when versions differ** and **0 when
    identical** (documented in cli-reference.md). Both exit codes are normal — the
    stdout is valid JSON in either case. We can't go through the generic `run_ctxl`
    helper here because it treats any non-zero exit as failure.
    """
    if instance_id is None:
        # Type definitions don't currently support recordversions diff in the same way; skip.
        return None
    uri = f"native-object:{type_id}/{instance_id}"
    result = subprocess.run(
        ["ctxl", "recordversions", "diff", uri, f"{low}..{high}",
         "--format", "jsonpatch", "--config-id", config_id],
        capture_output=True, text=True,
    )
    # exit 0 = identical, exit 1 = differs — both are valid outcomes; other codes are errors.
    if result.returncode not in (0, 1):
        return None
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, list):
        return parsed
    return None


def is_platform_metadata_path(path: str) -> bool:
    """Platform-managed audit envelope (`_metaData.*`) — `hash`, `updatedAt`, `version`,
    etc. — changes on every record save and is not a content change worth surfacing
    to a release manager."""
    lower = path.lower()
    return "/_metadata/" in lower or lower.endswith("/_metadata")


def is_env_sensitive_path(path: str) -> bool:
    """Best-effort: does this JSON Patch path touch a known env-sensitive field?"""
    lowered = path.lower()
    for kw in ENV_SENSITIVE_KEYWORDS:
        if kw.lower() in lowered:
            return True
    return False


def summarize_ops(ops: list[dict[str, Any]]) -> dict[str, Any]:
    """Group JSON Patch ops by type and bucket each path as platform-metadata noise,
    env-override-pattern divergence, or genuine functional change.

    Returns a structure suitable for direct rendering into the markdown report.
    """
    by_op: dict[str, list[str]] = {}
    metadata_paths: list[str] = []
    env_paths: list[str] = []
    functional_paths: list[str] = []
    for op in ops:
        op_name = str(op.get("op", "unknown"))
        path = str(op.get("path", ""))
        by_op.setdefault(op_name, []).append(path)
        if is_platform_metadata_path(path):
            metadata_paths.append(path)
        elif is_env_sensitive_path(path):
            env_paths.append(path)
        else:
            functional_paths.append(path)
    return {
        "total_ops": len(ops),
        "by_op": {k: {"count": len(v), "examples": v[:MAX_REPRESENTATIVE_PATHS_PER_OP]} for k, v in by_op.items()},
        "metadata_ops": len(metadata_paths),
        "metadata_example_paths": metadata_paths[:MAX_REPRESENTATIVE_PATHS_PER_OP],
        "env_pattern_ops": len(env_paths),
        "env_example_paths": env_paths[:MAX_REPRESENTATIVE_PATHS_PER_OP],
        "functional_ops": len(functional_paths),
        "functional_example_paths": functional_paths[:MAX_REPRESENTATIVE_PATHS_PER_OP],
    }


def build_drift_rows(
    incoming_direct: list[dict[str, Any]],
    config_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dep in incoming_direct:
        type_id = dep.get("typeId")
        instance_id = dep.get("instanceId")
        incoming_pin = dep.get("version")
        if not isinstance(type_id, str) or not isinstance(incoming_pin, int):
            continue
        tenant_max = fetch_tenant_max_version(type_id, instance_id, config_id)
        row: dict[str, Any] = {
            "typeId": type_id,
            "instanceId": instance_id,
            "incoming_version": incoming_pin,
            "tenant_max": tenant_max,
            "drift": 0,
            "summary": None,
        }
        if tenant_max is not None and tenant_max > incoming_pin:
            row["drift"] = tenant_max - incoming_pin
            ops = fetch_jsonpatch_diff(type_id, instance_id, incoming_pin, tenant_max, config_id)
            if ops is not None:
                row["summary"] = summarize_ops(ops)
        rows.append(row)
    rows.sort(key=lambda r: (-(r.get("drift") or 0), r.get("typeId") or "", r.get("instanceId") or ""))
    return rows


def render_dep_label(row: dict[str, Any]) -> str:
    instance = row.get("instanceId") or "(type definition)"
    return f"`{row.get('typeId')} / {instance}`"


def render_markdown(
    service_id: str,
    service: dict[str, Any],
    incoming_release: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    assessment_mode: bool,
) -> str:
    lines: list[str] = []
    now = datetime.now(timezone.utc).isoformat()
    lines.append(f"# Hotfix-drift assessment — `{service_id}`")
    lines.append("")
    lines.append(f"_Generated: {now}_")
    lines.append("")
    lines.append("## Context")
    lines.append("")
    lines.append(f"- Service: `{service_id}` — {service.get('name') or '(no name)'}")
    lines.append(f"- Currently installed version: **{service.get('version')}**")
    lines.append(f"- Incoming release version: **{incoming_release.get('version')}** (track: `{incoming_release.get('releaseTrack')}`)")
    if service.get("sourceTenantId"):
        lines.append(f"- Source tenant: `{service.get('sourceTenantId')}`")
    if incoming_release.get("description"):
        lines.append("")
        lines.append("**Incoming release notes:**")
        lines.append("")
        lines.append("> " + str(incoming_release.get("description")).replace("\n", "\n> "))
    lines.append("")

    drifted = [r for r in rows if r.get("drift", 0) > 0]

    def _has_diff(r: dict[str, Any]) -> bool:
        return r.get("summary") is not None

    def _functional(r: dict[str, Any]) -> int:
        return (r.get("summary") or {}).get("functional_ops", 0)

    def _env(r: dict[str, Any]) -> int:
        return (r.get("summary") or {}).get("env_pattern_ops", 0)

    def _metadata(r: dict[str, Any]) -> int:
        return (r.get("summary") or {}).get("metadata_ops", 0)

    metadata_only = [r for r in drifted if _has_diff(r) and _functional(r) == 0 and _env(r) == 0 and _metadata(r) > 0]
    env_only = [r for r in drifted if _has_diff(r) and _functional(r) == 0 and _env(r) > 0]
    mixed = [r for r in drifted if _has_diff(r) and _functional(r) > 0 and _env(r) > 0]
    functional_only = [r for r in drifted if _has_diff(r) and _functional(r) > 0 and _env(r) == 0]
    unknown_drift = [r for r in drifted if not _has_diff(r)]
    clean = [r for r in rows if r.get("drift", 0) == 0]

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **{len(drifted)}** of **{len(rows)}** direct dep(s) carry version drift above the incoming pin.")
    lines.append(f"- {len(functional_only)} appear to be true hotfixes (functional changes).")
    lines.append(f"- {len(env_only)} appear to be env-override-pattern divergences only.")
    lines.append(f"- {len(mixed)} mix functional + env-override patterns.")
    lines.append(f"- {len(metadata_only)} are platform-metadata-only drift (e.g. record was re-saved with no content change — `_metaData/hash`, `updatedAt`, `version` only).")
    if unknown_drift:
        lines.append(f"- {len(unknown_drift)} have drift but no diff could be computed (e.g. type definitions).")
    lines.append(f"- {len(clean)} dep(s) are clean (tenant version == incoming pin).")
    lines.append("")
    if functional_only or env_only or mixed:
        lines.append("If you proceed with this update in the workspace UI **without action on the items below**, the listed component versions in the target tenant will be pruned.")
    else:
        lines.append("No functional or env-override drift detected. Any drift below is platform-metadata noise — pruning it is harmless.")
    lines.append("")

    if drifted:
        lines.append("## Hotfixes that will be pruned")
        lines.append("")
        for row in drifted:
            lines.append(f"### {render_dep_label(row)} — incoming v{row['incoming_version']} → tenant v{row['tenant_max']} (drift {row['drift']})")
            lines.append("")
            summary = row.get("summary")
            if summary:
                # Classify this drift row.
                if summary.get("functional_ops", 0) == 0 and summary.get("env_pattern_ops", 0) == 0 and summary.get("metadata_ops", 0) > 0:
                    lines.append("**Platform-metadata-only drift** — the record was re-saved (e.g. accidental save) without a content change. Pruning this is harmless.")
                    lines.append("")
                lines.append(f"Diff (jsonpatch, {summary['total_ops']} op(s) total):")
                lines.append("")
                for op_name, info in summary["by_op"].items():
                    lines.append(f"- `{op_name}`: {info['count']} op(s)")
                    for p in info["examples"]:
                        lines.append(f"  - `{p}`")
                lines.append("")
                if summary["functional_ops"] > 0:
                    lines.append(f"**Functional changes:** {summary['functional_ops']} op(s)")
                    for p in summary["functional_example_paths"]:
                        lines.append(f"- `{p}`")
                    lines.append("")
                if summary["env_pattern_ops"] > 0:
                    lines.append(f"**Env-override-pattern ops:** {summary['env_pattern_ops']} op(s) (matches keywords like endpoint / secret / size / envVars)")
                    for p in summary["env_example_paths"]:
                        lines.append(f"- `{p}`")
                    lines.append("")
                if summary["metadata_ops"] > 0:
                    lines.append(f"**Platform-metadata noise:** {summary['metadata_ops']} op(s) on `_metaData/*` paths — changes on every record save, not a content change.")
                    lines.append("")
            else:
                lines.append("_(No diff available — this typically applies to type-definition entries.)_")
                lines.append("")

            if assessment_mode:
                lines.append("**Decision:**")
                lines.append("")
                lines.append("- [ ] Back-port to source service before update")
                lines.append("- [ ] Apply (or confirm) env-appropriate override at update time")
                lines.append("- [ ] Accept loss")
                lines.append("")
                lines.append("Notes: _(fill in)_")
                lines.append("")
            lines.append("---")
            lines.append("")

    if clean:
        lines.append("## Clean components")
        lines.append("")
        for row in clean:
            lines.append(f"- {render_dep_label(row)} at v{row['incoming_version']} (tenant v{row.get('tenant_max') if row.get('tenant_max') is not None else '—'})")
        lines.append("")

    lines.append("## Next steps")
    lines.append("")
    if assessment_mode:
        lines.append("1. Fill in a decision for each pruned component above.")
        lines.append("2. For any component marked **back-port**: apply the equivalent change to the source service before continuing.")
        lines.append("3. For any component marked **env-override**: note the values to apply at update time in the workspace UI.")
        lines.append("4. When all decisions are recorded, apply the update in the workspace UI at the service detail page.")
    else:
        lines.append("This is a preview report. For an intentional, recorded review (with acknowledgement checkboxes), re-run with `--mode assessment --output <path>`.")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-update hotfix-drift audit for a Contextual service.")
    parser.add_argument("--service", required=True, help="Service id.")
    parser.add_argument("--config-id", required=True, help="ctxl config id (target tenant).")
    parser.add_argument("--incoming-version", type=int, default=None,
                        help="The release version that will be applied. Defaults to highest available upstream update.")
    parser.add_argument("--mode", choices=["preview", "assessment"], default="preview")
    parser.add_argument("--output", default=None,
                        help="Output path for assessment mode. Defaults to "
                             "./release-assessment-<service>-<UTC-timestamp>.md in the "
                             "current working directory when omitted.")
    args = parser.parse_args()

    ensure_ctxl()

    service = fetch_service(args.service, args.config_id)
    if not isinstance(service, dict):
        raise SystemExit("Could not fetch service.")

    if not service.get("sourceTenantId"):
        raise SystemExit(
            f"Service `{args.service}` is owned by this tenant (no sourceTenantId). "
            "The hotfix-drift audit is meaningful only for installed services. "
            "If you want to audit an owned service's release composition instead, use "
            "service_manifest_summarize.py --compare-against-release."
        )

    updates = fetch_available_updates(args.service, args.config_id)
    if not updates:
        if args.incoming_version is None:
            sys.stdout.write(
                f"No upstream updates available for `{args.service}` "
                f"(current installed version {service.get('version')}). Nothing to audit.\n"
            )
            return 0
        raise SystemExit(
            f"No upstream updates available — cannot inspect release v{args.incoming_version}. "
            f"On an installed service, the audit can only see releases visible to "
            f"`servicereleases list --updates` (which routes via the source tenant); "
            f"`servicereleases get` directly on the target tenant 404s because release "
            f"records live on the source."
        )

    incoming_version = args.incoming_version
    if incoming_version is None:
        incoming_version = max(int(u.get("version")) for u in updates if isinstance(u.get("version"), int))

    incoming_release = next(
        (u for u in updates if isinstance(u.get("version"), int) and int(u.get("version")) == incoming_version),
        None,
    )
    if incoming_release is None:
        available = sorted(
            {int(u.get("version")) for u in updates if isinstance(u.get("version"), int)}
        )
        raise SystemExit(
            f"Release v{incoming_version} is not in the available-updates list for "
            f"`{args.service}`. Available updates above current install: {available}."
        )

    incoming_direct = ((incoming_release.get("dependencies") or {}).get("direct") or [])
    rows = build_drift_rows(incoming_direct, args.config_id)

    report = render_markdown(
        args.service, service, incoming_release, rows,
        assessment_mode=(args.mode == "assessment"),
    )

    if args.mode == "assessment":
        if args.output:
            out_path = Path(args.output)
        else:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            out_path = Path.cwd() / f"release-assessment-{args.service}-{ts}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        sys.stdout.write(f"Assessment artifact written to {out_path}\n")
    else:
        sys.stdout.write(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
