# Media pool

Reusable GIFs / clips for video tools — so a hot-news X clip doesn't
stall on GIF hunting (the X fast path).

## Use

In a shot list, set a scene's media to `"pool:<tag>"`:

```json
{"scene": 3, "media": "pool:facepalm", "mediaPosition": "fullscreen"}
```

Tag or name, case-insensitive, first match wins (see `pool.json`).
The builder copies ONLY the used files into `public/media-pool/` at
build time, so the Remotion bundle stays small.

## Grow the pool

1. Drop a file (MP4 for motion, JPG/PNG for stills) in `files/`.
2. Add an entry to `pool.json`: `{"name": "...", "file": "files/....",
   "tags": ["...", ...]}`.
3. Prefer short clips (1–6s). Clips play once per shot; if a shot
   outlasts the clip, the last frame holds.
4. Prefer GIFs WITHOUT baked-in text for fullscreen slots — the
   caption sits ON TOP of fullscreen media, so baked-in text collides
   with it (seen in the v5 X test: micdrop's "Owned." vs the quote).
   Fit slots are safe (caption sits above the GIF).

## Seed entries

Converted from the GIFs used in Short #8 / Short #9 (Tenor), 480px /
12fps MP4. Total pool: ~0.4 MB.
