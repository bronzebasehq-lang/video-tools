// SIVO-Remotion Phase 1 — render script.
// Generalized from the proven render-local.mjs of the Docker test:
//  - bundles via the supported bundle() API
//  - serves the bundle on 127.0.0.1 itself (Range support for OffthreadVideo)
//  - calls the supported renderMedia() API with explicit serveUrl +
//    browserExecutable. NEVER `npx remotion render` CLI (port-scan issues).
// Then normalizes loudness to -16 LUFS with ffmpeg and writes <out>.warnings.json.
// Usage:
//   node scripts/render.mjs --manifest out/manifest-brand.json --out out/poc-brand.mp4
//   node scripts/render.mjs --manifest out/manifest.json --out out/poc.mp4 \
//       --chrome /path/to/chrome --port 49153
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { bundle } from "@remotion/bundler";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(__dirname, "..");

function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : def;
}

const MANIFEST_PATH = path.resolve(arg("--manifest", ""));
const OUT = path.resolve(arg("--out", ""));

// Chrome resolution order: --chrome arg > CHROME_BIN env > bundled
// Windows installer layout (chrome/chrome-headless-shell.exe next to the
// project) > Linux dev fallback. The installer ALWAYS passes --chrome,
// so the fallbacks only matter for dev runs.
function bundledChrome() {
  const candidates = [
    path.join(PROJECT, "chrome", "chrome-headless-shell.exe"),
    path.join(PROJECT, "chrome", "chrome.exe"),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  // FIX 19/10: the old code returned a hardcoded Linux VM path even on
  // Windows when no bundled Chrome exists — Remotion then failed because
  // the browser executable did not exist. Now: Linux keeps its dev
  // fallback; other platforms return undefined so Remotion discovers the
  // system Chrome itself.
  if (process.platform === "linux") {
    return "/home/hatch/workspace/remotion-test/chrome-141/chrome-linux64/chrome";
  }
  return undefined;
}
const CHROME = arg("--chrome", process.env.CHROME_BIN || bundledChrome());
// ffmpeg resolution: FFMPEG_BIN env (set by gui.py to the bundled
// ffmpeg.exe on Windows) > bare "ffmpeg" from PATH (dev).
const FFMPEG = process.env.FFMPEG_BIN || "ffmpeg";
let PORT;
{
  const given = arg("--port", "");
  if (given) {
    PORT = Number(given);
  } else {
    // No port given: pick a free one (two concurrent renders must not
    // collide on a hardcoded default — e.g. GUI + CLI at once).
    const net = await import("node:net");
    const srv = net.createServer();
    await new Promise((resolve) => srv.listen(0, "127.0.0.1", resolve));
    PORT = srv.address().port;
    srv.close();
  }
}
const SERVE_URL = `http://127.0.0.1:${PORT}`;
const TMP_OUT = OUT + ".tmp.mp4";

if (!MANIFEST_PATH || !fs.existsSync(MANIFEST_PATH)) {
  console.error(`ERROR: manifest not found: ${MANIFEST_PATH}`);
  process.exit(1);
}
const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf8"));

const MIME = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".mjs": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".mp4": "video/mp4",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".wasm": "application/wasm",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".map": "application/json",
};

let BUNDLE_DIR = "";

function serveStatic(req, res) {
  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Allow-Private-Network": "true",
      "Access-Control-Allow-Local-Network": "true",
      "Access-Control-Max-Age": "86400",
    });
    res.end();
    return;
  }
  try {
    const urlPath = decodeURIComponent(new URL(req.url, SERVE_URL).pathname);
    let filePath = path.join(BUNDLE_DIR, urlPath);
    if (fs.existsSync(filePath) && fs.statSync(filePath).isDirectory()) {
      filePath = path.join(filePath, "index.html");
    }
    if (!fs.existsSync(filePath)) {
      res.writeHead(404);
      res.end("not found");
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    const type = MIME[ext] || "application/octet-stream";
    const stat = fs.statSync(filePath);
    const range = req.headers.range;
    if (range) {
      const [startStr, endStr] = range.replace(/bytes=/, "").split("-");
      const start = parseInt(startStr, 10) || 0;
      const end = endStr ? parseInt(endStr, 10) : stat.size - 1;
      res.writeHead(206, {
        "Access-Control-Allow-Private-Network": "true",
        "Access-Control-Allow-Local-Network": "true",
        "Access-Control-Allow-Origin": "*",
        "Content-Range": `bytes ${start}-${end}/${stat.size}`,
        "Accept-Ranges": "bytes",
        "Content-Length": end - start + 1,
        "Content-Type": type,
      });
      fs.createReadStream(filePath, { start, end }).pipe(res);
    } else {
      res.writeHead(200, {
        "Access-Control-Allow-Private-Network": "true",
        "Access-Control-Allow-Local-Network": "true",
        "Access-Control-Allow-Origin": "*",
        "Content-Length": stat.size,
        "Content-Type": type,
        "Accept-Ranges": "bytes",
      });
      fs.createReadStream(filePath).pipe(res);
    }
  } catch (e) {
    res.writeHead(500);
    res.end(String(e));
  }
}

function run(cmd, args) {
  // windowsHide: ffmpeg must never flash a console window for the customer
  // (plan section 2.4: the terminal must never be visible).
  const r = spawnSync(cmd, args, { encoding: "utf8", windowsHide: true });
  if (r.status !== 0) {
    throw new Error(`${cmd} ${args.join(" ")} failed:\n${r.stderr || r.stdout}`);
  }
  return r;
}

// Parse loudnorm JSON from ffmpeg stderr. The JSON block follows the
// "[Parsed_loudnorm...]" line; trailing ffmpeg progress lines after the
// closing "}" must NOT be included (JSON.parse fails on them).
function parseLoudnormJson(stderr) {
  const marker = stderr.indexOf("[Parsed_loudnorm");
  if (marker === -1) return null;
  const start = stderr.indexOf("{", marker);
  const end = stderr.indexOf("}", start);
  if (start === -1 || end === -1) return null;
  try {
    return JSON.parse(stderr.slice(start, end + 1));
  } catch {
    return null;
  }
}

const t0 = Date.now();
const timings = {};

console.log("Bundling...");
const tBundle0 = Date.now();
BUNDLE_DIR = await bundle({
  entryPoint: path.join(PROJECT, "src", "index.ts"),
  onProgress: (p) => {
    if (p % 25 === 0) console.log(`bundle ${p}%`);
  },
});
timings.bundle_sec = (Date.now() - tBundle0) / 1000;
console.log(`Bundle at ${BUNDLE_DIR} (${timings.bundle_sec.toFixed(1)}s)`);

const server = http.createServer(serveStatic);
await new Promise((resolve) => server.listen(PORT, "127.0.0.1", resolve));
console.log(`Serving bundle at ${SERVE_URL}`);

const renderWarnings = [];
let composition;

// Phase 4 (multi-style): the composition is picked from manifest.style
// first (style=news -> NewsStyle, style=x -> XStyle), then
// manifest.template for the fireship style. Unknown style/template ->
// WARNING + fall back to Explainer (never a silent wrong render,
// never a crash).
const TEMPLATE_COMPOSITIONS = {
  explainer: "SivoExplainer",
  listicle: "SivoListicle",
  news: "SivoNews",
};
let compositionId;
if (manifest.style === "news") {
  compositionId = "NewsStyle";
} else if (manifest.style === "x") {
  compositionId = "XStyle";
} else {
  compositionId = TEMPLATE_COMPOSITIONS[manifest.template] || "SivoExplainer";
}
if (
  manifest.style &&
  !["fireship", "news", "x"].includes(manifest.style)
) {
  renderWarnings.push(
    `Unknown style "${manifest.style}" — fell back to Explainer.`
  );
}
if (
  !TEMPLATE_COMPOSITIONS[manifest.template] &&
  manifest.style !== "news" &&
  manifest.style !== "x"
) {
  renderWarnings.push(
    `Unknown template "${manifest.template}" — fell back to Explainer.`
  );
}
try {
  composition = await selectComposition({
    serveUrl: SERVE_URL,
    id: compositionId,
    inputProps: manifest,
    browserExecutable: CHROME,
    chromeMode: "chrome-for-testing",
  });
  console.log(
    `Composition: ${composition.id} ${composition.durationInFrames} frames @ ${composition.fps}fps`
  );
  const tRender0 = Date.now();
  await renderMedia({
    composition,
    serveUrl: SERVE_URL,
    codec: "h264",
    outputLocation: TMP_OUT,
    browserExecutable: CHROME,
    chromeMode: "chrome-for-testing",
    concurrency: 1,
    overwrite: true,
    onProgress: ({ progress, renderedFrames }) => {
      if (renderedFrames % 300 === 0 || progress === 1) {
        console.log(`progress ${(progress * 100).toFixed(1)}% (${renderedFrames} frames)`);
      }
    },
  });
  timings.render_sec = (Date.now() - tRender0) / 1000;
  console.log(`Rendered -> ${TMP_OUT} (${timings.render_sec.toFixed(1)}s)`);
} finally {
  server.close();
}

// Loudness: single-pass loudnorm to -16 LUFS (target, plan section 2.3).
console.log("Normalizing loudness to -16 LUFS...");
const tNorm0 = Date.now();
run(FFMPEG, [
  "-y", "-v", "error", "-i", TMP_OUT,
  "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
  "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", OUT,
]);
timings.loudnorm_sec = (Date.now() - tNorm0) / 1000;

// Verify measured loudness of the final file (analysis only).
const probe = run(FFMPEG, [
  "-i", OUT, "-af", "loudnorm=print_format=json", "-f", "null", "-",
]);
const measured = parseLoudnormJson(probe.stderr || "");
if (measured) {
  console.log(
    `Measured loudness: I=${measured.input_i} LUFS, TP=${measured.input_tp} dB, LRA=${measured.input_lra} LU`
  );
} else {
  renderWarnings.push("Could not measure final loudness (loudnorm probe gave no JSON).");
}
try {
  fs.unlinkSync(TMP_OUT);
} catch { /* tmp already gone */ }

timings.total_sec = (Date.now() - t0) / 1000;

// No-lying: warnings file always written next to the output.
const warningsDoc = {
  generatedAt: new Date().toISOString(),
  output: OUT,
  manifestWarnings: manifest.warnings || [],
  renderWarnings,
  render: {
    composition: compositionId,
    durationInFrames: composition.durationInFrames,
    fps: composition.fps,
    brand: manifest.brand,
    voice: manifest.voice,
    measuredLoudness: measured
      ? { I: measured.input_i, TP: measured.input_tp, LRA: measured.input_lra }
      : null,
    timings,
  },
};
fs.writeFileSync(OUT + ".warnings.json", JSON.stringify(warningsDoc, null, 2));
console.log(`DONE -> ${OUT}`);
console.log(`Warnings file -> ${OUT}.warnings.json`);
console.log(`TIMINGS ${JSON.stringify(timings)}`);
