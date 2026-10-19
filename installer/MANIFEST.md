# SIVO-Remotion — Phase 3 Installer Manifest

## Installer

| | |
|---|---|
| File | `build/SIVO-Setup.exe` |
| Size | **233,190,591 bytes (222.4 MB)** — REAL, measured |
| SHA256 | `0f667e78263c82c680dce4af948a531db2dfa05f6c05b3b32139bcf434f50925` |
| Type | PE32 GUI, Nullsoft Installer self-extracting archive (NSIS 3.09) |
| Compression | LZMA, non-solid, 16 MB dictionary — payload 739,803,266 bytes → datablock 740,133,625 bytes (diff = NSIS per-file overhead) → installer 233,190,591 bytes (31.4%) |
| Built | 2026-10-17 on Linux VM with makensis (NSIS 3.09) |

## Packaging choice + why

**NSIS** (not a self-extracting ZIP): a real installer with a folder screen,
progress, Finish page with "Run SIVO", Desktop + Start Menu shortcuts, an
uninstaller, and an Add/Remove Programs entry. A self-extracting archive
cannot do shortcuts/uninstaller cleanly. Built on Linux with makensis —
no Windows machine needed to build.

**Per-user install** (`%LOCALAPPDATA%\Programs\SIVO`, `RequestExecutionLevel user`):
no admin, no UAC prompt. Customer flow: double-click → folder screen →
Install → Finish → app opens.

## What the installer does (in order)

1. Extracts the payload to the install folder.
2. Runs Microsoft-signed `vc_redist.exe` silently (node.exe needs the Visual
   C++ runtime; exit 1638 = already installed, 3010 = restart needed —
   both treated as OK; any other code → warn and continue).
3. Runs the python.org installer silently into `<install>\python`
   (`InstallAllUsers=0`, `Include_tcltk=1` — tkinter is REQUIRED for the
   GUI; no pip/test/docs, no .py association, no Python Start Menu entries).
   Python install failure → STOP with a plain-language error (SIVO cannot
   run without Python).
4. Creates Desktop shortcut **SIVO** + Start Menu shortcuts (SIVO, Uninstall).
   Shortcuts run `pythonw.exe gui.py` — no console window, ever.
5. Writes the uninstaller + Add/Remove Programs entry (HKCU, per-user).

## Payload (inside the installer) — all REAL measured sizes

| Component | Version | Size | Notes |
|---|---|---|---|
| Chrome for Testing | headless-shell **141.0.7390.76** win64 | 253 MB | Minimal headless set (not full Chrome) |
| node_modules (Windows) | Remotion **4.0.407** + deps | 258 MB | `npm ci --os=win32 --cpu=x64 --ignore-scripts`; `@esbuild/win32-x64` + `@remotion/compositor-win32-x64-msvc` present; ZERO Linux platform packages |
| ffmpeg | gyan.dev essentials (`ffmpeg.exe` only) | 101 MB | Static build |
| Node.js | **22.23.3** LTS ("Jod") win x64 (`node.exe` only) | 83 MB | |
| Python installer | **3.12.10** amd64 `.exe` | 26 MB | Run once at install, then deleted (not shipped as runtime) |
| VC++ redistributable | `vc_redist.x64.exe` (Microsoft) | 25 MB | Run once at install, then deleted |
| App code (gui.py, build_props.py, voice, src, scripts/render.mjs, config) | — | ~1 MB | |
| Meme library (10 MP4s, SIVO-original, license-clean) | — | ~1 MB | See MEMES.md |
| **Payload total** | | **739,803,266 bytes (705.5 MiB)** | Verified: byte sum matches NSIS datablock |

## What the app does at runtime (installed)

- GUI (`pythonw gui.py`) → script → SAPI voice WAVs (real SAPI, Windows) →
  manifest → Node `render.mjs` (`bundle()` + `renderMedia()`, explicit
  bundled Chrome) → ffmpeg loudnorm to −16 LUFS → MP4 + `.warnings.json`.
- Runtimes are resolved from inside the app folder (gui.py: `node/node.exe`,
  `chrome/chrome-headless-shell.exe`, `ffmpeg/ffmpeg.exe` via `FFMPEG_BIN`).
- Brand badge: customer's channel name, small white text at top, throughout;
  empty = no badge. NEVER hardcoded BRONZE BASE (grep-verified).
- No-lying: every fallback → WARNING + `.warnings.json`. Mock voice stays
  explicit-flag-only (never the default).
- BOM fix intact: `build_props.py` reads SAPI JSON with `utf-8-sig`;
  `sapi_tts.ps1` writes JSON with `WriteAllText` + UTF8 NoBOM
  (Minh's Windows test proved it was needed).

## Verified on this Linux VM

- [x] Payload completeness: 14,213 files; byte sum 739,803,266 = NSIS datablock
      (minus ~330 KB per-file overhead) → the ENTIRE payload is in the installer.
- [x] Installer is a valid PE32 NSIS self-extracting archive (233,190,591 bytes).
- [x] Windows platform packages present; no Linux platform packages.
- [x] All three runtime exes are PE32+ Windows x86-64
      (`node.exe`, `chrome-headless-shell.exe`, `ffmpeg.exe`).
- [x] No sandbox-only patch, no make_memes.py, no samples/, no out/,
      no `__pycache__`, no mock WAVs in the payload.
- [x] No hardcoded BRONZE BASE in product code.
- [x] NSIS script compiles clean (syntax test passed; full build exit 0).

## NOT verified here — needs Minh's Windows test (SAC-on machine)

- [ ] **Installer launch**: double-click → SmartScreen "Run anyway" (NORMAL) →
      install → Finish. SAC hard block (no "Run anyway") = FAIL.
- [ ] **Python + vc_redist silent installs** inside the installer.
- [ ] **App launch**: Desktop shortcut → GUI opens, no console, no SAC block
      on `pythonw.exe` / `node.exe` / `chrome-headless-shell.exe` / `ffmpeg.exe`.
- [ ] **SAPI voice** via the installed app (Render → "Reading voice…" →
      "Building visuals…").
- [ ] **Full Render flow** on Windows → MP4 + warnings file.
- [ ] **SAC behaviour for the Node + Chrome stack** — still the biggest risk.
- [ ] **Uninstaller** (Settings → Apps → SIVO → Uninstall).
- See `TEST-SAC.md` for the step-by-step test script (what Minh will see
  after each step, PASS/FAIL per test, SmartScreen-vs-SAC distinction).
