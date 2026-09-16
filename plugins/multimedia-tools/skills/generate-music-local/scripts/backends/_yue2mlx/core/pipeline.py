"""Torch-free base protocol for YuE2 pipelines (vendored from ``yue2/pipeline.py``).

Vendored from ``yue2_infer`` 0.1.5, which is built on PyTorch. The MLX runtime
inherits only the planning / semantic-protocol / persistence layer from this
module, so the torch-dependent members are removed rather than stubbed. The MLX
subclass overrides every one of them:

    removed: ``import torch``, ``__init__`` (device + CUDA setup),
             ``from_pretrained``, ``save_pretrained``, ``_load_model``,
             ``_generate``, ``synthesize``, ``decode``, ``close``, ``__call__``
    kept:    ``_request``, ``_status``, ``plan``, ``generate_semantic``,
             ``effective_config``

``plan``/``generate_semantic`` delegate to ``self._generate``, which the MLX
subclass replaces, so the kept methods never reach a torch code path. This is
what makes the vendored runtime genuinely torch-free; see ``VENDORED.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from contextlib import contextmanager
from pathlib import Path
import dataclasses
import json

import numpy as np

from .protocol import (
    CODEC_OFFSET,
    GenerationConfig,
    SongRequest,
    negative_prefix,
    resolve_sampling,
    token_prefixes,
)
from .progress import Progress
from .storage import collect_hashes, identity, model_identity, sha256_file, write_json


@dataclass
class SymbolicPlan:
    request: SongRequest
    abc: str | None
    abc_ids: list[int]
    prefix: list[int]
    timing: dict = field(default_factory=dict)
    truncated: bool = False

    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        if self.abc is not None:
            (directory / "score.abc").write_bytes(self.abc.encode("utf-8"))
        np.save(directory / "abc_tokens.npy", np.asarray(self.abc_ids, dtype=np.int32))
        np.save(directory / "prefix.npy", np.asarray(self.prefix, dtype=np.int32))
        write_json(directory / "plan.json", {"request": self.request.to_dict(), "timing": self.timing,
                                              "truncated": self.truncated, "prefix": self.prefix,
                                              "abc_ids": self.abc_ids, "abc": self.abc})

        names = ["plan.json", "abc_tokens.npy", "prefix.npy"] + (["score.abc"] if self.abc is not None else [])
        write_json(directory / "plan_manifest.json", {name: sha256_file(directory / name) for name in names})

    @classmethod
    def load(cls, directory):
        """Restore exact planner output without decoding and retokenizing its ABC."""
        directory = Path(directory)
        hashes = json.loads((directory / "plan_manifest.json").read_text())
        if not {"plan.json", "abc_tokens.npy", "prefix.npy"} <= hashes.keys():
            raise ValueError("Incomplete saved plan")
        for name, digest in hashes.items():
            if name not in {"plan.json", "abc_tokens.npy", "prefix.npy", "score.abc"} or (directory / name).is_symlink():
                raise ValueError("Invalid plan artifact")
            if sha256_file(directory / name) != digest:
                raise ValueError("Saved plan changed; supply modified ABC as an external planner input")
        data = json.loads((directory / "plan.json").read_text())
        for field_name, filename in (("abc_ids", "abc_tokens.npy"), ("prefix", "prefix.npy")):
            array = np.load(directory / filename, allow_pickle=False)
            if array.ndim != 1 or array.dtype.kind not in "iu" or array.tolist() != data[field_name]:
                raise ValueError("Saved plan token array mismatch")
        if data["abc"] is not None and ("score.abc" not in hashes or (directory / "score.abc").read_bytes() != data["abc"].encode("utf-8")):
            raise ValueError("Saved ABC text mismatch")
        return cls(SongRequest(**data["request"]), data["abc"], data["abc_ids"], data["prefix"],
                   data["timing"], data["truncated"])


@dataclass
class SemanticResult:
    plan: SymbolicPlan
    tokens: list[int]
    timing: dict
    truncated: bool


@dataclass
class SongResult:
    audio: np.ndarray
    sample_rate: int
    semantic: SemanticResult
    latents: np.ndarray
    config: dict
    weights: dict
    timing: dict
    request_identity: str

    @property
    def abc(self):
        return self.semantic.plan.abc

    @property
    def truncated(self):
        return {"abc": self.semantic.plan.truncated, "semantic": self.semantic.truncated}

    def save(self, path):
        """Write audio; use save_artifacts(directory) to retain a reproducible run."""
        import soundfile as sf
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() not in {".flac", ".wav"}:
            raise ValueError("Use .flac or .wav; MP3 is an optional delivery conversion")
        sf.write(path, self.audio, self.sample_rate, subtype="PCM_24" if path.suffix.lower() == ".flac" else "FLOAT")
        return str(path)

    def save_artifacts(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.semantic.plan.save(directory)
        self.save(directory / "audio.flac")
        np.save(directory / "semantic.npy", np.asarray(self.semantic.tokens, dtype=np.int32))
        np.save(directory / "latent.npy", self.latents.astype(np.float32))
        write_json(directory / "request.json", self.semantic.plan.request.to_dict())
        write_json(directory / "config.json", self.config)
        result = {"status": "complete", "identity": self.request_identity,
                  "truncated": self.truncated, "sample_rate": self.sample_rate,
                  "audio_seconds": len(self.audio) / self.sample_rate,
                  "weights": self.weights, "timing": self.timing,
                  "artifacts": collect_hashes(directory)}
        write_json(directory / "result.json", result)
        return result


class YuE2Pipeline:
    """Planning + semantic protocol shared by every backend.

    Only the torch-free members survive here; the MLX runtime supplies
    ``__init__``, ``_load_model``, ``_generate``, ``synthesize``, ``decode`` and
    ``__call__``. Everything below either uses no tensor library or delegates to
    ``self._generate``.
    """

    @contextmanager
    def _status(self, label, *, total=None, unit=None):
        # Display state never enters the request/config identity or model RNG.
        with Progress(enabled=self.progress) as reporter:
            with reporter.stage(label, total=total, unit=unit) as stage:
                yield stage

    def _request(self, style=None, lyrics=None, *, tags=None, **kwargs):
        if style is not None and tags is not None and style != tags:
            raise ValueError("style and tags are aliases and cannot disagree")
        style = tags if style is None else style
        if style is None or lyrics is None:
            raise ValueError("Provide style and lyrics")
        return SongRequest(style=style, lyrics=lyrics, **kwargs)

    def plan(self, style=None, lyrics=None, *, tags=None, request=None, abc_sampling=None,
             cancelled=None, on_token=None, **kwargs):
        request = request or self._request(style, lyrics, tags=tags, **kwargs)
        if request.cot == "off":
            return SymbolicPlan(request, None, [], token_prefixes(request, self.tokenizer))
        if request.abc is not None:
            with self._status("Using provided score"):
                ids = self.tokenizer.encode(request.abc)
                return SymbolicPlan(request, request.abc, ids, token_prefixes(request, self.tokenizer, ids),
                                    {"seconds": 0., "output_tokens": 0, "external_prefix_tokens": len(ids)})
        sampling = resolve_sampling(abc_sampling, self.generation_config.abc)
        ids, timing, truncated = self._generate(token_prefixes(request, self.tokenizer), sampling,
                            request.seed, "abc", cancelled=cancelled, on_token=on_token)
        return SymbolicPlan(request, self.tokenizer.decode(ids), ids,
                            token_prefixes(request, self.tokenizer, ids), timing, truncated)

    def generate_semantic(self, plan, *, sampling=None, cancelled=None, on_token=None):
        if not isinstance(plan, SymbolicPlan):
            raise TypeError("Pass the SymbolicPlan returned by pipe.plan()")
        request = plan.request
        expected = token_prefixes(request, self.tokenizer, plan.abc_ids)
        if expected != plan.prefix:
            raise ValueError("Plan prefix disagrees with request/exact ABC IDs")
        sampling = resolve_sampling(sampling, self.generation_config.semantic)
        negative = negative_prefix(request, self.tokenizer, plan.abc_ids) if request.guidance != 1 else None
        ids, timing, truncated = self._generate(plan.prefix, sampling, request.seed, "semantic",
                        negative=negative, cfg_scale=request.guidance, legacy_off=request.cot == "off",
                        cancelled=cancelled, on_token=on_token)
        return SemanticResult(plan, [int(t) - CODEC_OFFSET for t in ids], timing, truncated)

    def effective_config(self, request, abc_sampling=None, semantic_sampling=None):
        config = self.generation_config.to_dict()
        for key, sampling in (("abc", abc_sampling), ("semantic", semantic_sampling)):
            if sampling is not None:
                config[key] = dataclasses.asdict(resolve_sampling(sampling, getattr(self.generation_config, key)))
        defaults = GenerationConfig().to_dict()
        overrides = {k: v for k, v in config.items() if defaults.get(k) != v}
        if request.guidance != (1.01 if request.cot == "off" else 1.0):
            overrides["cfg_scale"] = request.guidance
        return {"generation": config, "overrides": overrides,
                "cot": request.cot, "cfg_scale": request.guidance,
                "cfg_negative": "instruction_only" if request.cot == "off" else "same_instruction_and_exact_abc",
                "backend": self.backend, "quantization": self.quantization,
                "model_dtype": "bfloat16", "vae_dtype": "float32", "vae_decode": "halo_crop",
                "vae_core_frames": self.vae_core_frames, "vae_halo_frames": 16,
                "device": str(self.device), "memory_budget_gib": self.memory_budget_gib,
                "offload_ar": self.offload_ar, "runtime_sha256": self.runtime_sha256,
                "decoder_release": json.loads((self.vae_dir / "config.json").read_text()).get("release_variant"),
                "validation_status": "unvalidated"}


# Kept for the package surface (`_yue2mlx.core.pipeline.YuE2Pipeline`); the MLX
# runtime subclasses it. `model_identity`/`identity` are re-exported because
# callers of the reference module imported them from here.
__all__ = ["SongResult", "SemanticResult", "SymbolicPlan", "YuE2Pipeline",
           "identity", "model_identity"]
