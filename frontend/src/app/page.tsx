import type { Metadata } from "next";
import { Sora } from "next/font/google";
import Link from "next/link";

import AdaptivePipeline from "@/components/landing/AdaptivePipeline";
import AnswerIntelligence from "@/components/landing/AnswerIntelligence";
import FinalAssessment from "@/components/landing/FinalAssessment";
import Hero from "@/components/landing/Hero";
import InterviewerBrain from "@/components/landing/InterviewerBrain";
import KnowledgeState from "@/components/landing/KnowledgeState";
import LandingNav from "@/components/landing/LandingNav";
import { Reveal } from "@/components/landing/motion";
import Multimodal from "@/components/landing/Multimodal";
import ResumeIntelligence from "@/components/landing/ResumeIntelligence";
import Statement from "@/components/landing/Statement";

import "./landing.css";

const sora = Sora({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-display" });

export const metadata: Metadata = {
  title: "Adaptive AI interviews that understand your answers",
  description:
    "Practice with an AI interviewer that analyzes your answers, verifies resume claims, tracks your knowledge state, and decides what to ask next. Text, voice and video interviews with an evidence-based final assessment.",
  openGraph: {
    title: "AI Interview Intelligence",
    description:
      "Adaptive AI interviews that analyze your answers, verify resume claims, track your knowledge, and dynamically decide what to ask next.",
    type: "website",
  },
};

export default function HomePage() {
  return (
    <div className={`lp ${sora.variable}`}>
      {/* Scroll-reveal hides content until it animates in. Gate that on JS being
          present so the page is fully readable without it. Runs during parse,
          before first paint, so there is no flash. */}
      <script
        dangerouslySetInnerHTML={{
          __html: 'document.documentElement.classList.add("lp-js")',
        }}
      />

      <div className="lp-announce">
        <div className="lp-announce-inner">
          <Link href="/resume/upload">
            Adaptive AI interviews, multimodal assessment, and real-time intelligence
            <span aria-hidden="true">→</span>
          </Link>
        </div>
      </div>

      <LandingNav />

      <main>
        <Hero />
        <Statement />
        <AdaptivePipeline />
        <ResumeIntelligence />
        <Multimodal />
        <AnswerIntelligence />
        <KnowledgeState />
        <InterviewerBrain />
        <FinalAssessment />

        <section className="lp-section lp-cta">
          <div className="lp-shell">
            <Reveal>
              <h2>Your next interview should adapt to you.</h2>
              <p className="lp-lede">
                Practice with an AI interviewer that follows your evidence—not a script.
              </p>
              <div className="lp-cta-actions">
                <Link href="/resume/upload" className="lp-btn lp-btn--primary">
                  Start Your Interview
                  <span className="lp-btn-arrow" aria-hidden="true">
                    →
                  </span>
                </Link>
                <Link href="/dashboard" className="lp-btn lp-btn--ghost">
                  Explore the Platform
                </Link>
              </div>
            </Reveal>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-shell">
          <div className="lp-footer-inner">
            <div>
              <Link href="/" className="lp-brand">
                <span className="lp-brand-mark" aria-hidden="true" />
                Interview Intelligence
              </Link>
              <p>
                Adaptive AI interviews grounded in your resume, with evidence-based analysis and a
                structured final assessment.
              </p>
            </div>
            <nav aria-label="Footer">
              <a href="#platform">Platform</a>
              <a href="#how-it-works">How It Works</a>
              <a href="#assessment">Assessment</a>
              <Link href="/login">Login</Link>
            </nav>
          </div>
          <p className="lp-footer-legal">
            AI Interview Intelligence &amp; Assessment Platform. Interface previews on this page are
            illustrative renderings of platform behaviour, not records of real candidates.
          </p>
        </div>
      </footer>
    </div>
  );
}
