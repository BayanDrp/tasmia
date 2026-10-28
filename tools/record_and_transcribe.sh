#!/usr/bin/env bash
# Record a Quran recitation (headset, safe volume) and transcribe with the
# Quran-finetuned Wav2Vec2 model.
#
# Usage:
#   ./tools/record_and_transcribe.sh [seconds] [pulse-source]
#
# Defaults: 25 s, Bluetooth headset bluez_input.41:42:C4:D5:45:30.
#
# The recordings go to tools/recordings/ (on disk, not volatile /tmp).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REC_DIR="$PROJECT_DIR/tools/recordings"
VENV="${TASMIA_VENV:-/tmp/opencode/warsh-venv}"

DUR="${1:-25}"
SRC="${2:-bluez_input.41:42:C4:D5:45:30}"

mkdir -p "$REC_DIR"

# Headset mic needs full gain; 60% made recordings too quiet (-39 dB).
# Set to 100%; user can still adjust with pactl if it clips.
pactl set-source-volume "$SRC" "100%" 2>/dev/null || true

OUT="$REC_DIR/recitation_$(date +%Y%m%d_%H%M%S).wav"

echo "Microphone : $SRC"
echo "Length     : ${DUR}s"
echo "Mic volume : 60% (clipping fix)"
echo "Output     : $OUT"
echo
echo "Recite Surah Ash-Sharh (94:1-5):"
echo "  أَلَمْ نَشْرَحْ لَكَ صَدْرَكَ وَوَضَعْنَا عَنكَ وِزْرَكَ"
echo "  الَّذِي أَنقَضَ ظَهْرَكَ وَرَفَعْنَا لَكَ ذِكْرَكَ"
echo "  فَإِنَّ مَعَ الْعُسْرِ يُسْرًا"
echo "Wait 1 second after 'RECORDING NOW', then start. Do not touch the mic."
echo
for i in 3 2 1; do
    echo "  starting in $i..."
    sleep 1
done
echo ">>> RECORDING NOW <<<"
ffmpeg -hide_banner -loglevel warning -y \
    -f pulse -i "$SRC" \
    -t "$DUR" -ac 1 -ar 16000 -c:a pcm_s16le "$OUT"
echo ">>> DONE: $OUT <<<"
echo

# Check input level before transcribing; quiet/noisy audio hurts ASR accuracy.
RAW_LEVELS=$(ffmpeg -hide_banner -i "$OUT" -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume")
echo "$RAW_LEVELS"
RAW_MAX=$(echo "$RAW_LEVELS" | grep -oE "max_volume: [-0-9.]+" | awk '{print $2}')
RAW_MEAN=$(echo "$RAW_LEVELS" | grep -oE "mean_volume: [-0-9.]+" | awk '{print $2}')
if [[ -n "$RAW_MEAN" ]] && awk -v a="$RAW_MEAN" 'BEGIN{exit !(a < -25)}'; then
    echo
    echo "!! WARNING: recording is too quiet (mean ${RAW_MEAN} dB, want ~-16 dB)."
    echo "!! تحذير: التسجيل هادئ جدًا, acercó المايك من فمك أو زد مستوى المايك."
    echo "!! The transcription will likely be poor. Re-record after fixing the level."
    echo
fi
if [[ -n "$RAW_MAX" ]] && awk -v a="$RAW_MAX" 'BEGIN{exit !(a > -0.5)}'; then
    echo
    echo "!! WARNING: level reached ${RAW_MAX} dB, possible clipping."
    echo "!! تحذير: звук قوي جدًا, ابتعد قليلاً عن المايك."
    echo
fi

# Normalize loudness to make quieter recordings easier to recognize.
# Target: mean ~ -16 dB, true peak ~ -1.5 dB.
OUT_NORM="$REC_DIR/recitation_$(date +%Y%m%d_%H%M%S)_norm.wav"
ffmpeg -hide_banner -loglevel error -y \
    -i "$OUT" -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
    -ar 16000 -ac 1 -c:a pcm_s16le "$OUT_NORM"
echo "Normalized: $OUT_NORM"
echo

if [[ -x "$VENV/bin/python" ]]; then
    "$VENV/bin/python" "$PROJECT_DIR/tools/transcribe_lora.py" "$OUT_NORM"
else
    echo "venv not found at $VENV, create it with tools/setup_venv.sh first"
fi
