"use client";

import { useId } from "react";

import type { AvatarState } from "@/services/avatar";

interface InterviewerAvatarProps {
  state: AvatarState;
  /** Caption shown under the avatar and announced when the state changes. */
  label: string;
  /** From useAvatar; carries the `--avatar-level` the mouth and ring read. */
  rootRef?: React.RefObject<HTMLDivElement | null>;
}

/**
 * The AI interviewer's on-screen presence.
 *
 * Deliberately a stylised, obviously-synthetic figure rather than a synthetic
 * human: the platform does not claim to render a real person, and an abstract
 * presence avoids the uncanny valley entirely. It is drawn as inline SVG and
 * animated in CSS, so it needs no 3D asset, no avatar service, and no extra
 * dependency -- and it degrades to a still figure under prefers-reduced-motion.
 *
 * The component is presentational: it renders the state it is handed and holds
 * no interview logic of its own.
 */
export default function InterviewerAvatar({ state, label, rootRef }: InterviewerAvatarProps) {
  const gradientId = useId();
  const bodyGradient = `${gradientId}-body`;
  const haloGradient = `${gradientId}-halo`;
  const plateClip = `${gradientId}-plate`;

  return (
    <div className="avatar-stage" data-state={state} ref={rootRef}>
      <div className="avatar-ambient" aria-hidden="true" />

      <svg
        className="avatar-figure"
        viewBox="0 0 200 200"
        role="img"
        aria-label="AI interviewer"
        focusable="false"
      >
        <defs>
          <linearGradient id={bodyGradient} x1="0" y1="0" x2="0" y2="1">
            <stop className="avatar-stop-light" offset="0%" />
            <stop className="avatar-stop-deep" offset="100%" />
          </linearGradient>
          <radialGradient id={haloGradient} cx="50%" cy="50%" r="50%">
            <stop className="avatar-stop-halo-in" offset="55%" />
            <stop className="avatar-stop-halo-out" offset="100%" />
          </radialGradient>
          {/* Keeps the figure inside the portrait plate, so the shoulders read
              as a framed medallion rather than spilling past the disc. */}
          <clipPath id={plateClip}>
            <circle cx="100" cy="100" r="66" />
          </clipPath>
        </defs>

        <circle className="avatar-halo" cx="100" cy="100" r="86" fill={`url(#${haloGradient})`} />
        <circle className="avatar-ring" cx="100" cy="100" r="74" />
        <circle className="avatar-plate" cx="100" cy="100" r="66" />

        <g clipPath={`url(#${plateClip})`}>
          <g className="avatar-sway">
            <g className="avatar-breath">
              <path
                className="avatar-shoulders"
                d="M52 172c6-26 24-40 48-40s42 14 48 40z"
                fill={`url(#${bodyGradient})`}
              />
              <circle className="avatar-head" cx="100" cy="90" r="34" fill={`url(#${bodyGradient})`} />
              <path className="avatar-rim" d="M70 78a34 34 0 0 1 52-12" />

              <g className="avatar-eyes">
                <ellipse cx="88" cy="86" rx="4.2" ry="5" />
                <ellipse cx="112" cy="86" rx="4.2" ry="5" />
              </g>

              <g className="avatar-mouth-cadence">
                <ellipse className="avatar-mouth" cx="100" cy="106" rx="10" ry="6" />
              </g>
            </g>
          </g>
        </g>
      </svg>

      <div className="avatar-indicator" aria-hidden="true">
        <span className="avatar-dot" />
        <span className="avatar-dot" />
        <span className="avatar-dot" />
      </div>

      <p className="avatar-caption" role="status">
        {label}
      </p>
    </div>
  );
}
