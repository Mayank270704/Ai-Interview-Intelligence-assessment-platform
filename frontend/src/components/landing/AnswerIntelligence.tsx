"use client";

import { CountUp, useInView } from "./motion";

const METRICS = [
  { label: "Correctness", value: 91 },
  { label: "Reasoning", value: 86 },
  { label: "Depth", value: 78 },
  { label: "Relevance", value: 92 },
  { label: "Application", value: 76 },
];

export default function AnswerIntelligence() {
  const { ref, inView } = useInView<HTMLElement>();

  return (
    <section className={`lp-section lp-dark ${inView ? "is-visible" : ""}`} ref={ref}>
      <div className="lp-shell lp-split">
        <div>
          <span className="lp-eyebrow">Answer intelligence</span>
          <h2 style={{ marginTop: 16 }}>
            Don&apos;t just get a score.
            <br />
            Understand the answer.
          </h2>
          <p className="lp-lede" style={{ marginTop: 18 }}>
            Every answer is broken down into correctness, reasoning, depth, relevance and
            application—alongside the concepts you demonstrated, the ones you missed, and any claim
            you made without support.
          </p>
          <div className="lp-features">
            <div className="lp-feature" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
              <h3>Evidence, not vibes</h3>
              <p>Each judgement is tied to what you actually said.</p>
            </div>
            <div className="lp-feature" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
              <h3>Gaps become the next question</h3>
              <p>What you left out is exactly what the interviewer probes next.</p>
            </div>
          </div>
        </div>

        <div className="lp-panel">
          <div className="lp-mock-bar" style={{ background: "none", border: "none", padding: 0 }}>
            <span className="lp-mock-title" style={{ color: "var(--lp-on-navy)" }}>
              Answer Intelligence
            </span>
            <span className="lp-note" style={{ marginLeft: "auto" }}>
              Illustrative
            </span>
          </div>

          <div className="lp-score-head" style={{ marginTop: 14 }}>
            <span className="lp-score-big">
              <CountUp to={84} active={inView} />
            </span>
            <span style={{ color: "var(--lp-on-navy-muted)", fontSize: "0.9rem" }}>
              Overall analysis
            </span>
          </div>

          <div className="lp-metrics">
            {METRICS.map((metric, index) => (
              <div className="lp-metric" key={metric.label}>
                <span className="lp-metric-top">
                  <b>{metric.label}</b>
                  <i>
                    <CountUp to={metric.value} active={inView} />
                  </i>
                </span>
                <span
                  className="lp-bar"
                  style={
                    {
                      "--lp-i": index,
                      "--lp-v": metric.value / 100,
                    } as React.CSSProperties
                  }
                >
                  <i />
                </span>
              </div>
            ))}
          </div>

          <div className="lp-callouts">
            <div className="lp-callout" data-kind="strength">
              <b>Strength detected</b>
              <p>Clearly explained vector similarity and retrieval flow.</p>
            </div>
            <div className="lp-callout" data-kind="gap">
              <b>Knowledge gap</b>
              <p>Did not explain chunk-size tradeoffs.</p>
            </div>
            <div className="lp-callout" data-kind="action">
              <b>AI next action</b>
              <span className="lp-callout-action">CHALLENGE</span>
            </div>
          </div>

          <p className="lp-next-q">
            <strong style={{ fontWeight: 600 }}>Next question · </strong>
            What happens when your chunks become too large?
          </p>
        </div>
      </div>
    </section>
  );
}
