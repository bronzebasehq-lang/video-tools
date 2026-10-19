import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { GenericScene } from "./GenericScene";
import { PopIn, ROLE_COLORS, SivoSubtitle } from "./components";
import type { SivoScene } from "./types";

// Listicle item: BIG number + big caption + plain subtitle. Hard cut comes
// from Series between scenes. The number is the scene's 1-based index.
export const ItemScene: React.FC<{
  scene: SivoScene;
  durationInFrames: number;
}> = ({ scene, durationInFrames }) => {
  const accent = ROLE_COLORS.item;
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
          gap: 24,
          paddingLeft: 48,
          paddingRight: 48,
          textAlign: "center",
        }}
      >
        <PopIn>
          <div
            style={{
              fontSize: 200,
              fontWeight: 900,
              lineHeight: 1,
              color: accent,
              textShadow: "0 8px 0 rgba(0,0,0,0.9)",
            }}
          >
            {scene.index ?? 1}
          </div>
        </PopIn>
        <PopIn delay={6}>
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

// Listicle scene router: hook + outro reuse the generic scene (big
// caption + optional media + subtitle); items get the big-number layout.
export const ListicleScene: React.FC<{
  scene: SivoScene;
  durationInFrames: number;
}> = ({ scene, durationInFrames }) => {
  if (scene.role === "item") {
    return <ItemScene scene={scene} durationInFrames={durationInFrames} />;
  }
  return (
    <GenericScene scene={scene} durationInFrames={durationInFrames} />
  );
};
