#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
PROTOCOL_VERSION = "2025-06-18"
ID_SCHEMA = {
    "oneOf": [
        {"type": "string"},
        {"type": "array", "items": {"type": "string"}, "minItems": 1},
    ]
}
INPUT_SCHEMA = {
    "oneOf": [
        {"type": "object"},
        {"type": "array"},
        {"type": "string"},
    ]
}


def stderr(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def write_message(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":"), ensure_ascii=True))
    sys.stdout.write("\n")
    sys.stdout.flush()


def parse_json_output(stdout: str) -> Any:
    trimmed = stdout.strip()
    if not trimmed:
        return None

    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        pass

    lines = [line.strip() for line in trimmed.splitlines() if line.strip()]
    if not lines:
        return None

    try:
        return [json.loads(line) for line in lines]
    except json.JSONDecodeError:
        return trimmed


def pretty_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, indent=2, sort_keys=True)


def tool_result(payload: Any, *, text: str | None = None, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "content": [
            {
                "type": "text",
                "text": text or pretty_text(payload),
            }
        ]
    }
    if isinstance(payload, dict):
        result["structuredContent"] = payload
    elif isinstance(payload, list):
        result["structuredContent"] = {"items": payload}
    if is_error:
        result["isError"] = True
    return result


def error_tool_result(message: str, **details: Any) -> dict[str, Any]:
    payload = {"ok": False, "message": message, **details}
    return tool_result(payload, is_error=True)


def success_response(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def error_response(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def run_process(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        cwd=str(cwd or ROOT),
        env=env,
        input=input_text,
        text=True,
    )


def ctxl_installed() -> bool:
    return run_process(["bash", "-lc", "command -v ctxl >/dev/null 2>&1"]).returncode == 0


def looks_like_auth_error(stdout: str, stderr_text: str) -> bool:
    haystack = f"{stdout}\n{stderr_text}".lower()
    hints = [
        "authorization",
        "unauthorized",
        "invalid_grant",
        "refresh token",
        "401",
        "login",
        "expired",
    ]
    return any(hint in haystack for hint in hints)


def run_ctxl(
    args: list[str],
    *,
    config_id: str | None = None,
    input_text: str | None = None,
    expect_json: bool = True,
) -> tuple[bool, dict[str, Any]]:
    if not ctxl_installed():
        return False, {
            "ok": False,
            "message": "Contextual access is not installed.",
            "nextStep": "Run setup_access first.",
        }

    command = ["ctxl", *args]
    if config_id:
        command.extend(["--config-id", config_id])

    completed = run_process(command, input_text=input_text)
    stdout = completed.stdout.strip()
    stderr_text = completed.stderr.strip()
    if completed.returncode != 0:
        return False, {
            "ok": False,
            "message": "Contextual command failed.",
            "command": command,
            "stdout": stdout,
            "stderr": stderr_text,
            "authRequired": looks_like_auth_error(stdout, stderr_text),
        }

    parsed = parse_json_output(stdout) if expect_json else stdout
    return True, {
        "ok": True,
        "command": command,
        "stdout": stdout,
        "stderr": stderr_text,
        "result": parsed,
    }


def run_login_script(arguments: list[str]) -> tuple[bool, dict[str, Any]]:
    completed = run_process([sys.executable, str(SCRIPTS_DIR / "contextual_login.py"), *arguments])
    stdout = completed.stdout.strip()
    stderr_text = completed.stderr.strip()
    parsed = parse_json_output(stdout)
    if completed.returncode != 0:
        if isinstance(parsed, dict) and parsed.get("error"):
            return False, {"ok": False, "message": parsed["error"], "stderr": stderr_text}
        return False, {"ok": False, "message": "Login helper failed.", "stdout": stdout, "stderr": stderr_text}
    if isinstance(parsed, dict):
        parsed["ok"] = True
        return True, parsed
    return True, {"ok": True, "result": parsed}


def as_string(arguments: dict[str, Any], key: str, *, required: bool = False) -> str | None:
    value = arguments.get(key)
    if value is None:
        if required:
            raise ValueError(f"Missing required field: {key}")
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected '{key}' to be a non-empty string")
    return value


def require_string(arguments: dict[str, Any], key: str) -> str:
    value = as_string(arguments, key, required=True)
    assert value is not None
    return value


def as_integer(arguments: dict[str, Any], key: str) -> int | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"Expected '{key}' to be an integer")
    return value


def as_boolean(arguments: dict[str, Any], key: str) -> bool | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"Expected '{key}' to be a boolean")
    return value


def as_string_list(arguments: dict[str, Any], key: str) -> list[str]:
    value = arguments.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"Expected '{key}' to be an array of strings")
    return value


def as_id_list(arguments: dict[str, Any]) -> list[str]:
    value = arguments.get("id")
    if value is None:
        return []
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) and item for item in value):
        return value
    raise ValueError("Expected 'id' to be a string or an array of strings")


def as_input_text(arguments: dict[str, Any], *, required: bool = False) -> str | None:
    value = arguments.get("input")
    if value is None:
        if required:
            raise ValueError("Missing required field: input")
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def append_repeated_flag(args: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        args.extend([flag, value])


def append_optional_flag(args: list[str], flag: str, value: str | int | None) -> None:
    if value is not None:
        args.extend([flag, str(value)])


def append_boolean_flag(args: list[str], flag: str, value: bool | None) -> None:
    if value:
        args.append(flag)


def apply_selector(
    args: list[str],
    arguments: dict[str, Any],
    *,
    require_uri_or_type: bool = False,
    allow_multiple_ids: bool = True,
) -> None:
    uri = as_string(arguments, "uri")
    type_name = as_string(arguments, "type")
    ids = as_id_list(arguments)

    if require_uri_or_type and not uri and not type_name:
        raise ValueError("Expected 'uri' or 'type'")
    if not allow_multiple_ids and len(ids) > 1:
        raise ValueError("Only one id value is allowed for this command")

    if uri:
        args.append(uri)
    if type_name:
        args.extend(["--type", type_name])
    append_repeated_flag(args, "--id", ids)


def apply_list_flags(args: list[str], arguments: dict[str, Any], *, include_search_filters: bool) -> None:
    append_repeated_flag(args, "--order-by", as_string_list(arguments, "orderBy"))
    append_optional_flag(args, "--page-size", as_integer(arguments, "pageSize"))
    append_optional_flag(args, "--page-token", as_string(arguments, "pageToken"))
    append_boolean_flag(args, "--include-total", as_boolean(arguments, "includeTotal"))
    append_boolean_flag(args, "--export", as_boolean(arguments, "export"))
    append_boolean_flag(args, "--progress", as_boolean(arguments, "progress"))

    if include_search_filters:
        append_repeated_flag(args, "--search", as_string_list(arguments, "search"))
        append_repeated_flag(args, "--exact-search", as_string_list(arguments, "exactSearch"))
        append_repeated_flag(args, "--from", as_string_list(arguments, "from"))
        append_repeated_flag(args, "--to", as_string_list(arguments, "to"))


def setup_access(arguments: dict[str, Any]) -> dict[str, Any]:
    env = os.environ.copy()
    install_mode = as_string(arguments, "installMode")
    local_repo = as_string(arguments, "localRepo")
    if install_mode:
        if install_mode not in {"auto", "npm", "local"}:
            return error_tool_result("installMode must be one of: auto, npm, local")
        env["CONTEXTUAL_CLI_INSTALL_MODE"] = install_mode
    if local_repo:
        env["CONTEXTUAL_CLI_REPO"] = local_repo

    completed = run_process(["bash", str(SCRIPTS_DIR / "setup_access.sh")], env=env)
    if completed.returncode != 0:
        return error_tool_result(
            "Failed to set up Contextual access.",
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )

    version_ok, version_payload = run_ctxl(["--version"], expect_json=False)
    list_ok, list_payload = run_ctxl(["config", "list", "--json"])
    current_ok, current_payload = run_ctxl(["config", "current", "--json"])

    payload = {
        "ok": True,
        "message": "Contextual access is ready.",
        "version": version_payload.get("result") if version_ok else None,
        "configs": list_payload.get("result") if list_ok else None,
        "currentConfig": current_payload.get("result") if current_ok else None,
        "setupOutput": completed.stdout.strip(),
    }
    return tool_result(payload)


def config_list(arguments: dict[str, Any]) -> dict[str, Any]:
    del arguments
    ok, payload = run_ctxl(["config", "list", "--json"])
    return tool_result(payload, is_error=not ok)


def config_current(arguments: dict[str, Any]) -> dict[str, Any]:
    del arguments
    ok, payload = run_ctxl(["config", "current", "--json"])
    return tool_result(payload, is_error=not ok)


def config_get(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
    except ValueError as error:
        return error_tool_result(str(error))

    args = ["config", "get"]
    if config_id:
        args.append(config_id)
    args.append("--json")
    ok, payload = run_ctxl(args)
    return tool_result(payload, is_error=not ok)


def config_add(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = require_string(arguments, "configId")
        tenant_id = as_string(arguments, "tenantId")
    except ValueError as error:
        return error_tool_result(str(error))

    args = ["config", "add", config_id]
    append_optional_flag(args, "--tenant-id", tenant_id)
    ok, payload = run_ctxl(args, expect_json=False)
    return tool_result(payload, is_error=not ok)


def config_use(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = require_string(arguments, "configId")
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(["config", "use", config_id], expect_json=False)
    return tool_result(payload, is_error=not ok)


def config_delete(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = require_string(arguments, "configId")
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(["config", "delete", config_id], expect_json=False)
    return tool_result(payload, is_error=not ok)


def login_start(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = require_string(arguments, "configId")
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_login_script(["start", config_id])
    if ok and isinstance(payload, dict):
        payload["instruction"] = "Confirm the same verification code in the browser window and approve it there."
    return tool_result(payload, is_error=not ok)


def login_status(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        job_id = require_string(arguments, "jobId")
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_login_script(["status", job_id])
    return tool_result(payload, is_error=not ok)


def login_await(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        job_id = require_string(arguments, "jobId")
        timeout_seconds = as_integer(arguments, "timeoutSeconds") or 90
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_login_script(["await", job_id, "--timeout-seconds", str(timeout_seconds)])
    return tool_result(payload, is_error=not ok)


def types_add(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        input_text = as_input_text(arguments, required=True)
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(["types", "add", "--input-file", "-"], config_id=config_id, input_text=input_text)
    return tool_result(payload, is_error=not ok)


def types_list(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        args = ["types", "list"]
        apply_list_flags(args, arguments, include_search_filters=True)
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id)
    return tool_result(payload, is_error=not ok)


def types_get(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        args = ["types", "get"]
        apply_selector(args, arguments, require_uri_or_type=True, allow_multiple_ids=False)
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id)
    return tool_result(payload, is_error=not ok)


def types_replace(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        input_text = as_input_text(arguments, required=True)
        args = ["types", "replace"]
        apply_selector(args, arguments, require_uri_or_type=True, allow_multiple_ids=False)
        args.extend(["--input-file", "-"])
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id, input_text=input_text)
    return tool_result(payload, is_error=not ok)


def types_remove(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        args = ["types", "remove"]
        apply_selector(args, arguments, require_uri_or_type=True, allow_multiple_ids=False)
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id, expect_json=False)
    return tool_result(payload, is_error=not ok)


def records_add(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        input_text = as_input_text(arguments, required=True)
        args = ["records", "add"]
        apply_selector(args, arguments, require_uri_or_type=True)
        args.extend(["--input-file", "-"])
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id, input_text=input_text)
    return tool_result(payload, is_error=not ok)


def records_list(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        args = ["records", "list"]
        apply_selector(args, arguments, require_uri_or_type=True)
        apply_list_flags(args, arguments, include_search_filters=True)
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id)
    return tool_result(payload, is_error=not ok)


def records_get(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        args = ["records", "get"]
        apply_selector(args, arguments, require_uri_or_type=True)
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id)
    return tool_result(payload, is_error=not ok)


def records_query(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        input_text = as_input_text(arguments, required=True)
        args = ["records", "query"]
        apply_selector(args, arguments, require_uri_or_type=True)
        apply_list_flags(args, arguments, include_search_filters=False)
        args.extend(["--query-file", "-"])
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id, input_text=input_text)
    return tool_result(payload, is_error=not ok)


def records_patch(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        args = ["records", "patch"]
        apply_selector(args, arguments, require_uri_or_type=True, allow_multiple_ids=False)
        append_repeated_flag(args, "--set", as_string_list(arguments, "set"))
        append_repeated_flag(args, "--replace", as_string_list(arguments, "replace"))
        append_repeated_flag(args, "--remove", as_string_list(arguments, "remove"))
        append_repeated_flag(args, "--add", as_string_list(arguments, "add"))
        append_repeated_flag(args, "--increment", as_string_list(arguments, "increment"))
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id, expect_json=False)
    return tool_result(payload, is_error=not ok)


def records_replace(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        input_text = as_input_text(arguments, required=True)
        args = ["records", "replace"]
        apply_selector(args, arguments, require_uri_or_type=True, allow_multiple_ids=False)
        args.extend(["--input-file", "-"])
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id, input_text=input_text)
    return tool_result(payload, is_error=not ok)


def records_remove(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        args = ["records", "remove"]
        apply_selector(args, arguments, require_uri_or_type=True)
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id, expect_json=False)
    return tool_result(payload, is_error=not ok)


def records_stats(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        config_id = as_string(arguments, "configId")
        args = ["records", "stats"]
        apply_selector(args, arguments, require_uri_or_type=True, allow_multiple_ids=False)
    except ValueError as error:
        return error_tool_result(str(error))

    ok, payload = run_ctxl(args, config_id=config_id)
    return tool_result(payload, is_error=not ok)


TOOLS: list[dict[str, Any]] = [
    {
        "name": "setup_access",
        "description": "Install or verify local Contextual access and discover saved tenants.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "installMode": {"type": "string", "enum": ["auto", "npm", "local"]},
                "localRepo": {"type": "string"},
            },
        },
    },
    {"name": "config_list", "description": "List saved tenant configs.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "config_current", "description": "Show the current tenant config.", "inputSchema": {"type": "object", "properties": {}}},
    {
        "name": "config_get",
        "description": "Read one saved tenant config.",
        "inputSchema": {"type": "object", "properties": {"configId": {"type": "string"}}},
    },
    {
        "name": "config_add",
        "description": "Save a tenant config.",
        "inputSchema": {
            "type": "object",
            "properties": {"configId": {"type": "string"}, "tenantId": {"type": "string"}},
            "required": ["configId"],
        },
    },
    {
        "name": "config_use",
        "description": "Set the current tenant config.",
        "inputSchema": {
            "type": "object",
            "properties": {"configId": {"type": "string"}},
            "required": ["configId"],
        },
    },
    {
        "name": "config_delete",
        "description": "Delete a saved tenant config.",
        "inputSchema": {
            "type": "object",
            "properties": {"configId": {"type": "string"}},
            "required": ["configId"],
        },
    },
    {
        "name": "login_start",
        "description": "Start browser login for a tenant config.",
        "inputSchema": {
            "type": "object",
            "properties": {"configId": {"type": "string"}},
            "required": ["configId"],
        },
    },
    {
        "name": "login_status",
        "description": "Check a login job.",
        "inputSchema": {
            "type": "object",
            "properties": {"jobId": {"type": "string"}},
            "required": ["jobId"],
        },
    },
    {
        "name": "login_await",
        "description": "Wait for login to finish.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "jobId": {"type": "string"},
                "timeoutSeconds": {"type": "integer", "minimum": 1, "maximum": 110},
            },
            "required": ["jobId"],
        },
    },
    {
        "name": "types_add",
        "description": "Create one or more types.",
        "inputSchema": {
            "type": "object",
            "properties": {"configId": {"type": "string"}, "input": INPUT_SCHEMA},
            "required": ["input"],
        },
    },
    {
        "name": "types_list",
        "description": "List types.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "configId": {"type": "string"},
                "search": {"type": "array", "items": {"type": "string"}},
                "exactSearch": {"type": "array", "items": {"type": "string"}},
                "from": {"type": "array", "items": {"type": "string"}},
                "to": {"type": "array", "items": {"type": "string"}},
                "orderBy": {"type": "array", "items": {"type": "string"}},
                "pageSize": {"type": "integer", "minimum": 1, "maximum": 250},
                "pageToken": {"type": "string"},
                "includeTotal": {"type": "boolean"},
                "export": {"type": "boolean"},
                "progress": {"type": "boolean"},
            },
        },
    },
    {
        "name": "types_get",
        "description": "Read one type.",
        "inputSchema": {
            "type": "object",
            "properties": {"configId": {"type": "string"}, "uri": {"type": "string"}, "type": {"type": "string"}},
        },
    },
    {
        "name": "types_replace",
        "description": "Replace one type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "configId": {"type": "string"},
                "uri": {"type": "string"},
                "type": {"type": "string"},
                "input": INPUT_SCHEMA,
            },
            "required": ["input"],
        },
    },
    {
        "name": "types_remove",
        "description": "Delete one type.",
        "inputSchema": {
            "type": "object",
            "properties": {"configId": {"type": "string"}, "uri": {"type": "string"}, "type": {"type": "string"}},
        },
    },
    {
        "name": "records_add",
        "description": "Create one or more records.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "configId": {"type": "string"},
                "uri": {"type": "string"},
                "type": {"type": "string"},
                "input": INPUT_SCHEMA,
            },
            "required": ["input"],
        },
    },
    {
        "name": "records_list",
        "description": "List records.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "configId": {"type": "string"},
                "uri": {"type": "string"},
                "type": {"type": "string"},
                "search": {"type": "array", "items": {"type": "string"}},
                "exactSearch": {"type": "array", "items": {"type": "string"}},
                "from": {"type": "array", "items": {"type": "string"}},
                "to": {"type": "array", "items": {"type": "string"}},
                "orderBy": {"type": "array", "items": {"type": "string"}},
                "pageSize": {"type": "integer", "minimum": 1, "maximum": 250},
                "pageToken": {"type": "string"},
                "includeTotal": {"type": "boolean"},
                "export": {"type": "boolean"},
                "progress": {"type": "boolean"},
            },
        },
    },
    {
        "name": "records_get",
        "description": "Read one or more records.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "configId": {"type": "string"},
                "uri": {"type": "string"},
                "type": {"type": "string"},
                "id": ID_SCHEMA,
            },
        },
    },
    {
        "name": "records_query",
        "description": "Run a query against records.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "configId": {"type": "string"},
                "uri": {"type": "string"},
                "type": {"type": "string"},
                "input": INPUT_SCHEMA,
                "orderBy": {"type": "array", "items": {"type": "string"}},
                "pageSize": {"type": "integer", "minimum": 1, "maximum": 250},
                "pageToken": {"type": "string"},
                "includeTotal": {"type": "boolean"},
                "export": {"type": "boolean"},
                "progress": {"type": "boolean"},
            },
            "required": ["input"],
        },
    },
    {
        "name": "records_patch",
        "description": "Patch one record.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "configId": {"type": "string"},
                "uri": {"type": "string"},
                "type": {"type": "string"},
                "id": ID_SCHEMA,
                "set": {"type": "array", "items": {"type": "string"}},
                "replace": {"type": "array", "items": {"type": "string"}},
                "remove": {"type": "array", "items": {"type": "string"}},
                "add": {"type": "array", "items": {"type": "string"}},
                "increment": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "records_replace",
        "description": "Replace one record.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "configId": {"type": "string"},
                "uri": {"type": "string"},
                "type": {"type": "string"},
                "id": ID_SCHEMA,
                "input": INPUT_SCHEMA,
            },
            "required": ["input"],
        },
    },
    {
        "name": "records_remove",
        "description": "Delete one or more records.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "configId": {"type": "string"},
                "uri": {"type": "string"},
                "type": {"type": "string"},
                "id": ID_SCHEMA,
            },
        },
    },
    {
        "name": "records_stats",
        "description": "Read stats for one record.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "configId": {"type": "string"},
                "uri": {"type": "string"},
                "type": {"type": "string"},
                "id": ID_SCHEMA,
            },
        },
    },
]


TOOL_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "setup_access": setup_access,
    "config_list": config_list,
    "config_current": config_current,
    "config_get": config_get,
    "config_add": config_add,
    "config_use": config_use,
    "config_delete": config_delete,
    "login_start": login_start,
    "login_status": login_status,
    "login_await": login_await,
    "types_add": types_add,
    "types_list": types_list,
    "types_get": types_get,
    "types_replace": types_replace,
    "types_remove": types_remove,
    "records_add": records_add,
    "records_list": records_list,
    "records_get": records_get,
    "records_query": records_query,
    "records_patch": records_patch,
    "records_replace": records_replace,
    "records_remove": records_remove,
    "records_stats": records_stats,
}


def handle_tools_call(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(name, str) or not name:
        return error_tool_result("Tool call is missing a valid name")
    if not isinstance(arguments, dict):
        return error_tool_result("Tool arguments must be an object")

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return error_tool_result(f"Unknown tool: {name}")

    try:
        return handler(arguments)
    except Exception as error:  # noqa: BLE001
        stderr(f"[contextual-mcp] tool error for {name}: {error}")
        return error_tool_result(f"Tool '{name}' failed.", details=str(error))


def handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    message_id = message.get("id")
    params = message.get("params", {})

    if method == "initialize":
        return success_response(
            message_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "contextual", "version": "0.2.0"},
            },
        )

    if method == "notifications/initialized":
        return None

    if method == "ping":
        return success_response(message_id, {})

    if method == "tools/list":
        return success_response(message_id, {"tools": TOOLS})

    if method == "tools/call":
        if not isinstance(params, dict):
            return error_response(message_id, -32602, "Invalid params")
        return success_response(message_id, handle_tools_call(params))

    if message_id is None:
        return None

    return error_response(message_id, -32601, f"Method not found: {method}")


def main() -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            stderr(f"[contextual-mcp] invalid json: {line[:200]}")
            continue

        if not isinstance(message, dict):
            continue

        response = handle_message(message)
        if response is not None:
            write_message(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
