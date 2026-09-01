"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError } from "@/services/api/client";
import type { InterviewStateResponse } from "@/services/api/types";
import { getInterview } from "@/services/interview";

type Status = "loading" | "ready" | "error" | "not_found";

export default function ResultsSummary() {
  const searchParams = useSearchParams();
  const interviewId = searchParams.get("interviewId");

  const [status, setStatus] = useState<Status>("loading");
  const [interview, setInterview] = useState<InterviewStateResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
        <p className="progress-label">Loading your results…</p>
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

  return (
    <main className="narrow">
      <h1>Interview complete</h1>
      <p>
        You answered {answeredTurns.length} question{answeredTurns.length === 1 ? "" : "s"} on{" "}
        <strong>{interview.objective}</strong>.
      </p>

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

      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/resume/upload" className="button">
          Start a new interview
        </Link>
      </p>
    </main>
  );
}
