# video tools — v4 (multi-style, INTERNAL production tool)

"video tools" is an INTERNAL production tool for Minh's own channel — NOT a
product for non-tech customers. It creates videos in MANY styles
(Fireship is style #1). A style = composition + grammar + caption rules
+ default voice. New styles plug in as templates (see "How to add a
style" below).

Data-driven Remotion compositions + props builder + render script + GUI.

## v4 — what changed (2026-10-17)

1. **Multi-style architecture.** Manifest gains `style` (fireship | news
   | x). Fireship style = the v3 Fireship grammar (3 template frames:
   explainer/listicle/news) + collage `mediaList`. News style = ONE
   composition (`NewsStyle`) rendering 7 news layouts per scene (see
   below). X style = ONE composition (`XStyle`) rendering the Short
   #8/#9 grammar. Render picks the composition from `manifest.style`
   first, then `manifest.template`.
2. **News style (style #2, Facebook).** Layout grammar ADAPTED from the
   auto-video-gen template set (hook / stat-hero / comparison / callout /
   feature-list / outro) — re-implemented in Remotion. Brand is
   BRONZE BASE (never the source repo's brand). Every layout takes the
   media slot (image/chart/footage/screenshot/avatar) — the fix for the
   news style's known weakness (text-heavy / monotonous). News scenes
   are layout CARDS: never split (splitting breaks the layout). The
   news frame gains an `action` beat (dùng được ngay) + a verdict
   outro (see below).
3. **X style (style #3, X).** The Short #8/#9 grammar ported to the
   tool's engine (Remotion, NOT the PIL frame pipeline): pixel font
   (VT323), GIF fullscreen (cover, pops in last 2s) or fit (contain
   below caption, no crop), 100% hard cuts, ~30s, caption-only
   (silence backend) + quote punchline end card (FICTIONAL QUOTE tag)
   + `ship it.` signature + cross-link. One script line = one shot.
4. **VOICE — FREE ONLY (Minh locked 17/10 tối: ElevenLabs is OUT,
   even paid).** ElevenLabs integration was built, then REMOVED —
   `voice/elevenlabs.py`, config, usage ledger, GUI fields, and CLI
   flags are all deleted. Backends: `sapi` (draft default), `silence`
   (caption-only, X style), `mock` (Linux test only), external WAV +
   timings (recorded voice / Edge TTS output — Edge TTS feeds in here;
   the tool has NO native Edge TTS backend).
5. **"ship it" system (Minh locked 17/10 tối).** Slogan `ship it` on
   EVERY video: YouTube = `$ ship_it;` code outro (Phase 1); Facebook
   = verdict card `Ship it / Skip it / Scam it` + slogan; X = `ship
   it.` punchline line. Every video ends with a CROSS-LINK end card
   (outro text, not caption links): FB → "Full breakdown on YouTube,
   roast version on X." / YT → "Vietnamese version on Facebook, roast
   on X." / X → "Full version on YouTube, Vietnamese on Facebook."
   FB script template gains a final `action` shot (dùng được ngay — 1
   concrete thing the viewer can use TODAY).
6. **X fast path + media pool.** Hot news → X clip in 1–2h: the X
   style renders fast (caption-only, no voice synthesis), and
   shot-list media can be `"pool:<tag>"` (e.g. `pool:facepalm`) — the
   builder copies ONLY the used files from `media-pool/` (seed: 8
   reaction clips converted from the Short #8/#9 GIFs, 0.4 MB total)
   into `public/media-pool/`, so a hot-news X clip never stalls on
   GIF hunting. Measured X render time: see "Known limitations".
7. **Free/cloud OK.** The tool may use cloud APIs + forked repos;
   local-only is NO LONGER required. The tool itself costs $0.
8. **GUI:** style picker (Fireship / News / X), voice backend picker
   (SAPI / Silence / External WAV), media-pool hint on the shot-list
   row. Window title is now "video tools (internal)". Output folder
   is now `Desktop/Video Tools`.

## News style — 7 layouts (Facebook)

| Layout | Grammar | layoutData fields |
|---|---|---|
| breaking-news | BREAKING pill + huge headline (+ subhead) over media bg or navy gradient | `subhead` |
| stat-callout | Giant cyan value + label + context + optional chart panel | `value`, `label`, `context` |
| split-screen | Two cards (cyan / purple) + VS + optional WINNER badge | `left: {label, value, color?, winner?}`, `right: {...}` |
| quote-card | Tag pill + statement in a card + optional avatar | `tag`, `statement` |
| listicle | Title + rule + staggered bullets + optional top image band | `title`, `bullets: [...]` |
| big-number | Like stat-callout, value even bigger (210px) + chart panel | `value`, `label`, `context` |
| action-card | Green `DÙNG ĐƯỢC NGAY` chip + big action text + media (ideally a screenshot of the tool/prompt) | (uses scene text / bigCaption) |
| outro | Verdict card + `ship it` slogan + CTA + channel name + source + BRONZE BASE follow card + cross-link | `ctaTop`, `source`, `verdict: ship \| skip \| scam` (default `ship`) |

The shot list sets `layout` + `layoutData` per scene. Without them, the
layout defaults by role: headline → breaking-news, event →
stat-callout, why → quote-card, action → action-card, source →
quote-card (tag SOURCE), outro → outro. The outro is a PURE end card
(verdict + `ship it` + CTA + follow + cross-link) — it consumes NO
script sentence (fixed 4.0s silent card), so the last content sentence
always belongs to the action beat. News scenes are layout cards
and are NEVER split (the Fireship pacing split applies to fireship
style only). Every layout except outro shows the plain bottom
subtitle. A news content scene with NO media gets a WARNING (FB news
style needs a visual per shot).

## X style (Short #8/#9 grammar)

Ported to the tool's engine (Remotion) — same GRAMMAR as the PIL frame
pipeline, different renderer. Do NOT copy the PIL pipeline.

| Rule | X style |
|---|---|
| Canvas | 1080x1920 @ 30fps, `#0a0a0a` bg, 100% hard cuts |
| Shots | 1 script line = 1 shot, ~3–6s each, total ~30s (8 shots) |
| Caption | VT323 pixel font, big (130px, shrinks to fit), per-line color (WHITE / RED / ORANGE / YELLOW / GREEN / GRAY / DARKGRAY or hex), thick black outline. TOP (y=250) when media present, CENTERED when text-only, ON TOP of fullscreen media |
| Media | `fullscreen` = cover, caption on top, appears in the LAST 2s of the shot. `fit` = contain below caption, no crop, from frame 0. `corner` → treated as `fit`. GIFs: convert to MP4 for motion (a raw GIF renders as a static first frame) |
| Deadpan | Single-word shots are just a 1-line `lines` entry (e.g. `Again.`) |
| End card | Outro shot's `lines` ARE the quote + `FICTIONAL QUOTE` tag (the quote is invented — never presented as real) + `ship it.` line + cross-link |
| Audio | Caption-only: NO subtitle (the big captions ARE the content). Audio element carries the silence WAV (or a voice WAV if a voice backend was used) |
| Durations | `--voice-backend silence`: per-shot `durationSec` from the shot list, else 3.0s. Voice backends set durations from voice |

Shot-list fields for X: `lines: [{text, color}]` (wins over
`bigCaption`), `durationSec`, `media` (+ `mediaPosition`:
`fullscreen` | `fit`), `media: "pool:<tag>"` for pool GIFs.

## Voice — FREE ONLY (Minh locked 17/10 tối)

ElevenLabs is OUT — even paid. The ElevenLabs integration (module,
config, usage ledger, GUI fields, CLI flags) was built in Phase 2 and
then REMOVED. Do not re-add it without Minh explicitly reversing the
lock.

| Backend | What |
|---|---|
| `sapi` (default) | PowerShell 5.1 System.Speech. Zero-config draft. Flat — real delivery enters via the external slot |
| `silence` | Caption-only. Duration per scene = shot-list `durationSec`, else 3.0s. No audio |
| `mock` (explicit flag only) | Soft sine-tone WAV + even-split timings (Linux testing). Manifest records `voice="mock …"` + WARNING — never a real-voice render |
| external (`--voice-wav` + `--voice-timings`) | ONE recorded WAV (Minh's voice, Edge TTS output, …) + timings JSON, one `{start, end}` per script line. Builder slices the WAV per scene. External wins over `--voice-backend`. Edge TTS feeds in here (generate the WAV elsewhere, pass it in) — the tool has NO native Edge TTS backend |

## How to add a style

1. New composition in `src/sivo/` (e.g. `MyStyle.tsx`) — shell:
   `AbsoluteFill` + `SivoBrand` OUTSIDE `Series` + hard cuts only.
2. Register it in `src/Root.tsx` (Composition id + defaultProps).
3. Add the composition id to `scripts/render.mjs` (pick by
   `manifest.style`, fall back to Explainer with a WARNING).
4. Add the style id to `STYLES` in `build_props.py` + a manifest
   `style` value + scene fields if the style needs new ones
   (`src/sivo/types.ts`).
5. Add a GUI radio button (`gui.py`, style picker) + a
   `STYLE_DESCRIPTIONS` entry.
6. Add a README row (this section) + a test render. New style only
   ships when Minh approves it (style library rule).

1. **Karaoke REMOVED.** Subtitle is now plain white (one color per scene;
   yellow allowed for a whole joke/punchline scene) — words never change
   color individually. No keyword highlighting.
2. **Media slot per shot.** Each scene accepts `media` (video or image,
   fullscreen or corner) + `mediaSource` attribution (metadata, not
   rendered — sources go in the video description, Long #4 style).
   The old `meme` field is gone; memes now flow through the media slot.
3. **Shot list.** `--shot-list shotlist.json` sets per-shot big captions,
   colors, media, subtitle color, effect. Format mirrors Long #4's shot
   list (scene | big caption | GIF+position | visual+source | effect);
   time/dialogue come from the script + voice. Example:
   `shotlist-compound.json`. "scene" is 1-based over PRE-SPLIT scenes.
4. **Voice slot.** `--voice-wav FILE --voice-timings FILE` accepts one
   recorded WAV (Minh's voice, Edge TTS, ...) + a timings JSON with one
   `{start, end}` per script line. The builder slices the WAV per scene.
   External voice wins over `--voice-backend`. SAPI stays as the
   zero-effort draft default (flat — real delivery enters via this slot).
5. **Fireship pacing.** `--max-shot-sec` (default 4.0): scenes longer than
   the max are split into sub-shots at word boundaries. First sub-shot
   keeps the scene's bigCaption/media; later ones get auto captions.
   `--max-shot-sec 0` disables splitting.
6. **No role labels on screen.** Scenes show the big caption (+ media),
   not "HOOK"/"THE PROBLEM" tags (Long #4 style).
7. **GUI:** brand defaults to `BRONZE BASE`; new pickers for shot list
   JSON + voice WAV + voice timings.
8. **SAC / installer are FROZEN.** SAC is no longer a constraint (Minh's
   own machine, SAC off). The Phase 3 installer is legacy — do not
   rebuild it for this tool. See `installer/` (kept for reference).

## Run it

### GUI (internal path — Windows)

```bash
pythonw gui.py
# Paste script (1 sentence/line) -> pick style (Fireship / News / X) ->
# template -> brand -> shot list (optional) -> voice (SAPI draft /
# Silence caption-only / external WAV + timings) -> Render -> Open video.
# Output: Desktop/Video Tools/<timestamp>/sivo.mp4 + sivo.mp4.warnings.json
```

### Command line (dev / Linux, mock voice — proves the pipeline, NOT the voice)

```bash
# 1. Build the manifest from a script (1 sentence/line) + shot list
python3 build_props.py samples/compound-interest.txt \
    --out out/v3-manifest.json --public-dir public \
    --brand "BRONZE BASE" --voice-backend mock --template explainer \
    --shot-list shotlist-compound.json

# 2. Render
node scripts/render.mjs --manifest out/v3-manifest.json --out out/v3-fireship-test.mp4
# -> out/v3-fireship-test.mp4 + out/v3-fireship-test.mp4.warnings.json
```

On Windows (real voice — SAPI is the default):
```bash
python build_props.py script.txt --out manifest.json --public-dir public --brand "BRONZE BASE"
# --voice-backend sapi is the default; --rate 2 matches old SAPI behaviour
```

With a recorded voice (Minh's voice / Edge TTS):
```bash
python build_props.py script.txt --out manifest.json --public-dir public \
    --voice-wav voice.wav --voice-timings timings.json
# timings.json: [{"start": 0.0, "end": 3.2}, ...] — one per script line.
# The WAV must be PCM (export MP3/m4a recordings to WAV first).

X clip, fast path (hot news -> X clip in 1-2h):
```bash
# Script: 1 line = 1 shot. Shot list: lines + durationSec + pool media.
python build_props.py x-script.txt --out manifest.json --public-dir public \
    --brand "BRONZE BASE" --style x --voice-backend silence \
    --shot-list x-shotlist.json
node scripts/render.mjs --manifest manifest.json --out x-clip.mp4
# Shot-list media "pool:<tag>" pulls from media-pool/pool.json
# (e.g. "pool:facepalm") — no GIF hunting for hot-news clips.
```

## Templates (deterministic mapping, no LLM)

| Template | Frame | Media |
|---|---|---|
| Explainer (default) | Hook → Pain → Solution → Workflow → Benefits → Outro (6 slots; long scripts merge middle sentences into the 4 middle slots) | Shot list per scene; `--meme-on` assigns `memes/pain-01.mp4` to Pain when the shot list sets no media |
| Listicle | Hook ("N ITEMS") → numbered items (max 7, overflow merges) → Outro | Shot list per scene |
| News | Headline card → events → Why-it-matters → Action (dùng được ngay, last middle beat when ≥2 middle sentences) → Source (only if a line starts with `Source:` / `Nguồn:`) → Outro (verdict + ship it + cross-link) | Shot list per scene (layout + layoutData + verdict) |
| X | 1 line = 1 shot. First = hook, last = outro (quote punchline), middle = item. No merging, no split | Shot list per shot (lines + durationSec + media/pool) |

Script too short/long → WARNING + fewer/merged scenes. A sentence is NEVER
silently dropped. Meme on + non-Explainer template → WARNING + ignored.

## Files

| Path | What |
|---|---|
| `src/sivo/types.ts` | Zod schema for the manifest (style, scenes, brand, voice, warnings, template, media, bigCaption, layout, layoutData) |
| `src/sivo/SivoExplainer.tsx` | Fireship composition: brand badge + Series of generic scenes (hard cuts) |
| `src/sivo/SivoListicle.tsx` | Fireship composition: Hook + numbered items + Outro |
| `src/sivo/SivoNews.tsx` | Fireship composition: Headline card + events + why + source + Outro |
| `src/sivo/NewsStyle.tsx` | **News style** composition: 7 news layouts + verdict outro + cross-link |
| `src/sivo/XStyle.tsx` | **X style** composition: Short #8/#9 grammar (VT323, GIF fullscreen/fit, hard cuts, quote end card, ship it, cross-link) |
| `media-pool/` | Reusable media pool: `pool.json` (tag -> file) + `files/` (8 seed reaction MP4s, 0.4 MB). Shot-list `pool:<tag>` refs resolve + copy here |
| `src/sivo/GenericScene.tsx` | One shot: big static caption (+ optional media / collage `mediaList`) + plain subtitle + audio + outro cross-link |
| `src/sivo/ListicleScene.tsx` | Listicle item: BIG number + big caption + subtitle |
| `src/sivo/NewsScene.tsx` | News headline card / event (big number) / why / source scenes |
| `src/sivo/components.tsx` | PopIn, SivoSubtitle (plain, fixed position), SivoBrand, MediaShot, role colors |
| `src/Root.tsx` | Registers all 5 compositions (Explainer, Listicle, News, NewsStyle, XStyle); `calculateMetadata` derives total duration from manifest |
| `build_props.py` | Script -> style/template mapping (merge when long) -> voice WAVs -> shot list merge -> Fireship split -> manifest JSON |
| `gui.py` | Internal GUI (tkinter, stdlib): style + script + template + brand + meme + shot list + voice (SAPI / Silence / external) + Render -> Open video |
| `shotlist-compound.json` | Example shot list for `samples/compound-interest.txt` (Wikimedia media) |
| `voice/sapi_tts.ps1` | Real SAPI path (PowerShell 5.1) |
| `scripts/render.mjs` | bundle() + renderMedia() + loudnorm to -16 LUFS + warnings JSON; composition picked from manifest.style, then manifest.template |
| `scripts/make_memes.py` | Generates the 10 license-clean meme MP4s (PIL + ffmpeg, original artwork) |
| `scripts/patch-renderer-sandbox-only.mjs` | SANDBOX-ONLY port-scan patch. DO NOT SHIP in the installer |
| `public/memes/` | 10 meme MP4s (2s loops) — see `MEMES.md` for the license record |
| `public/media/` | Real photos for the media slot (Wikimedia Commons, CC0 / Public domain) — see `public/media/SOURCES.json` |
| `MEMES.md` | Per-meme license/source record (all original, no restrictions) |
| `samples/compound-interest.txt` | 9-line generic explainer sample (NOT Docker content) |
| `out/` | v3 test render: `v3-fireship-test.mp4` + warnings JSON + `v3-manifest.json` |
| `MEASUREMENTS.md` | Real sizes + render times + loudness (Phase 1 numbers, no estimates) |

## Design decisions (v3)

1. **Brand badge**: `SivoBrand` renders the `brand` prop as small white
   text at the top, OUTSIDE `Series` so it persists across the whole
   video without re-animating. Empty brand renders NOTHING. For Minh's
   own channel the brand is `BRONZE BASE` (GUI default).
2. **Shots, not scenes**: a scene is split into ≤4s sub-shots at word
   boundaries (Fireship pacing). Hard cuts come from `Series` between
   shots.
3. **Subtitle**: chunk-based (6 words), time-split within the shot, ONE
   plain color per scene — the method proven in the Docker test, minus
   the keyword highlight. Word timings are used by build_props for
   splitting, never for per-word colors.
4. **Big caption** (Fireship layer 2): shot list `bigCaption` wins;
   fallback = auto headline (first ≤ 4 words, UPPERCASE; News headline
   card uses the full first sentence, truncated to 80 chars). Pop-in
   once (4-6 frames), then STATIC.
5. **Media slot**: shot list `media` (video loops, image covers). Fullscreen
   = cover + caption overlaid; corner = bottom-right card (border +
   shadow) + centered caption. `mediaSource` is metadata for the video
   description, never rendered on screen. Animated GIFs render as a
   static first frame — convert GIFs to MP4 for motion.
6. **Voice**: SAPI is the draft default (PowerShell 5.1). `--voice-backend
   mock` is explicit-only and always writes a WARNING. External WAV +
   timings is the real-delivery path (Minh's voice / Edge TTS). The
   builder NEVER silently falls back to mock.
7. **No-lying**: every fallback lands in `manifest.warnings` + `<out>.warnings.json`.
8. **Render path**: `bundle()` + `renderMedia()` APIs, never the CLI.
   `scripts/patch-renderer-sandbox-only.mjs` is VM-only scaffolding (this VM's
   network stack lies about 0.0.0.0 ports); real Windows machines don't need it.
10. **Cross-link end cards**: the builder sets `crossLink` on the
    outro scene per style (YT / FB / X text — see v4 changelog §5).
    Rendered by GenericScene / NewsStyle Outro / XStyle outro. The
    Fireship split carries `crossLink` to the first sub-shot.
11. **"ship it"**: YT `$ ship_it;` (GenericScene outro), FB verdict
    card + slogan (NewsStyle Outro, `layoutData.verdict`), X `ship
    it.` line (XStyle outro). The slogan is automatic — no script
    change needed.
12. **FB action beat**: the news frame's last middle slot is `action`
    (dùng được ngay) when there are ≥2 middle sentences. The shot
    list can set `layout: "action-card"` explicitly on any scene.
13. **Media pool**: `media-pool/pool.json` + `files/`. `pool:<tag>`
    in any shot-list media entry resolves (first tag match) and the
    builder copies ONLY the used file into `public/media-pool/`.
    Unknown tag → WARNING + media ignored (never a silent wrong clip).
14. **Fireship collage**: shot-list `mediaList` (2–4 media) renders a
    grid (2 = side-by-side, 3 = 1 big + 2 stacked, 4 = 2×2) + big
    caption overlaid. Wins over single `media`. Fireship style only.
15. **GUI**: tkinter stdlib only. Render runs in a background thread;
   progress is plain language; errors are plain language + details to the
   warnings file, never a stack trace. Subprocess consoles hidden on
   Windows (`CREATE_NO_WINDOW` / `windowsHide`); launch the GUI with
   `pythonw gui.py` so no console shows at all.

## Timeline export (EDL + FCPXML) — added in consolidation Phase 1 (18/10)

Export a manifest to an editable timeline for Premiere / DaVinci /
Final Cut — each manifest scene becomes one cut event/clip referencing
the RENDERED MP4 (flattened cut list: source in/out == record in/out),
with scene id, role, caption, and media source as comments (EDL) /
markers (FCPXML).

CLI:
  python export_timeline.py --manifest out/manifest.json --video out/video.mp4
  # -> out/video.edl + out/video.fcpxml (next to the video)
  python export_timeline.py --manifest out/manifest.json   # manifest-only

GUI: Render → "Export timeline (EDL + FCPXML)" → two files saved next
to the video.

Timing: the manifest is the frame-accurate source (raw shot-list JSON
has no durations, so it cannot be exported). X style shots use raw
`durationInFrames`; every other style adds +3 per shot (+10 last) —
the buffer inside each `Series.Sequence`. When `--video` is given, the
exporter probes the rendered video's frame count and appends a TAIL
event if the render is longer than the shot sum (X style: known
Root.tsx buffer mismatch — see CONSOLIDATION.md). Full consolidation
plan: CONSOLIDATION.md.

## Known limitations (v4)

- ElevenLabs is OUT (Minh locked 17/10: free voices only, even paid
  tiers). The integration was removed — do not re-add it without Minh
  explicitly reversing the lock.
- Mock voice on Linux (sine tone) — SAPI on real Windows VERIFIED earlier
  (6 WAVs, clear, usable); SAPI is flat, so real delivery needs the
  external voice slot (Minh's recorded voice).
- No music/SFX in the composition yet (Fireship §8 requires synthwave
  -20dB + SFX) — the v3 test render has voice only. Music is the next
  gap to close.
- Single-pass loudnorm hits -16 LUFS integrated but TP is -15.18 dB, not -1.5
  (no clipping; strict TP is a later decision).
- Animated GIFs render static (no @remotion/gif) — convert to MP4.
- Default font is the system sans-serif (bold) — no blocky display font
  bundled yet.
- The money-stack test photo (1848 banknote engraving) reads as a history
  document, not "money" — replace with modern banknotes/coins for real
  videos. Media choice per shot list is Minh's call.
- SAC / installer FROZEN (Phase 3 installer is legacy; SAC is off on
  Minh's machine and no longer a constraint for this internal tool).
- Render time on Minh's machine UNTESTED for v3 (4.1–4.4× realtime on
  this VM for the old pipeline; v3 test took ~5 min for 60s on this VM).
- X-style test render (`out/v5-x-test.mp4`, 30.0s): MEASURED —
  191s total on this VM (bundle 5.7s + render 173s + loudnorm 3.3s;
  wall 3m12s). Build_props (manifest) adds ~1s. End-to-end, a hot-news
  X clip is ~4 minutes of machine time + script/shot-list writing —
  well inside the 1–2h hot-news window. Loudness reads -inf (pure
  silence — caption-only, expected, not an error).
- X-style eye-check (v5 test): VT323 loads, per-line colors, fullscreen
  GIF last-2s pop-in, fit GIF below caption, deadpan single-word shot,
  outro quote + FICTIONAL QUOTE + `ship it.` + cross-link all render.
  Known collision: the seed `micdrop` pool GIF has baked-in "Owned."
  text that overlaps the quote's 2nd line on fullscreen outro shots
  (same collision the original PIL pipeline would produce). Guidance:
  prefer pool GIFs WITHOUT baked-in text for fullscreen slots; fit
  slots are safe (caption sits above the GIF, never on top).
- DARKGRAY caption segments (Short #9 grammar, e.g. "noticed.") are
  dim by design — readable but muted, the deadpan effect.

## Rename note (2026-10-17)

The old name SIVO is DELETED. The tool is now called "video tools".
Directory / code identifiers (`sivo-remotion/`, `src/sivo/`, `Sivo*`
components, `sivo-remotion-v3-fireship` manifest version) were NOT
renamed — renaming them would break paths for zero user benefit. Only
user-facing naming (this README, the final report, future GUI/docs
labels) uses "video tools". The GUI window title is now
"video tools (internal)" (fixed in v4).

---
Built by [Bronze Base](https://cleantake.bronzebasehq.workers.dev/) for the Bronze Base channel. Writing: [Bronze Base blog](https://cleantake.bronzebasehq.workers.dev/blog/).
