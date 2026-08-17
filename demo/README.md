# Automated demo recorder

Drives a real Chromium browser through the whole raffle workflow and records
video **automatically** — no manual screen capture. It produces two videos:

- `videos/operator-*.webm` — the volunteer walkthrough: ticket sale → drawing
  console (scan/lookup/confirm) → prize pickup/claim.
- `videos/display-*.webm` — the public TV board reacting **live** over
  WebSockets as each winner is confirmed (including the highlight overlay).

## Run it

You need a running server (local or deployed). The script seeds the raffle
automatically if it is empty.

```bash
cd demo
npm install                 # installs Playwright (downloads a browser once)

# against a local server
BASE_URL=http://localhost:8000 ADMIN_PIN=1234 npm run record

# against the deployed demo
BASE_URL=https://picnic-raffle-207884166310.us-central1.run.app ADMIN_PIN=0068 npm run record
```

The finished video paths are printed at the end (`VIDEO_OPERATOR=…`,
`VIDEO_DISPLAY=…`).

## Notes

- Playwright records WebM (VP8), which plays in Chrome, Edge, Firefox and VLC.
  To convert to MP4: `ffmpeg -i display.webm -c:v libx264 -pix_fmt yuv420p display.mp4`.
- `PW_CHROME` can point at a pre-installed Chromium (e.g. in CI images); by
  default Playwright uses the browser it manages itself.
- Recording resolution is 1280×720; adjust `VIEWPORT` in `record-demo.mjs`.
