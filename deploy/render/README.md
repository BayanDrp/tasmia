# Render deployment

The active Blueprint is at the repository root: `/render.yaml`.

This setup runs two free Render web services:

- `tasmia-ai-bayan`: Python FastAPI judge on port 10000.
- `tasmia-bayan`: Go site and API, calling the judge over public HTTPS.

The ASR still runs on the Hugging Face Space at
`https://dr-pisto-tasmia-live.hf.space`. Judging stays local to the
Python service.

## Deploy

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint**.
3. Connect the GitHub repo and select the `master` branch.
4. Keep the Blueprint path `render.yaml`.
5. Apply the Blueprint and wait for both builds.
6. Open the Go service URL, normally `https://tasmia-bayan.onrender.com`.

No secrets are required.

## Notes

- The AI service is public because Render's free web services cannot
  receive private network traffic. The Go service calls it through
  `TASMIA_AI_URL`.
- If Render appends a suffix to the AI service name, update
  `TASMIA_AI_URL` in `render.yaml` to the actual URL.
- Free services have 512 MB RAM and sleep after inactivity. The first
  request is a cold start.
- The local Whisper and Wav2Vec2 fallback is not installed on Render.
  The Python service uses the Hugging Face Space for transcription.
  Warm the Space before a demo.
- `config.render.json` only changes the Go listening port to 10000.
  Local development still uses `config.json` on ports 8080 and 7860.
