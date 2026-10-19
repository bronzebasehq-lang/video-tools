#!/usr/bin/env python3
"""Timeline export — video tools (INTERNAL).

Exports a build_props.py MANIFEST (the frame-accurate source of truth)
to the two timeline formats editors read:

  - CMX 3600 EDL  (.edl)  — Premiere / DaVinci / Resolve import.
  - FCPXML 1.11   (.fcpxml) — Final Cut Pro import.

Each manifest scene becomes ONE cut event/clip referencing the
RENDERED MP4 (flattened cut list: source in/out == record in/out), so
the editor opens the finished video as a sequence of trimmable clips —
one per shot — instead of one opaque file. Shot labels carry the scene
id, role, big caption (or X lines), and media source as comments /
markers, so the edit stays readable.

Timing rule (must match the compositions exactly):
  - X style:      shot = durationInFrames (XStyle uses raw durations).
  - Every other style: shot = durationInFrames + 3 (10 on the last shot)
    — the +3/+10 buffer inside each Series.Sequence (SivoExplainer,
    SivoListicle, SivoNews, NewsStyle). Root.tsx's durationFromProps
    uses the same rule, so manifest total == rendered total for these
    styles. XStyle does NOT add the buffer (Root.tsx still does — that
    mismatch is the ~1s blank tail on X renders; see CONSOLIDATION.md),
    so when --video is given the exporter probes the rendered file and
    appends a TAIL event if the render is longer than the shot sum.

Input: a manifest JSON (build_props.py output). The raw shot-list JSON
does NOT carry durations, so it cannot be exported frame-accurately —
build a manifest first, then export it.

Usage:
  python export_timeline.py --manifest out/manifest.json --video out/video.mp4
  python export_timeline.py --manifest out/manifest.json   # manifest-only, no tail check
  python export_timeline.py --manifest out/manifest.json --video out/video.mp4 --out-dir out/

Output: <video-stem>.edl + <video-stem>.fcpxml next to the video (or in
--out-dir). Stdlib only — runs on Windows (GUI) and Linux (dev).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from urllib.request import pathname2url

GENERATOR = "video-tools export_timeline.py"
FCPXML_VERSION = "1.11"


def fail(msg):
    print(f"[export_timeline] ERROR: {msg}", file=sys.stderr)
    return 1


def tc(frames, fps):
    """Frame count -> CMX non-drop timecode HH:MM:SS:FF."""
    frames = int(frames)
    f = frames % fps
    s = (frames // fps) % 60
    m = (frames // (fps * 60)) % 60
    h = frames // (fps * 3600)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def rational(frames, fps):
    """Frame count -> FCPXML rational seconds (frame-exact)."""
    return f"{int(frames)}/{int(fps)}s"


def shot_label(scene):
    """Human-readable shot label: bigCaption > X lines > headline > id."""
    if scene.get("bigCaption"):
        return str(scene["bigCaption"])
    lines = scene.get("lines")
    if lines:
        return " / ".join(str(l.get("text", "")) for l in lines)
    if scene.get("headline"):
        return str(scene["headline"])
    return str(scene.get("id", "shot"))


def shot_note(scene):
    """One-line metadata: role | caption | media. Newlines stripped."""
    media = scene.get("media") or {}
    media_src = media.get("src", "") if isinstance(media, dict) else ""
    parts = [
        f"ROLE={scene.get('role', '')}",
        f"CAPTION={shot_label(scene)}",
    ]
    if media_src:
        parts.append(f"MEDIA={media_src}")
    if scene.get("layout"):
        parts.append(f"LAYOUT={scene['layout']}")
    note = " | ".join(parts).replace("\n", " ").replace("\r", "")
    return note[:400]


def shot_spans(manifest):
    """Manifest scenes -> [(start_frame, end_frame)] in render order.

    X style: raw durationInFrames. Everything else: +3 per shot,
    +10 on the last (the buffer inside each Series.Sequence).
    """
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Manifest has no scenes — nothing to export.")
    fps = manifest.get("fps") or 30
    style = manifest.get("style", "fireship")
    spans = []
    cursor = 0
    for i, scene in enumerate(scenes):
        dur = scene.get("durationInFrames")
        if not isinstance(dur, int) or dur <= 0:
            raise ValueError(
                f"Scene {i + 1} ({scene.get('id', '?')}): bad "
                f"durationInFrames {dur!r} — rebuild the manifest."
            )
        if style != "x":
            dur += 10 if i == len(scenes) - 1 else 3
        spans.append((cursor, cursor + dur))
        cursor += dur
    return spans, int(fps)


def reel_name(stem):
    """CMX reel: <=8 chars, uppercase alnum. Fallback VIDEO001."""
    clean = re.sub(r"[^A-Za-z0-9]", "", stem or "").upper()[:8]
    return clean or "VIDEO001"


def probe_rendered_frames(video_path, fps):
    """Rendered VIDEO frame count (exact).

    Uses the video stream's nb_frames when present (exact frame count),
    else the video stream duration * fps. The CONTAINER (format)
    duration must NOT be used: it follows the longer audio track
    (the loudnorm pass leaves audio ~0.13s longer than video) and
    would invent a phantom tail. Returns None when ffprobe is
    unavailable or the probe fails — the caller falls back to
    manifest-only export + a warning."""
    candidates = ["ffprobe"]
    ffbin = os.environ.get("FFMPEG_BIN")
    if ffbin:
        d = os.path.dirname(ffbin)
        candidates.append(os.path.join(d, "ffprobe.exe"))
        candidates.append(os.path.join(d, "ffprobe"))
    for exe in candidates:
        try:
            res = subprocess.run(
                [exe, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=nb_frames,duration",
                 "-of", "default=noprint_wrappers=1", video_path],
                capture_output=True, text=True, timeout=30,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            continue
        if res.returncode != 0:
            continue
        kv = {}
        for line in res.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                kv[k.strip()] = v.strip()
        try:
            if kv.get("nb_frames") and kv["nb_frames"] != "N/A":
                return int(kv["nb_frames"])
            if kv.get("duration") and kv["duration"] != "N/A":
                return max(0, round(float(kv["duration"]) * fps))
        except ValueError:
            continue
    return None


def build_edl(title, reel, spans, scenes, fps, tail_frames, warnings):
    lines = [f"TITLE: {title}", "FCM: NON-DROP FRAME"]
    for w in warnings:
        lines.append(f"* WARNING: {w}")
    events = []
    for i, ((start, end), scene) in enumerate(zip(spans, scenes)):
        events.append((i + 1, start, end, scene))
    if tail_frames and tail_frames > 0:
        tail_start = spans[-1][1] if spans else 0
        events.append((len(events) + 1, tail_start,
                       tail_start + tail_frames, None))
    for n, start, end, scene in events:
        src_in, src_out = tc(start, fps), tc(end, fps)
        lines.append(
            f"{n:03d}  {reel:<8} V     C        "
            f"{src_in} {src_out} {src_in} {src_out}"
        )
        if scene is None:
            lines.append("* FROM CLIP NAME: TAIL (blank — render longer "
                         "than shot sum; see CONSOLIDATION.md X tail)")
            lines.append("* COMMENT: TAIL=blank frames past the last shot")
        else:
            label = shot_label(scene).replace("\n", " ")
            lines.append(
                f"* FROM CLIP NAME: {scene.get('id', '')} — {label}"[:240]
            )
            lines.append(f"* COMMENT: {shot_note(scene)}")
    return "\n".join(lines) + "\n"


def build_fcpxml(title, video_path, spans, scenes, fps, tail_frames,
                 total_frames, audio_rate):
    root = ET.Element("fcpxml", {"version": FCPXML_VERSION})
    resources = ET.SubElement(root, "resources")
    ET.SubElement(resources, "format", {
        "id": "r1",
        "name": f"FFVideoFormat1080p{fps}",
        "frameDuration": f"1/{fps}s",
        "width": "1080",
        "height": "1920",
        "colorSpace": "1-1-1 (Rec. 709)",
    })
    abs_video = os.path.abspath(video_path) if video_path else ""
    uid = hashlib.sha1(abs_video.encode("utf-8")).hexdigest() if abs_video else "0" * 40
    asset_attrs = {
        "id": "r2",
        "name": os.path.basename(video_path) if video_path else title,
        "uid": uid,
        "start": "0s",
        "duration": rational(total_frames, fps),
        "hasVideo": "1",
        "hasAudio": "1",
        "format": "r1",
    }
    if abs_video:
        asset_attrs["src"] = urljoin("file:", pathname2url(abs_video))
    ET.SubElement(resources, "asset", asset_attrs)
    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", {"name": title})
    project = ET.SubElement(event, "project", {"name": title})
    sequence = ET.SubElement(project, "sequence", {
        "format": "r1",
        "duration": rational(total_frames, fps),
        "tcStart": "0s",
        "tcFormat": "NDF",
        "audioLayout": "stereo",
        "audioRate": str(audio_rate),
    })
    spine = ET.SubElement(sequence, "spine")
    clips = []
    for (start, end), scene in zip(spans, scenes):
        clips.append((start, end, scene))
    if tail_frames and tail_frames > 0:
        tail_start = spans[-1][1] if spans else 0
        clips.append((tail_start, tail_start + tail_frames, None))
    for start, end, scene in clips:
        dur = end - start
        if scene is None:
            name, note = "TAIL (blank)", "TAIL=blank frames past the last shot"
        else:
            name = f"{scene.get('id', '')} — {shot_label(scene)}"[:100]
            note = shot_note(scene)
        clip = ET.SubElement(spine, "clip", {
            "name": name,
            "offset": rational(start, fps),
            "start": rational(start, fps),
            "duration": rational(dur, fps),
        })
        ET.SubElement(clip, "video", {"ref": "r2"})
        ET.SubElement(clip, "marker", {
            "start": "0s",
            "duration": rational(dur, fps),
            "value": note,
        })
    xml = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml + "\n"


def probe_audio_rate(video_path):
    """Audio sample rate of the rendered file (ffprobe); default 48000."""
    for exe in ("ffprobe",):
        try:
            res = subprocess.run(
                [exe, "-v", "error", "-select_streams", "a:0",
                 "-show_entries", "stream=sample_rate", "-of",
                 "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True, text=True, timeout=30,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return 48000
        if res.returncode == 0:
            try:
                return int(res.stdout.strip())
            except ValueError:
                return 48000
    return 48000


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Export a video-tools manifest to EDL + FCPXML.")
    ap.add_argument("--manifest", required=True,
                    help="manifest JSON from build_props.py")
    ap.add_argument("--video", default="",
                    help="rendered MP4 (reel/asset name + tail check). "
                    "Optional: without it, export is manifest-only.")
    ap.add_argument("--out-dir", default="",
                    help="output dir (default: next to --video, else next "
                    "to --manifest)")
    ap.add_argument("--title", default="",
                    help="sequence title (default: video filename stem)")
    args = ap.parse_args(argv)

    if not os.path.exists(args.manifest):
        return fail(f"manifest not found: {args.manifest}")
    try:
        with open(args.manifest, "r", encoding="utf-8-sig") as f:
            manifest = json.load(f)
    except (OSError, ValueError) as e:
        return fail(f"could not read manifest {args.manifest}: {e}")
    try:
        spans, fps = shot_spans(manifest)
    except ValueError as e:
        return fail(str(e))
    scenes = manifest["scenes"]
    computed_total = spans[-1][1]

    video_path = args.video
    if video_path and not os.path.exists(video_path):
        return fail(f"video not found: {video_path}")
    stem = (os.path.splitext(os.path.basename(video_path))[0]
            if video_path else
            os.path.splitext(os.path.basename(args.manifest))[0])
    title = args.title or stem
    out_dir = args.out_dir or (
        os.path.dirname(os.path.abspath(video_path)) if video_path
        else os.path.dirname(os.path.abspath(args.manifest)))
    os.makedirs(out_dir, exist_ok=True)

    warnings = list(manifest.get("warnings") or [])
    tail_frames = 0
    total_frames = computed_total
    if video_path:
        probed = probe_rendered_frames(video_path, fps)
        if probed is None:
            warnings.append(
                "ffprobe unavailable — export is manifest-only; no tail "
                "check against the rendered file."
            )
        elif probed > computed_total:
            tail_frames = probed - computed_total
            total_frames = probed
            tail_note = (
                f"Rendered video is {tail_frames} frames longer than "
                f"the shot sum — appended a TAIL event (blank)."
            )
            if manifest.get("style") == "x":
                tail_note += (" X style: known Root.tsx buffer mismatch "
                              "(see CONSOLIDATION.md).")
            warnings.append(tail_note)
        elif probed < computed_total:
            warnings.append(
                f"Rendered video is {computed_total - probed} frames "
                f"SHORTER than the manifest shot sum — the manifest may "
                "be stale (rebuilt after the render?). Export still uses "
                "the manifest; re-render to be safe."
            )

    edl_path = os.path.join(out_dir, stem + ".edl")
    fcpxml_path = os.path.join(out_dir, stem + ".fcpxml")
    edl = build_edl(title, reel_name(stem), spans, scenes, fps,
                     tail_frames, warnings)
    with open(edl_path, "w", encoding="utf-8") as f:
        f.write(edl)
    audio_rate = probe_audio_rate(video_path) if video_path else 48000
    fcpxml = build_fcpxml(title, video_path, spans, scenes, fps,
                          tail_frames, total_frames, audio_rate)
    with open(fcpxml_path, "w", encoding="utf-8") as f:
        f.write(fcpxml)

    n_events = len(scenes) + (1 if tail_frames > 0 else 0)
    print(f"[export_timeline] {len(scenes)} shots"
          + (f" + {tail_frames}f tail" if tail_frames else "")
          + f" -> {n_events} events, {total_frames} frames "
          f"({total_frames / fps:.2f}s @ {fps}fps)")
    print(f"[export_timeline] EDL -> {edl_path}")
    print(f"[export_timeline] FCPXML -> {fcpxml_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
