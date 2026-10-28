# Tasmia API Contract

Frozen contract between the **AI layer** (`ai/app/pipeline.py`), the **Go backend** (`web/backend/handlers.go`), and the **frontend** (`web/frontend/js/app.js`).

Every recitation session produces one JSON document shaped by
`core/tasmia_core/models.SessionResult.to_dict()`.

---

## Session result (top level)

```json
{
  "schema_version": 1,
  "surah": 94,
  "surah_name": "الشرح",
  "ayah_from": 1,
  "ayah_to": 5,
  "score": 0.9118,
  "strict_accuracy": 0.8235,
  "counts": {
    "ok": 14,
    "missing": 0,
    "wrong": 1,
    "mispronounced": 2,
    "repeated": 0,
    "uncertain": 0,
    "extra": 0
  },
  "total_words": 17,
  "words": [ ... ],
  "extras": [ ... ],
  "model": "tahkik-warsh-medium-lora",
  "latency_ms": 13400
}
```

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | int | Contract version (currently 1) |
| `surah` | int | Surah number (1..114) |
| `surah_name` | str | Surah name (Arabic) |
| `ayah_from`, `ayah_to` | int | Recited ayah range (inclusive) |
| `score` | float | Weighted score 0..1 (see weights below) |
| `strict_accuracy` | float | Fraction of words marked `ok` |
| `counts` | dict | Per-status word counts (all 7 statuses) |
| `total_words` | int | Number of expected words |
| `words` | list | One `WordResult` per expected word |
| `extras` | list | Heard words with no expected match |
| `model` | str | ASR model used |
| `latency_ms` | int | End-to-end transcription+alignment time |

---

## Word result (one per expected word)

```json
{
  "expected": "صَدْرَكَ",
  "heard": "صَدَر",
  "status": "mispronounced",
  "ayah": 1,
  "index": 4,
  "start": 3.2,
  "end": 4.1,
  "probability": 0.91,
  "distance": 1
}
```

| Field | Type | Meaning |
|---|---|---|
| `expected` | str | Expected word (display form, with tashkeel) |
| `heard` \| null | str | What ASR heard (null if missing) |
| `status` | str | One of: ok, mispronounced, wrong, missing, repeated, uncertain |
| `ayah` | int | Ayah number |
| `index` | int | Word index within the ayah (1-based) |
| `start`, `end` \| null | float | Word start/end seconds in the audio |
| `probability` \| null | float | ASR confidence 0..1 |
| `distance` \| null | int | Edit distance expected↔heard |

---

## Extra result (heard-only word)

```json
{
  "text": "اللهم",
  "status": "extra",
  "start": 0.4,
  "end": 1.1,
  "probability": 0.88,
  "after_index": 2
}
```

| Field | Type | Meaning |
|---|---|---|
| `text` | str | Heard word text |
| `status` | str | `"extra"` |
| `start`, `end` \| null | float | Word start/end seconds |
| `probability` \| null | float | ASR confidence |
| `after_index` | int | Index of last expected word before this extra (`-1` if before the first) |

---

## Status vocabulary & scoring weights

| Status | Meaning | Weight |
|---|---|---|
| `ok` | Exact normalized match | 1.0 |
| `mispronounced` | Weak-letter match (alef/waw/ya differences) or high similarity | 0.75 |
| `uncertain` | Match but low ASR confidence | 0.5 |
| `wrong` | Clear mismatch | 0 |
| `missing` | Expected word not recited | 0 |
| `repeated` | Duplicate of an already-recited word | 0 |
| `extra` | Heard word with no expected match | n/a (not scored) |

```
score = sum(weight[status] for expected words) / total_expected_words
strict_accuracy = count(ok) / total_expected_words
```

Extras are counted in `counts["extra"]` but **do not affect the score**.

---

## Input contract (AI layer)

The AI layer receives:

- `audio`: WAV/PCM 16 kHz mono (frontend/browser recording or file upload)
- `surah`, `ayah_from`, `ayah_to`: the passage being recited

The AI layer:

1. Loads the ASR model (`openai/whisper-medium` + LoRA adapter
   `Dr-pisto/tahkik-warsh-medium-lora`)
2. Transcribes the audio (Arabic, forced decoder ids)
3. Normalizes **only** for matching, the frontend must **not** normalize or tokenize Quran text
4. Aligns heard words against expected words from `core/tasmia_core/surahs.py`
5. Returns the session result JSON above

---

## Output contract (AI → Go backend → frontend)

The Go backend exposes a single endpoint:

```
POST /api/recite
  multipart/form-data: audio (file), surah, ayah_from, ayah_to
  -> 200 application/json: SessionResult (above)
```

The frontend renders each `WordResult` with a color per `status` and
places `extras` after the word at `after_index`.

---

## Notes

- Expected words are sent to the ASR as an **initial prompt** (decoder hint) so the model stays on the recited passage. The prompt is capped at 200 characters.
- The matcher normalizes `ٰ` (superscript alef) → `ا` and `ے` → `ي` so Warsh orthography and full-alef ASR output match exactly.
- Display forms preserve tashkeel and Warsh marks; only matching uses normalized forms.
