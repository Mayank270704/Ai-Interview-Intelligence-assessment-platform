"use client";

import { useInView } from "./motion";

const STEPS = [
  { label: "Candidate Answer", sub: "Text, voice or video" },
  { label: "Answer Intelligence", sub: "Correctness, reasoning, depth, relevance" },
  { label: "Knowledge State", sub: "Concept confidence and evidence" },
  { label: "Interviewer Brain", sub: "Chooses the next action", accent: true },
  { label: "AI Decision", sub: "Deepen, clarify, challenge, investigate…", accent: true },
  { label: "Next Question", sub: "Generated from the decision" },
];

const FEATURES = [
  {
    title: "Dynamic Question Generation",
    body: "Questions are generated from candidate context and previous evidence—not a static question bank.",
  },
  {
    title: "Adaptive Difficulty",
    body: "Interview difficulty responds to demonstrated performance.",
  },
  {
    title: "Interviewer Brain",
    body: "The system can deepen, clarify, challenge, investigate claims, explore related concepts, or change direction.",
  },
  {
    title: "Knowledge State",
    body: "Candidate understanding evolves throughout the interview.",
  },
];

export default function AdaptivePipeline() {
  const { ref, inView } = useInView<HTMLElement>();

  return (
    <section
      className={`lp-section lp-section--tint ${inView ? "is-visible" : ""}`}
      ref={ref}
      id="how-it-works"
    >
      <div className="lp-shell lp-split">
        <div className="lp-flow">
          <span className="lp-eyebrow">Interview loop</span>
          <div className="lp-flow-list" style={{ marginTop: 18 }}>
            <span className="lp-flow-line" aria-hidden="true" />
            {STEPS.map((step, index) => (
              <div
                className="lp-flow-step"
                key={step.label}
                data-accent={step.accent ? "true" : undefined}
                style={{ "--lp-i": index } as React.CSSProperties}
              >
                <span className="lp-flow-node" aria-hidden="true">
                  {index + 1}
                </span>
                <span>
                  <span className="lp-flow-label">{step.label}</span>
                  <span className="lp-flow-sub">{step.sub}</span>
                </span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <span className="lp-eyebrow">Adaptive interviewing</span>
          <h2 style={{ marginTop: 16 }}>Interviews that think.</h2>
          <p className="lp-lede">
            Each turn is a decision, not a lookup. The system reads the answer, updates what it
            believes about the candidate, and chooses where the interview goes next.
          </p>

          <div className="lp-features">
            {FEATURES.map((feature) => (
              <div className="lp-feature" key={feature.title}>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
