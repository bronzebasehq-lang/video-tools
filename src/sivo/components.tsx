import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  Loop,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { SivoMedia, SivoScene } from "./types";

// ---------------------------------------------------------------------------
// Shared visual grammar — Fireship rebuild (v3).
// Dark bg #0a0a0a, ALL-CAPS pop-in big captions, PLAIN bottom subtitle,
// hard cuts. NO per-word karaoke color change anywhere.
// ---------------------------------------------------------------------------

// Pop-in over 4-6 frames (spring). No typing animation.
export const PopIn: React.FC<{
  children: React.ReactNode;
  delay?: number;
  className?: string;
  style?: React.CSSProperties;
}> = ({ children, delay = 0, className, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({
    frame: frame - delay,
    fps,
    config: { damping: 14, stiffness: 220, mass: 0.5 },
  });
  const opacity = interpolate(frame - delay, [0, 4], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{ transform: `scale(${scale})`, opacity, ...style }}
      className={className}
    >
      {children}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Subtitle (Fireship layer 1): bottom, chunked 5-7 words, PLAIN color.
// The whole subtitle is ONE color for the scene (white, or yellow for a
// joke/punchline scene). Words NEVER change color individually — no
// karaoke. Chunks swap on a hard cut as the voice moves on.
// FIXED position (bottom: 180) — the block never moves with line count.
//
// TIMING (FIX 19/10, option B): when the scene carries real wordTimings
// (SAPI word boundaries on Windows), the chunk follows the VOICE — the
// chunk shown is the one containing the word spoken at this frame.
// Without wordTimings (or when their word count disagrees with the text),
// falls back to the old even-division clock. The even clock is what made
// subtitles drift from the voice ("voice nhảy lộn xộn").
// ---------------------------------------------------------------------------
function chunkText(text: string, wordsPerChunk = 6): string[] {
  const words = text.trim().split(/\s+/);
  const chunks: string[] = [];
  for (let i = 0; i < words.length; i += wordsPerChunk) {
    chunks.push(words.slice(i, i + wordsPerChunk).join(" "));
  }
  return chunks.length > 0 ? chunks : [text];
}

export type WordTiming = { w: string; s: number; e: number };

export const SivoSubtitle: React.FC<{
  text: string;
  durationInFrames: number;
  color?: string;
  wordTimings?: WordTiming[];
}> = ({ text, durationInFrames, color = "#ffffff", wordTimings }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.trim().split(/\s+/);
  const chunks = chunkText(text, 6);
  let idx: number;
  const timed =
    wordTimings && wordTimings.length > 0 && wordTimings.length === words.length;
  if (timed) {
    const t = frame / fps;
    let wi = wordTimings!.findIndex((w) => t >= w.s && t < w.e);
    if (wi === -1) {
      wi = t < (wordTimings![0]?.s ?? 0) ? 0 : wordTimings!.length - 1;
    }
    idx = Math.min(Math.floor(wi / 6), chunks.length - 1);
  } else {
    const framesPerChunk = durationInFrames / chunks.length;
    idx = Math.min(Math.floor(frame / framesPerChunk), chunks.length - 1);
  }
  return (
    <div
      style={{
        position: "absolute",
        bottom: 180,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        zIndex: 40,
      }}
    >
      <p
        style={{
          maxWidth: 960,
          textAlign: "center",
          fontSize: 40,
          fontWeight: 900,
          lineHeight: 1.25,
          color,
          textShadow: "0 3px 0 rgba(0,0,0,0.9), 0 0 28px rgba(0,0,0,0.9)",
        }}
      >
        {chunks[idx]}
      </p>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Channel badge: small text at the top, throughout the video.
// Rendered ONCE at the composition root (outside Series) so it never
// re-animates or jumps between scenes. Static — no spring, no pop-in.
// Default brand "" renders NOTHING.
// ---------------------------------------------------------------------------
export const SivoBrand: React.FC<{ brand: string }> = ({ brand }) => {
  const clean = brand.trim();
  if (!clean) {
    return null;
  }
  return (
    <div
      style={{
        position: "absolute",
        top: 56,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        zIndex: 50,
        pointerEvents: "none",
      }}
    >
      <span
        style={{
          fontSize: 26,
          fontWeight: 700,
          letterSpacing: "0.28em",
          textTransform: "uppercase",
          color: "rgba(255,255,255,0.85)",
          textShadow: "0 2px 0 rgba(0,0,0,0.9)",
        }}
      >
        {clean}
      </span>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Media shot (Fireship meme/GIF/footage slot, Long #4 style).
// - fullscreen: media covers the frame; big caption overlaid on top.
// - corner: dark background; big caption centered; media as a card in the
//   bottom-right (thin border + drop shadow, like a sourced screenshot).
// Video loops for the shot duration; images render cover.
// ---------------------------------------------------------------------------
const DARK_GRADIENT =
  "linear-gradient(to bottom, rgba(0,0,0,0.55) 0%, transparent 35%, transparent 60%, rgba(0,0,0,0.65) 100%)";

export const MediaShot: React.FC<{
  media: SivoMedia;
  caption: React.ReactNode;
  captionColor?: string;
  durationInFrames: number;
}> = ({ media, caption, captionColor = "#ffffff", durationInFrames }) => {
  const mediaEl =
    media.type === "video" ? (
      <Loop durationInFrames={durationInFrames}>
        <OffthreadVideo
          src={staticFile(media.src)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </Loop>
    ) : (
      <Img
        src={staticFile(media.src)}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
    );

  if (media.position === "corner") {
    return (
      <AbsoluteFill>
        <div
          style={{
            position: "absolute",
            right: 48,
            bottom: 280,
            width: 420,
            height: 300,
            overflow: "hidden",
            border: "3px solid rgba(255,255,255,0.85)",
            borderRadius: 16,
            boxShadow: "0 16px 48px rgba(0,0,0,0.8)",
            zIndex: 10,
          }}
        >
          {mediaEl}
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill>
      {mediaEl}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 0,
          bottom: 0,
          background: DARK_GRADIENT,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 0,
          bottom: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          paddingLeft: 48,
          paddingRight: 48,
          textAlign: "center",
          zIndex: 10,
        }}
      >
        <PopIn>
          <div
            style={{
              fontSize: 84,
              fontWeight: 900,
              lineHeight: 1.05,
              letterSpacing: "-0.01em",
              color: captionColor,
              textShadow:
                "0 5px 0 rgba(0,0,0,0.95), 0 0 30px rgba(0,0,0,0.95)",
            }}
          >
            {caption}
          </div>
        </PopIn>
      </div>
    </AbsoluteFill>
  );
};

// Role accent colors (visual rhythm only — the big caption falls back to
// the role accent when the shot list does not set an explicit color).
export const ROLE_COLORS: Record<SivoScene["role"], string> = {
  hook: "#ff6b35",
  pain: "#ef4444",
  solution: "#58d68d",
  workflow: "#58a6ff",
  benefits: "#facc15",
  outro: "#58d68d",
  // Listicle
  item: "#58a6ff",
  // News
  headline: "#ff6b35",
  event: "#58a6ff",
  why: "#facc15",
  source: "#9ca3af",
  action: "#22c55e",
};
