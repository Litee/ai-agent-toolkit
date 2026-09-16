"""Vendored MLX runtime for YuE2-3B (GGUF weights) — self-contained, torch-free.

This package is a *vendored, pre-patched* copy of the MLX inference runtime, so
installing the backend needs no clone, no network fetch of the upstream repo and
no patch step on the user's machine. Provenance, upstream revision and the exact
list of local changes are recorded in ``VENDORED.md`` next to this file.

Layout:
    ``core``     torch-free planning/protocol/storage/tokenization layer
    ``runtime``  MLX inference: AR, NAR flow-matching, Oobleck VAE, sampling,
                 model-artifact validation and the memory guard
    ``gguf.py``  converts the audio.cpp GGUF weight set into runtime artifacts

Imports are deliberately lazy: ``core`` is torch-free and cheap, while
``runtime`` requires MLX and must only load inside the backend's own venv.
"""
from __future__ import annotations

__all__ = ["core", "runtime"]
