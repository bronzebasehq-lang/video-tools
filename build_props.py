#!/usr/bin/env python3
"""SIVO-Remotion v3 (Fireship rebuild) — props builder.

SIVO is now an INTERNAL production tool for Minh's own channel (NOT a
product for non-tech customers). The quality bar is Fireship / Long #4:
plain bottom subtitle (NO per-word karaoke color change) + big static
mid-screen caption per shot + a media slot per shot + hard cuts only.

Inputs:
  script.txt (English, 1 sentence/line)
    -> scenes -> voice WAVs -> manifest JSON for the Remotion composition.

Templates (deterministic mapping, no LLM, no guessing):
  - explainer: Hook -> Pain -> Solution -> Workflow -> Benefits -> Outro
    (6 slots; middle sentences merge into the 4 middle slots when the
    script has more than 6 sentences; fewer sentences -> fewer scenes).
  - listicle: Hook + numbered items (max 7, overflow merges) + Outro.
  - news: Headline card + up to 3 numbered events + Why-it-matters +
    Source (only if a line starts with "Source:" / "Nguồn:") + Outro.
Script too short/long -> WARNING + fewer/merged scenes. A sentence is
NEVER silently dropped: merging concatenates the per-sentence WAVs
(SAPI and mock both write 22050 Hz / 16-bit / mono) and offsets timings.

Shot list (optional, --shot-list shotlist.json):
  JSON: {"shots": [{"scene": 1, "bigCaption": "YOUR MONEY SLEEPS?",
  "bigCaptionColor": "#ffd700", "subtitleColor": "#ffffff",
  "media": "media/piggy-bank.jpg", "mediaType": "image",
  "mediaPosition": "fullscreen", "mediaSource": "Wikimedia Commons / ...",
  "effect": "hard-cut"}, ...]}
  "scene" is 1-based over the PRE-SPLIT scenes (template order). Fields
  are optional; missing fields fall back to auto headlines / role colors /
  no media. Mirrors the Long #4 shot-list columns (# | time | dialogue |
  big caption | GIF+position | visual+source | effect) — time/dialogue
  come from the script + voice, so they are not repeated in the JSON.
  Extra fields: "lines" (X style: [{text, color}] caption segments),
  "durationSec" (X style: shot length, silence backend), "mediaList"
  (Fireship collage: 2-4 media), "layout" + "layoutData" (news style:
  7 layouts + verdict). Media may be "pool:<tag>" — resolved from
  media-pool/pool.json (only the used file is copied into public/).

Voice backends:
  - sapi (DEFAULT on Windows): calls voice/sapi_tts.ps1 via PowerShell 5.1
    (System.Speech). This is the zero-effort draft default. SAPI is flat —
    real delivery enters through the EXTERNAL voice slot below.
  - mock (EXPLICIT flag only, for Linux testing): generates a soft sine-tone
    WAV at a plausible duration (~150 wpm) + evenly-split word timings.
    The manifest records voice="mock ..." and a WARNING so no one mistakes
    a mock render for a real-voice render.
  - external (--voice-wav FILE --voice-timings FILE): ONE recorded WAV
    (Minh's voice, Edge TTS, ...) + a timings JSON with one {start, end}
    per script line (seconds in the WAV). The builder slices the WAV per
    scene. External voice WINS over --voice-backend when both are given.
    Timings JSON: [{"start": 0.0, "end": 3.2}, ...] or
    {"sentences": [{"start": ..., "end": ...}, ...]}.
    The WAV must be PCM (Edge TTS / Audacity / phone recordings exported
    as WAV are PCM). Non-PCM -> LOUD failure, never a silent wrong render.

Fireship pacing (--max-shot-sec, default 4.0) — FIRESHP STYLE ONLY:
a scene whose voice is longer than max-shot-sec is split into
sub-shots at word boundaries (one hard cut per sub-shot). The first
sub-shot keeps the scene's bigCaption/media/crossLink; later
sub-shots get auto captions from their own words and no media
(media -> text -> media rhythm). --max-shot-sec 0 disables splitting.
News scenes are layout cards and are NEVER split; X scenes are
1 line = 1 shot and are NEVER split.

Meme: Explainer + --meme-on + a Pain scene with NO shot-list media ->
scene media = "memes/pain-01.mp4" (license-clean, see MEMES.md).
The meme now flows through the generic media slot.

Styles (v4, multi-style): a style = composition + grammar + caption
rules + default voice. --style fireship (default) = Fireship grammar
(3 template frames: explainer/listicle/news) + collage mediaList.
--style news = news grammar: each scene renders ONE of 6 news layouts
(breaking-news, stat-callout, split-screen, quote-card, listicle,
big-number) + outro. --style x = X grammar (Short #8/#9): pixel font,
GIF fullscreen or fit, hard cuts, ~30s, caption-only (silence backend)
+ quote punchline end card. The shot list sets "layout" + "layoutData"
per scene (news); "lines" + "durationSec" per shot (x). Without them,
the news layout defaults by role (headline -> breaking-news, event ->
stat-callout, why -> quote-card, source -> quote-card tag SOURCE,
outro -> outro). News style requires template=news; X style requires
template=x (both forced with a WARNING if another template is given).
News layouts come from the auto-video-gen template grammar
(hook/comparison/stat-hero/feature-list/callout/outro) — re-implemented
in Remotion, NOT copied: brand is BRONZE BASE (never @cuongit96), and
every layout takes the media slot (image/chart/footage/screenshot) to
fix the news style's known weakness (text-heavy / monotonous).
Adding a style: new composition + Root.tsx registration + render.mjs
map + a build_props.py style entry + GUI radio + README row (see
README "How to add a style").

Voice backends — FREE ONLY (Minh locked 17/10 tối: ElevenLabs is OUT,
even paid. "chỉ dùng miễn phí, giọng nào cũng được."):
  - sapi (DEFAULT on CLI): see above. Zero-config draft default.
  - silence: caption-only renders (X style). Duration per scene comes
    from the shot list's durationSec, else 3.0s. No audio, no voice.
  - mock (EXPLICIT flag only, for Linux testing): see above.
  - external (--voice-wav + --voice-timings): see above. Edge TTS
    output feeds in here (generate WAV elsewhere, pass it in) — the
    tool has NO native Edge TTS backend.

No-lying rule: every fallback is recorded in manifest["warnings"] and
printed. A scene whose voice failed gets an estimated-duration silent WAV
+ a WARNING entry, never a silent success.

Usage:
  python build_props.py samples/compound-interest.txt \
      --out out/manifest.json --public-dir public \
      --brand "BRONZE BASE" --voice-backend mock --template explainer \
      --shot-list shotlist.json --max-shot-sec 4
  python build_props.py script.txt --out manifest.json --public-dir public
      --voice-backend sapi --rate 2 --template listicle
  python build_props.py script.txt --out manifest.json --public-dir public
      --voice-wav voice.wav --voice-timings timings.json
"""
import argparse
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import wave
from datetime import datetime

FPS = 30
WPM_MOCK = 150.0
SAMPLE_RATE = 22050
HERE = os.path.dirname(os.path.abspath(__file__))
SAPI_PS1 = os.path.join(HERE, "voice", "sapi_tts.ps1")
TEMPLATES = ["explainer", "listicle", "news", "x"]
EXPLAINER_FRAME = ["hook", "pain", "solution", "workflow", "benefits", "outro"]
LISTICLE_MAX_ITEMS = 7
NEWS_MAX_EVENTS = 3
DEFAULT_MAX_SHOT_SEC = 4.0
# Silent end-card duration for slots with no script sentence (news outro).
OUTRO_CARD_SEC = 4.0
STYLES = ["fireship", "news", "x"]
# News-style per-scene layouts (adapted from the auto-video-gen template
# grammar: hook -> breaking-news, stat-hero -> stat-callout/big-number,
# comparison -> split-screen, callout -> quote-card, feature-list ->
# listicle, outro -> outro). Re-implemented in Remotion; brand is
# BRONZE BASE, never the source repo's brand.
NEWS_LAYOUTS = ["breaking-news", "stat-callout", "split-screen",
                "quote-card", "listicle", "big-number", "action-card",
                "outro"]
NEWS_LAYOUT_DEFAULTS = {
    "headline": "breaking-news",
    "event": "stat-callout",
    "why": "quote-card",
    # Source renders as a quote-card (tag SOURCE) — NOT a second outro
    # card (the real outro scene already renders the follow card).
    "source": "quote-card",
    "action": "action-card",
    "outro": "outro",
}

# Cross-link end cards — REMOVED per Minh 18/10: "tôi không cần móc nối nữa".
# No video ends with hooks to the other platforms anymore. All values empty.
CROSS_LINK = {
    "fireship": "",
    "news": "",
    "x": "",
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTS = {".mp4", ".webm", ".mov"}


def log(msg):
    print(f"[build_props] {msg}", flush=True)


def warn(msg):
    print(f"[build_props] WARNING: {msg}", flush=True)


def tokenize(text):
    return text.split()


def clean_word(w):
    return re.sub(r"[^a-z']", "", w.lower())


def headline_for(text, full=False):
    if full:
        head = text.strip().upper()
        return head[:80].rstrip()
    words = tokenize(text)[:4]
    head = " ".join(words).upper()
    return head[:40].rstrip()


def wav_duration_sec(path):
    with wave.open(path, "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def estimate_word_times(text, duration):
    words = tokenize(text)
    if not words:
        return []
    per = duration / len(words)
    return [
        {"w": w, "s": round(i * per, 3), "e": round((i + 1) * per, 3)}
        for i, w in enumerate(words)
    ]


def write_wav(path, samples, rate=SAMPLE_RATE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"".join(struct.pack("<h", s) for s in samples))


def write_silence(path, duration):
    n = int(duration * SAMPLE_RATE)
    write_wav(path, [0] * n)
    return duration


def slice_wav(in_path, start_sec, end_sec, out_path):
    """Slice a PCM WAV with the wave module. Returns duration in seconds.
    Raises RuntimeError (plain-language) on non-WAV / non-PCM input or
    empty slices — never writes a corrupt file."""
    try:
        wf = wave.open(in_path, "rb")
    except (wave.Error, EOFError) as e:
        raise RuntimeError(
            f"{in_path}: not a WAV file ({e}). External voice must be a "
            "plain PCM WAV — export MP3/m4a recordings to WAV first."
        ) from e
    with wf:
        if wf.getcomptype() != "NONE":
            raise RuntimeError(
                f"{in_path}: only PCM WAVs are supported "
                f"(got compression {wf.getcomptype()!r}). Export the voice "
                "as a plain PCM WAV (Audacity / Edge TTS output)."
            )
        rate = wf.getframerate()
        ch, sw = wf.getnchannels(), wf.getsampwidth()
        n = wf.getnframes()
        start_f = max(0, int(start_sec * rate))
        end_f = min(n, int(end_sec * rate))
        if end_f <= start_f:
            raise RuntimeError(
                f"slice [{start_sec}, {end_sec}] is empty in {in_path} "
                f"({n} frames @ {rate} Hz)."
            )
        wf.setpos(start_f)
        frames = wf.readframes(end_f - start_f)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(sw)
        wf.setframerate(rate)
        wf.writeframes(frames)
    return (end_f - start_f) / rate


def mock_voice(text, wav_path):
    """Linux-test voice ONLY. Soft sine tone, plausible duration."""
    n_words = max(1, len(tokenize(text)))
    duration = max(1.0, n_words / WPM_MOCK * 60.0)
    n = int(duration * SAMPLE_RATE)
    samples = [
        int(0.08 * 32767 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE))
        for i in range(n)
    ]
    write_wav(wav_path, samples)
    timings = estimate_word_times(text, duration)
    return {"words": timings, "timing": "mock", "n_words": n_words}


def sapi_voice(text, wav_path, json_path, rate, tmpdir):
    """REAL Windows SAPI path. Raises on any failure — never silent."""
    txt_path = os.path.join(tmpdir, "sentence.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", SAPI_PS1,
        "-TextFile", txt_path, "-OutWav", wav_path, "-OutJson", json_path,
        "-Rate", str(rate),
    ]
    kwargs = {}
    if sys.platform == "win32":
        # No console window flashing (the terminal must never be visible).
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=300, **kwargs)
    except FileNotFoundError as e:
        raise RuntimeError(
            "powershell.exe not found — SAPI voice requires Windows "
            "PowerShell 5.1. Use --voice-backend mock ONLY for Linux testing."
        ) from e
    if res.returncode != 0:
        raise RuntimeError(
            f"sapi_tts.ps1 failed (exit {res.returncode}): "
            f"{res.stderr.strip()[:500]}"
        )
    # PowerShell 5.1 Set-Content -Encoding UTF8 writes a UTF-8 BOM at the
    # start of the file, and plain json.load(chokes) on it ("Unexpected
    # UTF-8 BOM"). utf-8-sig strips the BOM if present and reads normally
    # if there is none — so this works with both old and new .ps1 output.
    try:
        with open(json_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"could not parse SAPI JSON {json_path}: {e}"
        ) from e


def concat_wavs(wav_paths, out_path):
    """Concatenate WAVs with IDENTICAL params (22050/16-bit/mono).
    Raises if params differ — never writes a corrupt mixed-format WAV."""
    if len(wav_paths) == 1:
        shutil.copyfile(wav_paths[0], out_path)
        return wav_duration_sec(out_path)
    params = None
    frames = []
    for p in wav_paths:
        with wave.open(p, "rb") as wf:
            cur = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
            if params is None:
                params = cur
            elif cur != params:
                raise RuntimeError(
                    f"Cannot merge WAVs with different params: {params} vs "
                    f"{cur} ({p}). Voice backend must be consistent."
                )
            frames.append(wf.readframes(wf.getnframes()))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(params[0])
        wf.setsampwidth(params[1])
        wf.setframerate(params[2])
        for fr in frames:
            wf.writeframes(fr)
    return wav_duration_sec(out_path)


def offset_timings(timings, offset):
    return [
        {"w": t["w"], "s": round(t["s"] + offset, 3),
         "e": round(t["e"] + offset, 3)}
        for t in timings
    ]


def distribute(n_items, n_slots):
    """Split n_items into n_slots groups, as even as possible (>=1 each).
    Extra items go to the earliest slots. Requires n_items >= n_slots."""
    base, rem = divmod(n_items, n_slots)
    return [base + (1 if i < rem else 0) for i in range(n_slots)]


# ---------------------------------------------------------------------------
# Script -> slots mapping (deterministic, per template). A slot is one
# rendered scene holding 1+ sentences (merged when the script is long).
# Returns (slots, warnings). Slot: {role, sentence_indices, index?, meta?}
# ---------------------------------------------------------------------------
def map_script(sentences, template, no_merge=False):
    n = len(sentences)
    warnings = []
    if n == 0:
        return [], ["Script has no non-empty lines."]
    if n > 30:
        warnings.append(
            f"Script has {n} sentences (> 30) — video will be very long; "
            "consider splitting it."
        )

    if template == "explainer":
        if no_merge:
            # FIX 19/10 (shot-list desync bug): when a shot list is given,
            # the user plans 1 shot per SENTENCE. The old code still merged
            # sentences into 6 Explainer slots, so shot-list scene numbers
            # mapped to the WRONG sentences (caption said one thing while
            # the voice read another — "karaoke voice jumping around").
            # With a shot list, merging is disabled: 1 sentence = 1 scene.
            if n == 1:
                roles = ["hook"]
            elif n == 2:
                roles = ["hook", "outro"]
            else:
                middle_roles = EXPLAINER_FRAME[1:5]  # pain/solution/workflow/benefits
                roles = ["hook"] + [
                    middle_roles[i % len(middle_roles)]
                    for i in range(n - 2)
                ] + ["outro"]
            warnings.append(
                "Shot list given — Explainer merging disabled "
                "(1 sentence = 1 scene) so shot-list scene numbers match "
                "sentences."
            )
            return [{"role": r, "indices": [i]} for i, r in enumerate(roles)], warnings
        if n < 3:
            warnings.append(
                f"Script has only {n} sentence(s) (< 3) — video renders "
                "with fewer scenes than the Explainer frame."
            )
        if n <= len(EXPLAINER_FRAME):
            # Keep hook + outro + the first (n-2) middle roles.
            if n == 1:
                roles = ["hook"]
            elif n == 2:
                roles = ["hook", "outro"]
            else:
                roles = ["hook"] + EXPLAINER_FRAME[1:1 + (n - 2)] + ["outro"]
            return [{"role": r, "indices": [i]} for i, r in enumerate(roles)], warnings
        # Long script: hook + outro keep 1 sentence; middle merges into
        # the 4 middle slots (pain, solution, workflow, benefits).
        middle = distribute(n - 2, 4)
        slots = [{"role": "hook", "indices": [0]}]
        pos = 1
        for role, count in zip(EXPLAINER_FRAME[1:5], middle):
            slots.append({"role": role, "indices": list(range(pos, pos + count))})
            pos += count
        slots.append({"role": "outro", "indices": [n - 1]})
        warnings.append(
            f"{n} sentences merged into 6 Explainer scenes "
            "(middle scenes hold multiple sentences)."
        )
        return slots, warnings

    if template == "listicle":
        if n < 3:
            warnings.append(
                f"Script has only {n} sentence(s) (< 3) — video renders "
                "with fewer scenes than the Listicle frame."
            )
        if n == 1:
            return [{"role": "hook", "indices": [0], "meta": "1 ITEM"}], warnings
        if n == 2:
            return [
                {"role": "hook", "indices": [0], "meta": "1 ITEM"},
                {"role": "outro", "indices": [1]},
            ], warnings
        middle_n = n - 2
        if middle_n <= LISTICLE_MAX_ITEMS:
            counts = [1] * middle_n
        else:
            counts = distribute(middle_n, LISTICLE_MAX_ITEMS)
            warnings.append(
                f"{middle_n} list items merged into {LISTICLE_MAX_ITEMS} "
                "numbered items (max 7)."
            )
        n_items = len(counts)
        slots = [{"role": "hook", "indices": [0], "meta": f"{n_items} ITEMS"}]
        pos = 1
        for j, count in enumerate(counts):
            slots.append({
                "role": "item",
                "indices": list(range(pos, pos + count)),
                "index": j + 1,
            })
            pos += count
        slots.append({"role": "outro", "indices": [n - 1]})
        return slots, warnings

    if template == "news":
        # Source line: first sentence starting with "Source:" / "Nguồn:".
        source_idx = None
        source_text = None
        for i, s in enumerate(sentences):
            m = re.match(r"^(source|nguồn)\s*:\s*(.+)$", s, re.IGNORECASE)
            if m:
                source_idx = i
                source_text = m.group(2).strip()
                break
        pool = [i for i in range(n) if i != source_idx]
        m = len(pool)
        if m == 0:
            return [], ["Script has only a source line — no news content."]
        # The outro is a PURE end card (verdict + CTA + follow +
        # cross-link) — it consumes NO script sentence. The last content
        # sentence belongs to the action beat (dùng được ngay), never to
        # the outro (previously the outro swallowed the last sentence and
        # mislabeled it as the "source" line).
        if m == 1:
            slots = [{"role": "headline", "indices": [pool[0]]},
                     {"role": "outro", "indices": []}]
        else:
            middle_n = m - 1
            # Middle beats: the LAST middle slot is always "action"
            # (dùng được ngay — 1 concrete thing the viewer can use
            # TODAY) when there are >= 2 middle sentences.
            if middle_n == 1:
                middle_slots = ["event"]
            elif middle_n == 2:
                middle_slots = ["event", "action"]
            elif middle_n == 3:
                middle_slots = ["event", "why", "action"]
            else:
                middle_slots = ["event", "event", "why", "action"]
            if middle_n <= len(middle_slots):
                used = middle_slots[:middle_n]
                counts = [1] * middle_n
            else:
                used = middle_slots
                counts = distribute(middle_n, len(middle_slots))
                warnings.append(
                    f"{middle_n} news sentences merged into 4 middle scenes "
                    "(2 events + why + action / dùng được ngay)."
                )
            slots = [{"role": "headline", "indices": [pool[0]]}]
            pos = 1
            event_no = 0
            for role, count in zip(used, counts):
                slot = {"role": role,
                        "indices": [pool[pos + k] for k in range(count)]}
                if role == "event":
                    event_no += 1
                    slot["index"] = event_no
                slots.append(slot)
                pos += count
            slots.append({"role": "outro", "indices": []})
        if source_idx is not None:
            # Source slot goes after why/events, before outro.
            insert_at = len(slots) - 1 if slots and slots[-1]["role"] == "outro" else len(slots)
            slots.insert(insert_at, {
                "role": "source",
                "indices": [source_idx],
                "source_text": source_text,
            })
        elif m >= 3:
            warnings.append(
                "No source line found — add a line starting with 'Source:' "
                "to show one."
            )
        return slots, warnings

    if template == "x":
        # X style (Short #8/#9): ONE script line = ONE shot. No merging,
        # no frame. First line = hook, last = outro (quote punchline),
        # middle = item. Durations come from the shot list (durationSec)
        # with the silence backend, or from voice otherwise.
        if n > 12:
            warnings.append(
                f"Script has {n} lines — X style targets ~8 shots / 30s; "
                "more lines make a longer video."
            )
        slots = []
        for i in range(n):
            role = "hook" if i == 0 else ("outro" if i == n - 1 else "item")
            slots.append({"role": role, "indices": [i]})
        return slots, warnings

    raise ValueError(f"Unknown template: {template}")


# ---------------------------------------------------------------------------
# Shot list (Long #4 columns, JSON). "scene" is 1-based over PRE-SPLIT
# scenes. Returns {scene_index: overrides}, warnings.
# ---------------------------------------------------------------------------
def load_media_pool():
    """Reusable media pool (media-pool/pool.json next to build_props.py).
    Entries: {"name", "file" (relative to media-pool/), "tags": [...]}.
    Returns {tag_lower: entry} (first entry wins per tag) + the pool dir.
    Missing/unreadable pool.json -> empty pool (pool: refs then warn)."""
    pool_dir = os.path.join(HERE, "media-pool")
    pool_path = os.path.join(pool_dir, "pool.json")
    if not os.path.exists(pool_path):
        return {}, pool_dir
    try:
        with open(pool_path, "r", encoding="utf-8") as f:
            entries = json.load(f).get("entries", [])
    except (OSError, ValueError) as e:
        warn(f"Media pool unreadable ({pool_path}): {e} — pool: refs will fail.")
        return {}, pool_dir
    by_tag = {}
    for e in entries:
        if not isinstance(e, dict) or not e.get("file"):
            continue
        for t in e.get("tags", []) or []:
            by_tag.setdefault(str(t).lower(), e)
        if e.get("name"):
            by_tag.setdefault(str(e["name"]).lower(), e)
    return by_tag, pool_dir


def _resolve_pool_ref(media_src, public_dir, si, warnings, pool, pool_dir):
    """pool:<tag> -> copy the pool file into public/media-pool/ and
    return its public-relative src, or None (warned). The pool is a
    source library in the work dir; only USED files are copied into
    public/ so the Remotion bundle stays small."""
    tag = media_src[5:].strip().lower()
    entry = (pool or {}).get(tag)
    if not entry:
        warnings.append(
            f"Shot list scene {si}: media pool has no entry for tag "
            f"{tag!r} — media ignored. See media-pool/pool.json."
        )
        return None
    src_file = os.path.join(pool_dir, entry["file"])
    if not os.path.exists(src_file):
        warnings.append(
            f"Shot list scene {si}: pool entry {entry.get('name')} file "
            f"missing: {src_file} — media ignored."
        )
        return None
    dest_dir = os.path.join(public_dir, "media-pool")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(entry["file"]))
    if not os.path.exists(dest):
        import shutil
        shutil.copy2(src_file, dest)
    return f"media-pool/{os.path.basename(entry['file'])}"


def _parse_media(m, public_dir, si, warnings, pool=None, pool_dir=""):
    """Validate one shot-list media entry -> media dict or None.
    Shared by the single `media` field and the `mediaList` collage."""
    if not isinstance(m, dict):
        warnings.append(f"Shot list scene {si}: media entry is not an object — ignored.")
        return None
    media_src = m.get("media")
    if not media_src:
        warnings.append(f"Shot list scene {si}: media entry has no 'media' path — ignored.")
        return None
    if isinstance(media_src, str) and media_src.startswith("pool:"):
        resolved = _resolve_pool_ref(media_src, public_dir, si, warnings,
                                     pool, pool_dir)
        if resolved is None:
            return None
        media_src = resolved
    full = os.path.join(public_dir, media_src)
    if not os.path.exists(full):
        warnings.append(
            f"Shot list scene {si}: media file missing: {media_src} — media ignored."
        )
        return None
    ext = os.path.splitext(media_src)[1].lower()
    mtype = m.get("mediaType")
    if not mtype:
        if ext in VIDEO_EXTS:
            mtype = "video"
        elif ext in IMAGE_EXTS or ext == ".gif":
            mtype = "image"
        else:
            warnings.append(
                f"Shot list scene {si}: unknown media extension {ext} "
                f"({media_src}) — media ignored."
            )
            return None
    if ext == ".gif":
        warnings.append(
            f"Shot list scene {si}: GIF renders as a STATIC first frame — "
            f"convert to MP4 for motion ({media_src})."
        )
    return {
        "src": media_src,
        "type": mtype,
        "position": m.get("mediaPosition", "fullscreen"),
        "source": m.get("mediaSource"),
    }


def load_shot_list(path, n_scenes, public_dir, style="fireship",
                   pool=None, pool_dir=""):
    with open(path, "r", encoding="utf-8-sig") as f:
        doc = json.load(f)
    shots = doc.get("shots", []) if isinstance(doc, dict) else doc
    if not isinstance(shots, list):
        raise RuntimeError("Shot list must be {\"shots\": [...]}.")
    out = {}
    warnings = []
    for entry in shots:
        if not isinstance(entry, dict):
            warnings.append("Shot list: non-object entry ignored.")
            continue
        si = entry.get("scene")
        if not isinstance(si, int) or si < 1 or si > n_scenes:
            warnings.append(
                f"Shot list: scene {si} out of range (1..{n_scenes}) — "
                "entry ignored."
            )
            continue
        ov = {}
        for key in ("bigCaption", "bigCaptionColor", "subtitleColor", "effect"):
            if entry.get(key):
                ov[key] = str(entry[key])
        # News-style per-scene layout (+ structured layoutData, e.g.
        # {"value": "$22B", "label": "..."} for stat-callout, {"left":..,
        # "right":..} for split-screen, {"bullets": [...]} for listicle).
        # Fireship style ignores layout (warn) — its scenes use the
        # template frame, not per-scene layouts.
        if entry.get("layout"):
            if style == "news":
                if entry["layout"] in NEWS_LAYOUTS:
                    ov["layout"] = entry["layout"]
                else:
                    warnings.append(
                        f"Shot list scene {si}: unknown news layout "
                        f"{entry['layout']!r} — using the role default."
                    )
            else:
                warnings.append(
                    f"Shot list scene {si}: 'layout' only applies to "
                    "news style — ignored for fireship."
                )
        if entry.get("layoutData") is not None:
            if style == "news":
                if isinstance(entry["layoutData"], dict):
                    ov["layoutData"] = entry["layoutData"]
                else:
                    warnings.append(
                        f"Shot list scene {si}: layoutData must be an "
                        "object — ignored."
                    )
        parsed = None
        if entry.get("media"):
            parsed = _parse_media(entry, public_dir, si, warnings,
                                  pool=pool, pool_dir=pool_dir)
        if parsed:
            ov["media"] = parsed
        # X-style: durationSec (shot length, silence backend) + lines
        # ([{text, color}] caption segments — Short #8/#9 shot grammar).
        if entry.get("durationSec") is not None:
            try:
                ov["durationSec"] = float(entry["durationSec"])
            except (TypeError, ValueError):
                warnings.append(
                    f"Shot list scene {si}: bad durationSec "
                    f"{entry['durationSec']!r} — ignored."
                )
        if entry.get("lines") is not None:
            raw_lines = entry["lines"]
            if (isinstance(raw_lines, list) and raw_lines
                    and all(isinstance(l, dict) and l.get("text")
                            for l in raw_lines)):
                ov["lines"] = [
                    {"text": str(l["text"]),
                     "color": str(l.get("color", "#ffffff"))}
                    for l in raw_lines
                ]
            else:
                warnings.append(
                    f"Shot list scene {si}: lines must be a non-empty list "
                    "of {text, color} — ignored."
                )
        # Fireship collage: mediaList (2-4 media entries) renders as a
        # grid + big caption overlaid (YT: denser topic-related media).
        if entry.get("mediaList") is not None:
            if style == "fireship" and isinstance(entry["mediaList"], list):
                ml = []
                for m in entry["mediaList"]:
                    pm = _parse_media(m, public_dir, si, warnings,
                                      pool=pool, pool_dir=pool_dir)
                    if pm:
                        ml.append(pm)
                if len(ml) >= 2:
                    ov["mediaList"] = ml
                elif ml:
                    warnings.append(
                        f"Shot list scene {si}: mediaList needs 2+ valid "
                        "entries (got 1) — use single media instead."
                    )
            else:
                warnings.append(
                    f"Shot list scene {si}: mediaList only applies to "
                    "fireship style — ignored."
                )
        out[si] = ov
    return out, warnings


# ---------------------------------------------------------------------------
# External voice (one recorded WAV + per-sentence timings).
# ---------------------------------------------------------------------------
def load_voice_timings(path, n_sentences):
    with open(path, "r", encoding="utf-8-sig") as f:
        doc = json.load(f)
    items = doc.get("sentences") if isinstance(doc, dict) else doc
    if not isinstance(items, list):
        raise RuntimeError(
            "Voice timings must be a JSON list of {start, end} objects, "
            "or {\"sentences\": [...]}."
        )
    if len(items) < n_sentences:
        raise RuntimeError(
            f"Voice timings have {len(items)} entries but the script has "
            f"{n_sentences} sentences — every sentence needs a timing."
        )
    if len(items) > n_sentences:
        warn(
            f"Voice timings have {len(items)} entries for {n_sentences} "
            "sentences — extras ignored."
        )
    out = []
    for i, it in enumerate(items[:n_sentences]):
        try:
            s, e = float(it["start"]), float(it["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Voice timings entry {i + 1} needs numeric start/end."
            ) from exc
        if e <= s:
            raise RuntimeError(
                f"Voice timings entry {i + 1}: end ({e}) must be > "
                f"start ({s})."
            )
        out.append((s, e))
    return out


# ---------------------------------------------------------------------------
# Fireship pacing: split a long scene into sub-shots at word boundaries.
# Returns a list of (text, start_sec, end_sec, wordTimings) chunks, or
# None when no split is needed. The first chunk keeps the scene's
# bigCaption/media; later chunks get auto captions and no media.
# ---------------------------------------------------------------------------
def split_scene_chunks(text, timings, duration, max_sec):
    if max_sec <= 0 or duration <= max_sec:
        return None
    if timings:
        # Maximal packing: each chunk <= max_sec, cut between words.
        chunks = []
        cur = []
        cur_start = timings[0]["s"]
        for t in timings:
            if cur and (t["e"] - cur_start) > max_sec:
                chunks.append(cur)
                cur = []
                cur_start = t["s"]
            cur.append(t)
        if cur:
            chunks.append(cur)
        if len(chunks) <= 1:
            return None
        out = []
        for ch in chunks:
            s, e = ch[0]["s"], ch[-1]["e"]
            wt = [
                {"w": t["w"], "s": round(t["s"] - s, 3),
                 "e": round(t["e"] - s, 3)}
                for t in ch
            ]
            out.append((" ".join(t["w"] for t in ch), s, e, wt))
        return out
    # No word timings: even split by word count.
    words = tokenize(text)
    if not words:
        return None
    n_chunks = math.ceil(duration / max_sec)
    if n_chunks <= 1:
        return None
    counts = distribute(len(words), n_chunks)
    out = []
    pos = 0
    for count in counts:
        group = words[pos:pos + count]
        s = pos / len(words) * duration
        e = (pos + count) / len(words) * duration
        out.append((" ".join(group), s, e,
                    estimate_word_times(" ".join(group), e - s)))
        pos += count
    return out


def sapi_timings_or_estimate(info, text, part_wav, scene_id, warnings):
    """SAPI word timings with the even-split fallback (shared by the
    SAPI backend)."""
    timings = info.get("words", [])
    n_tokens = len(tokenize(text))
    if info.get("n_words", 0) != n_tokens or not timings:
        dur = wav_duration_sec(part_wav)
        warnings.append(
            f"{scene_id}: SAPI returned {info.get('n_words', 0)} "
            f"word timings for {n_tokens} tokens "
            f"(timing={info.get('timing')}) — word timings fell "
            "back to even-split estimates."
        )
        timings = estimate_word_times(text, dur)
    return timings


def ensure_default_silence(public_dir):
    """3s silent WAV so the composition's defaultProps always resolve."""
    path = os.path.join(public_dir, "audio", "_default", "silence.wav")
    if not os.path.exists(path):
        write_silence(path, 3.0)
    return path


def main():
    ap = argparse.ArgumentParser(description="SIVO-Remotion v3 props builder (Fireship)")
    ap.add_argument("script", help="script.txt — English, 1 sentence/line")
    ap.add_argument("--out", required=True, help="manifest JSON output path")
    ap.add_argument("--public-dir", required=True,
                    help="Remotion project public/ dir (WAVs land here)")
    ap.add_argument("--run-id", default="poc", help="audio subdir under public/audio/")
    ap.add_argument("--brand", default="", help="channel badge ('' = no badge)")
    ap.add_argument("--template", default="explainer", choices=TEMPLATES)
    ap.add_argument("--style", default="fireship", choices=STYLES,
                    help="video style: fireship (Fireship grammar), news "
                    "(6 news layouts), or x (Short #8/#9 grammar). News "
                    "style forces template=news; X style forces template=x.")
    ap.add_argument("--meme-on", action="store_true",
                    help="meme slot on (Explainer Pain scene, no shot-list media)")
    ap.add_argument("--voice-backend", choices=["sapi", "mock", "silence"],
                    default="sapi",
                    help="sapi = draft default. silence = caption-only "
                    "(X style; durations from shot-list durationSec, "
                    "else 3.0s). mock = Linux test only.")
    ap.add_argument("--rate", type=int, default=0, help="SAPI rate (plain mode)")
    ap.add_argument("--shot-list", default="",
                    help="shot list JSON (Long #4 columns: bigCaption, media, ...)")
    ap.add_argument("--voice-wav", default="",
                    help="external voice WAV (recorded voice / Edge TTS)")
    ap.add_argument("--voice-timings", default="",
                    help="external voice timings JSON (one {start,end} per script line)")
    ap.add_argument("--max-shot-sec", type=float, default=DEFAULT_MAX_SHOT_SEC,
                    help="max seconds per shot; longer scenes split at word "
                    "boundaries (0 = disable). Default 4.0.")
    args = ap.parse_args()

    with open(args.script, "r", encoding="utf-8-sig") as f:
        lines = [ln.strip() for ln in f.readlines()]
    sentences = [ln for ln in lines if ln]
    if not sentences:
        print("[build_props] ERROR: script has no non-empty lines.", file=sys.stderr)
        return 1
    warnings = []
    if len(lines) != len(sentences):
        warnings.append(f"{len(lines) - len(sentences)} blank line(s) skipped.")

    # Map once; if a style rule forces a different template below, the
    # re-map's warnings REPLACE these (never keep stale warnings from a
    # template that was overridden).
    slots, map_warnings = map_script(sentences, args.template, no_merge=bool(args.shot_list))

    # Style/template rule: news style renders the news scene frame only.
    if args.style == "news" and args.template != "news":
        warnings.append(
            f"News style requires template=news (got {args.template!r}) — "
            "template forced to news."
        )
        args.template = "news"
        slots, map_warnings = map_script(sentences, args.template, no_merge=bool(args.shot_list))

    # Style/template rule: X style renders the X scene frame only.
    if args.style == "x" and args.template != "x":
        warnings.append(
            f"X style requires template=x (got {args.template!r}) — "
            "template forced to x."
        )
        args.template = "x"
        slots, map_warnings = map_script(sentences, args.template, no_merge=bool(args.shot_list))
    warnings.extend(map_warnings)

    if not slots:
        for w in warnings:
            warn(w)
        print("[build_props] ERROR: no scenes mapped.", file=sys.stderr)
        return 1

    # External voice wins over --voice-backend when both are given.
    external = bool(args.voice_wav)
    if bool(args.voice_wav) != bool(args.voice_timings):
        print("[build_props] ERROR: --voice-wav and --voice-timings must be "
              "given together.", file=sys.stderr)
        return 1
    voice_timings = None
    if external:
        if not os.path.exists(args.voice_wav):
            print(f"[build_props] ERROR: voice WAV not found: {args.voice_wav}",
                  file=sys.stderr)
            return 1
        try:
            voice_timings = load_voice_timings(args.voice_timings, len(sentences))
        except RuntimeError as e:
            print(f"[build_props] ERROR: {e}", file=sys.stderr)
            return 1

    # Shot list (validated against pre-split scene count).
    shot_overrides = {}
    pool, pool_dir = load_media_pool()
    if args.shot_list:
        if not os.path.exists(args.shot_list):
            print(f"[build_props] ERROR: shot list not found: {args.shot_list}",
                  file=sys.stderr)
            return 1
        try:
            shot_overrides, sl_warnings = load_shot_list(
                args.shot_list, len(slots), args.public_dir,
                style=args.style, pool=pool, pool_dir=pool_dir)
        except (json.JSONDecodeError, RuntimeError) as e:
            print(f"[build_props] ERROR: bad shot list: {e}", file=sys.stderr)
            return 1
        # FIX 19/10: an out-of-range shot-list entry used to be a WARNING
        # ("entry ignored") — but it means the user's scene numbers don't
        # line up with the template's scenes, so the remaining entries
        # would map to the WRONG sentences (caption/voice desync). Fail
        # loud instead of rendering a wrong video.
        if any("out of range" in w for w in sl_warnings):
            for w in sl_warnings:
                print(f"[build_props] WARNING: {w}", file=sys.stderr)
            print(
                "[build_props] ERROR: shot list scene numbers do not match "
                f"the template's {len(slots)} scene(s) — refusing to render "
                "a mis-mapped video. With a shot list, number scenes 1..N "
                "one per script sentence (Explainer merging is disabled "
                "when a shot list is given).",
                file=sys.stderr,
            )
            return 1
        warnings.extend(sl_warnings)

    audio_dir = os.path.join(args.public_dir, "audio", args.run_id)
    os.makedirs(audio_dir, exist_ok=True)
    ensure_default_silence(args.public_dir)
    tmpdir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "_sapi_tmp")
    os.makedirs(tmpdir, exist_ok=True)

    if external:
        voice_label = (
            f"external WAV ({os.path.basename(args.voice_wav)}) + timings"
        )
    elif args.voice_backend == "mock":
        voice_label = "mock (Linux test only — NOT real voice)"
        warnings.append(
            "VOICE IS MOCKED (sine tone, estimated timing) — "
            "this render proves the pipeline, NOT the voice."
        )
    elif args.voice_backend == "silence":
        voice_label = "silence (caption-only — no audio)"
    else:
        voice_label = f"sapi (PowerShell 5.1, rate={args.rate})"

    # Meme rules (no-lying): only Explainer Pain gets a meme, and only
    # when the shot list did not already set media for that scene.
    meme_path = os.path.join(args.public_dir, "memes", "pain-01.mp4")
    meme_available = os.path.exists(meme_path)
    if args.meme_on and args.template != "explainer":
        warnings.append(
            f"Memes only apply to the Explainer template — memeOn ignored "
            f"for {args.template}."
        )
    if args.meme_on and args.template == "explainer" and not meme_available:
        warnings.append(
            "Meme asset public/memes/pain-01.mp4 is missing — Pain scene "
            "renders without a meme."
        )

    scenes = []
    for i, slot in enumerate(slots):
        role = slot["role"]
        idxs = slot["indices"]
        scene_id = f"scene{i + 1:02d}_{role}"
        scene_no = i + 1  # 1-based, matches shot list "scene"

        # --- Voice for this scene -------------------------------------
        if not idxs:
            # Slot with no script sentence (news outro end card): a
            # fixed-duration SILENT card. No voice, no timings — the
            # card's verdict/CTA/follow/cross-link carry it.
            slot_wav = os.path.join(audio_dir, f"{scene_id}.wav")
            write_silence(slot_wav, OUTRO_CARD_SEC)
            duration = OUTRO_CARD_SEC
            text = ""
            part_timings = []
        elif external:
            start = voice_timings[idxs[0]][0]
            end = voice_timings[idxs[-1]][1]
            slot_wav = os.path.join(audio_dir, f"{scene_id}.wav")
            try:
                duration = slice_wav(args.voice_wav, start, end, slot_wav)
            except RuntimeError as e:
                print(f"[build_props] ERROR: {e}", file=sys.stderr)
                return 1
            text = " ".join(sentences[si] for si in idxs)
            part_timings = estimate_word_times(text, duration)
        elif args.voice_backend == "silence":
            # Caption-only: the scene's duration comes from the shot
            # list's durationSec, else 3.0s. One silent WAV per scene.
            dur = shot_overrides.get(scene_no, {}).get("durationSec")
            try:
                dur = float(dur) if dur is not None else 3.0
            except (TypeError, ValueError):
                warnings.append(
                    f"{scene_id}: bad durationSec {dur!r} — using 3.0s."
                )
                dur = 3.0
            dur = max(0.5, dur)
            slot_wav = os.path.join(audio_dir, f"{scene_id}.wav")
            write_silence(slot_wav, dur)
            duration = dur
            text = " ".join(sentences[si] for si in idxs)
            part_timings = estimate_word_times(text, duration)
        else:
            # Voice each sentence, then merge into one slot WAV.
            part_wavs = []
            part_timings = []
            offset = 0.0
            for j, si in enumerate(idxs):
                text = sentences[si]
                part_wav = os.path.join(tmpdir, f"{scene_id}_part{j}.wav")
                part_json = os.path.join(tmpdir, f"{scene_id}_part{j}.json")
                if args.voice_backend == "mock":
                    info = mock_voice(text, part_wav)
                    timings = info["words"]
                else:
                    info = sapi_voice(text, part_wav, part_json, args.rate, tmpdir)
                    timings = sapi_timings_or_estimate(
                        info, text, part_wav, scene_id, warnings)
                part_wavs.append(part_wav)
                part_timings.extend(offset_timings(timings, offset))
                offset += wav_duration_sec(part_wav)
            slot_wav = os.path.join(audio_dir, f"{scene_id}.wav")
            duration = concat_wavs(part_wavs, slot_wav)
            text = " ".join(sentences[si] for si in idxs)

        # --- Text / headline / shot-list overrides --------------------
        if role == "source":
            text = slot.get("source_text") or sentences[idxs[0]]
            headline = "SOURCE"
        else:
            full = (args.template == "news" and role == "headline")
            headline = headline_for(text, full=full)
        ov = shot_overrides.get(scene_no, {})
        scene = {
            "id": scene_id,
            "role": role,
            "text": text,
            "headline": headline,
            "audioPath": f"audio/{args.run_id}/{scene_id}.wav",
            "durationInFrames": round(duration * FPS),
            "wordTimings": part_timings,
            "_wav": slot_wav,  # internal only — stripped before manifest
            "_duration": duration,  # internal only
        }
        if "index" in slot:
            scene["index"] = slot["index"]
        if "meta" in slot:
            scene["meta"] = slot["meta"]
        if role == "outro":
            scene["codeOutro"] = True
            scene["crossLink"] = CROSS_LINK.get(args.style, "")
        if ov.get("bigCaption"):
            scene["bigCaption"] = ov["bigCaption"]
        if ov.get("bigCaptionColor"):
            scene["bigCaptionColor"] = ov["bigCaptionColor"]
        if ov.get("subtitleColor"):
            scene["subtitleColor"] = ov["subtitleColor"]
        if ov.get("effect"):
            scene["effect"] = ov["effect"]
        # News-style per-scene layout (+ structured layoutData). Fireship
        # scenes never carry layout (load_shot_list already warned).
        if args.style == "news":
            scene["layout"] = ov.get("layout") or NEWS_LAYOUT_DEFAULTS.get(
                role, "breaking-news")
            if ov.get("layoutData"):
                scene["layoutData"] = ov["layoutData"]
        # X-style per-shot caption lines ([{text, color}]) — lines win
        # over bigCaption in the X composition. Fireship collage
        # mediaList (2-4 media) — mediaList wins over single media in
        # GenericScene.
        if ov.get("lines"):
            scene["lines"] = ov["lines"]
        if ov.get("mediaList"):
            scene["mediaList"] = ov["mediaList"]
        if ov.get("media"):
            scene["media"] = ov["media"]
        elif (args.meme_on and args.template == "explainer" and role == "pain"
                and meme_available):
            scene["media"] = {
                "src": "memes/pain-01.mp4",
                "type": "video",
                "position": "fullscreen",
            }
        # News style needs a visual per shot (FB rule) — warn when a
        # content scene has no media at all (checked AFTER media is
        # assigned, so a shot-list media silences the warning).
        if (args.style == "news" and role in ("headline", "event", "why", "action")
                and "media" not in scene and "mediaList" not in scene):
            warnings.append(
                f"{scene_id} (news): no media — FB news style needs a "
                "visual per shot (image/chart/footage/screenshot)."
            )
        scenes.append(scene)
        log(f"{scene_id}: {duration:.2f}s -> {scene['durationInFrames']} frames "
            f"[{role}] {text[:60]}")

    # --- Fireship pacing: split long scenes into sub-shots -------------
    final_scenes = []
    for scene in scenes:
        # Fireship pacing (split long scenes) applies ONLY to the
        # fireship style. News scenes are layout cards (one card per
        # scene — splitting breaks the layout + loses the outro end
        # card). X style: each script line IS one shot — never split.
        chunks = None
        if args.style == "fireship":
            chunks = split_scene_chunks(
                scene["text"], scene.get("wordTimings") or [],
                scene["_duration"], args.max_shot_sec)
        if not chunks:
            final_scenes.append(scene)
            continue
        log(f"{scene['id']}: splitting {scene['_duration']:.2f}s into "
            f"{len(chunks)} shots (max {args.max_shot_sec}s/shot)")
        warnings.append(
            f"{scene['id']}: split into {len(chunks)} shots "
            f"(>{args.max_shot_sec}s scene, Fireship pacing)."
        )
        for j, (ctext, s, e, wt) in enumerate(chunks):
            chunk_wav = os.path.join(
                audio_dir, f"{scene['id']}s{j + 1}.wav")
            chunk_dur = slice_wav(scene["_wav"], s, e, chunk_wav)
            sub = {
                "id": f"{scene['id']}s{j + 1}",
                "role": scene["role"],
                "text": ctext,
                "headline": headline_for(ctext),
                "audioPath": f"audio/{args.run_id}/{scene['id']}s{j + 1}.wav",
                "durationInFrames": round(chunk_dur * FPS),
                "wordTimings": wt,
            }
            if j == 0:
                # First sub-shot keeps the scene's display overrides.
                for key in ("bigCaption", "bigCaptionColor", "subtitleColor",
                            "effect", "media", "index", "meta", "codeOutro",
                            "layout", "layoutData", "lines", "mediaList",
                            "crossLink"):
                    if key in scene:
                        sub[key] = scene[key]
            elif args.style == "news":
                # News-style continuation sub-shots render as a clean
                # text card (breaking-news), NOT as a stat-callout with
                # no value data (the role default would be misleading).
                sub["layout"] = "breaking-news"
            final_scenes.append(sub)

    # Strip internal keys before writing the manifest.
    for s in final_scenes:
        s.pop("_wav", None)
        s.pop("_duration", None)

    total_frames = sum(
        s["durationInFrames"] + (10 if j == len(final_scenes) - 1 else 3)
        for j, s in enumerate(final_scenes)
    )
    manifest = {
        "version": "video-tools-v4-multi-style",
        "style": args.style,
        "template": args.template,
        "brand": args.brand,
        "memeOn": args.meme_on,
        "voice": voice_label,
        "fps": FPS,
        "warnings": warnings,
        "scenes": final_scenes,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    for w in warnings:
        warn(w)
    log(f"Manifest -> {args.out}: {len(final_scenes)} scenes "
        f"({len(scenes)} pre-split), "
        f"{total_frames} frames ({total_frames / FPS:.1f}s), "
        f"brand={args.brand!r}, voice={voice_label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
