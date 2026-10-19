#!/usr/bin/env python3
"""video tools v4 (multi-style) — internal production GUI (tkinter, stdlib only).

Internal production tool for Minh's own channel (NOT a product for
non-tech customers). The GUI drives the video pipeline:
  1. Script box (textarea, English, 1 sentence/line).
  2. Style picker: Fireship (YouTube) / News (Facebook) / X (Short #8/#9).
     Template picker (Explainer / Listicle / News — news style forces
     template=news, X style forces template=x).
  3. Channel name (default "BRONZE BASE") + Meme on/off checkbox.
  4. Shot list (optional JSON — big captions + media + news layouts +
     X lines + media-pool refs "pool:<tag>").
  5. Voice — FREE ONLY (Minh locked 17/10: ElevenLabs is OUT, even paid):
     SAPI (draft) / Silence (caption-only, X style) / External WAV +
     timings (recorded voice / Edge TTS).
  6. Render button -> plain-language progress -> "Open video" button.
  7. Export timeline button -> EDL (Premiere/DaVinci) + FCPXML (Final Cut)
     for the last render (export_timeline.py, from the manifest).

No terminal window: launch with `pythonw gui.py` on Windows. Subprocess
calls hide their consoles on Windows (CREATE_NO_WINDOW). Errors are shown
in plain language + written to the warnings file — NEVER a stack trace.

Usage:
  pythonw gui.py            # Windows (no console)
  python3 gui.py            # dev / Linux (SAPI voice will fail on Linux;
                             # the GUI shows a plain-language error)
  python3 gui.py --smoke-test   # headless self-check (builds UI, quits)
"""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD_PROPS = os.path.join(HERE, "build_props.py")
RENDER_JS = os.path.join(HERE, "scripts", "render.mjs")


def _runtime_paths():
    """Resolve bundled runtimes.

    On Windows (installed via the NSIS installer) the runtimes live inside
    the app folder: node/node.exe, chrome/chrome-headless-shell.exe,
    ffmpeg/ffmpeg.exe. On other platforms (dev / Linux) fall back to the
    system PATH / CHROME_BIN env, exactly as before.

    FIX 19/10: the test package (zip, no installer) has NO bundled
    runtimes — the old code still returned the bundled paths, which do
    not exist, so render failed with a generic error. Now: a bundled
    binary is used ONLY if the file actually exists, otherwise fall back
    to the system PATH (node / ffmpeg) or None (Chrome -> Remotion
    default discovery)."""
    if sys.platform == "win32":
        def _bundled(sub, fallback):
            p = os.path.join(HERE, sub)
            return p if os.path.exists(p) else fallback
        return {
            "node": _bundled(os.path.join("node", "node.exe"), "node"),
            "chrome": _bundled(
                os.path.join("chrome", "chrome-headless-shell.exe"), None),
            "ffmpeg": _bundled(
                os.path.join("ffmpeg", "ffmpeg.exe"), None),
        }
    return {"node": "node", "chrome": None, "ffmpeg": None}


RUNTIME = _runtime_paths()

TEMPLATE_DESCRIPTIONS = {
    "explainer": "Explainer: for ideas and how-it-works videos.",
    "listicle": "Listicle: for lists — '5 ways…', '3 mistakes…'.",
    "news": "News: for news, no memes.",
}

STYLE_DESCRIPTIONS = {
    "fireship": "Fireship (YouTube): Fireship grammar — pop-in captions, hard cuts, media slots + collage.",
    "news": "News (Facebook): 7 news layouts (breaking-news, stat-callout, split-screen, quote-card, listicle, big-number, action-card) + verdict outro.",
    "x": "X (Short #8/#9): pixel font, GIF fullscreen/fit, hard cuts, ~30s, caption-only + quote punchline + ship it.",
}

VOICE_DESCRIPTIONS = {
    "sapi": "SAPI — flat draft voice, zero config (Windows).",
    "silence": "Silence — caption-only, no audio (X style; durations from shot-list durationSec, else 3.0s).",
    "external": "External WAV + timings — recorded voice / Edge TTS output.",
}

STATUS_TEXT = {
    "voice": "Reading voice…",
    "build": "Building visuals…",
    "done": "Done!",
}


class PipelineError(Exception):
    """Plain-language error for the customer. Details go to the warnings
    file, never to the customer-facing dialog."""


def parse_script_text(text):
    """Split pasted script text into sentences (1 non-empty line each)."""
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def default_output_dir():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    base = desktop if os.path.isdir(desktop) else os.path.expanduser("~")
    return os.path.join(base, "Video Tools")


def open_path(path):
    """Open a file/folder with the OS default app."""
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606 — path comes from our own output dir
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def _subprocess_kwargs():
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def run_pipeline(script_text, template, brand, meme_on, output_dir,
                 voice_backend="sapi", on_status=None,
                 shot_list="", voice_wav="", voice_timings="",
                 style="fireship"):
    """Run the full chain: build_props.py -> render.mjs -> MP4.
    Returns (mp4_path, warnings_path, manifest_path). Raises PipelineError with a
    plain-language message on any failure; the full traceback is written
    to the warnings file."""
    sentences = parse_script_text(script_text)
    if not sentences:
        raise PipelineError(
            "Your script is empty. Paste your script — one sentence per line — "
            "then press Render."
        )
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(output_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    script_path = os.path.join(run_dir, "script.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sentences) + "\n")
    manifest_path = os.path.join(run_dir, "manifest.json")
    mp4_path = os.path.join(run_dir, "sivo.mp4")
    warnings_path = mp4_path + ".warnings.json"

    def status(stage):
        if on_status:
            on_status(stage)

    try:
        status("voice")
        # "external" is a GUI-only label: the builder has no external
        # backend — the external WAV (--voice-wav) wins over
        # --voice-backend there, so pass sapi as the placeholder.
        effective_backend = "sapi" if voice_backend == "external" else voice_backend
        cmd = [sys.executable, BUILD_PROPS, script_path,
               "--out", manifest_path, "--public-dir",
               os.path.join(HERE, "public"),
               "--run-id", run_id,
               "--brand", brand,
               "--style", style,
               "--template", template,
               "--voice-backend", effective_backend]
        if meme_on:
            cmd.append("--meme-on")
        if shot_list:
            cmd += ["--shot-list", shot_list]
        if voice_wav:
            # External voice wins over --voice-backend in build_props.py.
            cmd += ["--voice-wav", voice_wav]
            if voice_timings:
                cmd += ["--voice-timings", voice_timings]
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=600, env=None,
                             **_subprocess_kwargs())
        if res.returncode != 0:
            err = res.stderr[-2000:] or res.stdout[-2000:]
            raise RuntimeError(
                f"build_props.py failed (exit {res.returncode}):\n{err}"
            )
        status("build")
        cmd = [RUNTIME["node"], RENDER_JS, "--manifest", manifest_path,
               "--out", mp4_path]
        render_env = None
        if RUNTIME["chrome"]:
            # Bundled Chrome for Testing (Windows installer layout).
            cmd += ["--chrome", RUNTIME["chrome"]]
        if RUNTIME["ffmpeg"]:
            # Bundled ffmpeg: render.mjs reads FFMPEG_BIN, never PATH.
            render_env = dict(os.environ)
            render_env["FFMPEG_BIN"] = RUNTIME["ffmpeg"]
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=3600, env=render_env, **_subprocess_kwargs())
        if res.returncode != 0:
            raise RuntimeError(
                f"render.mjs failed (exit {res.returncode}):\n"
                f"{res.stderr[-2000:] or res.stdout[-2000:]}"
            )
        if not os.path.exists(mp4_path):
            raise RuntimeError("Render finished but no video file was created.")
        status("done")
        return mp4_path, warnings_path, manifest_path
    except PipelineError:
        raise
    except Exception as e:  # noqa: BLE001 — details go to the warnings file
        import traceback
        detail_path = os.path.join(run_dir, "error-details.txt")
        with open(detail_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        if "powershell" in str(e).lower() or "sapi" in str(e).lower():
            raise PipelineError(
                "Voice could not be created on this computer. "
                "SAPI voice needs Windows.\n"
                f"Details saved to: {detail_path}"
            ) from e
        raise PipelineError(
            "Something went wrong while making your video. "
            "Nothing was charged and no video was made.\n"
            f"Details saved to: {detail_path}"
        ) from e


class SivoGui:
    def __init__(self, root):
        self.root = root
        self.root.title("video tools (internal)")
        # FIX 19/10: window was FIXED at 660x1000 + not resizable — on a
        # laptop screen the bottom (Render button) fell below the taskbar
        # and could not be reached. Now: resizable + scrollable + the
        # initial height fits the actual screen.
        self.root.resizable(True, True)
        self.root.minsize(620, 400)
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"660x{min(1000, max(400, screen_h - 60))}")
        # Scrollable container: every widget below is parented to
        # `scroll_frame` (via the rebinding of local `root`), so the whole
        # form scrolls when the window is shorter than the content.
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical",
                                  command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=scroll_frame,
                                         anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(window_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(-int(event.delta / 120), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows / macOS
        canvas.bind_all("<Button-4>",  # Linux: scroll up
                        lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>",  # Linux: scroll down
                        lambda e: canvas.yview_scroll(1, "units"))
        root = scroll_frame  # rebind: all widgets below parent here
        self.result_queue = queue.Queue()
        self.mp4_path = None
        self.warnings_path = None
        self.manifest_path = None

        self.style_var = tk.StringVar(value="fireship")
        self.template_var = tk.StringVar(value="explainer")
        self.brand_var = tk.StringVar(value="BRONZE BASE")
        self.meme_var = tk.BooleanVar(value=True)
        self.shot_list_var = tk.StringVar(value="")
        self.voice_backend_var = tk.StringVar(value="sapi")
        self.voice_wav_var = tk.StringVar(value="")
        self.voice_timings_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Paste your script, then press Render.")
        self.out_var = tk.StringVar(value="")

        pad = {"padx": 14, "pady": 6}
        ttk.Label(root, text="1. Your script (English, one sentence per line):",
                  font=("", 11, "bold")).pack(anchor="w", **pad)
        self.script_box = tk.Text(root, height=10, width=72, wrap="word")
        self.script_box.pack(fill="x", **pad)
        self.script_box.insert("1.0",
            "Your money can grow while you sleep.\n"
            "Compound interest means you earn interest on your interest too.\n"
            "Start early, and time does most of the heavy lifting for you.")
        self.script_box.tag_add("sel", "1.0", "end")  # sample selected: type to replace

        ttk.Label(root, text="2. Style:", font=("", 11, "bold")).pack(anchor="w", **pad)
        style_frame = ttk.Frame(root)
        style_frame.pack(anchor="w", **pad)
        for value, label in (("fireship", "Fireship"),
                             ("news", "News"),
                             ("x", "X")):
            ttk.Radiobutton(style_frame, text=label, variable=self.style_var,
                            value=value, command=self._on_style_change).pack(side="left", padx=8)
        self.style_desc = ttk.Label(root, text=STYLE_DESCRIPTIONS["fireship"],
                                    foreground="gray", wraplength=600)
        self.style_desc.pack(anchor="w", **pad)

        ttk.Label(root, text="3. Template:", font=("", 11, "bold")).pack(anchor="w", **pad)
        tpl_frame = ttk.Frame(root)
        tpl_frame.pack(anchor="w", **pad)
        self.tpl_radios = []
        for value, label in (("explainer", "Explainer"),
                             ("listicle", "Listicle"),
                             ("news", "News")):
            rb = ttk.Radiobutton(tpl_frame, text=label, variable=self.template_var,
                                 value=value, command=self._on_template_change)
            rb.pack(side="left", padx=8)
            self.tpl_radios.append(rb)
        self.tpl_desc = ttk.Label(root, text=TEMPLATE_DESCRIPTIONS["explainer"],
                                  foreground="gray")
        self.tpl_desc.pack(anchor="w", **pad)

        ttk.Label(root, text="4. Your channel name (optional — shows as a small badge):",
                  font=("", 11, "bold")).pack(anchor="w", **pad)
        ttk.Entry(root, textvariable=self.brand_var, width=60).pack(anchor="w", **pad)
        self.meme_check = ttk.Checkbutton(root, text="Meme: On",
                                          variable=self.meme_var,
                                          command=self._on_meme_toggle)
        self.meme_check.pack(anchor="w", **pad)

        ttk.Label(root, text="5. Shot list (optional JSON — big captions + media + news layouts):",
                  font=("", 11, "bold")).pack(anchor="w", **pad)
        shot_frame = ttk.Frame(root)
        shot_frame.pack(fill="x", **pad)
        ttk.Entry(shot_frame, textvariable=self.shot_list_var, width=52).pack(side="left")
        ttk.Button(shot_frame, text="Browse…",
                   command=lambda: self._pick_file(self.shot_list_var,
                                                   "Shot list JSON",
                                                   [("JSON", "*.json")])).pack(side="left", padx=6)
        ttk.Label(root, text="Example: {\"shots\": [{\"scene\": 1, \"bigCaption\": \"YOUR MONEY SLEEPS?\", \"media\": \"media/piggy-bank.jpg\", \"mediaType\": \"image\"}]}",
                  foreground="gray", wraplength=600).pack(anchor="w", **pad)
        ttk.Label(root, text="Media pool: use \"media\": \"pool:<tag>\" (e.g. pool:facepalm) to pull a reusable GIF/clip from media-pool/pool.json — no GIF hunting for hot-news X clips.",
                  foreground="gray", wraplength=600).pack(anchor="w", **pad)

        ttk.Label(root, text="6. Voice:", font=("", 11, "bold")).pack(anchor="w", **pad)
        voice_frame = ttk.Frame(root)
        voice_frame.pack(anchor="w", **pad)
        for value, label in (("sapi", "SAPI (draft)"),
                             ("silence", "Silence (caption-only)"),
                             ("external", "External WAV")):
            ttk.Radiobutton(voice_frame, text=label, variable=self.voice_backend_var,
                            value=value, command=self._on_voice_change).pack(side="left", padx=8)
        self.voice_desc = ttk.Label(root, text=VOICE_DESCRIPTIONS["sapi"],
                                    foreground="gray", wraplength=600)
        self.voice_desc.pack(anchor="w", **pad)

        ttk.Label(root, text="External voice (WAV + timings — recorded voice / Edge TTS):").pack(anchor="w", **pad)
        wav_frame = ttk.Frame(root)
        wav_frame.pack(fill="x", **pad)
        ttk.Label(wav_frame, text="WAV:", width=8).pack(side="left")
        ttk.Entry(wav_frame, textvariable=self.voice_wav_var, width=44).pack(side="left")
        ttk.Button(wav_frame, text="Browse…",
                   command=lambda: self._pick_file(self.voice_wav_var,
                                                   "Voice WAV",
                                                   [("WAV", "*.wav")])).pack(side="left", padx=6)
        tim_frame = ttk.Frame(root)
        tim_frame.pack(fill="x", **pad)
        ttk.Label(tim_frame, text="Timings:", width=8).pack(side="left")
        ttk.Entry(tim_frame, textvariable=self.voice_timings_var, width=44).pack(side="left")
        ttk.Button(tim_frame, text="Browse…",
                   command=lambda: self._pick_file(self.voice_timings_var,
                                                   "Voice timings JSON",
                                                   [("JSON", "*.json")])).pack(side="left", padx=6)

        ttk.Label(root, text="7. Render:", font=("", 11, "bold")).pack(anchor="w", **pad)
        self.render_btn = ttk.Button(root, text="Render", command=self._on_render)
        self.render_btn.pack(anchor="w", **pad)
        self.progress = ttk.Progressbar(root, mode="indeterminate", length=560)
        self.progress.pack(fill="x", **pad)
        ttk.Label(root, textvariable=self.status_var).pack(anchor="w", **pad)
        self.open_btn = ttk.Button(root, text="Open video", command=self._on_open,
                                   state="disabled")
        self.open_btn.pack(anchor="w", **pad)
        self.export_btn = ttk.Button(root, text="Export timeline (EDL + FCPXML)",
                                     command=self._on_export_timeline,
                                     state="disabled")
        self.export_btn.pack(anchor="w", **pad)
        ttk.Label(root, textvariable=self.out_var, foreground="gray",
                  wraplength=600).pack(anchor="w", **pad)
        self.root.after(200, self._poll_queue)

    def _on_style_change(self):
        style = self.style_var.get()
        self.style_desc.config(text=STYLE_DESCRIPTIONS[style])
        if style == "news":
            # News style forces template=news in the builder — lock the
            # template radios + meme (memes only apply to Explainer).
            self.template_var.set("news")
            for rb in self.tpl_radios:
                rb.config(state="disabled")
            self.meme_check.config(state="disabled")
        elif style == "x":
            # X style forces template=x in the builder (1 line = 1 shot)
            # — lock the template radios + meme (no memes in X style).
            for rb in self.tpl_radios:
                rb.config(state="disabled")
            self.tpl_desc.config(
                text="X style: template forced to x (1 line = 1 shot).")
            self.meme_check.config(state="disabled")
        else:
            for rb in self.tpl_radios:
                rb.config(state="normal")
            self._on_template_change()  # restores meme state for template

    def _on_voice_change(self):
        self.voice_desc.config(
            text=VOICE_DESCRIPTIONS[self.voice_backend_var.get()])

    def _on_template_change(self):
        tpl = self.template_var.get()
        self.tpl_desc.config(text=TEMPLATE_DESCRIPTIONS[tpl])
        # Memes only apply to Explainer — disable the checkbox otherwise
        # so the customer never thinks a meme is coming for Listicle/News.
        if tpl == "explainer":
            self.meme_check.config(state="normal")
        else:
            self.meme_check.config(state="disabled")

    def _pick_file(self, var, title, filetypes):
        from tkinter import filedialog
        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if path:
            var.set(path)

    def _on_meme_toggle(self):
        self.meme_check.config(text="Meme: On" if self.meme_var.get() else "Meme: Off")

    def _on_render(self):
        script = self.script_box.get("1.0", "end")
        if not parse_script_text(script):
            messagebox.showerror(
                "Script is empty",
                "Your script is empty. Paste your script — one sentence per "
                "line — then press Render.")
            return
        self.render_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self.progress.start(10)
        self.status_var.set(STATUS_TEXT["voice"])
        out_dir = default_output_dir()
        args = (script, self.template_var.get(), self.brand_var.get().strip(),
                self.meme_var.get(), out_dir)
        kwargs = {
            "shot_list": self.shot_list_var.get().strip(),
            "voice_wav": self.voice_wav_var.get().strip(),
            "voice_timings": self.voice_timings_var.get().strip(),
            "style": self.style_var.get(),
            "voice_backend": self.voice_backend_var.get(),
        }

        def worker():
            try:
                mp4, warnings, manifest = run_pipeline(
                    *args, on_status=lambda stage: self.result_queue.put(("status", stage)),
                    **kwargs)
                self.result_queue.put(("done", mp4, warnings, manifest))
            except PipelineError as e:
                self.result_queue.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                item = self.result_queue.get_nowait()
                if item[0] == "status":
                    self.status_var.set(STATUS_TEXT.get(item[1], item[1]))
                elif item[0] == "done":
                    _, mp4, warnings, manifest = item
                    self.mp4_path = mp4
                    self.warnings_path = warnings
                    self.manifest_path = manifest
                    self.progress.stop()
                    self.status_var.set(STATUS_TEXT["done"])
                    self.out_var.set(f"Saved to: {mp4}")
                    self.open_btn.config(state="normal")
                    self.export_btn.config(state="normal")
                    self.render_btn.config(state="normal")
                elif item[0] == "error":
                    self.progress.stop()
                    self.status_var.set("Something went wrong — see the message.")
                    self.render_btn.config(state="normal")
                    messagebox.showerror("Something went wrong", item[1])
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _on_open(self):
        if self.mp4_path and os.path.exists(self.mp4_path):
            open_path(self.mp4_path)

    def _on_export_timeline(self):
        """Export the last render's manifest to EDL + FCPXML (edit in
        Premiere / DaVinci / Final Cut). Plain-language errors only."""
        if not self.mp4_path or not self.manifest_path:
            messagebox.showerror(
                "Nothing to export",
                "Render a video first, then export its timeline.")
            return
        exporter = os.path.join(HERE, "export_timeline.py")
        try:
            res = subprocess.run(
                [sys.executable, exporter, "--manifest", self.manifest_path,
                 "--video", self.mp4_path],
                capture_output=True, text=True, timeout=120,
                **_subprocess_kwargs())
        except Exception as e:  # noqa: BLE001 — plain-language dialog
            messagebox.showerror(
                "Export failed",
                f"Could not run the timeline exporter: {e}")
            return
        if res.returncode != 0:
            messagebox.showerror(
                "Export failed",
                "The timeline exporter could not read this render.\n"
                f"{(res.stderr or res.stdout)[-800:]}")
            return
        edl = os.path.splitext(self.mp4_path)[0] + ".edl"
        fcpxml = os.path.splitext(self.mp4_path)[0] + ".fcpxml"
        self.out_var.set(f"Timeline exported:\n{edl}\n{fcpxml}")
        messagebox.showinfo(
            "Timeline exported",
            "Two files were saved next to your video:\n"
            f"{os.path.basename(edl)} — Premiere / DaVinci\n"
            f"{os.path.basename(fcpxml)} — Final Cut Pro")


def main():
    if "--smoke-test" in sys.argv:
        # Headless self-check: build the UI, quit. Used under xvfb-run.
        root = tk.Tk()
        SivoGui(root)
        root.after(600, root.destroy)
        root.mainloop()
        print("GUI smoke test: UI built OK")
        return 0
    root = tk.Tk()
    SivoGui(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
