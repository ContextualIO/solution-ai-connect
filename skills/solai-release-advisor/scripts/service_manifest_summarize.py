#!/usr/bin/env python3
"""Summarize a Contextual service manifest as a compact table.

Two modes:
  - Single manifest: print the current working manifest (or a specific release) with
    typeId / instanceId / version per direct and peer dependency. Strips inline
    `data` payloads so output is bounded even for large services.
  - Comparison: with --compare-against-release, additionally fetch that release's
    manifest and align rows side-by-side. For each direct dep, also fetch the
    tenant's actual current max version of the record so the operator can spot
    drift between the working pin and the live record.

Auth is delegated to the active `ctxl` config; pass --config-id explicitly.

Outputs JSON when --format=json (suitable for piping into another tool) or a
markdown table when --format=table (default, human-readable).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any


def ensure_ctxl() -> None:
    if shutil.which("ctxl") is None:
        raise SystemExit("ctxl is not installed or not on PATH.")


def run_ctxl(args: list[str]) -> dict[str, Any] | list[Any]:
    """Run a ctxl subcommand and return parsed JSON. Raises on non-zero exit."""
    result = subprocess.run(["ctxl", *args], capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"ctxl {' '.join(args)} failed with exit {result.returncode}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"could not parse ctxl JSON output: {exc}")


def fetch_service(service_id: str, config_id: str) -> dict[str, Any]:
    return run_ctxl(["services", "get", service_id, "--config-id", config_id])  # type: ignore[return-value]


def fetch_service_with_data(service_id: str, config_id: str) -> dict[str, Any]:
    return run_ctxl(["services", "get", service_id, "--with-data", "--config-id", config_id])  # type: ignore[return-value]


def fetch_release(service_id: str, version: int, config_id: str) -> dict[str, Any]:
    return run_ctxl([
        "servicereleases", "get", service_id,
        "-v", str(version),
        "--config-id", config_id,
    ])  # type: ignore[return-value]


def fetch_tenant_max_version(type_id: str, instance_id: str | None, config_id: str) -> int | None:
    """Return the highest existing _metaData.version for a record in the tenant.

    For type-definition entries (no instance_id), we read the type record itself.
    For instance entries, we use recordversions list with page-size 1 and a
    descending version order so the first item carries the max.
    """
    if instance_id is None:
        # Type definition itself — version is on the type record, not in recordversions.
        try:
            type_record = run_ctxl(["types", "get", f"native-object:{type_id}", "--config-id", config_id])
        except SystemExit:
            return None
        if isinstance(type_record, dict):
            meta = type_record.get("_metaData") or {}
            v = meta.get("version")
            return int(v) if isinstance(v, int) else None
        return None

    try:
        result = run_ctxl([
            "recordversions", "list",
            "--type", type_id,
            "--id", instance_id,
            "--page-size", "1",
            "--include-total",
            "--order-by", "version:desc",
            "--config-id", config_id,
        ])
    except SystemExit:
        return None
    if not isinstance(result, dict):
        return None
    items = result.get("items") or []
    if not items:
        return None
    # recordversions list items carry the underlying record's version as a top-level
    # `version` field. The item's own `_metaData` is audit metadata about the version
    # record itself, not the underlying record.
    v = items[0].get("version")
    return int(v) if isinstance(v, int) else None


def strip_data(dep: dict[str, Any]) -> dict[str, Any]:
    """Project a dependency entry to (typeId, instanceId, version) — drop `data`."""
    return {
        "typeId": dep.get("typeId"),
        "instanceId": dep.get("instanceId"),
        "version": dep.get("version"),
    }


def manifest_deps(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (direct, peer) dependency lists with `data` stripped."""
    deps = manifest.get("dependencies") or {}
    direct = [strip_data(d) for d in (deps.get("direct") or [])]
    peer = [strip_data(d) for d in (deps.get("peer") or [])]
    return direct, peer


def dep_key(dep: dict[str, Any]) -> tuple[str, str]:
    """Stable identity for a dep across manifests."""
    return (dep.get("typeId") or "", dep.get("instanceId") or "")


def classify(released_version: int | None, working_version: int | None, tenant_max: int | None) -> str:
    """Classify the relationship between released, working, and tenant-max versions."""
    if released_version is None and working_version is not None:
        return "added"
    if released_version is not None and working_version is None:
        return "removed"
    if released_version == working_version:
        if tenant_max is not None and working_version is not None and tenant_max > working_version:
            return f"drift (+{tenant_max - working_version})"
        return "clean"
    if working_version is not None and released_version is not None:
        if working_version > released_version:
            return "bump"
        return "behind"
    return "unknown"


def render_table_single(
    service: dict[str, Any],
    direct: list[dict[str, Any]],
    peer: list[dict[str, Any]],
    *,
    is_release: bool = False,
) -> str:
    lines: list[str] = []
    sid = service.get("id")
    name = service.get("name")
    version = service.get("version")
    track = service.get("releaseTrack")
    source = service.get("sourceTenantId")
    header = f"# Service: {sid}"
    if name:
        header += f" — {name}"
    lines.append(header)
    detail_bits = []
    if version is not None:
        version_label = "release version" if is_release else "working/current version"
        detail_bits.append(f"{version_label}: {version}")
    if track:
        detail_bits.append(f"release track: {track}")
    if source:
        detail_bits.append(f"installed from: {source}")
    elif not is_release:
        detail_bits.append("ownership: owned")
    lines.append("_" + " · ".join(detail_bits) + "_")
    lines.append("")

    lines.append(f"## Direct dependencies ({len(direct)})")
    if direct:
        lines.append("")
        lines.append("| typeId | instanceId | version |")
        lines.append("|---|---|---|")
        for d in direct:
            instance = d.get("instanceId") or "(type definition)"
            lines.append(f"| {d.get('typeId')} | {instance} | {d.get('version')} |")
    else:
        lines.append("_(none)_")
    lines.append("")

    lines.append(f"## Peer dependencies ({len(peer)})")
    if peer:
        lines.append("")
        lines.append("| typeId | instanceId | version |")
        lines.append("|---|---|---|")
        for d in peer:
            instance = d.get("instanceId") or "(type definition)"
            lines.append(f"| {d.get('typeId')} | {instance} | {d.get('version')} |")
    else:
        lines.append("_(none)_")

    return "\n".join(lines) + "\n"


def render_table_comparison(
    service: dict[str, Any],
    released_version: int,
    rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    sid = service.get("id")
    name = service.get("name")
    working_version = service.get("version")
    source = service.get("sourceTenantId")
    header = f"# Service: {sid}"
    if name:
        header += f" — {name}"
    lines.append(header)
    detail_bits = [
        f"working version: {working_version}",
        f"compared to released version: {released_version}",
    ]
    if source:
        detail_bits.append(f"installed from: {source}")
    else:
        detail_bits.append("ownership: owned")
    lines.append("_" + " · ".join(detail_bits) + "_")
    lines.append("")

    lines.append("## Direct dependency comparison")
    lines.append("")
    lines.append("| typeId | instanceId | released | working | tenant max | status |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        instance = r.get("instanceId") or "(type definition)"
        lines.append(
            f"| {r.get('typeId')} | {instance} | "
            f"{r.get('released_version') if r.get('released_version') is not None else '—'} | "
            f"{r.get('working_version') if r.get('working_version') is not None else '—'} | "
            f"{r.get('tenant_max') if r.get('tenant_max') is not None else '—'} | "
            f"{r.get('status')} |"
        )
    lines.append("")
    bump_count = sum(1 for r in rows if r.get("status") == "bump")
    drift_count = sum(1 for r in rows if str(r.get("status", "")).startswith("drift"))
    lines.append(
        f"_Summary: {bump_count} bump(s) staged in working manifest, "
        f"{drift_count} dep(s) with tenant drift above working pin._"
    )

    return "\n".join(lines) + "\n"


def build_comparison_rows(
    released_direct: list[dict[str, Any]],
    working_direct: list[dict[str, Any]],
    config_id: str,
    skip_tenant_max: bool,
) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for d in released_direct:
        by_key[dep_key(d)] = {
            "typeId": d.get("typeId"),
            "instanceId": d.get("instanceId"),
            "released_version": d.get("version"),
            "working_version": None,
            "tenant_max": None,
        }
    for d in working_direct:
        key = dep_key(d)
        row = by_key.setdefault(key, {
            "typeId": d.get("typeId"),
            "instanceId": d.get("instanceId"),
            "released_version": None,
            "working_version": None,
            "tenant_max": None,
        })
        row["working_version"] = d.get("version")

    rows = list(by_key.values())
    if not skip_tenant_max:
        for row in rows:
            row["tenant_max"] = fetch_tenant_max_version(
                row["typeId"], row.get("instanceId"), config_id,
            )

    for row in rows:
        row["status"] = classify(
            row.get("released_version"),
            row.get("working_version"),
            row.get("tenant_max"),
        )
    rows.sort(key=lambda r: (r.get("typeId") or "", r.get("instanceId") or ""))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a Contextual service manifest.")
    parser.add_argument("--service", required=True, help="Service id.")
    parser.add_argument("--config-id", required=True, help="ctxl config id.")
    parser.add_argument("--release", type=int, default=None,
                        help="Show this released version's manifest instead of the working manifest.")
    parser.add_argument("--compare-against-release", type=int, default=None,
                        help="Diff the working manifest against this released version.")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--skip-tenant-max", action="store_true",
                        help="In comparison mode, skip per-dep tenant-max lookups (faster, less complete).")
    args = parser.parse_args()

    ensure_ctxl()

    if args.release is not None and args.compare_against_release is not None:
        raise SystemExit("--release and --compare-against-release are mutually exclusive.")

    if args.compare_against_release is not None:
        working = fetch_service_with_data(args.service, args.config_id)
        released = fetch_release(args.service, args.compare_against_release, args.config_id)
        working_direct, _working_peer = manifest_deps(working)
        released_direct, _released_peer = manifest_deps(released)
        rows = build_comparison_rows(released_direct, working_direct, args.config_id, args.skip_tenant_max)
        if args.format == "json":
            sys.stdout.write(json.dumps({
                "service": args.service,
                "working_version": working.get("version"),
                "released_version": args.compare_against_release,
                "rows": rows,
            }, indent=2) + "\n")
        else:
            sys.stdout.write(render_table_comparison(working, args.compare_against_release, rows))
        return 0

    if args.release is not None:
        manifest = fetch_release(args.service, args.release, args.config_id)
        direct, peer = manifest_deps(manifest)
        if args.format == "json":
            sys.stdout.write(json.dumps({
                "service": args.service,
                "release_version": args.release,
                "direct": direct,
                "peer": peer,
            }, indent=2) + "\n")
        else:
            sys.stdout.write(render_table_single(manifest, direct, peer, is_release=True))
        return 0

    manifest = fetch_service_with_data(args.service, args.config_id)
    direct, peer = manifest_deps(manifest)
    if args.format == "json":
        sys.stdout.write(json.dumps({
            "service": args.service,
            "working_version": manifest.get("version"),
            "direct": direct,
            "peer": peer,
        }, indent=2) + "\n")
    else:
        sys.stdout.write(render_table_single(manifest, direct, peer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
