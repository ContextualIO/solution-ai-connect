#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STATE_DIR = ROOT / ".local" / "login-jobs"
USER_CODE_RE = re.compile(r"verification code:\s*(.+)$", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_ctxl() -> None:
    if shutil.which("ctxl") is None:
        raise RuntimeError("ctxl is not installed or not on PATH.")


def ensure_state_dir(state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)


def run_command(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, capture_output=True, text=True)


def current_config_id() -> str | None:
    try:
        result = run_command(["ctxl", "config", "current", "--json"])
    except subprocess.CalledProcessError:
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    value = payload.get("configId")
    return value if isinstance(value, str) and value else None


def switch_config(config_id: str) -> None:
    run_command(["ctxl", "config", "use", config_id])


def state_path(state_dir: Path, job_id: str) -> Path:
    return state_dir / f"{job_id}.json"


def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path: Path, payload: dict) -> None:
    payload["updatedAt"] = now_iso()
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_line(payload: dict, line: str) -> None:
    lines = [item for item in payload.get("lines", []) if isinstance(item, str)]
    text = line.strip()
    if not text:
        return
    if not lines or lines[-1] != text:
        lines.append(text)
    payload["lines"] = lines[-20:]
    match = USER_CODE_RE.search(text)
    if match:
        payload["userCode"] = match.group(1).strip()


def process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def refresh_pending_state(payload: dict) -> dict:
    if payload.get("status") != "pending":
        return payload

    worker_pid = payload.get("workerPid")
    if isinstance(worker_pid, int) and not process_alive(worker_pid):
        payload["status"] = "error"
        payload.setdefault("errorText", "Login worker exited before reporting completion.")
    return payload


def print_state(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


def command_start(state_dir: Path, config_id: str) -> int:
    ensure_ctxl()
    ensure_state_dir(state_dir)

    previous_config_id = current_config_id()
    switch_config(config_id)

    job_id = uuid.uuid4().hex
    path = state_path(state_dir, job_id)
    log_path = state_dir / f"{job_id}.log"
    payload = {
        "jobId": job_id,
        "configId": config_id,
        "previousConfigId": previous_config_id,
        "status": "pending",
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
        "userCode": None,
        "errorText": None,
        "exitCode": None,
        "lines": [f"Switched to '{config_id}'. Starting browser login..."],
        "logPath": str(log_path),
    }
    write_state(path, payload)

    worker = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "_worker", str(path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    payload["workerPid"] = worker.pid
    write_state(path, payload)

    deadline = time.time() + 3.0
    while time.time() < deadline:
        current = load_state(path)
        if current.get("userCode") or current.get("lines"):
            break
        time.sleep(0.2)

    print_state(load_state(path))
    return 0


def command_status(state_dir: Path, job_id: str) -> int:
    path = state_path(state_dir, job_id)
    if not path.exists():
        raise RuntimeError(f"Unknown job id: {job_id}")

    payload = refresh_pending_state(load_state(path))
    write_state(path, payload)
    print_state(payload)
    return 0


def command_await(state_dir: Path, job_id: str, timeout_seconds: int) -> int:
    path = state_path(state_dir, job_id)
    if not path.exists():
        raise RuntimeError(f"Unknown job id: {job_id}")

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        payload = refresh_pending_state(load_state(path))
        write_state(path, payload)
        if payload.get("status") != "pending":
            payload["timedOut"] = False
            print_state(payload)
            return 0
        time.sleep(1)

    payload = refresh_pending_state(load_state(path))
    write_state(path, payload)
    payload["timedOut"] = payload.get("status") == "pending"
    print_state(payload)
    return 0


def command_worker(path_value: str) -> int:
    path = Path(path_value)
    payload = load_state(path)
    log_path = Path(payload["logPath"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        process = subprocess.Popen(
            ["ctxl", "config", "login"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        payload["loginPid"] = process.pid
        write_state(path, payload)

        with log_path.open("a", encoding="utf-8") as handle:
            assert process.stdout is not None
            for raw_line in process.stdout:
                handle.write(raw_line)
                handle.flush()
                append_line(payload, raw_line)
                write_state(path, payload)

        exit_code = process.wait()
        payload["exitCode"] = exit_code
        if exit_code == 0:
            payload["status"] = "completed"
            append_line(payload, f"Login completed for '{payload['configId']}'.")
        else:
            payload["status"] = "error"
            payload["errorText"] = f"Login exited with code {exit_code}."

    except Exception as error:  # noqa: BLE001
        payload["status"] = "error"
        payload["errorText"] = str(error)
        append_line(payload, f"Login error: {error}")

    previous = payload.get("previousConfigId")
    current = payload.get("configId")
    if isinstance(previous, str) and previous and previous != current:
        try:
            switch_config(previous)
            append_line(payload, f"Restored previous config '{previous}'.")
        except Exception as error:  # noqa: BLE001
            append_line(payload, f"Failed to restore previous config '{previous}': {error}")

    write_state(path, payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage login jobs for the local Contextual CLI.")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("config_id")

    status = subparsers.add_parser("status")
    status.add_argument("job_id")

    await_parser = subparsers.add_parser("await")
    await_parser.add_argument("job_id")
    await_parser.add_argument("--timeout-seconds", type=int, default=90)

    worker = subparsers.add_parser("_worker")
    worker.add_argument("state_path")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    state_dir = Path(args.state_dir)

    if args.command == "start":
        return command_start(state_dir, args.config_id)
    if args.command == "status":
        return command_status(state_dir, args.job_id)
    if args.command == "await":
        return command_await(state_dir, args.job_id, args.timeout_seconds)
    if args.command == "_worker":
        return command_worker(args.state_path)
    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        raise SystemExit(1)
