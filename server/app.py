#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, Optional

SERVER_DIR = Path(__file__).resolve().parent
ROOT_DIR = SERVER_DIR.parent
BACKEND_APP_DIR = SERVER_DIR / "app"
CLOUDFLARED_DIR = SERVER_DIR / "cloudflared"
BACKEND_ENV_FILE = SERVER_DIR / ".env"
CLOUDFLARED_ENV_FILE = CLOUDFLARED_DIR / ".env"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
BACKEND_HEALTH_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}/health"
BACKEND_HEALTH_TIMEOUT_SECONDS = int(os.getenv("APP_BACKEND_HEALTH_TIMEOUT_SECONDS", "45"))
BACKEND_HEALTH_INTERVAL_SECONDS = float(os.getenv("APP_BACKEND_HEALTH_INTERVAL_SECONDS", "1.0"))


def load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        values[key] = value

    return values


def merge_env(env: Dict[str, str], values: Dict[str, str]) -> None:
    for key, value in values.items():
        env.setdefault(key, value)


def build_pythonpath(env: Dict[str, str]) -> None:
    entries = [str(SERVER_DIR)]
    major_minor = f"python{sys.version_info.major}.{sys.version_info.minor}"

    local_libs = [
        ROOT_DIR / ".local" / "lib" / major_minor / "site-packages",
        SERVER_DIR / ".local" / "lib" / major_minor / "site-packages",
        SERVER_DIR / ".venv" / "Lib" / "site-packages",
        SERVER_DIR / ".venv" / "lib" / major_minor / "site-packages",
    ]

    for candidate in local_libs:
        if candidate.exists():
            entries.append(str(candidate))

    existing = env.get("PYTHONPATH")
    if existing:
        entries.append(existing)

    env["PYTHONPATH"] = os.pathsep.join(list(dict.fromkeys(entries)))


def build_path(env: Dict[str, str]) -> None:
    entries = [
        str(ROOT_DIR / ".local" / "bin"),
        str(SERVER_DIR / ".local" / "bin"),
        env.get("PATH", ""),
    ]
    env["PATH"] = os.pathsep.join([entry for entry in entries if entry])


def resolve_python() -> str:
    candidates = [
        SERVER_DIR / ".venv" / "bin" / "python",
        SERVER_DIR / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return sys.executable


def run_command(command: Iterable[str], *, cwd: Path, env: Dict[str, str], label: str) -> subprocess.Popen:
    print(f"[startup] launching {label}: {' '.join(command)}", flush=True)
    return subprocess.Popen(list(command), cwd=str(cwd), env=env)


def wait_for_backend_health(process: subprocess.Popen) -> None:
    deadline = time.time() + BACKEND_HEALTH_TIMEOUT_SECONDS
    last_error: Optional[str] = None

    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"backend exited early with code {process.returncode}")

        try:
            with urllib.request.urlopen(BACKEND_HEALTH_URL, timeout=2) as response:
                if 200 <= getattr(response, "status", 200) < 300:
                    print(f"[startup] backend is healthy at {BACKEND_HEALTH_URL}", flush=True)
                    return
        except urllib.error.URLError as exc:
            last_error = str(exc)
        except Exception as exc:  # pragma: no cover - defensive
            last_error = str(exc)

        time.sleep(BACKEND_HEALTH_INTERVAL_SECONDS)

    raise RuntimeError(
        f"backend did not become healthy at {BACKEND_HEALTH_URL} within {BACKEND_HEALTH_TIMEOUT_SECONDS}s"
        + (f" (last error: {last_error})" if last_error else "")
    )


def terminate_process(process: Optional[subprocess.Popen], label: str) -> None:
    if process is None or process.poll() is not None:
        return

    print(f"[startup] stopping {label}...", flush=True)
    process.terminate()

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        print(f"[startup] forcing {label} shutdown...", flush=True)
        process.kill()
        process.wait(timeout=10)


def main() -> int:
    cloudflared_env = load_env_file(CLOUDFLARED_ENV_FILE)
    tunnel_token = os.environ.get("CLOUDFLARED_TOKEN") or cloudflared_env.get("CLOUDFLARED_TOKEN")

    if not tunnel_token:
        print(
            f"Error: CLOUDFLARED_TOKEN is missing. Create {CLOUDFLARED_ENV_FILE} from .env.example first.",
            file=sys.stderr,
        )
        return 1

    backend_env = os.environ.copy()
    merge_env(backend_env, load_env_file(BACKEND_ENV_FILE))
    build_pythonpath(backend_env)
    build_path(backend_env)

    backend_python = resolve_python()
    backend_command = [
        backend_python,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        BACKEND_HOST,
        "--port",
        str(BACKEND_PORT),
    ]

    backend_process: Optional[subprocess.Popen] = None
    tunnel_process: Optional[subprocess.Popen] = None

    def shutdown(*_: object) -> None:
        terminate_process(tunnel_process, "cloudflared tunnel")
        terminate_process(backend_process, "backend server")

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        backend_process = run_command(backend_command, cwd=BACKEND_APP_DIR, env=backend_env, label="backend")
        wait_for_backend_health(backend_process)

        tunnel_command = [
            "/usr/bin/env",
            "bash",
            str(CLOUDFLARED_DIR / "startwithtunnel.sh"),
        ]
        tunnel_env = os.environ.copy()
        merge_env(tunnel_env, cloudflared_env)
        build_path(tunnel_env)

        tunnel_process = run_command(tunnel_command, cwd=CLOUDFLARED_DIR, env=tunnel_env, label="cloudflared tunnel")

        while True:
            backend_code = backend_process.poll() if backend_process else None
            tunnel_code = tunnel_process.poll() if tunnel_process else None

            if backend_code is not None:
                print(f"[startup] backend exited with code {backend_code}", flush=True)
                terminate_process(tunnel_process, "cloudflared tunnel")
                return backend_code or 1

            if tunnel_code is not None:
                print(f"[startup] cloudflared tunnel exited with code {tunnel_code}", flush=True)
                terminate_process(backend_process, "backend server")
                return tunnel_code or 1

            time.sleep(1)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        terminate_process(tunnel_process, "cloudflared tunnel")
        terminate_process(backend_process, "backend server")


if __name__ == "__main__":
    raise SystemExit(main())
