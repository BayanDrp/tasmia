"""Tasmia ASR engine layer  model resolution, caching and transcription.

Pure PyTorch side of the Space: knows nothing about http/gradio, so it can
be reused by ai/app/pipeline.py or any local runner later.
"""

from __future__ import annotations

import gc
import json
import subprocess
import tempfile
import threading
from collections import OrderedDict

import numpy as np
import soundfile as sf
import torch
from config import MAX_AUDIO_SECONDS  # local module, shared with app.py
from tasmia_core.normalize import merge_chunk_texts  # vendored core (pure stdlib)
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

ENGINE_ALIASES = {
    "quick": "rabah2026/wav2vec2-large-xlsr-53-arabic-quran-v_final",
    "warsh": "Dr-pisto/tahkik-warsh-medium-lora",
}

MAX_CHUNK_SECONDS = 20
CHUNK_OVERLAP_SECONDS = 1
SILENCE_RMS = 0.003           # near-silent windows are skipped (no hallucination basis)
MAX_CACHED_MODELS = 2         # FIFO eviction; whisper-medium fp16 is ~1.5 GB each
WHISPER_MAX_NEW_TOKENS = 444  # 30 s window maximum


def resolve_model(key: str) -> str:
    """Map an alias or bare repo id to a concrete HF model id."""
    requested = (key or "").strip() or DEFAULT_MODEL_ALIAS
    return ENGINE_ALIASES.get(requested, requested)


def _read_adapter_base(model_id: str) -> str | None:
    """Return the PEFT base model id when the repo is a LoRA adapter."""
    try:
        path = hf_hub_download(model_id, "adapter_config.json")
    except Exception:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:  # malformed adapter config
        raise ValueError(f"adapter_config.json of {model_id} is unreadable: {exc}")
    base = data.get("base_model_name_or_path")
    if not base:
        raise ValueError(f"adapter {model_id} has no base_model_name_or_path")
    return str(base)


def load_engine(model_id: str):
    """Load one ASR repo as a ready to use CPU engine, detecting its family."""
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

    model = model_cls.from_pretrained(config_id, torch_dtype=torch.float16)
    if adapter_base:
        model = PeftModel.from_pretrained(model, model_id)
    model.eval()

    print(f"[tasmia] loaded engine {model_id} (type={kind}, peft={bool(adapter_base)})")
    return kind, processor, model


def _release_engine(engine):
    # engine is the immutable tuple (kind, processor, model);
    # dropping the only reference lets the GC free the weights.
    del engine
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


class EngineCache:
    """LRU-ish cache (FIFO eviction) so arbitrary model ids can't soak RAM."""

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

        # Load outside the lock: slow (network + from_pretrained).
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
# --------------------------------------------------------------------------
# Audio pipeline
# --------------------------------------------------------------------------

def decode_audio(audio_path: str):
    """Decode common uploaded formats to mono 16 kHz float audio."""
    with tempfile.NamedTemporaryFile(suffix=".wav") as converted:
        command = [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            audio_path,
            "-t",
            str(MAX_AUDIO_SECONDS),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            converted.name,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            detail = result.stderr.strip().splitlines()
            raise ValueError(detail[-1] if detail else "Could not decode audio.")

        audio, sample_rate = sf.read(converted.name, dtype="float32")

    if audio.size == 0:
        raise ValueError("The uploaded recording is empty.")
    return np.asarray(audio, dtype=np.float32), sample_rate


def split_audio(audio, sample_rate):
    """Split into short overlapping windows for stable CTC inference."""
    max_samples = MAX_CHUNK_SECONDS * sample_rate
    overlap_samples = CHUNK_OVERLAP_SECONDS * sample_rate
    total_samples = len(audio)

    if total_samples <= max_samples:
        return [audio]

    stride_limit = max_samples - overlap_samples
    chunk_count = (total_samples - overlap_samples + stride_limit - 1) // stride_limit
    chunk_samples = (
        total_samples + (chunk_count - 1) * overlap_samples + chunk_count - 1
    ) // chunk_count
    stride_samples = chunk_samples - overlap_samples

    chunks = []
    for index in range(chunk_count):
        start = index * stride_samples
        end = min(start + chunk_samples, total_samples)
        if start < total_samples:
            chunks.append(audio[start:end])
    return chunks


def _forward_chunk(chunk, sample_rate, engine, language):
    kind, processor, model = engine
    device = next(model.parameters()).device
    dtype = next(model.parameters()).dtype  # engines load in fp16

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


def transcribe_transcript(audio_path: str, model_id: str, language: str = "ar"):
    """Decode, chunk, transcribe and merge - returns (kind, text, chunks, seconds)."""
    engine = ENGINES.get_or_load(model_id)

    kind, processor, model = engine
    if torch.cuda.is_available():
        model.to("cuda")

    audio, sample_rate = decode_audio(audio_path)
    chunks = split_audio(audio, sample_rate)

    texts = []
    for chunk in chunks:
        # Ignore near-silent windows, which can trigger hallucinations.
        if float(np.sqrt(np.mean(np.square(chunk)))) < SILENCE_RMS:
            continue
        texts.append(_forward_chunk(chunk, sample_rate, engine, language))

    text = merge_chunk_texts(texts)
    if not text:
        raise ValueError("لم أتمكن من تمييز كلام واضح في التسجيل.")

    return kind, text, len(chunks), round(len(audio) / sample_rate, 3)
