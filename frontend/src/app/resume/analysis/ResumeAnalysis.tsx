"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import type { ATSScoreResponse } from "@/services/api/types";
import { getAtsScore } from "@/services/resume";

type Status = "idle" | "scoring" | "done" | "error";

function KeywordList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div>
      <h3>{title}</h3>
      <div className="badge-row">
        {items.map((item) => (
          <span key={item} className="badge">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function FeedbackList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div>
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function ResumeAnalysis() {
  const searchParams = useSearchParams();
  const resumeId = searchParams.get("resumeId");

  const [jobDescription, setJobDescription] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<ATSScoreResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!resumeId) {
    return (
      <main className="narrow">
        <div className="page-header">
          <h1>Resume analysis</h1>
        </div>
        <div className="error-banner" role="alert">
          No resume was specified. Upload a resume first to see its ATS score.
        </div>
        <div className="actions">
          <Link href="/resume/upload" className="button">
            Upload a resume
          </Link>
        </div>
      </main>
    );
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (status === "scoring") {
      return;
    }

    setStatus("scoring");
    setErrorMessage(null);

    try {
      const score = await getAtsScore(resumeId, jobDescription);
      setResult(score);
      setStatus("done");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong.");
      setStatus("error");
    }
  };

  return (
    <main className="narrow">
      <div className="page-header">
        <h1>Resume analysis</h1>
        <p>
          Score your resume on general ATS readiness, or paste a job description to score it against
          that specific role.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <label className="label" htmlFor="job-description">
          Job description (optional)
        </label>
        <textarea
          id="job-description"
          className="field"
          rows={6}
          value={jobDescription}
          onChange={(event) => setJobDescription(event.target.value)}
          disabled={status === "scoring"}
          placeholder="Paste the job description here to score against it…"
        />

        {status === "error" && errorMessage && <div className="error-banner" role="alert">{errorMessage}</div>}

        <div className="actions">
          <button type="submit" className="button" disabled={status === "scoring"}>
            {status === "scoring" && <span className="spinner" aria-hidden="true" />}
            {status === "scoring" ? "Scoring…" : "Score my resume"}
          </button>
        </div>
      </form>

      {result && (
        <>
          <div className="card">
            <div className="score-hero">
              <span className="score-value">{result.ats_score}</span>
              <span className="score-max">/ 100</span>
            </div>
            <p className="progress-label">
              {result.mode === "jd_match"
                ? "Match against the job description you provided"
                : "General ATS readiness (no job description provided)"}
            </p>
          </div>

          {(result.matched_keywords.length > 0 ||
            result.missing_keywords.length > 0 ||
            result.matched_skills.length > 0 ||
            result.missing_skills.length > 0) && (
            <div className="card">
              <h2>Keywords and skills</h2>
              <KeywordList title="Matched keywords" items={result.matched_keywords} />
              <KeywordList title="Missing keywords" items={result.missing_keywords} />
              <KeywordList title="Matched skills" items={result.matched_skills} />
              <KeywordList title="Missing skills" items={result.missing_skills} />
            </div>
          )}

          {(result.section_feedback.length > 0 ||
            result.experience_feedback.length > 0 ||
            result.project_feedback.length > 0 ||
            result.measurable_impact_feedback.length > 0 ||
            result.suggestions.length > 0) && (
            <div className="card">
              <h2>Feedback</h2>
              <FeedbackList title="Sections" items={result.section_feedback} />
              <FeedbackList title="Experience" items={result.experience_feedback} />
              <FeedbackList title="Projects" items={result.project_feedback} />
              <FeedbackList title="Measurable impact" items={result.measurable_impact_feedback} />
              <FeedbackList title="Suggestions" items={result.suggestions} />
            </div>
          )}

          {result.diagnostics.length > 0 && (
            <div className="card">
              <h2>Diagnostics</h2>
              {result.diagnostics.map((diagnostic, index) => (
                <div className="diagnostic" key={`${diagnostic.type}-${index}`}>
                  <p>
                    <span className="badge">{diagnostic.section}</span> {diagnostic.explanation}
                  </p>
                  {diagnostic.affected_text && (
                    <p className="diagnostic-fix">
                      <em>{diagnostic.affected_text}</em>
                    </p>
                  )}
                  <p className="diagnostic-fix">
                    <strong>Fix:</strong> {diagnostic.actionable_fix}
                  </p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}
