import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { GenericScene } from "./GenericScene";
import { PopIn, ROLE_COLORS, SivoSubtitle } from "./components";
import type { SivoScene } from "./types";

// News headline card: the full first sentence as a BIG title. No subtitle
// (the headline IS the text) — keeps the title card clean.
const HeadlineCard: React.FC<{
  scene: SivoScene;
}> = ({ scene }) => {
  const bigCaption = scene.bigCaption || scene.headline;
  const bigColor = scene.bigCaptionColor || ROLE_COLORS.headline;
  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a", color: "#ffffff" }}>
      <Audio src={staticFile(scene.audioPath)} />
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 28,
          paddingLeft: 48,
          paddingRight: 48,
          textAlign: "center",
        }}
      >
        <PopIn>
          <div
            style={{
              fontSize: 84,
              fontWeight: 900,
              lineHeight: 1.1,
              maxWidth: 980,
              color: bigColor,
            }}
          >
            {bigCaption}
          </div>
        </PopIn>
      </div>
    </AbsoluteFill>
  );
};

// News source line: "SOURCE" label + the source text in normal case
// (source names read better un-uppercased). No subtitle.
const SourceCard: React.FC<{
  scene: SivoScene;
}> = ({ scene }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a", color: "#ffffff" }}>
      <Audio src={staticFile(scene.audioPath)} />
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 24,
          paddingLeft: 64,
          paddingRight: 64,
          textAlign: "center",
        }}
      >
        <PopIn>
          <div
            style={{
              fontSize: 30,
              fontWeight: 900,
              letterSpacing: "0.3em",
              color: ROLE_COLORS.source,
            }}
          >
            SOURCE
          </div>
        </PopIn>
        <PopIn delay={6}>
          <div
            style={{
              fontSize: 48,
              fontWeight: 700,
              lineHeight: 1.25,
              maxWidth: 940,
            }}
          >
            {scene.text}
          </div>
        </PopIn>
      </div>
    </AbsoluteFill>
  );
};

// News event: big number + big caption + plain subtitle. Why: big caption
// + plain subtitle. No role labels on screen (Long #4 style).
const NewsBody: React.FC<{
  scene: SivoScene;
  durationInFrames: number;
}> = ({ scene, durationInFrames }) => {
  const accent = ROLE_COLORS[scene.role];
  const bigCaption = scene.bigCaption || scene.headline;
  const bigColor = scene.bigCaptionColor || accent;
  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a", color: "#ffffff" }}>
      <Audio src={staticFile(scene.audioPath)} />
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 28,
          paddingLeft: 48,
          paddingRight: 48,
          textAlign: "center",
        }}
      >
        {scene.role === "event" ? (
          <PopIn>
            <div
              style={{
                fontSize: 160,
                fontWeight: 900,
                lineHeight: 1,
                color: accent,
                textShadow: "0 8px 0 rgba(0,0,0,0.9)",
              }}
            >
              {scene.index ?? 1}
            </div>
          </PopIn>
        ) : null}
        <PopIn delay={scene.role === "event" ? 6 : 0}>
          <div
            style={{
              fontSize: 76,
              fontWeight: 900,
              lineHeight: 1.08,
              maxWidth: 960,
              color: bigColor,
            }}
          >
            {bigCaption}
          </div>
        </PopIn>
      </div>
      <SivoSubtitle
        text={scene.text}
        durationInFrames={durationInFrames}
        color={scene.subtitleColor}
        wordTimings={scene.wordTimings}
      />
    </AbsoluteFill>
  );
};

// News scene router. Outro reuses the generic scene.
export const NewsScene: React.FC<{
  scene: SivoScene;
  durationInFrames: number;
}> = ({ scene, durationInFrames }) => {
  if (scene.role === "headline") {
    return <HeadlineCard scene={scene} />;
  }
  if (scene.role === "source") {
    return <SourceCard scene={scene} />;
  }
  if (scene.role === "event" || scene.role === "why") {
    return <NewsBody scene={scene} durationInFrames={durationInFrames} />;
  }
  return (
    <GenericScene scene={scene} durationInFrames={durationInFrames} />
  );
};
