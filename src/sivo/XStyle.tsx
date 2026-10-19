import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Series,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { SivoBrand } from "./components";
import type { SivoManifest, SivoMedia, SivoScene } from "./types";

// ---------------------------------------------------------------------------
// X style (v4) — the Short #8 / Short #9 grammar, ported to the tool's
// engine (Remotion). NOT the PIL frame pipeline — same GRAMMAR, different
// renderer:
//   - 1080x1920, #0a0a0a background, 100% hard cuts (Series).
//   - One script line = one shot, ~3-6s each, total ~30s.
//   - Big pixel-font caption (VT323): one line per `lines` entry, per-line
//     color, thick black outline (multi-offset text-shadow, like the PIL
//     offset draws). Caption is TOP (y=250) when a GIF is present,
//     vertically CENTERED when text-only, ON TOP of fullscreen GIFs.
//   - GIF/media: fullscreen = cover, caption on top, appears in the LAST
//     2s of the shot (Short #9 rule); fit = contain below the caption,
//     no crop, from frame 0 (Short #8 rule); corner -> treated as fit.
//   - Deadpan single-word shots: just a 1-line `lines` entry.
//   - Quote punchline end card: the outro shot's lines ARE the quote,
//     with a small "FICTIONAL QUOTE" tag underneath (honest labeling —
//     the quote is invented, never presented as a real quote).
//   - Caption-only: NO subtitle (the big captions ARE the content), NO
//     voice. Audio element carries the silence WAV (or a voice WAV if
//     the builder was run with a voice backend).
// ---------------------------------------------------------------------------

const BG = "#0a0a0a";
const BASE_FONT = 130;
const LINE_HEIGHT = 150;

const X_COLORS: Record<string, string> = {
  WHITE: "#ffffff",
  RED: "#ef4444",
  ORANGE: "#ff6b35",
  YELLOW: "#ffd700",
  GREEN: "#58d68d",
  GRAY: "#a1a1aa",
  DARKGRAY: "#646464",
};

function xColor(color: string | undefined): string {
  if (!color) return "#ffffff";
  if (color.startsWith("#")) return color;
  return X_COLORS[color.toUpperCase()] ?? "#ffffff";
}

function captionLines(scene: SivoScene): { text: string; color: string }[] {
  if (scene.lines && scene.lines.length > 0) {
    return scene.lines.map((l) => ({
      text: l.text,
      color: xColor(l.color),
    }));
  }
  // Fallback: bigCaption (single line) when no shot-list lines.
  if (scene.bigCaption) {
    return [{ text: scene.bigCaption, color: xColor(scene.bigCaptionColor) }];
  }
  // Last resort: the scene text itself.
  return [{ text: scene.text, color: "#ffffff" }];
}

function fontSizeFor(lines: { text: string }[]): number {
  const maxChars = Math.max(...lines.map((l) => l.text.length), 1);
  // VT323 advance width ~= 0.5em; keep the longest line inside 1000px.
  return Math.min(BASE_FONT, Math.floor(1000 / (0.5 * maxChars)));
}

function XMedia({
  media,
  mode,
}: {
  media: SivoMedia;
  mode: "cover" | "contain";
}): React.ReactElement {
  const style: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: mode,
  };
  if (media.type === "video") {
    return (
      <OffthreadVideo
        src={staticFile(media.src)}
        style={style}
        volume={0}
        playbackRate={1}
      />
    );
  }
  return <Img src={staticFile(media.src)} style={style} />;
}

function XShot({ scene }: { scene: SivoScene }): React.ReactElement {
  const frame = useCurrentFrame();
  const lines = captionLines(scene);
  const fontSize = fontSizeFor(lines);
  const media = scene.media;
  const isFullscreen = media?.position === "fullscreen";
  const isFit = media && (media.position === "fit" || media.position === "corner");
  const isOutro = scene.role === "outro";

  // Fullscreen media pops in during the LAST 2s of the shot (Short #9).
  const fullscreenDelay = Math.max(0, scene.durationInFrames - 60);
  const showFullscreen = isFullscreen && frame >= fullscreenDelay;

  // Caption vertical placement: top when any media shows / is fit,
  // centered when text-only.
  const centered = !media;
  const topY = 250;

  // Outro + fullscreen media (the micdrop vampire GIF): split the text
  // around the GIF's baked-in "Owned." (measured: viewport y 365-513,
  // x 18-82%) — quote ABOVE it, FICTIONAL QUOTE + "ship it." in the
  // white gap BELOW it (y 550-700; vampire head starts ~810).
  // Tuned for the micdrop GIF; a different outro GIF needs re-measuring.
  const outroFullscreen = isOutro && isFullscreen;
  const OUTRO_TOP = 110;
  const OUTRO_GAP_TOP = 550;
  const OUTLINE_SM =
    "-3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000, " +
    "-3px 0 0 #000, 3px 0 0 #000, 0 -3px 0 #000, 0 3px 0 #000";
  const OUTLINE_LG =
    "-4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000, 4px 4px 0 #000, " +
    "-4px 0 0 #000, 4px 0 0 #000, 0 -4px 0 #000, 0 4px 0 #000";

  const lineDivs = lines.map((line, i) => (
    <div
      key={i}
      style={{
        fontFamily: "'VT323', monospace",
        fontSize,
        lineHeight: `${LINE_HEIGHT * (fontSize / BASE_FONT)}px`,
        color: line.color,
        textAlign: "center",
        whiteSpace: "nowrap",
        textShadow: OUTLINE_LG,
      }}
    >
      {line.text}
    </div>
  ));
  const fictionalTag = (
    <div
      style={{
        fontFamily: "'VT323', monospace",
        fontSize: 44,
        color: "#a1a1aa",
        marginTop: outroFullscreen ? 0 : 30,
        letterSpacing: 4,
        textShadow: OUTLINE_SM,
      }}
    >
      FICTIONAL QUOTE
    </div>
  );
  const shipIt = (
    <div
      style={{
        fontFamily: "'VT323', monospace",
        fontSize: 72,
        color: "#58d68d",
        marginTop: outroFullscreen ? 16 : 24,
        textShadow: OUTLINE_LG,
      }}
    >
      ship it.
    </div>
  );
  const crossLinkDiv = scene.crossLink ? (
    <div
      style={{
        fontFamily: "'VT323', monospace",
        fontSize: 44,
        color: "#a1a1aa",
        marginTop: 24,
        maxWidth: 920,
        textAlign: "center",
      }}
    >
      {scene.crossLink}
    </div>
  ) : null;

  const captionBlock = outroFullscreen ? (
    <>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: OUTRO_TOP,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 0,
        }}
      >
        {lineDivs}
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: OUTRO_GAP_TOP,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 0,
        }}
      >
        {fictionalTag}
        {shipIt}
        {crossLinkDiv}
      </div>
    </>
  ) : (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: centered ? undefined : topY,
        bottom: centered ? 0 : undefined,
        height: centered ? "100%" : undefined,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: centered ? "center" : "flex-start",
        gap: 0,
      }}
    >
      {lineDivs}
      {isOutro && fictionalTag}
      {isOutro && shipIt}
      {isOutro && crossLinkDiv}
    </div>
  );

  return (
    <AbsoluteFill style={{ backgroundColor: BG }}>
      {showFullscreen && media && (
        <AbsoluteFill>
          <XMedia media={media} mode="cover" />
        </AbsoluteFill>
      )}
      {isFit && media && (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: topY + lines.length * LINE_HEIGHT * (fontSize / BASE_FONT) + 60,
            bottom: 100,
            display: "flex",
            justifyContent: "center",
            alignItems: "flex-start",
          }}
        >
          <div style={{ width: 1080, height: 700, maxWidth: 1080, maxHeight: 700 }}>
            <XMedia media={media} mode="contain" />
          </div>
        </div>
      )}
      {captionBlock}
      {scene.audioPath ? <Audio src={staticFile(scene.audioPath)} /> : null}
    </AbsoluteFill>
  );
}

export const XStyle: React.FC<SivoManifest> = (props) => {
  return (
    <AbsoluteFill style={{ backgroundColor: BG }}>
      <style>{`@font-face { font-family: 'VT323'; src: url(${staticFile(
        "fonts/VT323.ttf"
      )}); }`}</style>
      <Series>
        {props.scenes.map((scene) => (
          <Series.Sequence
            key={scene.id}
            durationInFrames={scene.durationInFrames}
          >
            <XShot scene={scene} />
          </Series.Sequence>
        ))}
      </Series>
      <SivoBrand brand={props.brand} />
    </AbsoluteFill>
  );
};
