# Render deployment

Render runs only the Go site and API. Transcription and judging run on
the Hugging Face Space at `https://dr-pisto-tasmia-live.hf.space`.

## Existing Go service

If `tasmia.onrender.com` is already deployed:

1. Open the `tasmia` service in Render.
2. Open **Environment**.
3. Set `TASMIA_AI_URL` to `https://dr-pisto-tasmia-live.hf.space`.
4. Save and redeploy.
5. Delete or suspend any Python AI service on Render.

The Go service calls the Space at `/api/transcribe` over public HTTPS.
No private service and no Python runtime are needed on Render.

## Space deployment

Upload the contents of the `space/` directory to the Hugging Face Space.
The Space root must contain:

- `app.py`
- `judge.py`
- `tasmia_core/`
- `data/quran/quran.json`
- `requirements.txt`

The Space's `/api/transcribe` endpoint accepts the audio file plus
`surah`, `ayah_from`, `ayah_to`, and `mode`. When `surah` is present it
returns the full judged session.

Test the Space before the Go service:

```bash
curl https://dr-pisto-tasmia-live.hf.space/docs
```

## Blueprint

The root `render.yaml` now defines only the Go service. It is optional
if the service already exists.

## Notes

- Free Render services have 512 MB RAM and sleep after inactivity.
- The first request after sleep is a cold start.
- Warm the Space before a demo. The first GPU request can be slow.
- `config.render.json` only changes the Go listening port to 10000.
  Local development still uses `config.json` on ports 8080 and 7860.
