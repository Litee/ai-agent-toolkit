"""Torch-free core vendored from the ``yue2-infer`` wheel.

These modules are the planning / protocol / storage / tokenization layer that
the MLX runtime inherits. They are the *only* part of ``yue2`` the runtime
needs, and they are all importable without torch. See ``VENDORED.md``.
"""
