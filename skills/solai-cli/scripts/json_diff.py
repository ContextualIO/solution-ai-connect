#!/usr/bin/env python3

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path
from typing import Any


def load_value(path: str) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def render(value: Any) -> list[str]:
    if isinstance(value, str):
        return value.splitlines(keepends=True)
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").splitlines(keepends=True)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: json_diff.py <current-file> <proposed-file>", file=sys.stderr)
        return 1

    current_path, proposed_path = sys.argv[1], sys.argv[2]
    current = load_value(current_path)
    proposed = load_value(proposed_path)
    diff = difflib.unified_diff(
        render(current),
        render(proposed),
        fromfile=current_path,
        tofile=proposed_path,
    )
    sys.stdout.writelines(diff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
