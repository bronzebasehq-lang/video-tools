import React from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, staticFile } from "remotion";
import { MediaShot, PopIn, ROLE_COLORS, SivoSubtitle } from "./components";
import type { SivoMedia, SivoScene } from "./types";

// Collage (YT: denser topic-related media per shot). mediaList wins over
// single media. Layouts:
//   2 media -> side-by-side halves.
//   3 media -> 1 big left (60%) + 2 stacked right.
//   4 media -> 2x2 grid.
// The big caption overlays the collage (top area), subtitle stays on.
function Collage({
  mediaList,
  caption,
  captionColor,
}: {
  mediaList: SivoMedia[];
  caption: string;
  captionColor: string;
}): React.ReactElement {
  const tile = (m: SivoMedia, key: number): React.ReactElement => {
    const style: React.CSSProperties = {
      width: "100%",
      height: "100%",
      objectFit: "cover",
    };
    return m.type === "video" ? (
      <OffthreadVideo
        key={key}
        src={staticFile(m.src)}
        style={style}
        volume={0}
      />
    ) : (
      <Img key={key} src={staticFile(m.src)} style={style} />
    );
  };
  const grid: React.CSSProperties =
    mediaList.length === 2
      ? { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }
      : mediaList.length === 3
        ? {
            display: "grid",
            gridTemplateColumns: "60% 40%",
            gridTemplateRows: "1fr 1fr",
            gap: 8,
          }
        : { display: "grid", gridTemplateColumns: "1fr 1fr", gridTemplateRows: "1fr 1fr", gap: 8 };
  const cells =
    mediaList.length === 3
      ? [
          <div key={0} style={{ gridRow: "1 / 3", overflow: "hidden" }}>
            {tile(mediaList[0], 0)}
          </div>,
          <div key={1} style={{ overflow: "hidden" }}>
            {tile(mediaList[1], 1)}
          </div>,
          <div key={2} style={{ overflow: "hidden" }}>
            {tile(mediaList[2], 2)}
          </div>,
        ]
      : mediaList.map((m, i) => (
          <div key={i} style={{ overflow: "hidden" }}>
            {tile(m, i)}
          </div>
        ));
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          inset: 0,
          ...grid,
        }}
      >
        {cells}
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 180,
          display: "flex",
          justifyContent: "center",
          paddingLeft: 48,
          paddingRight: 48,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 76,
            fontWeight: 900,
            lineHeight: 1.08,
            color: captionColor,
            textShadow:
              "-3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000",
          }}
        >
          {caption}
        </div>
      </div>
    </AbsoluteFill>
  );
}

// Headline size by length so long captions still fit 1080 wide.
function captionFontSize(caption: string): number {
  if (caption.length > 30) return 56;
  if (caption.length > 18) return 72;
  return 92;
}

// Generic scene (Fireship rebuild): ONE shot = big static mid-screen
// caption (pop-in once, then static) + optional media slot + plain bottom
// subtitle. NO role labels on screen (Long #4 style), NO karaoke.
// Layout by media:
//  - fullscreen media: media covers the frame, big caption overlaid.
//  - corner media: dark background, big caption centered, media card
//    bottom-right.
//  - no media: dark background, big caption centered.
export const GenericScene: React.FC<{
  scene: SivoScene;
  durationInFrames: number;
}> = ({ scene, durationInFrames }) => {
  const accent = ROLE_COLORS[scene.role];
  const bigCaption = scene.bigCaption || scene.headline;
  const bigColor = scene.bigCaptionColor || accent;
  const media = scene.media;
  const mediaList = scene.mediaList;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a", color: "#ffffff" }}>
      <Audio src={staticFile(scene.audioPath)} />
      {mediaList && mediaList.length >= 2 ? (
        <Collage
          mediaList={mediaList}
          caption={bigCaption}
          captionColor={bigColor}
        />
      ) : media && media.position === "fullscreen" ? (
        <MediaShot
          media={media}
          caption={bigCaption}
          captionColor={bigColor}
          durationInFrames={durationInFrames}
        />
      ) : (
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
                fontSize: captionFontSize(bigCaption),
                fontWeight: 900,
                lineHeight: 1.08,
                maxWidth: 960,
                color: bigColor,
              }}
            >
              {bigCaption}
            </div>
          </PopIn>
          {scene.meta ? (
            <PopIn delay={9}>
              <div
                style={{
                  fontSize: 30,
                  fontWeight: 800,
                  letterSpacing: "0.25em",
                  color: bigColor,
                }}
              >
                {scene.meta}
              </div>
            </PopIn>
          ) : null}
          {scene.role === "outro" && scene.codeOutro ? (
            <PopIn delay={12}>
              <div
                style={{
                  fontFamily: "monospace",
                  fontSize: 48,
                  fontWeight: 700,
                  color: "#58d68d",
                }}
              >
                $ ship_it;
              </div>
            </PopIn>
          ) : null}
        </div>
      )}
      {media && !mediaList && media.position === "corner" ? (
        <MediaShot
          media={media}
          caption={null}
          durationInFrames={durationInFrames}
        />
      ) : null}
      {scene.role === "outro" && scene.crossLink ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 230,
            display: "flex",
            justifyContent: "center",
            paddingLeft: 48,
            paddingRight: 48,
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 30, fontWeight: 700, color: "#a1a1aa" }}>
            {scene.crossLink}
          </div>
        </div>
      ) : null}
      {/*
        FIX 19/10 (option A, refined): the bottom subtitle shows ONLY when
        the scene has NO user-provided bigCaption. When a shot list gives
        a bigCaption, the big caption IS the text layer — the old second
        layer changed on its own clock and fought the caption ("karaoke
        jumping"). When there is no bigCaption, the auto headline is
        truncated, so the subtitle stays to carry the FULL sentence.
        Subtitles in Listicle/News scenes now follow real wordTimings
        (option B).
      */}
      {!scene.bigCaption ? (
        <SivoSubtitle
          text={scene.text}
          durationInFrames={durationInFrames}
          color={scene.subtitleColor}
          wordTimings={scene.wordTimings}
        />
      ) : null}
    </AbsoluteFill>
  );
};
