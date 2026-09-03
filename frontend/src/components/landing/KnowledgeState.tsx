"use client";

import { CountUp, useInView } from "./motion";

const CENTER = { x: 450, y: 240 };
const NODE = { w: 182, h: 60 };

const NODES = [
  { label: "Python", x: 152, y: 78, value: 88 },
  { label: "RAG", x: 450, y: 56, value: 82 },
  { label: "LLMs", x: 748, y: 88, value: 74 },
  { label: "FastAPI", x: 112, y: 240, value: 79 },
  { label: "Vector Databases", x: 788, y: 248, value: 68 },
  { label: "SQL", x: 182, y: 402, value: 61 },
  { label: "System Design", x: 718, y: 408, value: 45 },
];

export default function KnowledgeState() {
  const { ref, inView } = useInView<HTMLElement>();

  return (
    <section className={`lp-section ${inView ? "is-visible" : ""}`} ref={ref}>
      <div className="lp-shell">
        <span className="lp-eyebrow">Knowledge state</span>
        <h2 style={{ marginTop: 16, fontSize: "clamp(1.95rem, 4vw, 3.05rem)", fontWeight: 600 }}>
          Watch your knowledge state evolve.
        </h2>
        <p className="lp-lede" style={{ marginTop: 18 }}>
          Every response becomes structured evidence of what the candidate knows, what requires
          verification, and where the interview should go next.
        </p>

        <div className="lp-graph-wrap">
          <svg
            className="lp-graph"
            viewBox="0 0 900 480"
            role="img"
            aria-label="Concept map showing seven concepts linked to the candidate, each with a confidence level"
          >
            {NODES.map((node, index) => {
              const length = Math.hypot(node.x - CENTER.x, node.y - CENTER.y);
              return (
                <line
                  key={`edge-${node.label}`}
                  className="lp-graph-edge"
                  x1={CENTER.x}
                  y1={CENTER.y}
                  x2={node.x}
                  y2={node.y}
                  style={{ "--lp-len": length, "--lp-i": index } as React.CSSProperties}
                />
              );
            })}

            <g className="lp-graph-core">
              <circle cx={CENTER.x} cy={CENTER.y} r={58} />
              <text x={CENTER.x} y={CENTER.y + 4} textAnchor="middle">
                Candidate
              </text>
            </g>

            {NODES.map((node, index) => {
              const x = node.x - NODE.w / 2;
              const y = node.y - NODE.h / 2;
              return (
                <g className="lp-graph-node" key={node.label}>
                  <rect x={x} y={y} width={NODE.w} height={NODE.h} rx={13} />
                  <text x={x + 16} y={y + 25}>
                    {node.label}
                  </text>
                  <text className="lp-graph-val" x={x + NODE.w - 16} y={y + 25} textAnchor="end">
                    <CountUp to={node.value} active={inView} />%
                  </text>
                  <rect
                    className="lp-graph-meter"
                    x={x + 16}
                    y={y + 37}
                    width={NODE.w - 32}
                    height={6}
                    rx={3}
                  />
                  <rect
                    className="lp-graph-fill"
                    x={x + 16}
                    y={y + 37}
                    width={((NODE.w - 32) * node.value) / 100}
                    height={6}
                    rx={3}
                    style={{ "--lp-i": index } as React.CSSProperties}
                  />
                </g>
              );
            })}
          </svg>
        </div>

        <p className="lp-note" style={{ marginTop: 18 }}>
          Representative concept map. Values illustrate how confidence accumulates during an
          interview and are not a record of a real candidate.
        </p>
      </div>
    </section>
  );
}
