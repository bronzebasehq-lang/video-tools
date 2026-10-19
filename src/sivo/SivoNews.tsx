import React from "react";
import { AbsoluteFill, Series } from "remotion";
import { NewsScene } from "./NewsScene";
import { SivoBrand } from "./components";
import type { SivoManifest } from "./types";

// SIVO-Remotion v3 (Fireship rebuild) — data-driven News composition.
// Headline card -> up to 3 numbered events -> Why-it-matters -> Source ->
// Outro. Same shell as Explainer/Listicle: brand badge OUTSIDE Series
// (persists, never re-animates), hard cuts only, no meme slot.
export const SivoNews: React.FC<SivoManifest> = (props) => {
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
              <NewsScene scene={scene} durationInFrames={d} />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
