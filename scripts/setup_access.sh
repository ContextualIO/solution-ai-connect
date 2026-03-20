#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
DEFAULT_LOCAL_REPO=""

if [ -d "$PLUGIN_ROOT/../contextual-cli" ]; then
  DEFAULT_LOCAL_REPO="$(cd -- "$PLUGIN_ROOT/../contextual-cli" && pwd)"
fi

INSTALL_MODE="${CONTEXTUAL_CLI_INSTALL_MODE:-npm}"
LOCAL_REPO="${CONTEXTUAL_CLI_REPO:-$DEFAULT_LOCAL_REPO}"

if command -v ctxl >/dev/null 2>&1; then
  echo "[ok] Contextual access is already available: $(command -v ctxl)"
  ctxl --version
  exit 0
fi

if ! command -v node >/dev/null 2>&1; then
  echo "[error] Contextual access setup requires Node.js." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[error] Contextual access setup requires npm." >&2
  exit 1
fi

case "$INSTALL_MODE" in
  auto)
    if [ -n "$LOCAL_REPO" ] && [ -d "$LOCAL_REPO" ]; then
      INSTALL_MODE="local"
    else
      INSTALL_MODE="npm"
    fi
    ;;
  npm|local)
    ;;
  *)
    echo "[error] Unsupported install mode: $INSTALL_MODE" >&2
    exit 1
    ;;
esac

if [ "$INSTALL_MODE" = "local" ]; then
  if [ -z "$LOCAL_REPO" ] || [ ! -d "$LOCAL_REPO" ]; then
    echo "[error] Local install source not found. Set CONTEXTUAL_CLI_REPO to a valid local Contextual checkout." >&2
    exit 1
  fi

  echo "[info] Setting up Contextual access from local source: $LOCAL_REPO"
  (
    cd "$LOCAL_REPO"
    npm install
    npm run build
    npm link
  )
else
  echo "[info] Installing Contextual access from npm"
  npm install -g @contextual-io/cli
fi

if ! command -v ctxl >/dev/null 2>&1; then
  echo "[error] Contextual access was not found after installation." >&2
  exit 1
fi

echo "[ok] Contextual access is ready: $(command -v ctxl)"
ctxl --version
