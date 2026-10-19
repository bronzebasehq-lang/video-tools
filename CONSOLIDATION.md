# Consolidation Plan — video tools (Phase 1 of consolidation, 18/10)

Minh locked 18/10: tool videos = TOP PRIORITY. FB video + X video are
PAUSED — the tool now serves YOUTUBE video only (Shorts + Long).
Permission: use everything, copy all repos, to complete/improve the
tool. This file is the consolidation plan: what to fold in, in what
order, what to skip and why. Consolidation = ONE pipeline, no
duplication — not a new product.

## Done in this phase (18/10)

**Timeline export** — `export_timeline.py` + GUI button "Export timeline
(EDL + FCPXML)". Exports a build_props manifest (the frame-accurate
source of truth) to:
- CMX 3600 EDL (`.edl`) — Premiere / DaVinci / Resolve import.
- FCPXML 1.11 (`.fcpxml`) — Final Cut Pro import.

Each manifest scene = one cut event/clip referencing the RENDERED MP4
(flattened cut list: source in/out == record in/out), so the editor
opens the finished video as trimmable clips — one per shot — with the
scene id, role, caption, and media source as comments (EDL) / markers
(FCPXML). Verified frame-accurate against ffprobe video `nb_frames` on
two real renders (see "Verification").

## Timing rule (the exporter + any future timeline work must match)

- X style: shot = `durationInFrames` (XStyle uses raw durations).
- Every other style: shot = `durationInFrames + 3` (+10 on the last
  shot) — the buffer inside each `Series.Sequence` (SivoExplainer,
  SivoListicle, SivoNews, NewsStyle). Root.tsx `durationFromProps`
  uses the same rule, so manifest total == rendered total for these
  styles.

## Root-cause findings from this audit (not yet fixed)

1. **X ~1s blank tail — ROOT CAUSE FOUND.** Root.tsx
   `durationFromProps` adds the +3/+10 buffer to EVERY composition,
   but XStyle sequences use raw `durationInFrames`. The X render is
   therefore ~31 frames (~1.03s) longer than the shot sum, and the tail
   is blank (background + badge only). Verified: x-1810-v3 manifest
   shot sum = 870f, rendered video = 901f (870 + 31). Fix: make
   `durationFromProps` composition-aware (X: no buffer) OR add the
   buffer to XStyle sequences. One-line-ish change; must re-verify
   with a test render + eye-check before shipping.
2. **Pool clips do NOT loop.** Media renders via `OffthreadVideo`
   with no loop (GenericScene, XStyle). A pool clip shorter than its
   shot holds its last frame. Fix options: (a) pre-loop the clip with
   ffmpeg at build time when the pool clip is shorter than the shot
   (robust, no composition change); (b) render with a cycling `start`
   offset in the composition. Prefer (a) — build-time, testable.
3. **Container duration lies.** ffprobe FORMAT duration follows the
   longer audio track (the loudnorm pass leaves audio ~0.13s longer
   than video). Always use the VIDEO stream `nb_frames` for
   frame counts. The exporter does this (an earlier version used
   format duration and invented a phantom 4-frame tail on FB v2 —
   caught by verification).

## Consolidation order (what to fold in, in what order)

### 1. Timeline export — DONE (this phase)

### 2. Music + SFX for Fireship compositions — NEXT (biggest quality gap)
The tool has NO music/SFX in any composition yet (Fireship formula
§8/§17 REQUIRES synthwave −20dB + SFX; "never ship a video without
music unless declared"). The PIL Short #8/#9 pipeline already proved
the pattern: `music_loop.wav` mixed at 0.25 + 1.5s fade-out (used for
X v3-music). Fold in:
- Manifest `music` field (music WAV + volume + fade) → applied in
  `render.mjs`'s ffmpeg pass (it already runs an ffmpeg loudnorm
  pass — add a music mix there, so no composition change).
- SFX: adopt auto-video-gen's 3-tier selector pattern (explicit
  override → keyword match → template default, deterministic hash so
  re-renders are idempotent). Do NOT copy its downloader source
  (myinstants.com scraping — licensing unclear). Source SFX from a
  license-clean library or record our own; `assets/sfx` in the
  auto-video-gen clone is EMPTY, so there is nothing to copy.

### 3. Media pool expansion — AFTER Short #10 ships
Pool has 8 entries (facepalm, brain, waiting, breakin, hacker,
searching, celebration, micdrop — from Short #8/#9 GIFs, 480px/12fps
MP4). Expand with Short #10's APPROVED GIFs (spy, chart, lightbulb,
comparison, shy + celebration reuse) — only after Short #10 ships, so
the pool never pulls an in-flight asset. Pool rules (18/10): NO emoji
icons (emoji faces, shrug/exploding-head emoji) — full scenes only;
no baked-in text that collides (exception: Minh likes "Owned." in the
outro); no watermarks. Also fix the pool-clip loop (finding #2).

### 4. auto-video-gen fold-in — MOSTLY ALREADY DONE, two pieces left
Its 6 News templates are ALREADY re-implemented in NewsStyle (7
layouts, brand BRONZE BASE, media slot per shot). Remaining:
- **Shot-list/script validation** (adopt its zod script-schema
  pattern): max lengths (headline 40, label 30–40, value 20, bullets
  ≤50 chars, statement ≤80) → hard warnings in build_props.py when a
  shot list exceeds them (today the builder only warns on missing
  media). Prevents unreadable overflow frames.
- **SFX selector pattern** (see §2).
SKIP: the HyperFrames HTML engine (different renderer, ~20x realtime
on this VM, Edge TTS dependency — Remotion is the renderer); a native
Edge TTS backend (Edge TTS keeps feeding via the external-WAV slot,
which works on Minh's Windows; the VM proxy breaks it — do not add a
backend that only works sometimes).

### 5. PIL Short #8/#9 fold-in — GRAMMAR DONE, two pieces left
X style already ports the grammar (pixel font, GIF fullscreen/fit,
hard cuts, deadpan, quote punchline). Remaining:
- **Music mixing** (see §2 — the PIL pipeline's music_loop.wav pattern).
- **GIF fit/fullscreen geometry**: PIL `load_gif_fit` (contain) /
  `load_gif_fullscreen` (cover crop) is already mirrored by XStyle
  `fit`/`fullscreen` positions — no further port needed.
SKIP: the PIL frame pipeline itself (prototype — Remotion is the
renderer; per-frame PNG + concat is slower and harder to edit).

### 6. X black-tail fix — from finding #1 (small, verify with a render)

### 7. Fireship collage eye-check — REMAINS
Collage (`mediaList` 2–4 grid + caption) is manifest-verified only,
never eye-checked. Render a collage test video + eye-check frames
before calling it done. (Fireship formula §6 wants denser
topic-related media for YT — collage is how the tool delivers that.)

## SKIP list (deliberate, do not re-add)

- HyperFrames engine (auto-video-gen) — different renderer, slow.
- PIL frame pipeline (Short #8/#9) — superseded by Remotion.
- Native Edge TTS backend — external-WAV slot already covers it.
- ElevenLabs — locked OUT 17/10 (even paid). Do not re-add.
- Mascot Bronze Base — banned 12/10.
- Cross-link end cards — REMOVED 18/10 ("tôi không cần móc nối nữa").
- Ollama / local LLM agent — dropped 18/10 (Minh: laptop can't run it).

## Verification (this phase)

- Exporter run on `out/fb-1810-v2-manifest.json` (news, 7 scenes) +
  `out/x-1810-v3-manifest.json` (X, 8 shots), each with its rendered
  MP4. Independent checker (`/tmp/tl-verify/check.py`, not shipped)
  parsed the EDL + FCPXML back and asserted: event/clip count ==
  shots (+1 tail iff rendered > shot sum), SRC==REC (flattened), no
  gaps/overlaps, last REC_OUT == ffprobe video `nb_frames`, FCPXML
  clip offsets/durations == manifest spans, markers present.
  Results: FB v2 — 7 shots, 0f tail, 1253f total, frame-accurate.
  X v3 — 8 shots + 31f tail (the Root.tsx mismatch), 901f total,
  frame-accurate. Manifest-only export (no --video) also verified.
- GUI smoke test (`xvfb-run gui.py --smoke-test`): UI built OK
  (includes the new Export timeline button).
- `python3 -m py_compile gui.py export_timeline.py`: clean.
- NOT verified: importing the EDL/FCPXML into Premiere/DaVinci/Final
  Cut (no NLE on this VM). The formats are standard CMX 3600 /
  FCPXML 1.11; Minh should import once on his machine to confirm.

## How to use timeline export

CLI:
  python export_timeline.py --manifest out/manifest.json --video out/video.mp4
  # -> out/video.edl + out/video.fcpxml (next to the video)
  python export_timeline.py --manifest out/manifest.json   # manifest-only

GUI: Render → "Export timeline (EDL + FCPXML)" → two files saved next
to the video. Import the .edl in Premiere/DaVinci, the .fcpxml in
Final Cut, then trim/reorder shots (each shot is one clip).
