import { z } from "zod";

// SIVO-Remotion v3 (Fireship rebuild) — manifest schema.
// SIVO is now an INTERNAL production tool for Minh's own channel (NOT a
// product for non-tech customers). The quality bar is Fireship / Long #4:
// plain bottom subtitle (NO per-word karaoke color change) + big static
// mid-screen caption per shot + a media slot per shot + hard cuts only.
//
// The manifest is the ONLY input the composition receives. It is produced
// by build_props.py from the script (1 sentence/line) + voice WAVs +
// an optional shot list (JSON) that sets per-shot big captions / media.
//
// Voiceover-first: every scene's duration comes from its real WAV file.
// Long scenes are split into <= maxShotSec sub-shots at word boundaries
// (Fireship pacing: a shot never sits still longer than ~4s).
export const sivoMediaSchema = z.object({
  // Path under public/, e.g. "media/piggy-bank.jpg" or "memes/pain-01.mp4".
  src: z.string(),
  // video -> looping OffthreadVideo; image -> Img (cover).
  // NOTE: animated GIFs render as a STATIC first frame — convert GIFs to
  // MP4 for motion (or install @remotion/gif later).
  type: z.enum(["video", "image"]),
  // fullscreen = cover the frame with the big caption overlaid (Fireship
  // meme/GIF style). corner = bottom-right card over the dark background.
  // fit = contain below the caption, no crop (X style GIFs, Short #8).
  position: z.enum(["fullscreen", "corner", "fit"]).default("fullscreen"),
  // Attribution / where the media came from (metadata only — NOT rendered
  // on screen; sources go in the video description, like Long #4).
  source: z.string().optional(),
});

export const sivoSceneSchema = z.object({
  id: z.string(),
  role: z.enum([
    "hook",
    "pain",
    "solution",
    "workflow",
    "benefits",
    "outro",
    // Listicle roles
    "item",
    // News roles
    "headline",
    "event",
    "why",
    "source",
    // News "dùng được ngay" beat (1 concrete thing to use TODAY).
    "action",
  ]),
  text: z.string(),
  // Auto headline (first words, uppercased). Kept as the fallback display
  // text when bigCaption is not set.
  headline: z.string(),
  // Explicit big mid-screen caption (from the shot list). Overrides
  // headline for display. Static after its pop-in — never karaoke.
  bigCaption: z.string().optional(),
  // Color for the big caption. Default = the scene role's accent color.
  bigCaptionColor: z.string().optional(),
  // Subtitle color. Default #ffffff (plain white). A whole scene may be
  // yellow for a joke/punchline (Fireship §14) — NEVER per-word color.
  subtitleColor: z.string().optional(),
  // Media slot (shot list). When present, the scene renders the media
  // instead of the plain text block (fullscreen) or alongside it (corner).
  media: sivoMediaSchema.optional(),
  // Per-scene news-style layout (style=news only). One of the 6 news
  // layouts: breaking-news | stat-callout | split-screen | quote-card |
  // listicle | big-number | outro. Fireship scenes never carry layout.
  layout: z.string().optional(),
  // Structured data for the layout, e.g. {value, label, context} for
  // stat-callout/big-number, {left, right} for split-screen,
  // {tag, statement} for quote-card, {title, bullets} for listicle.
  layoutData: z.record(z.unknown()).optional(),
  // X-style per-shot caption lines ([{text, color}] — Short #8/#9 shot
  // grammar). Lines win over bigCaption in the X composition. Each line
  // is one caption line; color is a hex string or a named X color
  // (WHITE/RED/ORANGE/YELLOW/GREEN/GRAY/DARKGRAY).
  lines: z
    .array(z.object({ text: z.string(), color: z.string().optional() }))
    .optional(),
  // Fireship collage: 2-4 media rendered as a grid + big caption
  // overlaid (YT: denser topic-related media). Wins over single media.
  mediaList: z.array(sivoMediaSchema).optional(),
  // Cross-link end-card text (builder-set on the outro scene, per
  // platform/style): hooks to the other 2 platforms.
  crossLink: z.string().optional(),
  // Effect tag from the shot list (metadata for now — every cut is a
  // hard cut; "overlay-cut" is a future composition concern).
  effect: z.string().optional(),
  audioPath: z.string(),
  durationInFrames: z.number().int().positive(),
  // 1-based number for listicle items and news events (rendered big).
  index: z.number().int().positive().optional(),
  // Show the `$ ship_it;` code outro. Set only on the (first) outro shot —
  // never repeated across split sub-shots.
  codeOutro: z.boolean().optional(),
  // Short extra label rendered under the headline (e.g. listicle hook:
  // "5 ITEMS"). Empty/omitted = nothing rendered.
  meta: z.string().optional(),
  // Word timings (SAPI real timings, mock even-split, or external-voice
  // estimates). Used by build_props to split long scenes at word
  // boundaries. The composition does NOT render per-word colors.
  wordTimings: z
    .array(z.object({ w: z.string(), s: z.number(), e: z.number() }))
    .optional(),
});

export const sivoManifestSchema = z.object({
  version: z.string(),
  // Video style: fireship (Fireship grammar, v3) or news (6 news
  // layouts, v4). Default fireship — v3 manifests without a style
  // still validate.
  style: z.enum(["fireship", "news"]).default("fireship"),
  template: z.enum(["explainer", "listicle", "news", "x"]),
  // Channel badge (small white text, top, throughout). For Minh's own
  // channel this is "BRONZE BASE". "" = no badge.
  brand: z.string(),
  memeOn: z.boolean(),
  voice: z.string(),
  fps: z.number().int().default(30),
  warnings: z.array(z.string()),
  scenes: z.array(sivoSceneSchema).min(1),
});

export type SivoScene = z.infer<typeof sivoSceneSchema>;
export type SivoManifest = z.infer<typeof sivoManifestSchema>;
export type SivoMedia = z.infer<typeof sivoMediaSchema>;
