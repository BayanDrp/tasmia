"""Model domain: resolve, load and cache ASR engines, one chunk forward.

Knows torch and Hugging Face repos; it never touches files or ffmpeg.
All values come from the shared config.json (via ai/app/config.py).
"""

from __future__ import annotations

import gc
import json
import threading
from collections import OrderedDict
from pathlib import Path

import torch
from huggingface_hub import hf_hub_download
from peft import PeftModel
from transformers import (
    AutoConfig,
    HubertForCTC,
    WhisperForConditionalGeneration,
    WhisperProcessor,
    Wav2Vec2ForCTC,
    Wav2Vec2Processor,
)

from .config import DEFAULT_MODEL_ALIAS, DEVICE_PREFERENCE, MODEL_ALIASES

MAX_CACHED_MODELS = 2         
WHISPER_MAX_NEW_TOKENS = 444  # 30 s window maximum


def resolve_model(key: str) -> str:
    """Map 'quick'/'warsh' to their repo ids; any other value is used as is."""
    requested = (key or "").strip() or DEFAULT_MODEL_ALIAS
    return MODEL_ALIASES.get(requested, requested)


def _read_adapter_base(model_id: str) -> str | None:
    """Return the base repo inside a PEFT adapter repo, else None."""
    try:
        path = hf_hub_download(model_id, "adapter_config.json")
        adapter_config = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    return adapter_config.get("base_model_name_or_path")


def _resolve_device() -> str:
    if DEVICE_PREFERENCE == "cuda" or (DEVICE_PREFERENCE == "auto" and torch.cuda.is_available()):
        return "cuda"
    return "cpu"


def load_engine(model_id: str):
    """Load one ASR repo as a ready to use engine, detecting its family."""
    device = _resolve_device()
    dtype = torch.float16 if device == "cuda" else torch.float32

    adapter_base = _read_adapter_base(model_id)
    config_id = adapter_base or model_id

    try:
        config = AutoConfig.from_pretrained(config_id)
    except Exception as exc:
        raise ValueError(f"cannot read config of {config_id}: {exc}")

    model_type = (getattr(config, "model_type", "") or "").lower()
    if model_type.startswith("whisper"):
        kind, model_cls = "whisper", WhisperForConditionalGeneration
    elif model_type in ("wav2vec2", "hubert"):
        kind = "ctc"
        model_cls = HubertForCTC if model_type == "hubert" else Wav2Vec2ForCTC
    else:
        raise ValueError(f"unsupported model type '{model_type}' for {config_id}")

    processor_cls = WhisperProcessor if kind == "whisper" else Wav2Vec2Processor
    try:
        processor = processor_cls.from_pretrained(model_id)
    except Exception:
        processor = processor_cls.from_pretrained(config_id)

    model = model_cls.from_pretrained(config_id, torch_dtype=dtype).to(device)
    if adapter_base:
        model = PeftModel.from_pretrained(model, model_id)
    model.eval()

    print(f"[tasmia] loaded engine {model_id} (type={kind}, peft={bool(adapter_base)}, device={device})")
    return kind, processor, model


class EngineCache:
    """LRU ish cache (FIFO eviction) so arbitrary model ids can't soak RAM.

    Loads happen outside the lock: they are slow (network + from_pretrained).
    Two threads asking for the same missing model may both load it once;
    the second result replaces the first in the cache. Accepted trad -off
    for simplicity.
    """

    def __init__(self, capacity: int):
        self._capacity = capacity
        self._items: OrderedDict[str, tuple] = OrderedDict()
        self._lock = threading.Lock()

    def get_or_load(self, model_id: str):
        with self._lock:
            engine = self._items.get(model_id)
            if engine is not None:
                self._items.move_to_end(model_id)
                return engine

        engine = load_engine(model_id)

        with self._lock:
            self._items[model_id] = engine
            self._items.move_to_end(model_id)
            while len(self._items) > self._capacity:
                _, evicted = self._items.popitem(last=False)
                _release_engine(evicted)
            return engine

    def snapshot(self) -> list[dict]:
        """Diagnostics: what is loaded right now (model id, family, size, device)."""
        with self._lock:
            items = list(self._items.items())
        out = []
        for model_id, (kind, _proc, model) in items:
            try:
                params = sum(p.numel() for p in model.parameters())
                device = str(next(model.parameters()).device)
            except Exception:  # diagnostics must never 500
                params, device = 0, "unknown"
            out.append(
                {"model": model_id, "type": kind, "params_m": round(params / 1e6), "device": device}
            )
        return out


ENGINES = EngineCache(MAX_CACHED_MODELS)


def transcribe_chunk(chunk, sample_rate: int, engine, language: str = "ar") -> str:
    """Run one prepared audio window through the loaded engine."""
    kind, processor, model = engine
    device = next(model.parameters()).device
    dtype = next(model.parameters()).dtype  # engines load in fp16 on cuda

    if kind == "ctc":
        inputs = processor(
            chunk,
            sampling_rate=sample_rate,
            return_tensors="pt",
            padding=True,
        )
        with torch.inference_mode():
            logits = model(inputs.input_values.to(device=device, dtype=dtype)).logits
        predicted_ids = torch.argmax(logits, dim=-1)
        return processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()

    # whisper
    inputs = processor(chunk, sampling_rate=sample_rate, return_tensors="pt")
    forced = processor.get_decoder_prompt_ids(language=language, task="transcribe")
    with torch.inference_mode():
        generated = model.generate(
            inputs.input_features.to(device=device, dtype=dtype),
            forced_decoder_ids=forced,
            max_new_tokens=WHISPER_MAX_NEW_TOKENS,
        )
    return processor.batch_decode(generated, skip_special_tokens=True)[0].strip()


def _release_engine(engine):
    # engine is the immutable tuple (kind, processor, model);
    # dropping the only reference lets the GC free the weights.
    del engine
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
