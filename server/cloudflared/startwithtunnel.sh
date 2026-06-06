#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-$SCRIPT_DIR/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: env file not found: $ENV_FILE" >&2
  echo "Copy $SCRIPT_DIR/.env.example to $ENV_FILE and set CLOUDFLARED_TOKEN." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${CLOUDFLARED_TOKEN:-}" ]]; then
  echo "Error: CLOUDFLARED_TOKEN is not set in $ENV_FILE." >&2
  exit 1
fi

CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-cloudflared}"
CLOUDFLARED_AUTO_INSTALL="${CLOUDFLARED_AUTO_INSTALL:-0}"
CLOUDFLARED_EXTRA_ARGS="${CLOUDFLARED_EXTRA_ARGS:-}"

install_cloudflared() {
  local platform arch download_url install_dir install_path

  install_dir="$SCRIPT_DIR/.bin"
  mkdir -p "$install_dir"

  case "$(uname -s | tr '[:upper:]' '[:lower:]')" in
    linux*) platform="linux" ;;
    darwin*) platform="darwin" ;;
    mingw*|msys*|cygwin*|windows*) platform="windows" ;;
    *)
      echo "Error: auto-install is not supported on this operating system." >&2
      return 1
      ;;
  esac

  case "$(uname -m)" in
    x86_64|amd64) arch="amd64" ;;
    aarch64|arm64) arch="arm64" ;;
    i386|i686) arch="386" ;;
    *)
      echo "Error: auto-install is not supported on this CPU architecture." >&2
      return 1
      ;;
  esac

  case "$platform" in
    linux|darwin)
      download_url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-${platform}-${arch}"
      install_path="$install_dir/cloudflared"
      ;;
    windows)
      download_url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-${arch}.exe"
      install_path="$install_dir/cloudflared.exe"
      ;;
  esac

  echo "cloudflared binary not found. CLOUDFLARED_AUTO_INSTALL=1 is set, so downloading a local copy..." >&2
  echo "Downloading from: $download_url" >&2

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$download_url" -o "$install_path"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$install_path" "$download_url"
  else
    echo "Error: neither curl nor wget is available to auto-install cloudflared." >&2
    return 1
  fi

  chmod +x "$install_path"
  CLOUDFLARED_BIN="$install_path"
  echo "cloudflared installed to: $CLOUDFLARED_BIN" >&2
}

if ! command -v "$CLOUDFLARED_BIN" >/dev/null 2>&1; then
  if [[ "$CLOUDFLARED_AUTO_INSTALL" == "1" ]]; then
    install_cloudflared || exit 1
  else
    echo "Error: cloudflared binary not found: $CLOUDFLARED_BIN" >&2
    echo "Set CLOUDFLARED_AUTO_INSTALL=1 to download a local copy, or install cloudflared manually." >&2
    exit 1
  fi
fi

extra_args=()
if [[ -n "$CLOUDFLARED_EXTRA_ARGS" ]]; then
  read -r -a extra_args <<< "$CLOUDFLARED_EXTRA_ARGS"
fi

echo "Starting Cloudflare Tunnel from: $SCRIPT_DIR"
echo "Using env file: $ENV_FILE"
echo "Using cloudflared binary: $CLOUDFLARED_BIN"
echo "Running: cloudflared tunnel run --token <redacted>${CLOUDFLARED_EXTRA_ARGS:+ $CLOUDFLARED_EXTRA_ARGS}"

exec "$CLOUDFLARED_BIN" tunnel run --token "$CLOUDFLARED_TOKEN" "${extra_args[@]}"
