# SIVO-Remotion Phase 1 — MEASUREMENTS (real numbers, no estimates)

Measured 2026-10-17 on this Linux VM (the build machine). Method: `du -sh`
for sizes; wall-clock timing from `scripts/render.mjs` output.
Anything marked ESTIMATE is explicitly not measured — do not quote it as fact.

## 1. Component sizes (what the installer would ship)

| Component | Measured | Notes |
|---|---|---|
| `node_modules` (fresh `npm ci`, 430 packages) | **271 MB** | Remotion 4.0.407 + React 19 + deps |
| `node_modules/.cache` (webpack build cache, created during bundle) | 74 MB | Regenerable — does NOT ship in the installer |
| `node_modules` after builds (incl. cache) | 344 MB | = 271 + 74 cache |
| Chrome for Testing 141 (full `chrome-linux64/` dir) | **363 MB** | Bigger than the plan's 150–180 MB estimate. Minimal headless set (headless_shell + libs only) NOT yet measured — Phase 3 must measure it; if the full 363 MB ships, the bundle grows accordingly |
| Python 3.12 stdlib (`/usr/lib/python3.12/`) | 55 MB | System install on this VM, not an installer bundle. Installer Python runtime size TBD in Phase 3 |
| ffmpeg binary (system, dynamically linked) | 465 KB + 355 MB shared libav* libs | System build. Installer uses a STATIC ffmpeg build (~30 MB, ESTIMATE from plan — not measured here) |
| Webpack bundle output (`/tmp/remotion-webpack-bundle-*`) | 14 MB | Built at render time; pre-bundling is a Phase 3 optimization |
| `public/audio/` (9 mock WAVs + default silence) | 2.6 MB | Mock voice only; real SAPI WAVs will be similar size |

### Installer total — REVISED

Plan estimated 450–700 MB. With measured numbers:
271 (node_modules) + 363 (Chrome full) + ~55–90 (Python) + ~30 (ffmpeg static, ESTIMATE) + ~20 (bundle + app + memes) = **~740–775 MB**.
The plan's estimate was low mainly on Chrome (363 measured vs 150–180 estimated).
If Phase 3 trims Chrome to a minimal headless set, the total falls. Do NOT
quote 450–700 MB any more — the measured floor is ~740 MB with full Chrome.

## 2. Render time — 59.1 s video, 1774 frames @ 30fps, concurrency 1

| Run | Bundle | Render | Loudnorm | Total | Render ÷ video length |
|---|---|---|---|---|---|
| `poc-brand` (brand "ACME LAB") | 21.2 s (cold) | 239.6 s | 6.8 s | **287.5 s** | 4.1× |
| `poc-nobrand` (brand "") | 4.5 s (warm cache) | 259.4 s | 4.5 s | **274.7 s** | 4.4× |

Render ≈ **4.1–4.4× realtime** on this VM. This VM's speed is NOT Minh's
machine speed — customer-facing render time MUST be measured on Minh's
Windows machine (Phase 1 checkpoint item). Expect slower on a mid-range
laptop; concurrency > 1 may help (not tested here).

## 3. Output files

| File | Duration | Format | Size |
|---|---|---|---|
| `out/poc-brand.mp4` | 59.2 s | h264 1080×1920 @30fps + AAC | 4,029,601 bytes |
| `out/poc-nobrand.mp4` | 59.2 s | h264 1080×1920 @30fps + AAC | 3,989,276 bytes |

## 4. Loudness (measured with `ffmpeg -af loudnorm=print_format=json`)

| File | Integrated (I) | True Peak (TP) | LRA |
|---|---|---|---|
| `poc-brand.mp4` | **-16.05 LUFS** (target -16 ✓) | -15.18 dB | 0.20 |
| `poc-nobrand.mp4` | **-16.05 LUFS** (target -16 ✓) | -15.18 dB | 0.20 |

Notes:
- Integrated loudness hits the -16 LUFS target.
- True Peak -15.18 dB is NOT the -1.5 dB broadcast-style headroom the
  loudnorm filter was asked for. Single-pass loudnorm does not guarantee TP.
  There is NO clipping (TP < 0 dBFS), so the file is safe for YouTube/Shorts.
  If strict -1.5 dB TP is required later, use two-pass loudnorm or a limiter
  — a Phase 3 decision, not a Phase 1 fix.
- LRA 0.20 is meaningless here (mock voice = constant sine tone).

## 5. License verdict (verified 17/10, parent agent, official LICENSE.md)

Remotion Free License covers: individuals; for-profit orgs up to 3 employees;
non-profits; evaluators not yet commercial — free even for commercial video
creation. Company License required only above 3 employees. Forbidden: selling/
relicensing Remotion itself. SIVO is an app that USES Remotion to create
videos (allowed), not a resale of Remotion (forbidden). Minh as an individual
qualifies for Free License, including when selling SIVO. Re-check at Remotion
5.0 (license changes) and when exceeding 3 employees. Full text in plan §6.

## 6. What these numbers do NOT prove (still open)

- SAPI voice on real Windows (mock voice used here — pipeline only).
- Render time / bundle size on Minh's mid-range Windows machine.
- SAC behaviour for the Node + Chrome stack (UNVERIFIED — biggest risk).
- Whether the minimal Chrome headless set is smaller than 363 MB.
- Installer total on Windows (Python + Node + static ffmpeg bundling).
