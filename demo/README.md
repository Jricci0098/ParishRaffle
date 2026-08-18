# Automated demo recorder

Drives a real Chromium browser through the raffle and records video
**automatically** — no manual screen capture. Two recorders:

- **`record-setup.mjs`** — the first-run setup/onboarding walkthrough (admin
  login → setup wizard → prize management → open sales). Run against an **empty**
  instance.
- **`record-demo.mjs`** — the operating workflow (sale → drawing → live TV
  display → pickup). **Seeds** the instance automatically if it is empty.

## Recorded videos

| 🛠️ Setup walkthrough (first run) |
| :------------------------------: |
| [![Setup walkthrough](media/setup-poster.png)](https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-setup-demo.webm) |

| Public TV display — live winner board | Volunteer workflow — sale → draw → pickup |
| :-----------------------------------: | :---------------------------------------: |
| [![TV display demo](media/tv-display-poster.png)](https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-tv-display-demo.webm) | [![Operator demo](media/operator-poster.png)](https://github.com/Jricci0098/ParishRaffle/raw/main/demo/media/raffle-operator-demo.webm) |

Click a thumbnail to play the WebM. Committed copies live in
[`media/`](media/); regenerate them with the recorders below.

## Run it

```bash
cd demo
npm install                 # installs Playwright (downloads a browser once)

# Setup walkthrough — point at a FRESH, empty server:
BASE_URL=http://localhost:8001 ADMIN_PIN=1234 node record-setup.mjs

# Operating demo — local server (auto-seeds if empty):
BASE_URL=http://localhost:8000 ADMIN_PIN=1234 npm run record

# …or against the deployed demo:
BASE_URL=https://picnic-raffle-207884166310.us-central1.run.app ADMIN_PIN=0068 npm run record
```

The finished video path is printed at the end (`VIDEO_SETUP=…`, `VIDEO_OPERATOR=…`,
`VIDEO_DISPLAY=…`).

## Narrated end-to-end video

`build_narrated.py` stitches the three clips into a single MP4
(`media/raffle-end-to-end.mp4`) with on-screen title cards and an offline
voice-over — no cloud services.

```bash
# Dependencies (Linux): a TTS engine, a full ffmpeg, and Pillow.
sudo apt-get install -y espeak-ng
pip install imageio-ffmpeg pillow

python build_narrated.py     # -> media/raffle-end-to-end.mp4
```

Edit the title text and the timed narration cues near the bottom of
`build_narrated.py`. Title cards are rendered with Pillow (DejaVu fonts),
narration with `espeak-ng`, and everything is muxed with the ffmpeg bundled by
`imageio-ffmpeg` (H.264 + AAC).

## Notes

- Playwright records WebM (VP8), which plays in Chrome, Edge, Firefox and VLC.
  To convert to MP4: `ffmpeg -i display.webm -c:v libx264 -pix_fmt yuv420p display.mp4`.
- `PW_CHROME` can point at a pre-installed Chromium (e.g. in CI images); by
  default Playwright uses the browser it manages itself.
- Recording resolution is 1280×720; adjust `VIEWPORT` in `record-demo.mjs`.
