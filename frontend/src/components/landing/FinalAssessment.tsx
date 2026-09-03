"use client";

import { CountUp, useInView } from "./motion";

const DIMENSIONS = [
  { label: "Technical Knowledge", value: 86 },
  { label: "Problem Solving", value: 79 },
  { label: "Communication", value: 84 },
  { label: "Reasoning", value: 88 },
  { label: "Application", value: 74 },
];

export default function FinalAssessment() {
  const { ref, inView } = useInView<HTMLElement>();

  return (
    <section
      className={`lp-section lp-section--tint ${inView ? "is-visible" : ""}`}
      ref={ref}
      id="assessment"
    >
      <div className="lp-shell">
        <span className="lp-eyebrow">Final assessment</span>
        <h2 style={{ marginTop: 16, fontSize: "clamp(1.95rem, 4vw, 3.05rem)", fontWeight: 600 }}>
          Turn the interview into a clear assessment.
        </h2>
        <p className="lp-lede" style={{ marginTop: 18 }}>
          When the interview ends, the evidence collected across every turn is aggregated into a
          structured readiness picture—strengths, gaps, and where to focus next.
        </p>

        <div className="lp-assess">
          <div className="lp-assess-card">
            <span className="lp-assess-complete">Interview complete</span>
            <div className="lp-assess-score">
              <b>
                <CountUp to={82} active={inView} />
              </b>
              <span>/ 100 interview readiness</span>
            </div>

            <div className="lp-assess-metrics">
              {DIMENSIONS.map((dimension, index) => (
                <div className="lp-metric" key={dimension.label}>
                  <span className="lp-metric-top">
                    <b>{dimension.label}</b>
                    <i>
                      <CountUp to={dimension.value} active={inView} />
                    </i>
                  </span>
                  <span
                    className="lp-bar"
                    style={
                      {
                        "--lp-i": index,
                        "--lp-v": dimension.value / 100,
                      } as React.CSSProperties
                    }
                  >
                    <i />
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="lp-lists">
            <div className="lp-list">
              <h3>Strongest areas</h3>
              <ul>
                <li data-marker="✓">Python</li>
                <li data-marker="✓">RAG architecture</li>
                <li data-marker="✓">API development</li>
              </ul>
            </div>
            <div className="lp-list">
              <h3>Knowledge gaps</h3>
              <ul>
                <li data-marker="→">Database scaling</li>
                <li data-marker="→">Distributed systems</li>
              </ul>
            </div>
            <div className="lp-list">
              <h3>Recommended focus</h3>
              <ul>
                <li data-marker="•">System design</li>
                <li data-marker="•">Vector DB optimization</li>
                <li data-marker="•">API scaling</li>
              </ul>
            </div>
          </div>
        </div>

        <p className="lp-note" style={{ marginTop: 20 }}>
          Example assessment. Real scores are derived from the evidence in your own interview.
        </p>
      </div>
    </section>
  );
}
