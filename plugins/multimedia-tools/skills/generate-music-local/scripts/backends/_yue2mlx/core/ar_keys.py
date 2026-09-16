"""AR/NAR tensor partition for YuE2, extracted verbatim from ``yue2/fast.py``.

``yue2/fast.py`` is 426 lines of vLLM/torch machinery; the AR extraction
specification the MLX runtime needs is these two pure-Python functions. Copying
just them keeps the vendored runtime free of torch and vLLM without altering
the partition rule. Provenance: yue2-infer 0.1.5, ``yue2/fast.py`` lines 33-54.
"""
from __future__ import annotations

from .protocol import CONTEXT


def ar_keys(config):
    """Names of every tensor the autoregressive stage needs."""
    names = {"model.embed_tokens.weight", "model.norm.weight", "lm_head.weight"}
    for index in range(config["num_hidden_layers"]):
        prefix = f"model.layers.{index}."
        names.update(prefix + name + ".weight" for name in (
            "input_layernorm", "post_attention_layernorm", "self_attn.q_proj",
            "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj",
            "self_attn.q_norm", "self_attn.k_norm", "mlp.gate_proj",
            "mlp.up_proj", "mlp.down_proj"))
    return names


def qwen_config(config):
    """Qwen3 config derived from a YuE2 config, for the AR subset."""
    required = ("hidden_size", "intermediate_size", "num_hidden_layers", "num_attention_heads",
                "num_key_value_heads", "head_dim", "vocab_size", "rms_norm_eps", "rope_theta")
    output = {name: config[name] for name in required}
    output.update(architectures=["Qwen3ForCausalLM"], model_type="qwen3", hidden_act="silu",
                  max_position_embeddings=config.get("max_position_embeddings", CONTEXT),
                  tie_word_embeddings=False, attention_bias=False, attention_dropout=0.,
                  use_sliding_window=False, sliding_window=None, max_window_layers=0,
                  torch_dtype="bfloat16")
    return output
