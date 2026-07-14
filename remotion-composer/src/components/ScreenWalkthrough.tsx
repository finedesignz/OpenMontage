import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// ---------------------------------------------------------------------------
// ScreenWalkthrough — real screen capture + human-feel annotation layer.
//
// Everything (video, cursor, ripples, ink) lives inside ONE transformed
// container, so overlays stay locked to the UI they annotate even while a
// zoom-to-region is active. Coordinates are raw capture pixels (1920x1080),
// viewport-relative at their timestamp — page scroll is already baked into
// the capture, so we never re-apply scroll offsets.
// ---------------------------------------------------------------------------

export interface ZoomRegion {
  start_seconds: number;
  end_seconds: number;
  zoom: number;
  focus: { x: number; y: number; w: number; h: number };
  transition_ms?: number;
}

export interface CursorKeyframe {
  t: number;
  x: number;
  y: number;
  state?: "idle" | "move" | "click";
}

export interface ClickRipple {
  t: number;
  x: number;
  y: number;
  radius_px?: number;
  color?: string;
  duration_ms?: number;
}

export interface InkCallout {
  t_in: number;
  t_out: number;
  style: "underline_sweep" | "highlight_box" | "ink_circle";
  box: { x: number; y: number; w: number; h: number };
  pad_px?: number;
  color?: string;
}

export interface ScreenWalkthroughProps {
  source: string;
  captureWidth?: number;
  captureHeight?: number;
  sourceInSeconds?: number;
  zoomRegions?: ZoomRegion[];
  cursorTrack?: CursorKeyframe[];
  clickRipples?: ClickRipple[];
  inkCallouts?: InkCallout[];
  accentColor?: string;
  /** Seconds of travel the cursor takes to reach each keyframe. */
  cursorTravelSeconds?: number;
}

function resolveAsset(src: string): string {
  if (src.startsWith("http://") || src.startsWith("https://") || src.startsWith("data:")) {
    return src;
  }
  const clean = src.replace(/^file:\/\/\/?/, "");
  if (clean.startsWith("/") || /^[A-Za-z]:[\\/]/.test(clean)) {
    return `file:///${clean.replace(/\\/g, "/")}`;
  }
  return staticFile(clean);
}

const easeInOutCubic = (p: number) =>
  p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;

/** Ease-out with a small overshoot, then settle — reads like a real hand. */
const easeOutBackSoft = (p: number) => {
  const c1 = 1.10158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2);
};

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

// --- Camera (zoom-to-region) --------------------------------------------------

function cameraAt(
  t: number,
  regions: ZoomRegion[],
  W: number,
  H: number
): { scale: number; tx: number; ty: number } {
  let zoom = 1;
  let cx = W / 2;
  let cy = H / 2;

  for (const r of regions) {
    const ramp = (r.transition_ms ?? 700) / 1000;
    const inStart = r.start_seconds - ramp;
    const outEnd = r.end_seconds + ramp;
    if (t < inStart || t > outEnd) continue;

    // How "engaged" this region is, 0..1
    let k: number;
    if (t < r.start_seconds) {
      k = easeInOutCubic(clamp((t - inStart) / ramp, 0, 1));
    } else if (t > r.end_seconds) {
      k = easeInOutCubic(clamp((outEnd - t) / ramp, 0, 1));
    } else {
      k = 1;
    }

    const fx = r.focus.x + r.focus.w / 2;
    const fy = r.focus.y + r.focus.h / 2;

    zoom = 1 + (r.zoom - 1) * k;
    cx = W / 2 + (fx - W / 2) * k;
    cy = H / 2 + (fy - H / 2) * k;
    break;
  }

  // Translate so (cx, cy) lands at frame centre, then clamp so we never
  // expose an edge (which would read as a letterbox/gray band).
  const tx = clamp(W / 2 - cx * zoom, W * (1 - zoom), 0);
  const ty = clamp(H / 2 - cy * zoom, H * (1 - zoom), 0);

  return { scale: zoom, tx, ty };
}

// --- Cursor -------------------------------------------------------------------

function cursorAt(
  t: number,
  track: CursorKeyframe[],
  travel: number
): { x: number; y: number; moving: boolean } {
  if (track.length === 0) return { x: -100, y: -100, moving: false };

  const first = track[0];
  if (t <= first.t) return { x: first.x, y: first.y, moving: false };

  for (let i = 1; i < track.length; i++) {
    const prev = track[i - 1];
    const cur = track[i];
    if (t > cur.t) continue;

    // Hold at the previous position, then make one deliberate eased move
    // that ARRIVES exactly on the keyframe time. Never a teleport, never a
    // 15-second dead drift across the screen.
    const gap = cur.t - prev.t;
    const dur = Math.min(travel, gap * 0.6);
    const moveStart = cur.t - dur;

    const samePoint = prev.x === cur.x && prev.y === cur.y;
    if (t < moveStart || samePoint || dur <= 0) {
      return { x: prev.x, y: prev.y, moving: false };
    }

    const p = clamp((t - moveStart) / dur, 0, 1);
    const dist = Math.hypot(cur.x - prev.x, cur.y - prev.y);
    // Long travels get the overshoot-and-settle; short nudges stay clean.
    const e = dist > 400 ? easeOutBackSoft(p) : easeInOutCubic(p);
    return {
      x: prev.x + (cur.x - prev.x) * e,
      y: prev.y + (cur.y - prev.y) * e,
      moving: p < 1,
    };
  }

  const last = track[track.length - 1];
  return { x: last.x, y: last.y, moving: false };
}

const CursorArrow: React.FC<{ x: number; y: number; press: number }> = ({ x, y, press }) => {
  // press: 0 = at rest, 1 = fully pressed
  const scale = 1 - press * 0.18;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `translate(-3px, -2px) scale(${scale})`,
        transformOrigin: "3px 2px",
        willChange: "transform",
        pointerEvents: "none",
      }}
    >
      <svg width={34} height={44} viewBox="0 0 34 44" fill="none">
        <defs>
          <filter id="cursorShadow" x="-60%" y="-60%" width="240%" height="240%">
            <feDropShadow dx="1" dy="2" stdDeviation="2.2" floodColor="#000" floodOpacity="0.45" />
          </filter>
        </defs>
        <path
          d="M3 2 L3 30.5 L10.4 23.6 L15.4 34.8 L20.7 32.4 L15.7 21.4 L25.6 21.0 Z"
          fill="#FFFFFF"
          stroke="#111827"
          strokeWidth={1.8}
          strokeLinejoin="round"
          filter="url(#cursorShadow)"
        />
      </svg>
    </div>
  );
};

// --- Ink ----------------------------------------------------------------------

const InkLayer: React.FC<{ t: number; callouts: InkCallout[]; accent: string; W: number; H: number }> = ({
  t,
  callouts,
  accent,
  W,
  H,
}) => (
  <svg
    width={W}
    height={H}
    viewBox={`0 0 ${W} ${H}`}
    style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
  >
    {callouts.map((c, i) => {
      if (t < c.t_in || t > c.t_out) return null;

      const color = c.color || accent;
      const drawDur = 0.45;
      const draw = easeInOutCubic(clamp((t - c.t_in) / drawDur, 0, 1));
      // Fade the ink out over the last 0.35s so it clears, never snaps off.
      const fade = interpolate(t, [c.t_out - 0.35, c.t_out], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      const pad = c.pad_px ?? 0;
      const { x, y, w, h } = c.box;

      if (c.style === "underline_sweep") {
        const y0 = y + h + 8;
        const len = w;
        return (
          <g key={i} opacity={fade}>
            <path
              d={`M ${x} ${y0} q ${len * 0.25} 5 ${len * 0.5} 1 q ${len * 0.25} -4 ${len * 0.5} 3`}
              stroke={color}
              strokeWidth={6}
              strokeLinecap="round"
              fill="none"
              strokeDasharray={len * 1.1}
              strokeDashoffset={len * 1.1 * (1 - draw)}
            />
          </g>
        );
      }

      if (c.style === "highlight_box") {
        const bx = x - pad - 6;
        const by = y - pad - 6;
        const bw = w + pad * 2 + 12;
        const bh = h + pad * 2 + 12;
        const peri = 2 * (bw + bh);
        return (
          <g key={i} opacity={fade}>
            <rect
              x={bx}
              y={by}
              width={bw}
              height={bh}
              rx={10}
              fill={color}
              opacity={0.07 * draw}
            />
            <rect
              x={bx}
              y={by}
              width={bw}
              height={bh}
              rx={10}
              stroke={color}
              strokeWidth={4}
              fill="none"
              strokeLinecap="round"
              strokeDasharray={peri}
              strokeDashoffset={peri * (1 - draw)}
            />
          </g>
        );
      }

      // ink_circle — hand-drawn ellipse looping past its own start
      const cx = x + w / 2;
      const cy = y + h / 2;
      const rx = w / 2 + pad + 12;
      const ry = h / 2 + pad + 10;
      const peri = Math.PI * (3 * (rx + ry) - Math.sqrt((3 * rx + ry) * (rx + 3 * ry)));
      return (
        <g key={i} opacity={fade}>
          <ellipse
            cx={cx}
            cy={cy}
            rx={rx}
            ry={ry}
            stroke={color}
            strokeWidth={5}
            fill="none"
            strokeLinecap="round"
            transform={`rotate(-4 ${cx} ${cy})`}
            strokeDasharray={peri}
            strokeDashoffset={peri * (1 - draw)}
          />
        </g>
      );
    })}
  </svg>
);

// --- Ripple -------------------------------------------------------------------

const RippleLayer: React.FC<{ t: number; ripples: ClickRipple[]; accent: string }> = ({
  t,
  ripples,
  accent,
}) => (
  <>
    {ripples.map((r, i) => {
      const dur = (r.duration_ms ?? 450) / 1000;
      // Start the ring exactly on the click frame and let it live a touch
      // longer than the press so the eye actually catches it.
      const life = dur * 1.6;
      if (t < r.t || t > r.t + life) return null;

      const p = clamp((t - r.t) / life, 0, 1);
      const maxR = r.radius_px ?? 54;
      const rad = 8 + (maxR - 8) * easeInOutCubic(p);
      const opacity = (1 - p) * 0.9;
      const color = r.color || accent;

      return (
        <div key={i}>
          {/* expanding ring */}
          <div
            style={{
              position: "absolute",
              left: r.x - rad,
              top: r.y - rad,
              width: rad * 2,
              height: rad * 2,
              borderRadius: "50%",
              border: `${Math.max(2, 5 * (1 - p))}px solid ${color}`,
              opacity,
              pointerEvents: "none",
            }}
          />
          {/* soft flash under the pointer */}
          <div
            style={{
              position: "absolute",
              left: r.x - maxR * 0.55,
              top: r.y - maxR * 0.55,
              width: maxR * 1.1,
              height: maxR * 1.1,
              borderRadius: "50%",
              background: color,
              opacity: opacity * 0.28 * (1 - p),
              filter: "blur(6px)",
              pointerEvents: "none",
            }}
          />
        </div>
      );
    })}
  </>
);

// --- Main ---------------------------------------------------------------------

export const ScreenWalkthrough: React.FC<ScreenWalkthroughProps> = ({
  source,
  captureWidth = 1920,
  captureHeight = 1080,
  sourceInSeconds = 0,
  zoomRegions = [],
  cursorTrack = [],
  clickRipples = [],
  inkCallouts = [],
  accentColor = "#EA580C",
  cursorTravelSeconds = 0.9,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;

  const W = captureWidth;
  const H = captureHeight;

  // Fade in from white on the open and back out on the close, so the cut never
  // snaps to/from the composition background (scene_plan: fade_from_white_10f /
  // fade_to_white_15f).
  const fadeIn = interpolate(frame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const opacity = Math.min(fadeIn, fadeOut);

  const cam = cameraAt(t, zoomRegions, W, H);
  const cur = cursorAt(t, cursorTrack, cursorTravelSeconds);

  // Cursor press dip, driven off the real click timestamps.
  let press = 0;
  for (const r of clickRipples) {
    const d = t - r.t;
    if (d >= -0.06 && d <= 0.16) {
      press = 1 - clamp(Math.abs(d) / 0.16, 0, 1);
    }
  }

  return (
    <AbsoluteFill style={{ overflow: "hidden", background: "#FFFFFF" }}>
      <div
        style={{
          position: "absolute",
          width: W,
          height: H,
          transformOrigin: "0 0",
          transform: `translate(${cam.tx}px, ${cam.ty}px) scale(${cam.scale})`,
          willChange: "transform, opacity",
          opacity,
        }}
      >
        <OffthreadVideo
          src={resolveAsset(source)}
          startFrom={Math.round(sourceInSeconds * fps)}
          style={{ width: W, height: H, objectFit: "fill", display: "block" }}
          muted
        />

        <InkLayer t={t} callouts={inkCallouts} accent={accentColor} W={W} H={H} />
        <RippleLayer t={t} ripples={clickRipples} accent={accentColor} />
        {cursorTrack.length > 0 && <CursorArrow x={cur.x} y={cur.y} press={press} />}
      </div>
    </AbsoluteFill>
  );
};
