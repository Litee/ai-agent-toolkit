"""Shared helpers used by generate-music backends (stdlib only)."""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path


def resolve_python311() -> str:
    for candidate in ("python3.11", "python3.12", "python3.13", "python3"):
        exe = shutil.which(candidate)
        if exe:
            return exe
    raise SystemExit("Python 3.11+ not found on PATH.")


def resolve_hf() -> str:
    for candidate in ("hf", "huggingface-cli"):
        if shutil.which(candidate):
            return candidate
    raise SystemExit(
        "Hugging Face CLI not found. Install it (`pip install -U 'huggingface_hub[cli]'` "
        "or `brew install huggingface-cli`) and re-run with --setup."
    )


def available_ram_gb() -> float:
    """Approximate available RAM in GB (free + inactive + speculative) on macOS.

    Returns ``inf`` if it can't be measured so the memory guard never blocks a
    run it cannot evaluate.
    """
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return float("inf")
    page = 4096
    m = re.search(r"page size of (\d+) bytes", out)
    if m:
        page = int(m.group(1))

    def _pages(label: str) -> int:
        mm = re.search(rf"{label}:\s+(\d+)\.", out)
        return int(mm.group(1)) if mm else 0

    free, inactive, speculative = _pages("Pages free"), _pages("Pages inactive"), _pages("Pages speculative")
    return (free + inactive + speculative) * page / (1024 ** 3)


def ensure_memory(required_gb: float, wait_seconds: int) -> None:
    """Abort (or wait) if there isn't enough free RAM to load the model safely.

    ``required_gb`` is backend-specific (e.g. 48 for MiniMax-Music3's ~56 GB
    peak, 8 for YuE2's smaller footprint).
    """
    avail = available_ram_gb()
    if avail >= required_gb:
        return
    if wait_seconds and wait_seconds > 0:
        deadline = time.time() + wait_seconds
        print(f"[mem] only {avail:.1f} GB free (< {required_gb:.0f} GB); "
              f"waiting up to {wait_seconds}s (re-check every 10s)…", flush=True)
        while time.time() < deadline:
            time.sleep(10)
            avail = available_ram_gb()
            if avail >= required_gb:
                print(f"[mem] {avail:.1f} GB free — proceeding.", flush=True)
                return
        raise SystemExit(
            f"Timed out after {wait_seconds}s: only {avail:.1f} GB free RAM "
            f"(< {required_gb:.0f} GB required). Aborting to avoid OOM."
        )
    raise SystemExit(
        f"Only {avail:.1f} GB RAM free (< {required_gb:.0f} GB required to load "
        f"the model safely). Free memory or pass --wait-for-memory <seconds> to wait."
    )


def ensure_venv_check(venv: Path, do_setup: bool, label: str, hint: str) -> Path:
    py = venv / "bin" / "python"
    if py.exists() and (venv / "bin" / "pip").exists():
        return venv
    if not do_setup:
        raise SystemExit(
            f"{label} venv not set up at {venv}. Re-run with --setup to create it "
            f"and install its dependencies. {hint}"
        )
    venv.parent.mkdir(parents=True, exist_ok=True)
    print(f"[setup] creating venv with {resolve_python311()} at {venv} ...", flush=True)
    subprocess.run([resolve_python311(), "-m", "venv", str(venv)], check=True)
    pip = venv / "bin" / "pip"
    subprocess.run([str(pip), "install", "-U", "pip"], check=True)
    return venv