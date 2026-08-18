#!/usr/bin/env python3
"""Stitch the three raffle clips into a single narrated end-to-end MP4 with
on-screen title cards.

Pipeline (all offline):
  - Pillow renders full-screen title cards.
  - espeak-ng synthesizes timed voice narration cues.
  - ffmpeg (from imageio-ffmpeg) builds normalized segments and concatenates
    them into demo/media/raffle-end-to-end.mp4.

Run: backend/.venv/bin/python demo/build_narrated.py
"""
import os
import re
import subprocess
import sys
import wave

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(HERE, "media")
BUILD = os.path.join(HERE, "build")
os.makedirs(BUILD, exist_ok=True)

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS, AR = 1280, 720, 25, 44100

# Cross-platform font resolution (Linux / Windows / macOS).
def _resolve_font(candidates, env):
    p = os.getenv(env)
    if p and os.path.exists(p):
        return p
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


FONT_BOLD = _resolve_font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
], "FONT_BOLD")
FONT_REG = _resolve_font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
], "FONT_REG")


def font(bold, size):
    path = FONT_BOLD if bold else FONT_REG
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


# TTS backend: "piper" (neural, most natural), "pico" (SVOX Pico), or
# "espeak" (robotic fallback).
TTS_BACKEND = os.getenv("TTS_BACKEND", "pico")
PICO_LANG = os.getenv("PICO_LANG", "en-US")
ESPEAK_VOICE = ["-v", "en-us+f3", "-s", "158", "-p", "42", "-g", "3"]
# Piper: model name (or full path to a .onnx) and the dir the voice was
# downloaded to. Default data dir is the repo root, where
# `python -m piper.download_voices <name>` puts the files by default.
PIPER_MODEL = os.getenv("PIPER_MODEL", "en_US-lessac-medium")
PIPER_DATA_DIR = os.getenv("PIPER_DATA_DIR", os.path.dirname(HERE))


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def probe_duration(path):
    out = subprocess.run([FF, "-i", path], stderr=subprocess.PIPE).stderr.decode("utf-8", "ignore")
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    h, mm, ss = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mm * 60 + ss


def tts(text, out_wav):
    if TTS_BACKEND == "piper":
        # Neural voice. Reads text from stdin; resolves the model by name in
        # PIPER_DATA_DIR (or accepts a full .onnx path in PIPER_MODEL).
        cmd = [sys.executable, "-m", "piper", "-m", PIPER_MODEL, "-f", out_wav]
        if not PIPER_MODEL.endswith(".onnx"):
            cmd += ["--data-dir", PIPER_DATA_DIR]
        subprocess.run(cmd, input=text.encode("utf-8"), check=True)
    elif TTS_BACKEND == "pico":
        subprocess.run(["pico2wave", "-l", PICO_LANG, "-w", out_wav, text], check=True)
    else:
        subprocess.run(["espeak-ng", *ESPEAK_VOICE, "-w", out_wav, text], check=True)
    with wave.open(out_wav) as w:
        return w.getnframes() / w.getframerate()


# ---------- Title cards ----------
def make_title(path, title, subtitle, step=None):
    img = Image.new("RGB", (W, H))
    # Vertical gradient background (deep blue -> indigo).
    top, bot = (23, 37, 84), (67, 56, 202)
    for y in range(H):
        t = y / H
        img.paste(
            tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)),
            (0, y, W, y + 1),
        )
    d = ImageDraw.Draw(img)

    def center(text, font, y, fill):
        bb = d.textbbox((0, 0), text, font=font)
        d.text(((W - (bb[2] - bb[0])) / 2, y), text, font=font, fill=fill)

    if step:
        center(step, font(True, 40), 210, (147, 197, 253))
    center(title, font(True, 84), 285, (255, 255, 255))
    if subtitle:
        center(subtitle, font(False, 36), 410, (203, 213, 225))
    img.save(path)


# ---------- Segment builders ----------
def build_title_segment(idx, title, subtitle, narration, out, step=None):
    png = os.path.join(BUILD, f"title{idx}.png")
    wav = os.path.join(BUILD, f"title{idx}.wav")
    make_title(png, title, subtitle, step)
    ndur = tts(narration, wav)
    seg = max(3.0, ndur + 1.3)
    fade_out = max(0.0, seg - 0.4)
    run([
        FF, "-y", "-loop", "1", "-i", png, "-i", wav,
        "-filter_complex",
        f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p,"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out:.2f}:d=0.4[v];"
        f"[1:a]aresample={AR},aformat=channel_layouts=stereo,adelay=400|400,apad[a]",
        "-map", "[v]", "-map", "[a]", "-t", f"{seg:.2f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-ar", str(AR), "-ac", "2", "-b:a", "160k",
        out,
    ])


def build_clip_segment(idx, webm, cues, out):
    clip_dur = probe_duration(webm)
    # Synthesize cue WAVs and compute the segment length.
    cue_files, ends = [], []
    for i, (t, text) in enumerate(cues):
        wav = os.path.join(BUILD, f"cue{idx}_{i}.wav")
        dur = tts(text, wav)
        cue_files.append((t, wav))
        ends.append(t + dur)
    seg = max(clip_dur, (max(ends) if ends else 0) + 0.6)
    extend = max(0.0, seg - clip_dur)

    inputs = [FF, "-y", "-i", webm]
    for _, wav in cue_files:
        inputs += ["-i", wav]

    # Video: scale, set fps, hold last frame to fill the segment, gentle fades.
    vf = (
        f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p,"
        f"tpad=stop_mode=clone:stop_duration={extend:.2f},"
        f"fade=t=in:st=0:d=0.3,fade=t=out:st={seg-0.3:.2f}:d=0.3[v]"
    )
    # Audio: place each cue at its timestamp, mix, pad/trim to segment length.
    a_parts, labels = [], []
    for i, (t, _) in enumerate(cue_files):
        delay = int(t * 1000)
        a_parts.append(
            f"[{i+1}:a]aresample={AR},aformat=channel_layouts=stereo,"
            f"adelay={delay}|{delay}[a{i}]"
        )
        labels.append(f"[a{i}]")
    if labels:
        a_mix = "".join(labels) + f"amix=inputs={len(labels)}:normalize=0[am];[am]apad,atrim=0:{seg:.2f}[a]"
        filtergraph = vf + ";" + ";".join(a_parts) + ";" + a_mix
    else:
        filtergraph = vf + f";anullsrc=r={AR}:cl=stereo,atrim=0:{seg:.2f}[a]"

    run(inputs + [
        "-filter_complex", filtergraph,
        "-map", "[v]", "-map", "[a]", "-t", f"{seg:.2f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-ar", str(AR), "-ac", "2", "-b:a", "160k",
        out,
    ])


def main():
    segments = []

    def add(name):
        segments.append(os.path.join(BUILD, name))
        return segments[-1]

    build_title_segment(
        0, "Picnic Raffle Manager",
        "A local-first church picnic raffle app",
        "Picnic Raffle Manager. A local first app for running a church picnic "
        "raffle, from ticket sales to the live television display.",
        add("seg0.mp4"),
    )
    build_title_segment(
        1, "Set Up the Raffle", "Wizard, stations, prizes",
        "Step one. Setting up the raffle.",
        add("seg1.mp4"), step="STEP 1",
    )
    build_clip_segment(2, os.path.join(MEDIA, "raffle-setup-demo.webm"), [
        (1.5, "First, sign in with the admin PIN."),
        (7.0, "Run the setup wizard. Name the event,"),
        (14.0, "define each ticket range and selling station,"),
        (23.0, "and choose the number of raffle sessions."),
        (31.0, "Add prizes by hand, or import them in bulk from a C S V file."),
        (43.0, "Then open ticket sales. The raffle is ready."),
    ], add("seg2.mp4"))

    build_title_segment(
        3, "Sell & Draw", "Ticket sales and the drawing console",
        "Step two. Selling tickets, and drawing the winners.",
        add("seg3.mp4"), step="STEP 2",
    )
    build_clip_segment(4, os.path.join(MEDIA, "raffle-operator-demo.webm"), [
        (2.0, "At a sales station, enter the buyer's name and quantity."),
        (10.0, "The system assigns the next tickets automatically."),
        (19.0, "To draw a winner, scan or type the winning ticket,"),
        (27.0, "and the buyer's name appears instantly."),
        (35.0, "One tap confirms the winner."),
        (43.0, "At the prize table, search by ticket or name,"),
        (51.0, "verify the physical ticket, and mark it picked up."),
    ], add("seg4.mp4"))

    build_title_segment(
        5, "Live on the TVs", "The public winner board",
        "Step three. Live on the televisions.",
        add("seg5.mp4"), step="STEP 3",
    )
    build_clip_segment(6, os.path.join(MEDIA, "raffle-tv-display-demo.webm"), [
        (3.0, "On the televisions, each winner appears the moment it is confirmed,"),
        (12.0, "with a big congratulations highlight."),
        (24.0, "The board then rotates through all of the winners."),
        (40.0, "Claimed and unclaimed prizes update live, on every device."),
    ], add("seg6.mp4"))

    build_title_segment(
        7, "Ready for Your Event", "github.com/Jricci0098/ParishRaffle",
        "Picnic Raffle Manager. Ready for your next event.",
        add("seg7.mp4"),
    )

    # Concatenate (identical params -> stream copy).
    listfile = os.path.join(BUILD, "concat.txt")
    with open(listfile, "w") as f:
        for s in segments:
            f.write(f"file '{s}'\n")
    out = os.path.join(MEDIA, "raffle-end-to-end.mp4")
    run([FF, "-y", "-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", out])
    print("FINAL=" + out)
    print("DURATION=%.1fs" % probe_duration(out))


if __name__ == "__main__":
    main()
