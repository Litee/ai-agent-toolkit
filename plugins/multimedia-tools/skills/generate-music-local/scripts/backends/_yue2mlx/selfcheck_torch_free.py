#!/usr/bin/env python3
"""Prove the vendored runtime is torch-free.

The meaningful proof is environmental, not synthetic: the backend venv must not
contain torch at all, and no vendored module may pull it into ``sys.modules``.
That is exactly how the backend ships, so this script asserts it directly.

(An earlier revision raised from ``find_spec`` to trap torch. That was wrong:
``transformers`` *probes* for torch via ``importlib.util.find_spec`` to decide
whether an optional backend is available, and a torch-free environment answers
"not found" rather than raising. Blocking the probe produced a false failure.)

Run with the backend venv:
    <venv>/bin/python scripts/backends/_yue2mlx/selfcheck_torch_free.py
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]   # .../generate-music-local/scripts
sys.path.insert(0, str(SCRIPTS))

MODULES = [
    "backends._yue2mlx",
    "backends._yue2mlx.core",
    "backends._yue2mlx.core.protocol",
    "backends._yue2mlx.core.storage",
    "backends._yue2mlx.core.progress",
    "backends._yue2mlx.core.tokenization_yue2",
    "backends._yue2mlx.core.ar_keys",
    "backends._yue2mlx.core.pipeline",
    "backends._yue2mlx.runtime",
    "backends._yue2mlx.runtime.sampling",
    "backends._yue2mlx.runtime.vae",
    "backends._yue2mlx.runtime.ar",
    "backends._yue2mlx.runtime.nar",
    "backends._yue2mlx.runtime.measure",
    "backends._yue2mlx.runtime.runtime",
    "backends._yue2mlx.runtime.conversion",
    "backends._yue2mlx.runtime.artifacts",
    "backends._yue2mlx.runtime.checkpoints",
    "backends._yue2mlx.runtime.pipeline",
]

# 1. The environment itself must be torch-free.
if importlib.util.find_spec("torch") is not None:
    print("FAIL: this environment has torch installed.")
    print("      The vendored runtime is meant to run in a torch-free venv, so this")
    print("      test cannot prove anything here. Re-run with the backend venv.")
    sys.exit(2)
print("  env   : torch is not installed (find_spec -> None)")

# 2. Nothing may import torch while we exercise the vendored surface.
failures = []
for name in MODULES:
    try:
        importlib.import_module(name)
        print(f"  ok    {name}")
    except BaseException as exc:  # noqa: BLE001 - report everything
        failures.append((name, exc))
        print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")

print()
if failures:
    print(f"RESULT: FAIL — {len(failures)} module(s) failed to import")
    for name, exc in failures:
        print(f"  {name}: {exc}")
    sys.exit(1)
if "torch" in sys.modules:
    print("RESULT: FAIL — torch reached sys.modules")
    sys.exit(1)

from backends._yue2mlx.core.ar_keys import ar_keys  # noqa: E402
from backends._yue2mlx.core.pipeline import YuE2Pipeline as Base  # noqa: E402
from backends._yue2mlx.runtime.pipeline import YuE2Pipeline  # noqa: E402

print(f"RESULT: PASS — {len(MODULES)} modules imported, torch absent throughout")
print(f"  torch in sys.modules        : {'torch' in sys.modules}")
print(f"  MLX pipeline subclasses base: {issubclass(YuE2Pipeline, Base)}")
print(f"  ar_keys() -> {len(ar_keys({'num_hidden_layers': 28}))} AR tensors")
