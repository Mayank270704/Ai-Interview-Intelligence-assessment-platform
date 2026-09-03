"use client";

import { useInView } from "./motion";

const CENTER = { x: 450, y: 262 };
const RADIUS = { x: 336, y: 198 };
const NODE = { w: 168, h: 40 };

const ACTIONS = [
  "DEEPEN",
  "CLARIFY",
  "CHALLENGE",
  "INVESTIGATE CLAIM",
  "INCREASE DIFFICULTY",
  "DECREASE DIFFICULTY",
  "EXPLORE RELATED",
  "CHANGE TOPIC",
  "CONCLUDE",
];

const ACTIVE = "INCREASE DIFFICULTY";

function position(index: number) {
  const angle = ((-90 + index * (360 / ACTIONS.length)) * Math.PI) / 180;
  return {
    x: CENTER.x + RADIUS.x * Math.cos(angle),
    y: CENTER.y + RADIUS.y * Math.sin(angle),
  };
}

export default function InterviewerBrain() {
  const { ref, inView } = useInView<HTMLElement>();

  return (
    <section className={`lp-section lp-dark ${inView ? "is-visible" : ""}`} ref={ref}>
      <div className="lp-shell" style={{ textAlign: "center" }}>
        <span className="lp-eyebrow">Interviewer brain</span>
        <h2 style={{ marginTop: 16 }}>
          The next question isn&apos;t predetermined.
        </h2>
        <p
          className="lp-statement-sub lp-grad-text"
          style={{ marginTop: 14, fontSize: "clamp(1.8rem, 3.6vw, 2.7rem)", fontWeight: 650 }}
        >
          It&apos;s decided.
        </p>

        <div className="lp-brain-wrap">
          <svg
            className="lp-brain"
            viewBox="0 0 900 524"
            role="img"
            aria-label="The Interviewer Brain connected to nine possible interview actions, with Increase Difficulty selected"
          >
            <defs>
              <linearGradient id="lpBrainGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#22d3ee" />
                <stop offset="100%" stopColor="#8b5cf6" />
              </linearGradient>
              <radialGradient id="lpBrainCore" cx="35%" cy="30%" r="80%">
                <stop offset="0%" stopColor="#3b82f6" />
                <stop offset="100%" stopColor="#6d28d9" />
              </radialGradient>
            </defs>

            {ACTIONS.map((action, index) => {
              const point = position(index);
              return (
                <line
                  key={`edge-${action}`}
                  className="lp-brain-edge"
                  data-active={action === ACTIVE ? "true" : undefined}
                  x1={CENTER.x}
                  y1={CENTER.y}
                  x2={point.x}
                  y2={point.y}
                />
              );
            })}

            <g className="lp-brain-core">
              <circle cx={CENTER.x} cy={CENTER.y} r={72} />
              <text x={CENTER.x} y={CENTER.y - 4} textAnchor="middle">
                INTERVIEWER
              </text>
              <text x={CENTER.x} y={CENTER.y + 14} textAnchor="middle">
                BRAIN
              </text>
            </g>

            {ACTIONS.map((action, index) => {
              const point = position(index);
              const active = action === ACTIVE;
              return (
                <g className="lp-brain-node" data-active={active ? "true" : undefined} key={action}>
                  <rect
                    x={point.x - NODE.w / 2}
                    y={point.y - NODE.h / 2}
                    width={NODE.w}
                    height={NODE.h}
                    rx={12}
                  />
                  <text x={point.x} y={point.y + 4} textAnchor="middle">
                    {action}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        <div className="lp-brain-caption">
          <div className="lp-brain-chain">
            <span>Candidate demonstrated strong understanding</span>
            <span aria-hidden="true">→</span>
            <b>INTERVIEWER BRAIN</b>
            <span aria-hidden="true">→</span>
            <b data-accent="true">INCREASE DIFFICULTY</b>
            <span aria-hidden="true">→</span>
            <span>Next question</span>
          </div>
          <p className="lp-note">
            Illustrative decision. The action taken depends on the evidence in the interview.
          </p>
        </div>
      </div>
    </section>
  );
}
