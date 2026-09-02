"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError } from "@/services/api/client";
import type { FinalAssessment, InterviewStateResponse } from "@/services/api/types";
import {
  completeInterview,
  createAssessment,
  getAssessment,
  getInterview,
} from "@/services/interview";

type Status = "loading" | "ready" | "error" | "not_found";
type AssessmentStatus = "idle" | "generating" | "ready" | "error";

function ScoreItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="score-item">
      <div className="score-item-label">{label}</div>
      <div className="score-item-value">{value}</div>
    </div>
  );
}

export default function ResultsSummary() {
  const searchParams = useSearchParams();
  const interviewId = searchParams.get("interviewId");

  const [status, setStatus] = useState<Status>("loading");
  const [interview, setInterview] = useState<InterviewStateResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<FinalAssessment | null>(null);
  const [assessmentStatus, setAssessmentStatus] = useState<AssessmentStatus>("idle");
  const [assessmentError, setAssessmentError] = useState<string | null>(null);

  useEffect(() => {
    if (!interviewId) {
      return;
    }
    let cancelled = false;
    getInterview(interviewId)
      .then((data) => {
        if (!cancelled) {
          setInterview(data);
          setStatus("ready");
        }
        // Show an assessment that was already generated for this interview.
        return getAssessment(interviewId)
          .then((existing) => {
            if (!cancelled) {
              setAssessment(existing);
              setAssessmentStatus("ready");
            }
          })
          .catch(() => {
            // No assessment yet; the page offers to generate one.
          });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const isNotFound = error instanceof ApiError && error.status === 404;
          setStatus(isNotFound ? "not_found" : "error");
          setErrorMessage(error instanceof Error ? error.message : "Something went wrong.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [interviewId]);

  if (!interviewId) {
    return (
      <main className="narrow">
        <h1>Interview complete</h1>
        <div className="error-banner">No interview was specified.</div>
      </main>
    );
  }

  if (status === "loading") {
    return (
      <main className="narrow">
        <h1>Interview complete</h1>
        <p className="progress-label">
          <span className="spinner" aria-hidden="true" />
          Loading your results…
        </p>
      </main>
    );
  }

  if (status === "not_found") {
    return (
      <main className="narrow">
        <h1>Interview not found</h1>
        <div className="error-banner">This interview could not be found.</div>
      </main>
    );
  }

  if (status === "error" || !interview) {
    return (
      <main className="narrow">
        <h1>Interview complete</h1>
        <div className="error-banner">{errorMessage ?? "Something went wrong."}</div>
      </main>
    );
  }

  const answeredTurns = interview.turns.filter((turn) => turn.answer !== null);

  const handleGenerateAssessment = async () => {
    if (assessmentStatus === "generating") {
      return;
    }
    setAssessmentStatus("generating");
    setAssessmentError(null);
    try {
      // The interview must be completed before it can be assessed; completing an
      // already-completed interview is a no-op we can safely ignore.
      try {
        await completeInterview(interviewId);
      } catch (error) {
        if (!(error instanceof ApiError && error.status === 409)) {
          throw error;
        }
      }
      const result = await createAssessment(interviewId);
      setAssessment(result);
      setAssessmentStatus("ready");
    } catch (error) {
      setAssessmentError(error instanceof Error ? error.message : "Something went wrong.");
      setAssessmentStatus("error");
    }
  };

  return (
    <main className="narrow">
      <div className="page-header">
        <h1>Interview complete</h1>
        <p>
          You answered {answeredTurns.length} question{answeredTurns.length === 1 ? "" : "s"} on{" "}
          <strong>{interview.objective}</strong>.
        </p>
      </div>

      {!assessment && (
        <div className="card">
          <h2>Final assessment</h2>
          <p>
            Generate an evidence-based score across technical knowledge, depth, problem solving, and
            communication, aggregated from your answers.
          </p>
          {assessmentStatus === "error" && assessmentError && (
            <div className="error-banner">{assessmentError}</div>
          )}
          <div className="actions">
            <button
              type="button"
              className="button"
              onClick={handleGenerateAssessment}
              disabled={assessmentStatus === "generating" || answeredTurns.length === 0}
            >
              {assessmentStatus === "generating" && <span className="spinner" aria-hidden="true" />}
              {assessmentStatus === "generating" ? "Generating…" : "Generate assessment"}
            </button>
          </div>
          {answeredTurns.length === 0 && (
            <p className="progress-label">Answer at least one question to generate an assessment.</p>
          )}
        </div>
      )}

      {assessment && (
        <div className="card">
          <h2>Final assessment</h2>
          <div className="score-hero">
            <span className="score-value">{assessment.overall_score}</span>
            <span className="score-max">/ 100 overall</span>
          </div>
          <p>{assessment.summary}</p>

          <div className="score-grid">
            <ScoreItem label="Technical knowledge" value={assessment.technical_knowledge} />
            <ScoreItem label="Knowledge depth" value={assessment.knowledge_depth} />
            <ScoreItem label="Problem solving" value={assessment.problem_solving} />
            <ScoreItem label="Communication" value={assessment.communication} />
            {assessment.resume_claim_accuracy !== null && (
              <ScoreItem label="Resume claim accuracy" value={assessment.resume_claim_accuracy} />
            )}
          </div>

          {assessment.strengths.length > 0 && (
            <>
              <h3>Strengths</h3>
              <ul>
                {assessment.strengths.map((strength) => (
                  <li key={strength}>{strength}</li>
                ))}
              </ul>
            </>
          )}

          {assessment.weaknesses.length > 0 && (
            <>
              <h3>Areas to improve</h3>
              <ul>
                {assessment.weaknesses.map((weakness) => (
                  <li key={weakness}>{weakness}</li>
                ))}
              </ul>
            </>
          )}

          <p className="progress-label">
            Based on {assessment.turns_assessed} answered question
            {assessment.turns_assessed === 1 ? "" : "s"}.
          </p>
        </div>
      )}

      {interview.knowledge_state.summary && (
        <div className="card">
          <h2>Summary</h2>
          <p>{interview.knowledge_state.summary}</p>
        </div>
      )}

      {interview.knowledge_state.concept_states.length > 0 && (
        <div className="card">
          <h2>Concepts covered</h2>
          {interview.knowledge_state.concept_states.map((concept) => (
            <p key={concept.concept}>
              {concept.concept}{" "}
              <span className={`badge confidence-${concept.confidence}`}>{concept.confidence} confidence</span>
            </p>
          ))}
        </div>
      )}

      {interview.knowledge_state.claim_verifications.length > 0 && (
        <div className="card">
          <h2>Resume claims investigated</h2>
          {interview.knowledge_state.claim_verifications.map((claim) => (
            <p key={claim.claim_id ?? claim.claim_text}>
              {claim.claim_text} <span className={`badge status-${claim.status}`}>{claim.status}</span>
            </p>
          ))}
        </div>
      )}

      {answeredTurns.length > 0 && (
        <div className="card">
          <h2>Transcript</h2>
          {answeredTurns.map((turn) => (
            <div className="transcript-turn" key={turn.id}>
              <p className="question">Q{turn.turn_number}: {turn.question.question}</p>
              <p className="answer">{turn.answer}</p>
            </div>
          ))}
        </div>
      )}

      <div className="actions">
        <Link href="/resume/upload" className="button">
          Start a new interview
        </Link>
      </div>
    </main>
  );
}
