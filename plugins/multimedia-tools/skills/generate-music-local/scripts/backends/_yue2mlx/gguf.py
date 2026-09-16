#!/usr/bin/env python3
"""Convert the audio.cpp GGUF weight set into artifacts the vendored runtime loads.

Consumes, unchanged:

    yue2-3b-q8_0.gguf   main model, Q8_0 + BF16/F16
    yue2-vae-f16.gguf   Oobleck VAE, F16

and emits the artifact set the runtime expects (``ar-bf16``/``nar-bf16``/
``ar-8bit`` + ``conversion.json``, plus a VAE directory), then validates the
result with the runtime's own strict manifest + hash + shape checker.

Why this is not a re-quantisation
---------------------------------
ggml Q8_0 stores 32-element groups of int8 with one fp16 scale (``w = scale*q``).
MLX's GGUF reader unpacks that straight into MLX's affine 8-bit layout --
uint32-packed quants plus fp16 ``scales``/``biases`` -- where ``scales`` is the
ggml fp16 scale bit-for-bit and ``biases = -128*scale``, which is algebraically
exact (MLX stores quants offset by +128). So Q8_0 weights are copied through *as
quantized data*: no dequantisation and no second, lossy quantisation. Only the
container precision of scales/biases changes (fp16 -> bf16, which the runtime's
loader requires), measured at ~3e-4 absolute against a Q8_0 error of ~1.8e-3.

It also runs without argparse so the backend can call ``convert()`` directly;
``python -m ...gguf`` gives the same thing on the command line.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import mlx.core as mx

MW = "model_weights/"
VW = "vae_weights/"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _record(path: Path) -> dict:
    return {"bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _bf16(x):
    return mx.array(x).astype(mx.bfloat16)


def _is_quantized(tensors, name) -> bool:
    value = tensors.get(MW + name)
    return value is not None and value.dtype == mx.uint32


def _companions(tensors, name):
    stem = name[: -len("weight")]
    return tensors.get(MW + stem + "scales"), tensors.get(MW + stem + "biases")


def _dequant(tensors, name, group_size: int, bits: int = 8):
    scales, biases = _companions(tensors, name)
    if scales is None or biases is None:
        raise KeyError(f"missing scales/biases for {name}")
    dense = mx.dequantize(tensors[MW + name], scales.astype(mx.float32),
                          biases.astype(mx.float32), group_size=group_size, bits=bits)
    return dense.astype(mx.bfloat16)


def vae_decoder_tensors(gguf_vae):
    """Map GGUF ``vae_weights/decoder.*`` onto MLX conv layouts.

    Two differences from the upstream safetensors path:

    * audio.cpp has already folded weight-norm, so tensors arrive as a single
      ``.weight`` with no ``weight_g``/``weight_v`` pair -- there is no gain to
      apply, only the layout transposes.
    * the transposes are the ones the runtime's own ``vae.decoder_weights``
      applies: Conv1d (out, in, k) -> (out, k, in); ConvTranspose1d
      (in, out, k) -> (out, k, in).

    The rule must be applied to the key *after* stripping ``decoder.``, exactly
    as upstream does, or the ConvTranspose at ``layers.<i>.layers.1`` is missed
    and keeps its (in, out, k) layout.

    Only the decoder is emitted: the runtime loads the decoder alone, and there
    is no independent MLX reference for the encoder layout.
    """
    out = {}
    for full_key, value in gguf_vae.items():
        if not full_key.startswith(VW + "decoder."):
            continue
        key = full_key[len(VW):]
        parts = key.removeprefix("decoder.").split(".")
        if key.endswith(".weight"):
            transposed = len(parts) == 5 and parts[2:4] == ["layers", "1"]
            value = value.transpose(1, 2, 0) if transposed else value.transpose(0, 2, 1)
        out[key] = value.astype(mx.float32)
    return out


def convert(main_gguf: Path, vae_gguf: Path, out: Path, vae_out: Path,
            source_dir: Path, vae_source_dir: Path, *, log=print) -> dict:
    """Build the runtime artifact from two GGUFs. Returns a summary dict."""
    from .runtime.conversion import (
        _COPY_FILES, _GENERATOR_SOURCE_FILES, _QUANTIZATION_GROUP_SIZE,
        _linear_keys, _new_manifest, verify_conversion,
    )
    from .runtime.vae import load_decoder
    from .core.ar_keys import ar_keys

    gs = _QUANTIZATION_GROUP_SIZE
    out.mkdir(parents=True, exist_ok=True)
    vae_out.mkdir(parents=True, exist_ok=True)

    config = json.loads((source_dir / "config.json").read_text())
    tensors = mx.load(str(main_gguf))
    gguf_vae = mx.load(str(vae_gguf))

    ar = ar_keys(config)
    all_names = {k[len(MW):] for k in tensors
                 if k.startswith(MW) and not k[len(MW):].endswith(("scales", "biases"))}
    nar = all_names - ar
    linear = _linear_keys(config)
    missing = ar - all_names
    if missing:
        raise ValueError(f"GGUF is missing AR tensors: {sorted(missing)[:5]}")

    log(f"[convert] AR keys {len(ar)}  NAR keys {len(nar)}  "
        f"AR linear (quantized) {len(linear)}  group size {gs}")

    log("[convert] 1/3 ar-bf16.safetensors (dense AR)")
    dense_ar = {name: (_dequant(tensors, name, gs) if _is_quantized(tensors, name)
                       else _bf16(tensors[MW + name])) for name in sorted(ar)}
    mx.eval(list(dense_ar.values()))
    mx.save_safetensors(str(out / "ar-bf16.safetensors"), dense_ar,
                        metadata={"format": "mlx", "partition": "ar", "precision": "bfloat16"})
    dense_ar = None
    mx.clear_cache()

    log("[convert] 2/3 nar-bf16.safetensors (dense NAR)")
    dense_nar = {name: (_dequant(tensors, name, gs) if _is_quantized(tensors, name)
                        else _bf16(tensors[MW + name])) for name in sorted(nar)}
    mx.eval(list(dense_nar.values()))
    mx.save_safetensors(str(out / "nar-bf16.safetensors"), dense_nar,
                        metadata={"format": "mlx", "partition": "nar", "precision": "bfloat16"})
    dense_nar = None
    mx.clear_cache()

    log("[convert] 3/3 ar-8bit.safetensors (native Q8_0 -> MLX affine, no requant)")
    quantized = {}
    passed = cast = 0
    for name in sorted(ar):
        if name in linear:
            if not _is_quantized(tensors, name):
                raise ValueError(f"{name} is an AR linear but is not Q8_0 in the GGUF")
            stem = name[: -len("weight")]
            scales, biases = _companions(tensors, name)
            quantized[name] = tensors[MW + name]
            quantized[stem + "scales"] = scales.astype(mx.bfloat16)
            quantized[stem + "biases"] = biases.astype(mx.bfloat16)
            passed += 1
        else:
            quantized[name] = _bf16(tensors[MW + name])
            cast += 1
    mx.eval(list(quantized.values()))
    mx.save_safetensors(str(out / "ar-8bit.safetensors"), quantized,
                        metadata={"format": "mlx", "partition": "ar", "precision": "8bit",
                                  "quantization": f"affine-group{gs}-linear"})
    log(f"[convert]     {passed} linears passed through, {cast} tensors cast to bf16")
    quantized = None
    mx.clear_cache()

    for name in _COPY_FILES:
        destination = out / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_dir / name, destination)
    shutil.copyfile(vae_source_dir / "config.json", vae_out / "config.json")

    files = {name: _record(out / name)
             for name in (*_COPY_FILES, "ar-bf16.safetensors", "nar-bf16.safetensors",
                          "ar-8bit.safetensors")}
    manifest = _new_manifest(_GENERATOR_SOURCE_FILES, ["8bit"], files)
    (out / "conversion.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    (out / "README.md").write_text(
        "# YuE2 generator converted from the audio.cpp GGUF\n\n"
        f"- `{main_gguf.name}` ({main_gguf.stat().st_size} bytes)\n"
        f"- `{vae_gguf.name}` ({vae_gguf.stat().st_size} bytes)\n\n"
        "from https://huggingface.co/audio-cpp/Yue2-3B-GGUF, which states it was converted\n"
        "from upstream revision `1a96eca688d6ae5d7f0feb88573fec89920fcd19` of m-a-p/YuE2-3B --\n"
        "the same revision these provenance files come from. Q8_0 linears are carried through\n"
        "as native MLX affine 8-bit (group 32) without dequantisation or re-quantisation.\n"
        "Weights are CC BY-NC 4.0 (non-commercial); see licenses/.\n")

    log("[convert] VAE decoder")
    decoder = vae_decoder_tensors(gguf_vae)
    mx.eval(list(decoder.values()))
    mx.save_safetensors(str(vae_out / "model.safetensors"), decoder)
    log(f"[convert]     {len(decoder)} decoder tensors")

    log("[convert] validating with the runtime's own verify_conversion()")
    verify_conversion(out)
    log("[convert] VALID: manifest, hashes, shapes, dtypes and metadata all pass")

    # Self-contained layout check: a wrong transpose or a missed weight-norm fold
    # would make the strict load fail on shape, so this catches structural errors
    # without needing the upstream safetensors.
    load_decoder(vae_out)
    log("[convert] VAE decoder loads strict=True (layouts consistent)")

    return {"ar_keys": len(ar), "nar_keys": len(nar), "linears_passthrough": passed,
            "tensors_cast": cast, "vae_tensors": len(decoder)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--main-gguf", required=True, type=Path)
    ap.add_argument("--vae-gguf", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path, help="generator artifact dir")
    ap.add_argument("--vae-out", required=True, type=Path, help="VAE artifact dir")
    ap.add_argument("--source-dir", required=True, type=Path,
                    help="pinned m-a-p/YuE2-3B snapshot (provenance files + config)")
    ap.add_argument("--vae-source-dir", required=True, type=Path,
                    help="pinned m-a-p/YuE2-Vae snapshot (config.json)")
    args = ap.parse_args(argv)
    convert(args.main_gguf, args.vae_gguf, args.out, args.vae_out,
            args.source_dir, args.vae_source_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
