"use client";

import Link from "next/link";

import InterviewerAvatar from "@/components/avatar/InterviewerAvatar";

import { usePointerTilt } from "./motion";

const KNOWLEDGE = [
  { concept: "RAG", state: "Strong", tone: "strong" },
  { concept: "Vector Search", state: "Developing", tone: "developing" },
  { concept: "System Design", state: "Needs evidence", tone: "evidence" },
] as const;

const WAVE_BARS = 34;

export default function Hero() {
  const tiltRef = usePointerTilt<HTMLDivElement>();

  return (
    <section className="lp-hero">
      <div className="lp-shell lp-hero-grid">
        <div>
          <span className="lp-eyebrow">Adaptive AI interviewing</span>
          <h1>
            Master interviews with an AI that{" "}
            <span className="lp-grad-text">actually understands you.</span>
          </h1>
          <p className="lp-lede">
            Adaptive AI interviews that analyze your answers, verify resume claims, track your
            knowledge, and dynamically decide what to ask next.
          </p>

          <div className="lp-hero-actions">
            <Link href="/resume/upload" className="lp-btn lp-btn--primary">
              Start Free Interview
              <span className="lp-btn-arrow" aria-hidden="true">
                →
              </span>
            </Link>
            <a href="#how-it-works" className="lp-btn lp-btn--ghost">
              See How It Works
            </a>
          </div>

          <div className="lp-hero-meta">
            <span>Resume-grounded questions</span>
            <span>Text, voice and video</span>
            <span>Evidence-based assessment</span>
          </div>
        </div>

        <div className="lp-hero-visual" ref={tiltRef}>
          <div className="lp-mock">
            <div className="lp-mock-bar">
              <span className="lp-mock-title">AI Interview</span>
              <span className="lp-live">LIVE</span>
              <span className="lp-note" style={{ marginLeft: "auto" }}>
                Illustrative
              </span>
            </div>

            <div className="lp-mock-body">
              <div className="lp-mock-question">
                <InterviewerAvatar state="speaking" label="Asking" />
                <div>
                  <span className="lp-q-label">Question 4</span>
                  <p className="lp-q-text">
                    You mentioned building a RAG-based PDF Reader. How did you handle retrieval
                    quality when the query was ambiguous?
                  </p>
                </div>
              </div>

              <div className="lp-wave" role="img" aria-label="Candidate audio input level">
                {Array.from({ length: WAVE_BARS }, (_, index) => (
                  <i key={index} style={{ "--lp-i": index } as React.CSSProperties} />
                ))}
              </div>

              <div>
                <span className="lp-q-label">Candidate Knowledge State</span>
                <div className="lp-ks">
                  {KNOWLEDGE.map((row) => (
                    <div className="lp-ks-row" key={row.concept}>
                      <b>{row.concept}</b>
                      <span className={`lp-tag lp-tag--${row.tone}`}>{row.state}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="lp-decision">
                <small>AI Decision</small>
                <b>DEEPEN</b>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
