#!/usr/bin/env python3
"""
Django project restart script — cross-platform (Python).

Reusable: copy into ANY Django project root and run:
    python restart_server.py          # default port 8000
    python restart_server.py --port 8000 --no-install --no-check

What it does:
  1. Activates the project virtualenv (.venv / venv)
  2. Installs/verifies requirements.txt (optional)
  3. Runs `python manage.py check` — blocks restart on failure
  4. Stops any existing runserver on the configured port
  5. Starts `python manage.py runserver` in a new console

Optional per-project config file: restart.env  (simple KEY=VALUE lines)
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


# --------------------------------------------------------------------------- #
# Defaults (overridable via --args or restart.env)
# --------------------------------------------------------------------------- #
DEFAULTS = {
    "MANAGE_PY": "manage.py",
    "VENV_DIR": "venv",
    "PROJECT_PORT": "8000",
    "BIND_ADDR": "0.0.0.0",
    "AUTO_INSTALL": "1",
    "RUN_CHECK": "1",
    "OPEN_BROWSER": "0",
}


def load_env_file(path: Path) -> dict[str, str]:
    """Load simple KEY=VALUE lines from restart.env (bash-ish, no exports)."""
    config: dict[str, str] = {}
    if not path.exists():
        return config
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        config[key.strip()] = value.strip().strip('"').strip("'")
    return config


def find_venv_activate(project_root: Path, venv_dir: str) -> Path | None:
    """Return the virtualenv activate script path for the current OS."""
    candidates = [
        project_root / venv_dir / ("Scripts" if os.name == "nt" else "bin") /
        ("activate.bat" if os.name == "nt" else "activate"),
        project_root / venv_dir / ("Scripts" if os.name == "nt" else "bin") /
        ("activate.ps1" if os.name == "nt" else "activate"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def python_exe(venv_dir: Path | None) -> str:
    """Return the python executable to use (venv python if available)."""
    if venv_dir is not None:
        if os.name == "nt":
            exe = venv_dir / "Scripts" / "python.exe"
        else:
            exe = venv_dir / "bin" / "python"
        if exe.exists():
            return str(exe)
    return sys.executable


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"[INFO] Running: {' '.join(cmd)}")
    return subprocess.run(cmd, **kwargs)


def stop_server_on_port(port: int) -> bool:
    """Kill whatever process is listening on `port`. Returns True if something was killed."""
    killed = False
    if os.name == "nt":
        # netstat -ano | findstr :<port>   (trailing space avoids matching :80000)
        try:
            out = subprocess.check_output(
                f'netstat -ano | findstr /C:":{port} "', shell=True, text=True, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            return False
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[-1]
                try:
                    subprocess.run(["taskkill", "/PID", pid, "/F"], check=False,
                                   capture_output=True)
                    print(f"[INFO]   Killed PID {pid} (listening on :{port})")
                    killed = True
                except Exception as exc:  # pragma: no cover - best effort
                    print(f"[WARN]   Could not kill PID {pid}: {exc}")
    else:
        # Unix: use fuser/lsof if available
        for finder in (["fuser", f"{port}/tcp"], ["lsof", "-ti", f":{port}"]):
            try:
                out = subprocess.check_output(finder, text=True, stderr=subprocess.DEVNULL)
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
            for pid in out.split():
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"[INFO]   Killed PID {pid} (listening on :{port})")
                    killed = True
                except (ProcessLookupError, PermissionError):
                    pass
            break
    return killed


def main() -> int:
    parser = argparse.ArgumentParser(description="Restart a Django development server.")
    parser.add_argument("--port", type=int, help=f"Port (default {DEFAULTS['PROJECT_PORT']})")
    parser.add_argument("--bind", default=DEFAULTS["BIND_ADDR"], help="Bind address")
    parser.add_argument("--manage-py", default=DEFAULTS["MANAGE_PY"], help="manage.py path")
    parser.add_argument("--venv-dir", default=DEFAULTS["VENV_DIR"], help="virtualenv dir")
    parser.add_argument("--no-install", action="store_true", help="Skip pip install")
    parser.add_argument("--no-check", action="store_true", help="Skip manage.py check")
    parser.add_argument("--open-browser", action="store_true", help="Open browser after start")
    args = parser.parse_args()

    # Resolve project root = directory containing this script
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)

    # Merge config: defaults < restart.env < CLI
    config = dict(DEFAULTS)
    config.update(load_env_file(project_root / "restart.env"))
    if args.port is not None:
        config["PROJECT_PORT"] = str(args.port)
    config["BIND_ADDR"] = args.bind
    config["MANAGE_PY"] = args.manage_py
    config["VENV_DIR"] = args.venv_dir
    config["AUTO_INSTALL"] = "0" if args.no_install else config["AUTO_INSTALL"]
    config["RUN_CHECK"] = "0" if args.no_check else config["RUN_CHECK"]
    config["OPEN_BROWSER"] = "1" if args.open_browser else config["OPEN_BROWSER"]

    port = int(config["PROJECT_PORT"])

    print("=" * 60)
    print(f"[INFO] Django Restart Script  ({time.strftime('%X')})")
    print(f"[INFO] Project root : {project_root}")
    print(f"[INFO] Manage.py    : {config['MANAGE_PY']}")
    print(f"[INFO] Bind         : {config['BIND_ADDR']}:{port}")
    print("=" * 60)

    # 1. manage.py must exist
    manage_py = project_root / config["MANAGE_PY"]
    if not manage_py.exists():
        print(f"[ERROR] {config['MANAGE_PY']} not found in {project_root}")
        print("        Place this script next to manage.py.")
        return 1

    # 2. Activate / locate virtualenv python
    venv_activate = find_venv_activate(project_root, config["VENV_DIR"])
    if venv_activate:
        print(f"[INFO] Virtualenv found: {config['VENV_DIR']}")
    else:
        print(f"[WARN]  Virtualenv '{config['VENV_DIR']}' not found; using system python")
    py = python_exe(venv_activate.parent.parent if venv_activate else None)

    # Show python version
    run([py, "--version"])

    # 3. Install / verify requirements
    req_file = project_root / "requirements.txt"
    if req_file.exists() and config["AUTO_INSTALL"] == "1":
        print("[INFO] Installing requirements from requirements.txt...")
        res = run([py, "-m", "pip", "install", "-r", str(req_file)])
        if res.returncode != 0:
            print("[ERROR] pip install failed.")
            return 1
        print("[OK]   Requirements installed.")

    if req_file.exists():
        print("[INFO] Verifying packages (pip check)...")
        res = run([py, "-m", "pip", "check"], capture_output=True, text=True)
        if res.returncode != 0:
            print("[WARN]  pip check reported dependency issues (non-fatal).")
        else:
            print("[OK]   pip check passed.")

    # 4. Django system check
    if config["RUN_CHECK"] == "1":
        print("[INFO] Running manage.py check...")
        res = run([py, str(manage_py), "check"])
        if res.returncode != 0:
            print("[ERROR] Django system check FAILED. Fix errors before restarting.")
            return 1
        print("[OK]   Django check passed.")

    # 5. Stop existing server
    print(f"[INFO] Stopping any existing server on port {port}...")
    killed = stop_server_on_port(port)
    if killed:
        print("[INFO] Waiting 2s for port to release...")
        time.sleep(2)
    else:
        print("[INFO]   No existing server found on that port.")

    # 6. Start server
    print(f"[INFO] Starting Django server on {config['BIND_ADDR']}:{port}...")
    if os.name == "nt":
        # New console window on Windows
        creationflags = subprocess.CREATE_NEW_CONSOLE
        subprocess.Popen(
            [py, str(manage_py), "runserver", f"{config['BIND_ADDR']}:{port}"],
            creationflags=creationflags,
            cwd=project_root,
        )
    else:
        subprocess.Popen(
            [py, str(manage_py), "runserver", f"{config['BIND_ADDR']}:{port}"],
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    if config["OPEN_BROWSER"] == "1":
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}/")

    print("[OK]   Restart complete.")
    print(f"[INFO] Visit: http://127.0.0.1:{port}/")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
