"""Backend registry for generate-music-local.

Add a new model here by dropping a module into this package that exposes
``NAME``, ``DESCRIPTION``, ``add_arguments(parser)`` and ``run(args) -> Path``,
then registering it in ``BACKENDS``.
"""
from __future__ import annotations

from . import minimax_mlx, yue2, yue2_mlx

BACKENDS: dict[str, object] = {
    "minimax-mlx": minimax_mlx,
    "yue2": yue2,
    "yue2-mlx": yue2_mlx,
}