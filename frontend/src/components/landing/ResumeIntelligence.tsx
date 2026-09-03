"use client";

import { useInView } from "./motion";

const CHIPS = [
  { label: "AI Task Planner" },
  { label: "FastAPI" },
  { label: "Gemini" },
  { label: "Multi-Agent AI" },
  { label: "RAG" },
  { label: "FAISS" },
];

const STEPS = [
  { kind: "Resume", text: "“Built a RAG-based PDF Reader”" },
  { kind: "Extracted", text: "Claim detected" },
  { kind: "Interview", text: "Queued for investigation" },
  { kind: "Question", text: "“Why did you choose FAISS for retrieval?”", final: true },
];

export default function ResumeIntelligence() {
  const { ref, inView } = useInView<HTMLElement>();

  return (
    <section className={`lp-section ${inView ? "is-visible" : ""}`} ref={ref}>
      <div className="lp-shell lp-split">
        <div className="lp-resume">
          <div className="lp-resume-card">
            <div className="lp-resume-head">
              <span className="lp-resume-doc" aria-hidden="true" />
              <span>
                <span className="lp-flow-label">resume.pdf</span>
                <span className="lp-flow-sub">Skills, projects and claims extracted</span>
              </span>
            </div>
            <div className="lp-chips">
              {CHIPS.map((chip, index) => (
                <span
                  className="lp-chip"
                  key={chip.label}
                  data-claim={chip.label === "RAG" || chip.label === "FAISS" ? "true" : undefined}
                  style={{ "--lp-i": index } as React.CSSProperties}
                >
                  {chip.label}
                </span>
              ))}
            </div>
          </div>

          <div className="lp-extract">
            {STEPS.map((step, index) => (
              <div
                className="lp-extract-step"
                key={step.kind}
                data-final={step.final ? "true" : undefined}
                style={{ "--lp-i": index } as React.CSSProperties}
              >
                <span className="lp-extract-kind">{step.kind}</span>
                <span>{step.text}</span>
              </div>
            ))}
          </div>
          <p className="lp-note">Illustrative extraction flow.</p>
        </div>

        <div>
          <span className="lp-eyebrow">Resume intelligence</span>
          <h2 style={{ marginTop: 16 }}>Your resume becomes part of the interview.</h2>
          <p className="lp-lede">
            AI extracts skills, projects, experience and claims—then turns relevant evidence into
            targeted interview questions.
          </p>
          <div className="lp-features">
            <div className="lp-feature">
              <h3>Claims become questions</h3>
              <p>
                A specific claim on your resume is something the interview can return to and probe,
                rather than a line that is read once and scored.
              </p>
            </div>
            <div className="lp-feature">
              <h3>Verified, not assumed</h3>
              <p>
                Each investigated claim ends the interview marked supported, unsupported or still
                uncertain, with the evidence that led there.
              </p>
            </div>
            <div className="lp-feature">
              <h3>ATS diagnostics too</h3>
              <p>
                The same extraction powers resume readiness scoring and job-description matching,
                with structured, actionable diagnostics.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
