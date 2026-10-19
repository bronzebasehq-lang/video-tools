import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Loop,
  OffthreadVideo,
  Series,
  staticFile,
} from "remotion";
import { PopIn, SivoBrand, SivoSubtitle } from "./components";
import type { SivoMedia, SivoScene, SivoManifest } from "./types";

// ---------------------------------------------------------------------------
// News style (v4) — data-driven composition for the news video style.
// Each scene renders ONE of 7 news layouts (layout field, set by the
// shot list or defaulted by role in build_props.py):
//   breaking-news | stat-callout | split-screen | quote-card |
//   listicle | big-number | action-card | outro
// Layout grammar is ADAPTED from the auto-video-gen template set
// (hook / stat-hero / comparison / callout / feature-list / outro) —
// re-implemented in Remotion. Brand is BRONZE BASE (never the source
// repo's brand). Every layout takes the media slot (image / chart /
// footage / screenshot / avatar) — the fix for the news style's known
// weakness (text-heavy / monotonous, no visual information).
// Grammar: dark navy gradient bg, cyan + purple accents, big numbers,
// hard cuts only (Series). Plain bottom subtitle on every scene except
// the outro (captions stay on — Minh's clips need them).
// ---------------------------------------------------------------------------

const NAVY_BG =
  "linear-gradient(180deg, #0b1220 0%, #101a33 55%, #0b1220 100%)";
const CYAN = "#22d3ee";
const PURPLE = "#a855f7";
const RED = "#ef4444";
const MUTED = "#94a3b8";

type LD = Record<string, unknown>;

const ld = (scene: SivoScene): LD =>
  (scene.layoutData ?? {}) as LD;

const str = (v: unknown, fallback = ""): string =>
  typeof v === "string" ? v : fallback;

const strArr = (v: unknown): string[] =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];

function layoutFor(scene: SivoScene): string {
  if (scene.layout) return scene.layout;
  switch (scene.role) {
    case "headline":
      return "breaking-news";
    case "event":
      return "stat-callout";
    case "why":
      return "quote-card";
    case "source":
    case "outro":
      return "outro";
    case "action":
      return "action-card";
    default:
      return "breaking-news";
  }
}

function captionFor(scene: SivoScene): string {
  return scene.bigCaption || scene.headline;
}

const MediaImg: React.FC<{ media: SivoMedia; style?: React.CSSProperties }> = ({
  media,
  style,
}) => (
  <Img
    src={staticFile(media.src)}
    style={{ width: "100%", height: "100%", objectFit: "cover", ...style }}
  />
);

const MediaVideo: React.FC<{
  media: SivoMedia;
  durationInFrames: number;
  style?: React.CSSProperties;
}> = ({ media, durationInFrames, style }) => (
  <Loop durationInFrames={durationInFrames}>
    <OffthreadVideo
      src={staticFile(media.src)}
      style={{ width: "100%", height: "100%", objectFit: "cover", ...style }}
    />
  </Loop>
);

const MediaEl: React.FC<{
  media: SivoMedia;
  durationInFrames: number;
}> = ({ media, durationInFrames }) =>
  media.type === "video" ? (
    <MediaVideo media={media} durationInFrames={durationInFrames} />
  ) : (
    <MediaImg media={media} />
  );

// Dimmed fullscreen media behind cards (split-screen).
const BgMedia: React.FC<{
  media?: SivoMedia;
  durationInFrames: number;
  dim?: number;
}> = ({ media, durationInFrames, dim = 0.35 }) => {
  if (!media) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: 0,
        bottom: 0,
        opacity: dim,
      }}
    >
      <MediaEl media={media} durationInFrames={durationInFrames} />
    </div>
  );
};

// Fullscreen media background with a dark scrim (breaking-news).
const CoverMedia: React.FC<{
  media?: SivoMedia;
  durationInFrames: number;
}> = ({ media, durationInFrames }) => {
  if (!media) return null;
  return (
    <>
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }}>
        <MediaEl media={media} durationInFrames={durationInFrames} />
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 0,
          bottom: 0,
          background:
            "linear-gradient(to bottom, rgba(4,8,18,0.55) 0%, rgba(4,8,18,0.35) 45%, rgba(4,8,18,0.78) 100%)",
        }}
      />
    </>
  );
};

// Chart / image panel under a stat (the text-heavy fix: visual proof
// next to the number, not a number alone on a gradient).
const ChartPanel: React.FC<{
  media?: SivoMedia;
  durationInFrames: number;
}> = ({ media, durationInFrames }) => {
  if (!media) return null;
  return (
    <div
      style={{
        width: 880,
        height: 420,
        overflow: "hidden",
        borderRadius: 20,
        border: "3px solid rgba(255,255,255,0.35)",
        boxShadow: "0 16px 48px rgba(0,0,0,0.6)",
      }}
    >
      <MediaEl media={media} durationInFrames={durationInFrames} />
    </div>
  );
};

const Wrap: React.FC<{
  scene: SivoScene;
  durationInFrames: number;
  children: React.ReactNode;
  subtitle?: boolean;
}> = ({ scene, durationInFrames, children, subtitle = true }) => (
  <AbsoluteFill
    style={{
      background: NAVY_BG,
      color: "#ffffff",
    }}
  >
    <Audio src={staticFile(scene.audioPath)} />
    {children}
    {subtitle ? (
      <SivoSubtitle
        text={scene.text}
        durationInFrames={durationInFrames}
        color={scene.subtitleColor}
        wordTimings={scene.wordTimings}
      />
    ) : null}
  </AbsoluteFill>
);

// breaking-news: BREAKING pill + huge headline (+ subhead) over media
// or gradient. The hook of a news video.
const BreakingNews: React.FC<{ scene: SivoScene; durationInFrames: number }> = ({
  scene,
  durationInFrames,
}) => {
  const data = ld(scene);
  const subhead = str(data.subhead, "");
  return (
    <Wrap scene={scene} durationInFrames={durationInFrames}>
      <CoverMedia media={scene.media} durationInFrames={durationInFrames} />
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
              fontSize: 34,
              fontWeight: 900,
              letterSpacing: "0.25em",
              color: "#ffffff",
              backgroundColor: RED,
              padding: "12px 28px",
              borderRadius: 999,
            }}
          >
            BREAKING
          </div>
        </PopIn>
        <PopIn delay={5}>
          <div
            style={{
              fontSize: 92,
              fontWeight: 900,
              lineHeight: 1.05,
              maxWidth: 980,
            }}
          >
            {captionFor(scene)}
          </div>
        </PopIn>
        {subhead ? (
          <PopIn delay={10}>
            <div
              style={{ fontSize: 42, fontWeight: 700, color: MUTED, maxWidth: 900 }}
            >
              {subhead}
            </div>
          </PopIn>
        ) : null}
      </div>
    </Wrap>
  );
};

// stat-callout: giant value + label + context + optional chart panel.
const StatCallout: React.FC<{
  scene: SivoScene;
  durationInFrames: number;
  big?: boolean;
}> = ({ scene, durationInFrames, big = false }) => {
  const data = ld(scene);
  const value = str(data.value, captionFor(scene));
  const label = str(data.label, "");
  const context = str(data.context, "");
  return (
    <Wrap scene={scene} durationInFrames={durationInFrames}>
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 22,
          paddingLeft: 48,
          paddingRight: 48,
          textAlign: "center",
        }}
      >
        <PopIn>
          <div
            style={{
              fontSize: big ? 210 : 150,
              fontWeight: 900,
              lineHeight: 1,
              color: CYAN,
              textShadow: "0 0 60px rgba(34,211,238,0.45)",
            }}
          >
            {value}
          </div>
        </PopIn>
        {label ? (
          <PopIn delay={5}>
            <div style={{ fontSize: 48, fontWeight: 900, maxWidth: 940 }}>{label}</div>
          </PopIn>
        ) : null}
        {context ? (
          <PopIn delay={10}>
            <div style={{ fontSize: 36, fontWeight: 600, color: MUTED, maxWidth: 900 }}>
              {context}
            </div>
          </PopIn>
        ) : null}
        {scene.media ? (
          <PopIn delay={14}>
            <ChartPanel media={scene.media} durationInFrames={durationInFrames} />
          </PopIn>
        ) : null}
      </div>
    </Wrap>
  );
};

// split-screen: two cards + VS + optional WINNER badge.
const SplitScreen: React.FC<{ scene: SivoScene; durationInFrames: number }> = ({
  scene,
  durationInFrames,
}) => {
  const data = ld(scene);
  const side = (v: unknown, fallbackColor: string) => {
    const o = (v ?? {}) as Record<string, unknown>;
    return {
      label: str(o.label, ""),
      value: str(o.value, ""),
      color: str(o.color, fallbackColor),
      winner: o.winner === true,
    };
  };
  const left = side(data.left, CYAN);
  const right = side(data.right, PURPLE);
  const card = (
    s: typeof left,
    accent: string,
  ) => (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 16,
        padding: 32,
        borderRadius: 24,
        border: `4px solid ${accent}`,
        backgroundColor: "rgba(4,8,18,0.72)",
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: 30,
          fontWeight: 800,
          letterSpacing: "0.2em",
          color: accent,
        }}
      >
        {s.label}
      </div>
      <div style={{ fontSize: 62, fontWeight: 900, lineHeight: 1.1 }}>{s.value}</div>
      {s.winner ? (
        <div
          style={{
            fontSize: 26,
            fontWeight: 900,
            letterSpacing: "0.15em",
            color: "#0b1220",
            backgroundColor: "#facc15",
            padding: "8px 20px",
            borderRadius: 999,
          }}
        >
          WINNER
        </div>
      ) : null}
    </div>
  );
  return (
    <Wrap scene={scene} durationInFrames={durationInFrames}>
      <BgMedia media={scene.media} durationInFrames={durationInFrames} />
      <div
        style={{
          height: "100%",
          display: "flex",
          alignItems: "stretch",
          gap: 24,
          padding: "220px 48px 260px 48px",
        }}
      >
        <PopIn>{card(left, CYAN)}</PopIn>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: 96,
              height: 96,
              borderRadius: "50%",
              backgroundColor: "#ffffff",
              color: "#0b1220",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 34,
              fontWeight: 900,
            }}
          >
            VS
          </div>
        </div>
        <PopIn delay={5}>{card(right, PURPLE)}</PopIn>
      </div>
    </Wrap>
  );
};

// quote-card: tag pill + statement in a card + optional avatar.
const QuoteCard: React.FC<{ scene: SivoScene; durationInFrames: number }> = ({
  scene,
  durationInFrames,
}) => {
  const data = ld(scene);
  const tag = str(data.tag, scene.role === "source" ? "SOURCE" : "");
  const statement = str(data.statement, scene.text);
  return (
    <Wrap scene={scene} durationInFrames={durationInFrames}>
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 28,
          paddingLeft: 64,
          paddingRight: 64,
        }}
      >
        {scene.media && scene.media.type === "image" ? (
          <PopIn>
            <div
              style={{
                width: 180,
                height: 180,
                borderRadius: "50%",
                overflow: "hidden",
                border: `4px solid ${CYAN}`,
              }}
            >
              <MediaImg media={scene.media} />
            </div>
          </PopIn>
        ) : null}
        <div
          style={{
            width: "100%",
            borderRadius: 28,
            border: "3px solid rgba(255,255,255,0.3)",
            backgroundColor: "rgba(255,255,255,0.06)",
            padding: 48,
            textAlign: "center",
          }}
        >
          {tag ? (
            <div
              style={{
                display: "inline-block",
                fontSize: 28,
                fontWeight: 900,
                letterSpacing: "0.2em",
                color: CYAN,
                marginBottom: 20,
              }}
            >
              {tag}
            </div>
          ) : null}
          <PopIn delay={5}>
            <div
              style={{
                fontSize: 56,
                fontWeight: 900,
                lineHeight: 1.2,
                fontStyle: "italic",
              }}
            >
              “{statement}”
            </div>
          </PopIn>
        </div>
      </div>
    </Wrap>
  );
};

// listicle: title + rule + staggered bullets (+ optional top image band).
const ListicleLayout: React.FC<{ scene: SivoScene; durationInFrames: number }> = ({
  scene,
  durationInFrames,
}) => {
  const data = ld(scene);
  const title = str(data.title, captionFor(scene));
  const bullets = strArr(data.bullets);
  const items = bullets.length > 0 ? bullets : [scene.text];
  return (
    <Wrap scene={scene} durationInFrames={durationInFrames}>
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
        }}
      >
        {scene.media ? (
          <div
            style={{
              width: "100%",
              height: 440,
              overflow: "hidden",
              borderRadius: 24,
              border: "3px solid rgba(255,255,255,0.3)",
            }}
          >
            <MediaEl media={scene.media} durationInFrames={durationInFrames} />
          </div>
        ) : null}
        <div
          style={{
            width: "100%",
            borderRadius: 28,
            border: "3px solid rgba(255,255,255,0.3)",
            backgroundColor: "rgba(255,255,255,0.06)",
            padding: 44,
          }}
        >
          <PopIn>
            <div style={{ fontSize: 62, fontWeight: 900, marginBottom: 16 }}>
              {title}
            </div>
          </PopIn>
          <div
            style={{
              height: 4,
              backgroundColor: CYAN,
              borderRadius: 2,
              marginBottom: 24,
            }}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            {items.map((b, i) => (
              <PopIn key={i} delay={5 + i * 5}>
                <div style={{ display: "flex", gap: 18, alignItems: "flex-start" }}>
                  <div
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: "50%",
                      backgroundColor: CYAN,
                      marginTop: 12,
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ fontSize: 40, fontWeight: 700, lineHeight: 1.25 }}>
                    {b}
                  </div>
                </div>
              </PopIn>
            ))}
          </div>
        </div>
      </div>
    </Wrap>
  );
};

// action-card: "DÙNG ĐƯỢC NGAY" — the FB beat that ends every news
// video with 1 concrete thing the viewer can use TODAY (a tool, a
// prompt, a setting). Green chip + big action text + media (ideally a
// screenshot of the tool/prompt). The shot-list media warning in
// build_props nudges authors to attach a visual here.
const ActionCard: React.FC<{
  scene: SivoScene;
  durationInFrames: number;
}> = ({ scene, durationInFrames }) => {
  const text = scene.bigCaption || scene.text;
  // Action card shows the FULL action sentence (it IS the content —
  // never the truncated auto headline).
  return (
    <Wrap scene={scene} durationInFrames={durationInFrames}>
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 30,
          paddingLeft: 48,
          paddingRight: 48,
          textAlign: "center",
        }}
      >
        <PopIn>
          <div
            style={{
              fontSize: 34,
              fontWeight: 900,
              letterSpacing: "0.25em",
              color: "#000000",
              backgroundColor: "#22c55e",
              padding: "14px 32px",
              borderRadius: 999,
            }}
          >
            DÙNG ĐƯỢC NGAY
          </div>
        </PopIn>
        <PopIn delay={5}>
          <div
            style={{
              fontSize: 64,
              fontWeight: 900,
              lineHeight: 1.15,
              maxWidth: 920,
            }}
          >
            {text}
          </div>
        </PopIn>
        {scene.media ? (
          <PopIn delay={10}>
            <ChartPanel media={scene.media} durationInFrames={durationInFrames} />
          </PopIn>
        ) : null}
      </div>
    </Wrap>
  );
};

// outro: verdict card + CTA + channel name + source + BRONZE BASE
// follow card + cross-link. Brand is Minh's channel — NEVER the
// source repo's brand. The verdict (layoutData.verdict: ship | skip |
// scam, default ship) is the FB signature: "Ship it / Skip it /
// Scam it" + the "ship it" slogan, on every FB video.
const Outro: React.FC<{
  scene: SivoScene;
  durationInFrames: number;
  brand: string;
}> = ({ scene, durationInFrames, brand }) => {
  const data = ld(scene);
  const cta = str(data.ctaTop, "FOLLOW FOR MORE");
  // Source line: ONLY from the shot list (layoutData.source). The
  // outro consumes no script sentence, so there is no scene.text to
  // fall back to — and falling back would mislabel the last content
  // sentence (the action beat) as the source. The source SCENE (role
  // source) already displays the source.
  const source = str(data.source, "");
  // Empty brand = NO badge (FB badge undecided — the caller passes
  // --brand '' to suppress all BRONZE BASE naming). The old fallback
  // (brand || "BRONZE BASE") ignored that contract.
  const displayName = brand.trim();
  const verdict = ["ship", "skip", "scam"].includes(
    str(data.verdict, "ship").toLowerCase()
  )
    ? str(data.verdict, "ship").toLowerCase()
    : "ship";
  const verdictOpts = [
    { key: "ship", label: "SHIP IT", color: "#22c55e" },
    { key: "skip", label: "SKIP IT", color: "#facc15" },
    { key: "scam", label: "SCAM IT", color: "#ef4444" },
  ];
  return (
    <Wrap scene={scene} durationInFrames={durationInFrames} subtitle={false}>
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
              fontSize: 36,
              fontWeight: 900,
              letterSpacing: "0.25em",
              color: CYAN,
            }}
          >
            {cta}
          </div>
        </PopIn>
        {displayName ? (
          <PopIn delay={5}>
            <div style={{ fontSize: 88, fontWeight: 900, lineHeight: 1.05 }}>
              {displayName}
            </div>
          </PopIn>
        ) : null}
        <PopIn delay={10}>
          <div
            style={{
              height: 5,
              width: 320,
              backgroundColor: PURPLE,
              borderRadius: 3,
            }}
          />
        </PopIn>
        <PopIn delay={12}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div
              style={{
                fontSize: 26,
                fontWeight: 900,
                letterSpacing: "0.35em",
                color: MUTED,
              }}
            >
              VERDICT
            </div>
            <div style={{ display: "flex", gap: 16 }}>
              {verdictOpts.map((opt) => {
                const selected = opt.key === verdict;
                return (
                  <div
                    key={opt.key}
                    style={{
                      fontSize: 32,
                      fontWeight: 900,
                      letterSpacing: "0.05em",
                      color: selected ? "#000000" : opt.color,
                      backgroundColor: selected ? opt.color : "transparent",
                      border: `3px solid ${opt.color}`,
                      opacity: selected ? 1 : 0.45,
                      padding: "12px 26px",
                      borderRadius: 16,
                    }}
                  >
                    {opt.label}
                  </div>
                );
              })}
            </div>
            <div
              style={{
                fontSize: 30,
                fontWeight: 700,
                color: MUTED,
                letterSpacing: "0.1em",
              }}
            >
              ship it
            </div>
          </div>
        </PopIn>
        {source ? (
          <PopIn delay={14}>
            <div style={{ fontSize: 34, fontWeight: 600, color: MUTED, maxWidth: 880 }}>
              Nguồn: {source}
            </div>
          </PopIn>
        ) : null}
        {displayName ? (
          <PopIn delay={18}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 20,
                marginTop: 16,
                padding: "20px 28px",
                borderRadius: 24,
                backgroundColor: "rgba(255,255,255,0.08)",
                border: "2px solid rgba(255,255,255,0.25)",
              }}
            >
              {scene.media && scene.media.type === "image" ? (
              <div
                style={{
                  width: 96,
                  height: 96,
                  borderRadius: "50%",
                  overflow: "hidden",
                  flexShrink: 0,
                }}
              >
                <MediaImg media={scene.media} />
              </div>
            ) : (
              <div
                style={{
                  width: 96,
                  height: 96,
                  borderRadius: "50%",
                  backgroundColor: CYAN,
                  color: "#0b1220",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 44,
                  fontWeight: 900,
                  flexShrink: 0,
                }}
              >
                B
              </div>
            )}
            <div style={{ textAlign: "left" }}>
              <div style={{ fontSize: 36, fontWeight: 900 }}>{displayName}</div>
              <div style={{ fontSize: 28, color: MUTED }}>@bronzebasehq</div>
            </div>
            <div
              style={{
                marginLeft: 12,
                fontSize: 30,
                fontWeight: 900,
                color: "#ffffff",
                backgroundColor: RED,
                padding: "12px 28px",
                borderRadius: 999,
              }}
            >
              Follow
            </div>
          </div>
          </PopIn>
        ) : null}
        {scene.crossLink ? (
          <PopIn delay={22}>
            <div
              style={{
                fontSize: 28,
                fontWeight: 700,
                color: MUTED,
                maxWidth: 880,
              }}
            >
              {scene.crossLink}
            </div>
          </PopIn>
        ) : null}
      </div>
    </Wrap>
  );
};

const NewsScene: React.FC<{
  scene: SivoScene;
  durationInFrames: number;
  brand: string;
}> = ({ scene, durationInFrames, brand }) => {
  switch (layoutFor(scene)) {
    case "stat-callout":
      return <StatCallout scene={scene} durationInFrames={durationInFrames} />;
    case "big-number":
      return (
        <StatCallout scene={scene} durationInFrames={durationInFrames} big />
      );
    case "split-screen":
      return <SplitScreen scene={scene} durationInFrames={durationInFrames} />;
    case "quote-card":
      return <QuoteCard scene={scene} durationInFrames={durationInFrames} />;
    case "listicle":
      return <ListicleLayout scene={scene} durationInFrames={durationInFrames} />;
    case "action-card":
      return <ActionCard scene={scene} durationInFrames={durationInFrames} />;
    case "outro":
      return <Outro scene={scene} durationInFrames={durationInFrames} brand={brand} />;
    case "breaking-news":
    default:
      return <BreakingNews scene={scene} durationInFrames={durationInFrames} />;
  }
};

// News style composition. Brand badge OUTSIDE Series (persists, never
// re-animates), hard cuts only.
export const NewsStyle: React.FC<SivoManifest> = (props) => {
  const { scenes } = props;
  return (
    <AbsoluteFill
      style={{ background: NAVY_BG, color: "#ffffff" }}
      className="overflow-hidden select-none"
    >
      <SivoBrand brand={props.brand} />
      <Series>
        {scenes.map((scene, i) => {
          const d =
            scene.durationInFrames + (i === scenes.length - 1 ? 10 : 3);
          return (
            <Series.Sequence key={scene.id} durationInFrames={d}>
              <NewsScene scene={scene} durationInFrames={d} brand={props.brand} />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
