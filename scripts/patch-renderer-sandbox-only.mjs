// SANDBOX-ONLY SCAFFOLDING — DO NOT SHIP IN THE INSTALLER.
//
// This VM's network stack accepts TCP connects to 0.0.0.0 / :: on ANY port,
// so Remotion's "is this port free?" check always reports busy
// ("No available ports found") and rendering fails before it starts.
// This script patches @remotion/renderer (ESM + CJS copies) so getHostsToTry
// probes only loopback hosts (::1, 127.0.0.1), which behave normally here.
//
// On a REAL customer Windows machine the port scan works normally, so the
// installer must NOT apply this patch. It is applied here only so Phase 1
// can render on this Linux VM. Idempotent: skips files already patched.
// Any `npm ci` / `npm install` erases it (node_modules is not shipped).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RENDERER = path.join(HERE, "..", "node_modules", "@remotion", "renderer");

const PATCH_BODY = (filterExpr) => `// SANDBOX PATCH (this VM only — see scripts/patch-renderer-sandbox-only.mjs):
  // this VM's network stack accepts TCP connects to 0.0.0.0 / :: on ANY port,
  // so Remotion's "is this port free?" check always reports busy
  // ("No available ports found"). Only probe loopback hosts, which behave
  // normally here. DO NOT SHIP — real Windows machines don't need this.
  return [
    hasIPv6LoopbackAddress(flattened) ? "::1" : null,
    hasIpv4LoopbackAddress(flattened) ? "127.0.0.1" : null,
  ].filter(${filterExpr});`;

function patchFile(file, startMarker, filterExpr) {
  if (!fs.existsSync(file)) {
    console.log(`skip (missing): ${file}`);
    return;
  }
  const src = fs.readFileSync(file, "utf8");
  if (src.includes("SANDBOX PATCH")) {
    console.log(`already patched: ${file}`);
    return;
  }
  const start = src.indexOf(startMarker);
  if (start === -1) {
    throw new Error(`marker not found in ${file}: ${startMarker}`);
  }
  // The function body ends at the first "\n};" after the start marker.
  const end = src.indexOf("\n};", start);
  if (end === -1) {
    throw new Error(`function end not found in ${file}`);
  }
  const bodyStart = src.indexOf("{", start) + 1;
  const patched =
    src.slice(0, bodyStart) + "\n  " + PATCH_BODY(filterExpr) + src.slice(end);
  fs.writeFileSync(file, patched);
  console.log(`patched: ${file}`);
}

// CJS: `const getHostsToTry = (flattened) => { ... };`
patchFile(
  path.join(RENDERER, "dist", "port-config.js"),
  "const getHostsToTry = (flattened) => {",
  "truthy_1.truthy"
);
// ESM: `var getHostsToTry = (flattened) => { ... };` (bundled index.mjs)
patchFile(
  path.join(RENDERER, "dist", "esm", "index.mjs"),
  "var getHostsToTry = (flattened) => {",
  "truthy"
);
console.log("Sandbox renderer patch applied (VM-only, do not ship).");
