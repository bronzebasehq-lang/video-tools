import React from "react";
import { AbsoluteFill, Series } from "remotion";
import { GenericScene } from "./GenericScene";
import { SivoBrand } from "./components";
import type { SivoManifest } from "./types";

// SIVO-Remotion v3 (Fireship rebuild) — data-driven Explainer composition.
// Everything comes from the manifest prop: scenes, brand, media slots.
// Voiceover-first timing: scene lengths come from real WAV durations
// (+3 frames buffer per scene, +10 on the last — same as the proven test).
// NO fades/dissolves — hard cuts only (Series).
// Brand badge lives OUTSIDE Series so it persists across the whole video.
export const SivoExplainer: React.FC<SivoManifest> = (props) => {
  const { scenes } = props;
  return (
    <AbsoluteFill
      style={{ backgroundColor: "#0a0a0a", color: "#ffffff" }}
      className="overflow-hidden select-none"
    >
      <SivoBrand brand={props.brand} />
      <Series>
        {scenes.map((scene, i) => {
          const d =
            scene.durationInFrames + (i === scenes.length - 1 ? 10 : 3);
          return (
            <Series.Sequence key={scene.id} durationInFrames={d}>
              <GenericScene scene={scene} durationInFrames={d} />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
