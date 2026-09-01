"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { useInterview } from "@/hooks/useInterview";

export default function InterviewTextSession() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const interviewId = searchParams.get("interviewId");

  const { status, question, turnNumber, difficulty, submitAnswer, errorMessage, retry } =
    useInterview(interviewId);
  const [answer, setAnswer] = useState("");

  if (!interviewId) {
    return (
      <main className="narrow">
        <h1>Interview</h1>
        <div className="error-banner">No interview was specified.</div>
      </main>
    );
  }

  if (status === "not_found") {
    return (
      <main className="narrow">
        <h1>Interview not found</h1>
        <div className="error-banner">This interview could not be found. It may have expired or the link is invalid.</div>
      </main>
    );
  }

  if (status === "loading" && !question) {
    return (
      <main className="narrow">
        <h1>Interview</h1>
        <p className="progress-label">Loading your interview…</p>
      </main>
    );
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!answer.trim() || status === "submitting") {
      return;
    }
    const succeeded = await submitAnswer(answer.trim());
    if (succeeded) {
      setAnswer("");
    }
  };

  const handleEndInterview = () => {
    router.push(`/results?interviewId=${interviewId}`);
  };

  const submitting = status === "submitting";

  return (
    <main className="narrow">
      <h1>Interview</h1>
      {turnNumber > 0 && (
        <p className="progress-label">
          Question {turnNumber}
          {difficulty ? ` · Difficulty: ${difficulty}` : ""}
        </p>
      )}

      {question && (
        <div className="card">
          <p style={{ fontSize: "1.1rem", fontWeight: 600 }}>{question.question}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <label className="label" htmlFor="answer">
          Your answer
        </label>
        <textarea
          id="answer"
          className="field"
          rows={6}
          value={answer}
          onChange={(event) => setAnswer(event.target.value)}
          disabled={submitting || !question}
          placeholder="Type your answer here…"
        />

        {status === "error" && errorMessage && (
          <div className="error-banner">
            {errorMessage}{" "}
            <button type="button" className="button secondary" onClick={() => retry()}>
              Retry
            </button>
          </div>
        )}

        <p>
          <button type="submit" className="button" disabled={submitting || !answer.trim() || !question}>
            {submitting ? "Submitting…" : "Submit Answer"}
          </button>{" "}
          <button type="button" className="button secondary" onClick={handleEndInterview} disabled={submitting}>
            End Interview
          </button>
        </p>
      </form>
    </main>
  );
}
