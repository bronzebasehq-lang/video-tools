import React from "react";
import { AbsoluteFill, Series } from "remotion";
import { ListicleScene } from "./ListicleScene";
import { SivoBrand } from "./components";
import type { SivoManifest } from "./types";

// SIVO-Remotion v3 (Fireship rebuild) — data-driven Listicle composition.
// Hook (headline + item count) -> numbered items (max 7) -> Outro (recap).
// Same shell as Explainer: brand badge OUTSIDE Series (persists, never
// re-animates), hard cuts only, no meme slot.
export const SivoListicle: React.FC<SivoManifest> = (props) => {
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
              <ListicleScene scene={scene} durationInFrames={d} />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
